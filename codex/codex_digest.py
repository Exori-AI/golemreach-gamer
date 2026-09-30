#!/usr/bin/env python3
"""Digest `codex exec --json` events (stdin) into a compact transcript (stdout)
for the coach, in the same spirit as gamer/transcript_digest.py.
argv[1] (optional): file to write one summary line to:
  commands=N in_tokens=N out_tokens=N errors=N"""
import json, sys

OUT_CAP = 1500
cmds = errs = tin = tout = 0
for line in sys.stdin:
    try:
        ev = json.loads(line)
    except ValueError:
        continue
    t = ev.get("type", "")
    it = ev.get("item") or {}
    if t == "item.completed" and it.get("type") == "agent_message":
        print("ASSISTANT: " + (it.get("text") or "").strip())
    elif t == "item.completed" and it.get("type") == "command_execution":
        cmds += 1
        out = it.get("aggregated_output") or ""
        if len(out) > OUT_CAP:
            out = out[:OUT_CAP] + "\n...[cut %d chars]" % (len(out) - OUT_CAP)
        print("$ %s  (exit %s)\n%s" % (it.get("command", ""), it.get("exit_code"), out.rstrip()))
    elif t in ("error", "turn.failed"):
        errs += 1
        msg = ev.get("message") or (ev.get("error") or {}).get("message") or json.dumps(ev)[:300]
        print("ERROR: " + str(msg)[:500])
    elif t == "turn.completed":
        u = ev.get("usage") or {}
        tin += u.get("input_tokens", 0)
        tout += u.get("output_tokens", 0)
if len(sys.argv) > 1:
    with open(sys.argv[1], "w") as f:
        f.write("commands=%d in_tokens=%d out_tokens=%d errors=%d\n" % (cmds, tin, tout, errs))
