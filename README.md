# golemreach-gamer

An LLM player for [Golemreach](https://golemreach.com), a real-time (10 ticks/s) MMORPG built for AI agents.
A party of four on one runner: **Vallum** (knight), **Adori** (paladin), **Favilla** (sorcerer) and **Silva** (druid).

## How it plays
- `gamer/run.sh` — the runner. Each character runs its own loop, concurrently, with staggered starts
  (`GAMER_STAGGER_SECONDS`, default 30 min; `GAMER_MAX_CONCURRENT`, default 4). A character plays a bounded
  window (default 2 h), then rests offline (stamina only recovers while logged out). Inside a window it loops agent sessions
  until the window ends, then a short wrap-up session parks the character in town.
- `gamer/gr.py` — tiny stdlib HTTP client the model calls: compact views, single actions, and a bounded
  `hunt` routine that fights, loots, eats and retreats on its own. A slow or cheap model stays viable
  because tick-level work happens in code, decisions happen in the model. Nothing runs in the background.
- After each window a cheap **coach** model reads the window transcript and rewrites the character's
  notebooks (goals, gotchas, playbook, atlas), which the next window starts from.
- `gamer/WORLD_FACTS.md` — shared rules of the world; `gamer/strategy-<slot>.md` — per-character persona.

## Two models, same characters
Each window is split between a **Codex** session (`gpt-5.6-terra` via the `codex` CLI) and a
**free-tier open model** (NVIDIA-hosted, through the hermes agent) on the same character. The order
alternates per window: odd windows start on Codex, even windows play the first half on the free model,
so neither arm always gets the freshly rested character. When Codex is out of usage the free model plays
the rest; if the limit message names its reset time, the Codex arm is held until then. Errors never
loop: two failed or four short sessions in a row end the Codex arm for that window.
On the free model, characters take turns over `GAMER_FREE_MODELS` (slot i plays model i mod n), so one
overloaded model doesn't rate-limit the whole party. A rate-limited session backs off 2-5 min
(jittered), and hermes falls back through `GAMER_FALLBACK_MODELS` (space-separated NVIDIA model ids,
written into the hermes config at startup).

- `codex/dispatch.sh` — runs on the host (cron, every minute). The runner container drops a request file
  per character into a shared queue; the dispatcher claims it atomically and starts one throwaway
  `codex/Dockerfile` container per window (non-root, no capabilities, memory/pid limits, max 2 at once).
  The Codex login is copied in, never mounted; the game key is passed as env, never in argv.
- `codex/play.sh` — inside that container: loops `codex exec` sessions until the window ends and
  writes a readable transcript (`codex_digest.py`) for the coach.
- Every model segment of a window is one row in `MODEL_WINDOWS.tsv` (character, model, start/end,
  online minutes, level/XP before and after, deaths, sessions, stalls, errors; the note carries window
  number and order), so the two models can be compared per character on XP per online hour, deaths per
  hour and stall rate, stratified by order.

## Config
All secrets live in a local, git-ignored `.env`:
```
GAMER_BASE_URL=https://play.golemreach.com
GAMER_SLOTS=vallum adori favilla silva
GAMER_CODEX=on            # off = free model only
GAMER_FREE_MODELS=...     # optional: NVIDIA model ids the slots take in turn
GAMER_DEATH_STOP=3        # end a window early after this many deaths (0 = never)
GAMER1_API_KEY=...        GAMER1_CHARACTER_ID=...
...                       (one GAMERn_ pair per slot, in GAMER_SLOTS order)
```

## License
MIT
