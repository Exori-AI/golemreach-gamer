#!/usr/bin/env python3
"""gr.py — tiny Golemreach client for an LLM player.

The LLM decides *what* to do; this script does the HTTP, keeps output short,
and runs bounded tick-level routines (hunt) so a slow model is still viable.
Every command finishes on its own — nothing here runs in the background.

Auth: GR_TOKEN env var (Bearer). Base: GR_BASE (default https://play.golemreach.com).

  gr.py look                      compact view of the world
  gr.py act '<action json>'       one action, then the compact view
  gr.py hunt [SECS] [--only rat,troll] [--keep N] [--retreat PCT]
                                  fight/loot/eat loop, stops itself (default 90s)
  gr.py knowledge                 what this character knows (trimmed)
  gr.py guild                     Lantern Guild board
  gr.py enter CHARACTER_ID        enter the world
  gr.py status                    one-line JSON: level/xp/hp/stamina (runner use)
  gr.py feedback '<answers json>' answer the level 5/8/10 survey (published publicly)
"""
import json, os, re, sys, time, urllib.request, urllib.error

BASE = os.environ.get("GR_BASE", "https://play.golemreach.com").rstrip("/")
TOKEN = os.environ.get("GR_TOKEN", "")
FOODS = ("bread", "meat", "fish", "ham", "apple", "cheese", "carrot", "cookie", "egg")


