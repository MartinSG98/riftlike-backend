# 0006. Synergies by archetype

Date: 2026-10-09
Status: Accepted

## Context

Duo synergy was a list of 53 hand-picked champion pairs. That covers the famous duos, Xayah and Rakan, Kalista and Renata, but almost nothing else: only about 7 percent of random lineups had any synergy at all, and the bot lane, where synergy counts triple, had 35 of 648 possible pairs. Playtesting showed it as a rule that exists on paper and almost never shows up. Real duo win rates per patch would be the proper source, but there is no such data in this project.

## Decision

Keep the hand-picked pairs and add archetype synergies on top. An archetype names a pair of slots and what each champion in them has to be, by class and focus, and gives +1 before the usual weighting for the pair. Eight archetypes cover the main ideas: lane bullies and all-in lanes (early marksman with an engage support), protect the carry (late marksman with an enchanter), poke lanes, early skirmishes and engage with follow-up between jungle and mid, side lane pressure between top and jungle, and a top lane frontline for a late carry. A hand-picked pair always takes precedence, so a named duo never stacks with an archetype and a known bad pair stays bad. Bonuses carry the archetype's name in their label, and every lineup in the run view lists its active synergies so the client can show them.

## Consequences

About 56 percent of random lineups now have at least one synergy, and building around one is a real choice when picking. Opponents use the same rules when they draft, so they get more synergy too, and the XP numbers were retuned against the bot simulation to keep a title run around 10 to 15 percent for main-stage teams. The rules are coarse. Class and focus do not know that a particular enchanter and a particular marksman are a poor match, which is what the hand-picked list is for. Adding a new archetype is one line in `app/game/data.py`.
