# 0005. Balance tuned with a bot simulation

Date: 2026-10-08
Status: Accepted

## Context

The difficulty of a run comes from many numbers working together: XP for lane fights and matches, the level the world is at on each match day, the bonus for skipping Swiss days, how often opponents bring signature champions and how well they draft. Changing one by hand and playing a few runs says very little, since a single run is mostly luck.

## Decision

The repo ships a small simulation, `scripts/simulate.py`, that plays a few hundred runs per team with a greedy bot. The bot takes the champion that raises team power the most, prefers picks while roles are empty and only takes lane fights it should win. The script prints how far the runs got. Every balance number in the engine was set by changing it and rerunning the simulation, and the diagnostics compared average team power and level per stage on both sides.

## Consequences

Balance changes are measured instead of guessed. The first version let the bot win the whole event in about 80 percent of runs, an over-correction got it down to 4 percent, and the current numbers land between roughly 8 and 16 percent for main-stage teams, with about half of the Play-In teams going out before the Swiss stage. The limit is that the bot is not a person. It ignores duo synergy when choosing where to walk and never swaps roles, so a thoughtful player should do better than these numbers, which is the intent.