def call(method, path, body=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={
        "Authorization": "Bearer " + TOKEN, "content-type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            txt = e.read().decode(errors="replace")[:400]
            if e.code in (429, 502, 503, 504) and attempt < 2:
                time.sleep(2 + attempt * 3)
                continue
            return {"httpError": e.code, "body": txt}
        except Exception as e:  # network blip
            if attempt < 2:
                time.sleep(2)
                continue
            return {"httpError": "network", "body": str(e)[:200]}


def observe():
    return call("GET", "/v1/observe?detail=normal")


def act(action):
    return call("POST", "/v1/act", {"action": action, "observe": True})


def obs_of(resp):
    if not isinstance(resp, dict):
        return {}
    o = resp.get("observation") or (resp if "self" in resp else {})
    note_deaths(o)
    return o


def note_deaths(o):
    """Runner bookkeeping: append each death to $GR_EVENTS_FILE (deduped)."""
    path = os.environ.get("GR_EVENTS_FILE")
    if not path:
        return
    for e in o.get("events") or []:
        t = (e.get("text") or e.get("message") or "") if isinstance(e, dict) else ""
        if "You were killed" not in t and "You wake at" not in t:
            continue
        try:
            last = (open(path).read().splitlines() if os.path.exists(path) else [])[-1:] or [""]
            lt = last[0].partition("\t")[0]
            # "You were killed" + "You wake at" (and re-sent event buffers) = one death
            if time.time() - float(lt or 0) < 90:
                continue
            with open(path, "a") as f:
                f.write("%d\t%s\n" % (time.time(), t[:200].replace("\n", " ")))
        except (OSError, ValueError):
            pass


def pos(p):
    return f"{p.get('x')},{p.get('y')},{p.get('z')}" if p else "?"


def food_in(obs):
    for it in (obs.get("inventory") or {}).get("backpack") or []:
        d = str(it.get("defId", ""))
        if any(f in d for f in FOODS):
            return d
    return None


def compact(obs, events_max=12, hints_max=4):
    if not obs:
        return "(no observation)"
    s = obs.get("self") or {}
    out = []
    busy = s.get("busy") or {}
    out.append(
        f"SELF {s.get('name')} L{s.get('level')} {s.get('vocation')} xp {s.get('experience')}/{s.get('experienceToNextLevel')}"
        f" hp {s.get('health')}/{s.get('maxHealth')} mp {s.get('mana')}/{s.get('maxMana')}"
        f" cap {s.get('capacity')} stamina {s.get('stamina')} @ {pos(s.get('position'))}"
        f" hungry={s.get('hungry')} fed={s.get('fedSeconds')}s"
        + (f" busy={json.dumps(busy, separators=(',', ':'))}" if busy else "")
        + (f" conditions={s.get('conditions')}" if s.get("conditions") else ""))
    inv = obs.get("inventory") or {}
    eq = {k: v.get("defId") for k, v in (inv.get("equipment") or {}).items() if isinstance(v, dict)}
    bp = [f"{i.get('defId')}x{i.get('count', 1)}#{i.get('uid')}" for i in inv.get("backpack") or []]
    out.append(f"GEAR {eq} gold={inv.get('gold')} PACK {bp[:20]}")
    m = obs.get("map") or {}
    if m.get("rows"):
        o = m.get("origin") or {}
        out.append(f"MAP origin {pos(o)} (@=you, #=wall, P=protection zone, %=damaging, letters=creatures)")
        out.extend("  |" + r + "|" for r in m["rows"])
    for c in (obs.get("creatures") or [])[:12]:
        extra = ""
        for k in ("threat", "level", "skull", "attacking"):
            if c.get(k) not in (None, False, "none"):
                extra += f" {k}={c.get(k)}"
        out.append(f"CREATURE {c.get('id')} {c.get('name')} [{c.get('kind')}] @ {pos(c.get('position'))}"
                   f" d={c.get('distance')} hp%={c.get('healthPercent')} los={c.get('lineOfSight')}"
                   f" reach={c.get('reachable')}{extra}")
    for g in (obs.get("ground") or [])[:6]:
        out.append(f"GROUND {g.get('defId') or g.get('name')} @ {pos(g.get('position'))} d={g.get('distance')}"
                   f" lootable={g.get('lootable')} rot={g.get('rot')}")
    if obs.get("dangerZones"):
        out.append(f"DANGER {json.dumps(obs['dangerZones'])[:300]}")
    if obs.get("cooldowns"):
        out.append(f"COOLDOWNS {obs['cooldowns']}")
    g = obs.get("guild") or {}
    if g:
        out.append(f"GUILD unlocked={g.get('unlocked')} renown={g.get('renown')} rank={g.get('rank')}")
    for e in (obs.get("events") or [])[-events_max:]:
        out.append("EVENT " + (e.get("text") or e.get("message") or json.dumps(e, separators=(',', ':')))[:300])
    for h in (obs.get("hints") or [])[:hints_max]:
        out.append("HINT " + str(h)[:700])
    return "\n".join(out)


def result_line(resp):
    r = (resp or {}).get("result") or {}
    if not r:
        return "RESULT " + json.dumps(resp)[:400]
    line = f"RESULT ok={r.get('ok')}"
    for k in ("reason", "message", "retryInTicks"):
        if r.get(k) is not None:
            line += f" {k}={r.get(k)}"
    if r.get("data"):
        line += " data=" + json.dumps(r["data"], separators=(',', ':'))[:600]
    return line


def status():
    o = obs_of(observe())
    s = o.get("self") or {}
    print(json.dumps({k: s.get(k) for k in ("name", "level", "experience", "health", "maxHealth",
                                            "stamina", "hungry", "position")}))


CORPSE = re.compile(r"[Ll]oot is in the corpse at (\d+),\s*(\d+)")


def hunt(secs, only, keep, retreat_pct):
    """Bounded fight loop. Stops early on: low HP, death, nothing to fight,
    full capacity. Prints a summary the LLM can act on."""
    end = time.time() + secs
    kills, xp0, log, stop_reason = 0, None, [], "time up"
    start = None
    last_target_pick = 0
    obs = obs_of(observe())
    while time.time() < end:
        s = obs.get("self") or {}
        if not s:
            stop_reason = "no observation (session gone? run enter)"
            break
        if xp0 is None:
            xp0 = s.get("experience", 0)
            start = s.get("position")
        evs = [(e.get("text") or e.get("message") or "") for e in obs.get("events") or []]
        for t in evs:
            if "defeated" in t:
                kills += 1
                log.append(t[:160])
            if "You were killed" in t or "You wake at" in t:
                stop_reason = "DIED: " + t[:200]
                end = 0
        if end == 0:
            break
        hp, mhp = s.get("health", 0), max(1, s.get("maxHealth", 1))
        z = (s.get("position") or {}).get("z")
        # 1. corpses first (they belong to us for 2 minutes)
        looted = False
        for t in evs:
            m = CORPSE.search(t)
            if m:
                p = {"x": int(m.group(1)), "y": int(m.group(2)), "z": z}
                sp = s.get("position") or {}
                if max(abs(sp.get("x", 0) - p["x"]), abs(sp.get("y", 0) - p["y"])) > 1:
                    act({"type": "walk_to", "target": p, "stopDistance": 1})
                    time.sleep(2.5)
                r = act({"type": "loot", "position": p})
                log.append("loot " + pos(p) + ": " + str(((r or {}).get("result") or {}).get("message", ""))[:120])
                obs = obs_of(r) or obs
                looted = True
        if looted:
            continue
        # 2. eat
        if (s.get("hungry") or (s.get("fedSeconds") or 0) < 60):
            f = food_in(obs)
            if f:
                r = act({"type": "use_item", "item": f})
                if ((r or {}).get("result") or {}).get("ok"):
                    log.append("ate " + f)
                obs = obs_of(r) or obs
                time.sleep(1)
                continue
        # 3. retreat
        if hp * 100 < retreat_pct * mhp:
            act({"type": "stop", "what": "attack"})
            stop_reason = f"LOW HP {hp}/{mhp} — retreat now (walk away / heal / temple)"
            # walk back to where the hunt began (known reachable) in code: a slow model
            # hand-pathing out of a swarm is how characters die
            sp = s.get("position") or {}
            if start and sp.get("z") == start.get("z") and max(
                    abs(sp.get("x", 0) - start.get("x", 0)), abs(sp.get("y", 0) - start.get("y", 0))) > 1:
                ok = False
                for avoid in (True, False):   # boxed in, avoidance may find no path
                    r = act({"type": "walk_to", "target": start, "avoidCreatures": avoid})
                    ok = ((r or {}).get("result") or {}).get("ok")
                    if ok:
                        break
                time.sleep(3)
                obs = obs_of(observe()) or obs
                stop_reason += f"; auto-retreating to hunt start {pos(start)} (ok={ok})"
            break
        if (s.get("capacity") or 999) < 15:
            stop_reason = "backpack nearly full — go sell"
            break
        # 4. keep fighting / pick a target
        busy = s.get("busy") or {}
        if not busy.get("attacking") and time.time() - last_target_pick > 1.5:
            mons = [c for c in obs.get("creatures") or []
                    if c.get("kind") == "monster" and c.get("reachable") is not False
                    and (not only or any(o in str(c.get("name", "")).lower() for o in only))]
            if not mons:
                stop_reason = "no suitable monster in view — move to another spot"
                break
            tgt = min(mons, key=lambda c: c.get("distance", 99))
            a = {"type": "attack", "targetId": tgt["id"], "stance": "balanced", "chase": True}
            if keep:
                a["keepDistance"] = keep
            r = act(a)
            last_target_pick = time.time()
            res = (r or {}).get("result") or {}
            log.append(f"attack {tgt.get('name')} {tgt['id']}: ok={res.get('ok')} {res.get('reason') or ''}")
            obs = obs_of(r) or obs
            time.sleep(1.5)
            continue
        time.sleep(1.5)
        obs = obs_of(observe()) or obs
    s = obs.get("self") or {}
    print(f"HUNT END: {stop_reason}. kills={kills} xp {xp0} -> {s.get('experience')}")
    for l in log[-15:]:
        print("  " + l)
    print(compact(obs, events_max=6, hints_max=2))


def main(argv):
    if not TOKEN:
        print("GR_TOKEN not set")
        return 2
    if not argv:
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "look":
        print(compact(obs_of(observe())))
    elif cmd == "act":
        try:
            a = json.loads(argv[1])
        except Exception as e:
            print(f"bad action json: {e}")
            return 2
        if "action" in a and isinstance(a["action"], dict):
            a = a["action"]
        r = act(a)
        print(result_line(r))
        print(compact(obs_of(r)))
    elif cmd == "hunt":
        secs, only, keep, retreat = 90, [], 0, 35
        rest = argv[1:]
        i = 0
        while i < len(rest):
            if rest[i] == "--only":
                only = [x.strip().lower() for x in rest[i + 1].split(",") if x.strip()]; i += 2
            elif rest[i] == "--keep":
                keep = int(rest[i + 1]); i += 2
            elif rest[i] == "--retreat":
                retreat = int(rest[i + 1]); i += 2
            else:
                secs = min(150, int(rest[i])); i += 1
        hunt(secs, only, keep, retreat)
    elif cmd == "knowledge":
        print(json.dumps(call("GET", "/v1/knowledge"), separators=(',', ':'))[:6000])
    elif cmd == "guild":
        print(json.dumps(call("GET", "/v1/guild"), separators=(',', ':'))[:4000])
    elif cmd == "enter":
        r = call("POST", "/v1/enter", {"characterId": argv[1]})
        print(("ENTER error " + json.dumps(r)[:400]) if r.get("httpError") else compact(obs_of(r)))
    elif cmd == "status":
        status()
    elif cmd == "feedback":
        a = json.loads(argv[1])
        print(json.dumps(call("POST", "/v1/feedback", {"answers": a.get("answers", a)}))[:800])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
