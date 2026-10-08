# Riftlike backend

FastAPI backend for Riftlike, the 2026 League of Legends World Championship played as a roguelike. Pick one of the 19 teams at Worlds, walk a map on every match day to level champions and draft new ones, and see how far the roster gets before it loses once too often.

This repo holds the API and the whole game engine. The browser client lives in [riftlike-ui](https://github.com/MartinSG98/riftlike-ui) and only draws what this service returns.

Architecture decisions are recorded in [docs/adr](docs/adr/README.md), one numbered file per decision.

## How a run goes

1. Pick a team. Main-stage teams start in the Swiss stage, Play-In teams start one step earlier in a four-team bracket.
2. Choose the first champion for one of your players from an early, a mid and a late game option.
3. Every match day is a map. Walk it from top to bottom. Lane fights give XP to the champion in that lane, pick nodes add a champion to any role.
4. The match against a real Worlds 2026 roster waits at the bottom of the map.
5. Three Swiss wins reach the Quarterfinals, three losses end the run. From the Quarterfinals on one loss ends it.
6. The Semifinal and the Final have no map. Every champion jumps to level 17 (Final 18) and the team gets three picks in a row.

The server decides everything. The client posts one action at a time and gets back the complete run, with power numbers, reachable nodes and pick previews already worked out.

## Running locally

Requires Python 3.11 or newer.

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010
```

The API starts on http://127.0.0.1:8010. Check it is alive at http://127.0.0.1:8010/api/health and browse the interactive API reference at http://127.0.0.1:8010/docs. The SQLite file `riftlike.db` is created on first start. Nothing else is needed, there are no external services and no API keys.

## Configuration

Copy `.env.example` to `.env` if you need to change anything.

| Variable | Default | Purpose |
|---|---|---|
| `RIFTLIKE_CORS_ORIGIN` | `http://localhost:5180` | Origin the frontend dev server runs on |
| `RIFTLIKE_DATABASE_URL` | `sqlite:///riftlike.db` | SQLAlchemy database URL, a local SQLite file by default |

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/catalog` | Champions, teams with rosters, and leagues |
| GET | `/api/matchups/{champ}` | Who this champion counters in lane and who counters it, `?role=` to pick the lane |
| POST | `/api/runs` | Start a run for `{"team": "GEN"}` |
| GET | `/api/runs` | Recent runs, newest first, `?limit=` up to 50 |
| GET | `/api/runs/{id}` | One run as the client renders it |
| POST | `/api/runs/{id}/actions` | Play one action and get the updated run back |

Actions are JSON objects tagged by `type`:

| Action | Body | When |
|---|---|---|
| `choose_first` | `champ` | Opening pick of the run |
| `enter` | `node` | Step onto a reachable map node, or `"match"` once at the bottom |
| `pick` | `champ`, `role` | Take an offered champion into a role, replacing whoever is there |
| `skip` | | Take nobody from the current offers |
| `swap` | `a`, `b` | Swap two roles, between steps or while picking |
| `continue` | | Move on after a fight, a match or a stage change |
| `start_match` | | Play the Semifinal or the Final once the draft is done |

An action that does not fit the current step returns 409 with the reason, for example entering a node that is not connected to where you stand. A short run from the command line looks like this:

```bash
curl -X POST -H "Content-Type: application/json" -d '{"team":"T1"}' http://127.0.0.1:8010/api/runs
curl -X POST -H "Content-Type: application/json" -d '{"type":"choose_first","champ":"Azir"}' http://127.0.0.1:8010/api/runs/<id>/actions
curl -X POST -H "Content-Type: application/json" -d '{"type":"enter","node":"0-1"}' http://127.0.0.1:8010/api/runs/<id>/actions
curl -X POST -H "Content-Type: application/json" -d '{"type":"continue"}' http://127.0.0.1:8010/api/runs/<id>/actions
```

The run view carries the pending step (`first`, `pick`, `fight`, `match` or `stage`), the lineup with every champion's power and its breakdown, the map with the reachable node ids, the next opponent with their lineup, and for each offered champion the power it would have in every role and how the team total would change.

## The rules in numbers

**Power.** Every champion is one number. It is 20 at level 1 and grows by 2 per level, up to level 18, or 20 for whoever plays top. On top of that comes the champion's focus. Early game champions start 6 ahead and slide to 6 behind by level 18, late game champions start 4 behind and finish 11 ahead, and mid game champions peak around the middle with up to 2.

**Bonuses.** A champion outside its own roles loses 6. Each player has five signature champions worth +5 down to +1 when that player plays one in their own role. Duo synergies add their value to both champions, triple for the bot lane pair, double for jungle and mid, single anywhere else, and a few known bad pairs subtract. A full team that is all AD or all AP loses 3 on every champion. Mixed damage champions break that streak.

**Matches.** Before the clash, each lane gets a matchup bonus of up to 2 for the champion that counters its opponent. `GET /api/matchups/{champ}` lists, for one lane, every champion it counters and every champion that counters it, strongest first. Then lanes clash from top to bottom. The stronger side wins and carries what it has left into the next enemy, and whoever has power left at the end wins. Every clash takes the same amount off both sides, so the team with the higher total always wins and the order only tells the story. A dead even match goes to the opponent, and an empty role is worth nothing.

**XP.** A level costs 1000 XP. A lane fight only levels the champion who fought it, the rest of the team levels from matches. Champions trailing the team's best earn 25 percent more for every level they are behind beyond the first, up to double, so new picks catch up.

| Event | Champion in that lane | Rest of the team |
|---|---|---|
| Lane fight won | 1100, plus 100 per level the enemy was ahead | 0 |
| Lane fight drawn | 700 | 0 |
| Lane fight lost | 350 | 0 |
| Lane fight forfeited (nobody in that role) | 0 | 0 |
| Match won | 700 | 700 |
| Match lost | 450 | 450 |
| Swiss day skipped by finishing 3-0 or 3-1 | 2000 per day | 2000 per day |

Play-In XP is scaled down to 35 percent so its winner does not arrive in the Swiss stage far ahead of everyone else.

**The world's level.** Each match day has a level that sets the enemies on the map and the opponent at the bottom.

| Stage | Day level | Opponent at the bottom |
|---|---|---|
| Play-In | 1, 2, 3, 4 | day level + 2 |
| Swiss rounds 1 to 5 | 4, 6, 8, 10, 12 | day level + 2, one more for LCK and LPL first seeds |
| Quarterfinal | 14 | 16, or 17 for LCK and LPL first seeds |
| Semifinal | 17 | 17 |
| Final | 18 | 18 |

## The tournament

**Play-In.** Four teams in a double elimination bracket with one qualifier. A first loss drops you to the lower bracket, a second one ends the run, and the qualifier final decides who joins the Swiss stage.

**Swiss stage.** Sixteen teams, the fifteen main-stage teams plus the Play-In qualifier. Each round draws an opponent you have not met yet. Reaching three wins first sends you to the Quarterfinals, and every Swiss day you skip by finishing 3-0 or 3-1 is paid out as training XP.

**Knockouts.** Quarterfinal, Semifinal and Final, single elimination. Opponents are drawn with a lean toward the strongest teams, and more so after the Quarterfinal.

**Maps.** Six rows on a diamond lattice, two to four nodes wide, then the match. Every row has at least one lane fight and one pick. On the first day roughly a third of the nodes are fights, later about half. Fights in the top two rows always fall in a lane you already have someone in. Enemy levels rise by up to two from the top of the map to the bottom, and offered champions arrive one level above the row, never more than one level below your team's average.

**Picks.** An offer of three. If you have an empty role, one of the three plays it. Some offers include a signature champion of one of your players. Champions already on your team or the opponent's are never offered.

**Opponents.** Early in the run they play whatever their players like, with a growing chance of signature champions. From the second Swiss round on, a rising share of their roles is drafted properly: the strongest option at that level among the player's signatures and a handful of meta picks, counting duo synergy with what is already in. In the Final that is almost every role.

## Data

The 19 rosters are the 2026 World Championship lineups. The champion pool has 157 champions, each with its roles, focus, damage type and class. Signature lists are hand-picked for 37 well-known players, and every other player gets a stable list generated from their role's pool. The 53 duo synergies and the lane matchups are approximations written for this game, not statistics pulled from a live source.

## Saving and determinism

A run is one JSON document in the `run` table, with team, stage and result copied into columns for the recent-runs list. The engine works on plain Pydantic models and has no database code in it.

Each run carries its own random generator state. Offers, maps, opponents and results are drawn from it and stored on the run when a step starts, so reloading never changes an outcome and the same seed with the same choices replays the same run.

## Tests and balance

```bash
pip install -r requirements-dev.txt
pytest
python -m scripts.simulate 300
```

The tests cover the data (every signature exists, every role has early, mid and late options), the power and clash rules, illegal actions, determinism, the API lifecycle, and a full bot run for each of the 19 teams.

The simulation plays a few hundred runs per team with a greedy bot and prints how far they got. The numbers in the engine were tuned against it. With the current values a main-stage team wins the event in roughly 8 to 16 percent of bot runs, and about half of the Play-In teams go out before the Swiss stage. A person who plays around synergies and roles should do better.

## Structure

```
app/
├── main.py          app, CORS and routers
├── config.py        settings from RIFTLIKE_ environment variables
├── db.py            SQLite engine and sessions
├── models.py        the run table
├── repository.py    load, save and list runs
├── routers/         catalog and runs endpoints
└── game/
    ├── data.py      champions, synergies, teams and signatures
    ├── state.py     the saved run and the player actions
    ├── rng.py       seeded Mulberry32 generator
    ├── power.py     power formula, bonuses, matchups and the clash
    ├── engine.py    the tournament: maps, picks, fights, matches, bracket
    └── views.py     the run as the client sees it
scripts/simulate.py  balance simulation
tests/               engine and API tests
```

Riftlike is a fan project. It is not affiliated with or endorsed by Riot Games. League of Legends and all related names are trademarks of Riot Games.
