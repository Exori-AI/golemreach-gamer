# Golemreach world facts — shared by every character on this runner

Real-time MMORPG in the Tibia tradition, 10 ticks/s. World Aethermoor = the starter island Efidia (levels 1-10:
one town, sewer, cellars, beach, shoals, caves west/east/south) + the mainland (three cities, reached ONE WAY at level 10).
Efidia monsters: troll, goblin, rat, cave rat, wolf, bear, snake, spider, bug, one rotworm. The mainland has more.
Goal: as much experience as possible WITHOUT dying. Acting faster never helps — cooldowns gate everything.

## Hunger and healing (the #1 trap)
- `hungry=True` → NOTHING regenerates (hp, mana). Eat: act '{"type":"use_item","item":"bread"}'.
- A loaf ≈ 4 min fed time; stacks to 20 min max. Eat whenever fed < 60s. `hunt` eats for you if food is in the pack.
- Protection zones (P tiles: temple, depot) never heal. Step outside to regenerate.
- Fast heal: say the incantation `exura` (act '{"type":"say","text":"exura"}') or cast light_healing.
- Brother Aldwin (temple): "heal me" = free full heal out of combat (old guide; the 10-29 guide no longer lists it — if he ignores you, eat and rest outside). "bless me all" = every blessing you can afford (20+18×level gold each); "blessings" = what you hold.
- Broke and hungry at level ≤7 with <10 gold: walk within 3 tiles of Brother Pitt, say "relief" (2 bread + basic gear, every 10 min).

## Fighting
- Survive rule: health ÷ total threat = seconds alive doing nothing. Under ~15 s → walk away.
- Retreat at 35% hp, not 15%. `hunt` stops itself below --retreat (default 35; at L10+ never under 50).
- Death on Efidia (Island Grace): levels 1-4 lose nothing; levels 5-9 lose 3% xp (never below the level floor), nothing else.
  **Grace ENDS at level 10**: from L10 a death on Efidia costs the full mainland price below (~1,000 xp at L10,
  skills, items). At L10+ retreat at 50% hp, never fight hungry, and keep blessings up when gold allows (200 each at L10).
- Death on the mainland: −10% xp (you CAN lose a level), −10% skill progress, each item 10% drop chance (5% at L10-19).
  Blessings soften it (see below). `observation.lastDeath` lists the killer, damage by type and what you lost.
- After any death you wake at the temple healed but HUNGRY, inside a protection zone: eat, then step outside.
- Server-side reflexes (set once per window, up to 12 rules):
  act '{"type":"set_combat_rules","rules":[{"condition":{"type":"self_hp_below","percent":55},"effect":{"type":"cast_spell","spell":"light_healing"}}]}'
- Stances: offensive (dmg ×1, def ×0.5), balanced (×0.75/×0.75), defensive (×0.5/×1).
- Groups kill. Fight one at a time. Camping a cleared spawn: it is suppressed within 9 tiles — walk a lap.
- Creature ids die with the creature; always use ids from the latest view.

## Loot and money
- Kill event: "Loot is in the corpse at X,Y" — loot from on/next to that tile (`hunt` does it). Corpse is yours for ~2 min.
- Sell junk (rat tails etc.) to the general store: act '{"type":"trade","npcId":"<id>","operation":"sell","itemId":"rat_tail","count":12}'.
- Bank gold at the bank clerk (banked gold survives death). Never buy cosmetics, never send gold/items to other players.

## Moving
- walk_to does the pathing: act '{"type":"walk_to","target":{"x":X,"y":Y,"z":Z},"stopDistance":1}'. Diagonal steps cost 3×. A partial cross-floor walk is normal — re-issue it.
- Creatures block tiles; `push` moves a creature to a free non-damaging tile.
- `%` tiles hurt (monsters won't cross them). Monsters cannot enter P tiles or cross the warded town bridges.

## Talking to NPCs
- Plain chat reaches NPCs within 3 tiles: act '{"type":"say","text":"where can I hunt?"}'.
- Ask EVERY new NPC "where can I hunt?" and "have you got a job for me?". Asking = accepting a quest.
- Reply `data.topic` empty = you weren't understood; rephrase.
- There is no public atlas: `gr.py knowledge` shows only grounds/places YOU have visited or been told about.
- Lantern Guild (`gr.py guild`) offers short expeditions with a ready `nextAction`; rewards when back in a protection zone.

## Session rules
- 10 minutes without a real action (observe/look don't count) → disconnected. Keep acting.
- There is NO stamina and NO rested bonus (since 10-29). Kill xp never depends on time played or away.
- Levels 5, 8, 10: a feedback_request event. Answer honestly with gr.py feedback '{"enjoying":"...","difficulty":"...","repetitive":"...","satisfying":"...","struggling":"..."}' — it is published with your name.
- Tutorial (new character): push Corporal Ansel north/south, cross the burning doorway, kill the rat, walk_to the stairs, lose to the cyclops on purpose, then at the temple say "kit" to Brother Pitt, ask him where to hunt and for a job, eat. The HINT lines give exact actions.

## Leaving the island (level 10+)
- `observation.island` = Ferry Token {onIsland, notches{have,need:10}, ferryReady}. One notch per level.
- From level 13, kill xp on Efidia is HALVED. Plan to cross around level 12.
- The crossing is ONE WAY: afterwards Efidia answers `island_closed`. Before it, mainland ground answers `not_crossed`.
- How: stand by Old Cassian on the quay (551,460), act talk/say `passage`, pick a city from his `data.choices`,
  confirm with the keyword he names (`aye`). ~30 s of voyage_line events, then voyage_end with your new home town.
- You arrive as Islander with 1 free blessing, 200 gold, 5 red draughts, local food, the city chart and a keepsake.
- Cities: Brecca (west, hunting, Lantern Guild hall, Root Cellars 12-20), Kaldera (north, mining/smithing,
  Furnace Caves 12-22), Coralis (south, fishing/cooking/trade, Cisterns 12-20). All fine for any vocation.
- Before crossing: bank or carry gold, and at the temple say "bless me all" (20+18×level gold each, carried gold).
  Each blessing: −10% of the xp loss, −20% of skill loss and drop chance. All five: a death costs 5% xp, no skill,
  no equipment (backpack still rolls). A death spends every blessing it softened — rebuy after each death.
- Keepsake of the Ninth (neck): keeps all items on one death, then shatters. Nothing for xp/skills.
- Mainland ferries between cities cost 60-120 gold; each city has its own depot.
