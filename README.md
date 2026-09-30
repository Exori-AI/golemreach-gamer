# golemreach-gamer

An LLM player for [Golemreach](https://golemreach.com), a real-time (10 ticks/s) MMORPG built for AI agents.
A party of four on one runner: **Exori** (knight), **Adori** (paladin), **Tibianus** (sorcerer) and **Silva** (druid).

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

Play uses free-tier open models, not a paid frontier model.

## Config
All secrets live in a local, git-ignored `.env`:
```
GAMER_BASE_URL=https://play.golemreach.com
GAMER_SLOTS=exori adori tibianus silva
GAMER1_API_KEY=...        GAMER1_CHARACTER_ID=...
...                       (one GAMERn_ pair per slot, in GAMER_SLOTS order)
```

## License
MIT
