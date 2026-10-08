from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.game.data import CHAMPIONS
from app.game.power import lane_matchups, matchup_note
from app.game.state import Role

router = APIRouter(prefix="/api/matchups", tags=["matchups"])


class MatchupEntry(BaseModel):
    champ: str
    value: int  # lane bonus, 1 to 5
    note: str  # why the winning side of the matchup has the edge


class Matchups(BaseModel):
    champ: str
    role: Role
    counters: list[MatchupEntry]  # champions this one beats in lane
    countered_by: list[MatchupEntry]  # champions that beat this one in lane


@router.get("/{champ}", response_model=Matchups)
def get_matchups(champ: str, role: Role | None = None) -> Matchups:
    """Lane matchups against every champion that can play the given role, the champion's
    main role when none is given."""
    info = CHAMPIONS.get(champ)
    if info is None:
        raise HTTPException(404, "unknown champion")
    lane = role or info.roles[0]
    counters, countered_by = lane_matchups(champ, lane)
    return Matchups(
        champ=champ,
        role=lane,
        counters=[MatchupEntry(champ=c, value=v, note=matchup_note(champ, c)) for c, v in counters],
        countered_by=[MatchupEntry(champ=c, value=v, note=matchup_note(c, champ)) for c, v in countered_by],
    )
