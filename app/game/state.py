"""Run state. One RunState is the whole saved game, the engine mutates it in place."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

Role = Literal["TOP", "JGL", "MID", "BOT", "SUP"]
Stage = Literal["playin", "swiss", "qf", "sf", "final"]
ROLES: tuple[Role, ...] = ("TOP", "JGL", "MID", "BOT", "SUP")


class Unit(BaseModel):
    champ: str
    level: int
    xp: int = 0


class MapNode(BaseModel):
    id: str
    row: int
    col: int
    x: float  # 0..1 across the map
    type: Literal["fight", "pick"]
    children: list[str] = Field(default_factory=list)
    role: Role | None = None  # fight nodes only
    enemy: Unit | None = None
    power: int | None = None
    level: int | None = None  # pick nodes only, the level offers arrive at


class MapState(BaseModel):
    nodes: list[MapNode]
    current: str = "start"
    path: list[str] = Field(default_factory=lambda: ["start"])


class Opponent(BaseModel):
    code: str
    level: int
    slots: dict[Role, Unit]


class PowerPart(BaseModel):
    label: str
    value: int
    kind: Literal["level", "focus", "offrole", "signature", "synergy", "comp"]


class PowerLine(BaseModel):
    total: int
    base: int  # level plus focus curve
    bonus: int  # everything else: signature, synergy, off-role, composition
    parts: list[PowerPart]


class XpGain(BaseModel):
    role: Role
    champ: str
    before: int
    after: int
    gained: int


class Offer(BaseModel):
    champ: str
    level: int


class FightResult(BaseModel):
    role: Role
    champ: str | None
    level: int | None
    enemy: Unit
    ours: int  # matchup included
    theirs: int
    ours_parts: list[PowerPart]
    theirs_parts: list[PowerPart] = Field(default_factory=list)
    matchup: int  # positive favours us
    matchup_note: str = ""  # why the side with the matchup bonus has it
    outcome: Literal["win", "loss", "draw", "forfeit"]
    xp: list[XpGain]


class LaneSide(BaseModel):
    role: Role
    champ: str | None
    level: int | None
    player: str
    power: int  # power entering the clash, matchup included
    counter: int = 0  # matchup bonus this side received
    counter_note: str = ""  # why this side counters its lane opponent
    parts: list[PowerPart] = Field(default_factory=list)  # how the power was built, before the matchup


class ClashStep(BaseModel):
    ours: int  # lane index of our fighter
    theirs: int
    ours_power: int
    theirs_power: int
    winner: Literal["us", "them", "tie"]
    left: int


class NextStep(BaseModel):
    kind: Literal["day", "stage", "out", "champion"]
    stage: Stage | None = None
    skipped: int = 0  # Swiss match days skipped by advancing early
    label: str


class MatchResult(BaseModel):
    opponent: str
    label: str
    ours: list[LaneSide]
    theirs: list[LaneSide]
    steps: list[ClashStep]
    win: bool
    left: int  # power the winner still had at the end
    xp: list[XpGain]
    next: NextStep


class PendingFirst(BaseModel):
    kind: Literal["first"] = "first"
    role: Role
    level: int
    offers: list[Offer]


class PendingPick(BaseModel):
    kind: Literal["pick"] = "pick"
    node: str | None = None
    level: int
    offers: list[Offer]
    draft_left: int = 0  # above zero while drafting before a semifinal or final


class PendingFight(BaseModel):
    kind: Literal["fight"] = "fight"
    node: str
    result: FightResult


class PendingMatch(BaseModel):
    kind: Literal["match"] = "match"
    result: MatchResult


class PendingStage(BaseModel):
    kind: Literal["stage"] = "stage"
    from_stage: Stage
    to_stage: Stage
    skipped: int
    xp: list[XpGain]


Pending = Annotated[
    PendingFirst | PendingPick | PendingFight | PendingMatch | PendingStage,
    Field(discriminator="kind"),
]


class PlayIn(BaseModel):
    node: str = "UB1"
    came_from: str | None = None
    played: int = 0
    order: list[str] = Field(default_factory=list)  # the other three play-in teams


class Swiss(BaseModel):
    w: int = 0
    l: int = 0


class MatchRecord(BaseModel):
    stage: Stage
    label: str
    opponent: str
    win: bool


class RunState(BaseModel):
    rs: int  # random generator state, so a saved run continues the same sequence
    team: str
    stage: Stage
    slots: dict[Role, Unit | None]
    qualifier: str  # the play-in team that reaches the Swiss stage
    playin: PlayIn = Field(default_factory=PlayIn)
    swiss: Swiss = Field(default_factory=Swiss)
    faced: list[str] = Field(default_factory=list)
    history: list[MatchRecord] = Field(default_factory=list)
    day: int = 0
    map: MapState | None = None
    opponent: Opponent | None = None
    pending: Pending | None = None
    result: Literal["champion", "eliminated"] | None = None


# Player actions, posted to /api/runs/{id}/actions.


class ChooseFirst(BaseModel):
    type: Literal["choose_first"]
    champ: str


class Enter(BaseModel):
    type: Literal["enter"]
    node: str


class Pick(BaseModel):
    type: Literal["pick"]
    champ: str
    role: Role


class Skip(BaseModel):
    type: Literal["skip"]


class Swap(BaseModel):
    type: Literal["swap"]
    a: Role
    b: Role


class Continue(BaseModel):
    type: Literal["continue"]


class StartMatch(BaseModel):
    type: Literal["start_match"]


Action = Annotated[
    ChooseFirst | Enter | Pick | Skip | Swap | Continue | StartMatch,
    Field(discriminator="type"),
]
