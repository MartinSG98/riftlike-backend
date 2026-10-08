# 0004. A run is one JSON document

Date: 2026-10-08
Status: Accepted

## Context

A run has a lot of nested state: five roster slots, a generated map with its nodes and the path walked so far, the current opponent and their lineup, the bracket position, the match history and whichever step is waiting for the player. Modelling all of that relationally means a table per concept and joins on every request, for data that is only ever read and written as a whole.

## Decision

The run state is a tree of Pydantic models, and the database stores it as one JSON column in a single `run` table in SQLite, through SQLModel. A few fields are copied out next to it (team, stage, result, timestamps) so the list of recent runs can be queried and sorted without opening every document. Each request loads the document, applies one action and writes it back.

## Consequences

The engine works on plain typed objects with no persistence code in it, and adding a field to the game is a model change with no migration. The same models validate what comes back from the database and describe the API in the OpenAPI schema. What this gives up is querying inside runs, for example "every run where Faker played Azir", which would need a scan or a separate analytics table. Older saved runs stay readable as long as new fields have defaults. A breaking change to the shape would need a version field and an upgrade step, which is not there yet.
