from fastapi import APIRouter
from pydantic import BaseModel

from app.game.data import CHAMPIONS, LEAGUES, TEAMS

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


class ChampionInfo(BaseModel):
    roles: list[str]
    focus: str
    dmg: str
    cls: str


class TeamInfo(BaseModel):
    code: str
    name: str
    league: str
    seed: int
    play_in: bool
    color: str
    players: dict[str, str]


class LeagueInfo(BaseModel):
    code: str
    region: str


class Catalog(BaseModel):
    champions: dict[str, ChampionInfo]
    teams: list[TeamInfo]
    leagues: list[LeagueInfo]


@router.get("", response_model=Catalog)
def get_catalog() -> Catalog:
    return Catalog(
        champions={
            name: ChampionInfo(roles=list(c.roles), focus=c.focus, dmg=c.dmg, cls=c.cls)
            for name, c in CHAMPIONS.items()
        },
        teams=[
            TeamInfo(
                code=t.code,
                name=t.name,
                league=t.league,
                seed=t.seed,
                play_in=t.play_in,
                color=t.color,
                players=dict(t.players),
            )
            for t in TEAMS
        ],
        leagues=[LeagueInfo(code=l.code, region=l.region) for l in LEAGUES],
    )
