# Golemreach world facts — shared by every character on this runner

Real-time MMORPG in the Tibia tradition, 10 ticks/s. One world (Efidia): one town, caves, islands.
Monsters: troll, goblin, rat, cave rat, wolf, bear, snake, spider, bug, one rotworm. Nothing else.
Goal: as much experience as possible WITHOUT dying. Acting faster never helps — cooldowns gate everything.

## Hunger and healing (the #1 trap)
- `hungry=True` → NOTHING regenerates (hp, mana). Eat: act '{"type":"use_item","item":"bread"}'.
- A loaf ≈ 4 min fed time; stacks to 20 min max. Eat whenever fed < 60s. `hunt` eats for you if food is in the pack.
- Protection zones (P tiles: temple, depot) never heal. Step outside to regenerate.
- Fast heal: say the incantation `exura` (act '{"type":"say","text":"exura"}') or cast light_healing.
- Brother Aldwin (temple): "heal me" = free full heal out of combat. "bless me" = blessings (20+18×level gold each).
- Broke and hungry at level ≤7 with <10 gold: walk within 3 tiles of Brother Pitt, say "relief" (2 bread + basic gear, every 10 min).

## Fighting
- Survive rule: health ÷ total threat = seconds alive doing nothing. Under ~15 s → walk away.
- Retreat at 35% hp, not 15%. `hunt` stops itself below --retreat (default 35).
- Death: −10% xp, −10% skill progress, 10% chance per item to drop, −60 stamina, wake at temple healed but hungry.
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
- Stamina: −1/min online, recovers only offline. >2400 kill xp ×1.5, ≤840 kill xp halved. The runner schedules rest.
- Levels 5, 8, 10: a feedback_request event. Answer honestly with gr.py feedback '{"enjoying":"...","difficulty":"...","repetitive":"...","satisfying":"...","struggling":"..."}' — it is published with your name.
- Tutorial (new character): push Corporal Ansel north/south, cross the burning doorway, kill the rat, walk_to the stairs, lose to the cyclops on purpose, then at the temple say "kit" to Brother Pitt, ask him where to hunt and for a job, eat. The HINT lines give exact actions.
