# 0001. Two separate repos

Date: 2026-10-08
Status: Accepted

## Context

Riftlike is a browser game with a server behind it. The game rules, the saved runs and the API are one concern, the screens the player clicks through are another. They could share a monorepo or live apart.

## Decision

Two repos. `riftlike-backend` holds the FastAPI service with the game engine, and `riftlike-ui` holds the React client. Both sit next to each other locally under one parent folder, the same layout as the other projects in this portfolio.

## Consequences

Each repo reads on its own and has its own history, which suits a portfolio where someone may only open one of them. The cost is that a change to the API shape needs a matching change in the client without a shared commit to tie them together. The client keeps a hand-written copy of the response types for that reason, and the two run on different ports, so the backend has to allow the client's origin through CORS.
