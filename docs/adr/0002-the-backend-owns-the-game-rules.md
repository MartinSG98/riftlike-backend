# 0002. The backend owns the game rules

Date: 2026-10-08
Status: Accepted

## Context

A single-player browser game can run entirely in the browser, with a server that only stores saves, or the server can run the game and the browser only draws it. Riftlike has a fair amount of logic: champion power curves, signature and synergy bonuses, map generation, a double elimination Play-In, a Swiss stage and opponents that draft differently as the run goes on.

## Decision

The game runs in a FastAPI service written in Python. The client sends one action at a time (enter a node, pick a champion, swap two roles, continue) and gets the whole run back. Everything the screens need that depends on the rules is computed on the server too: each champion's power with its breakdown, which map nodes are reachable, and for every offered champion the power it would have in each role and how the team total would change.

## Consequences

The rules exist in exactly one place, written once and tested with plain pytest, with no TypeScript copy that could drift. Invalid moves are rejected by the server with a 409 and a reason, so a modified client cannot cheat its way through a run, which matters if results are ever shown to other people. The price is a round trip per action and a bigger response, both small for a turn-based game on localhost. Hover previews on the pick screen would need a request per hover if they were computed lazily, so the server precomputes them for all offers and roles up front instead.
