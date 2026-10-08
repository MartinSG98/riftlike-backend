# 0007. Signature champions from career data

Date: 2026-10-09
Status: Accepted

## Context

Every player had five signature champions. 37 well-known players had lists written by hand, and the other 58 got five champions drawn at random from their role's pool. Playtesting found both halves lacking. The hand-written lists missed obvious picks, BrokenBlade without Kled for example, and the random lists meant nothing at all. With 157 champions in the game, five per player also made signature bonuses rare.

Leaguepedia's Cargo API was the first choice as a source, since it holds every professional game. In practice it rate limits anonymous queries so hard that not a single request got through, and using it properly would need a bot account.

## Decision

Signature champions come from each player's professional career as counted by gol.gg. `scripts/fetch_signatures.py` reads the current season's player list to find each rostered player, opens their career page across all seasons, takes the number of games on every champion, keeps the ten most played that exist in the game's pool, and writes them to `app/game/signatures.json`, which is committed. The bonus goes down the list as +5, +4, +3, +3, +2, +2, +1, +1, +1, +1. The hand-written lists remain only as a fallback for a player the data has nothing for, and the random lists only for a player in neither.

## Consequences

Signatures now match what each player actually plays, and every player has up to ten of them, so building around a player's comfort picks is a real option on most rosters, for opponents as much as for the player. A rookie with few games has a shorter list, which is accurate. The data is a snapshot. When rosters change, or after a season, the script has to be run again, which takes about five minutes since it waits a few seconds between requests. The script reads public pages and depends on their markup, so a redesign on gol.gg would mean updating two regular expressions. The counts come from gol.gg, and the README credits it.
