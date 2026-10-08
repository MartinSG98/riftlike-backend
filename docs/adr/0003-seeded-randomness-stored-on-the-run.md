# 0003. Seeded randomness stored on the run

Date: 2026-10-08
Status: Accepted

## Context

A roguelike lives on randomness: which champions are offered, which lanes the map fights in, which opponent comes next and what they draft. If the server rolled with a global random module, reloading the page in the middle of a pick could produce different offers, and a lost match could be retried by refreshing until it came out differently. It would also make the engine hard to test, since the same inputs would not give the same run.

## Decision

Every run carries its own generator state, a single 32 bit integer driving a Mulberry32 generator, stored with the rest of the run. A run is created from a random seed and every draw advances the stored state. Outcomes are computed at the moment a step starts and saved on the run as the pending step, so a fight or a match is already decided when the player first sees it and the screen only plays it back.

## Consequences

Reloading always shows the same offers and the same result, and there is nothing to gain from refreshing. The same seed and the same choices replay the exact same run, which is what the determinism test checks and what makes the bot simulation repeatable. Mulberry32 is not cryptographic and does not need to be. The one thing to watch is that any new random draw changes every draw after it for a given seed, so saved runs from before such a change continue fine but replays of old seeds will diverge.
