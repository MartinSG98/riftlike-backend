"""What the client sees: the run state plus everything derived from it (power, reachable
nodes, pick projections), so the UI never has to reimplement the rules."""

from datetime import datetime

from pydantic import BaseModel

from app.game import data
from app.game.engine import PLAYIN_LABEL, STAGE_LABEL, reachable
from app.game.power import champion_power, duo_bonus, duo_label, signatures_of, team_power, total_power
from app.game.state import (
    ROLES,
    MapState,
    MatchRecord,
    Offer,
    Pending,
    PendingFirst,
    PendingPick,
    PowerLine,
    Role,
    RunState,
    Stage,
    Swiss,
    Unit,
)


class SynergyLink(BaseModel):
    roles: tuple[Role, Role]
    champs: tuple[str, str]
    archetype: str | None  # None for a hand-picked duo
    value: int  # what each of the two champions gets, already weighted


class Lineup(BaseModel):
    slots: dict[Role, Unit | None]
    power: dict[Role, PowerLine | None]
    total: int
    warnings: list[str]
    synergies: list[SynergyLink]


class OpponentView(BaseModel):
    code: str
    level: int
    lineup: Lineup


class Projection(BaseModel):
    power: int  # this champion's power in that role
    delta: int  # change to the team total
    replaces: str | None


class OfferSignature(BaseModel):
    role: Role
    player: str
    bonus: int


class OfferSynergy(BaseModel):
    champ: str
    role: Role
    value: int  # already weighted for the role pair, assuming the best role
    label: str


class OfferView(BaseModel):
    champ: str
    level: int
    power: int
    power_16: int
    signatures: list[OfferSignature]
    synergies: list[OfferSynergy]
    projections: dict[Role, Projection]
    best_role: Role


class RunView(BaseModel):
    id: str
    team: str
    stage: Stage
    day: int
    day_label: str
    swiss: Swiss
    playin_node: str
    lineup: Lineup
    map: MapState | None
    reachable: list[str]
    opponent: OpponentView | None
    pending: Pending | None
    offers: list[OfferView]
    history: list[MatchRecord]
    result: str | None


class RunSummary(BaseModel):
    id: str
    team: str
    stage: Stage
    result: str | None
    label: str
    updated_at: datetime


def lineup(slots: dict[Role, Unit | None], players: dict[Role, str]) -> Lineup:
    power = team_power(slots, players)
    warnings: list[str] = []
    empty = [role for role in ROLES if not slots.get(role)]
    if empty:
        warnings.append(f"{len(empty)} empty role{'s' if len(empty) > 1 else ''}, worth 0 power in a match")
    comp = next((p for line in power.values() if line for p in line.parts if p.kind == "comp"), None)
    if comp:
        warnings.append(f"{comp.label}: {comp.value} on every champion")
    links: list[SynergyLink] = []
    for i, a in enumerate(ROLES):
        for b in ROLES[i + 1 :]:
            ua, ub = slots.get(a), slots.get(b)
            if ua and ub:
                value, archetype = duo_bonus(ua.champ, a, ub.champ, b)
                if value:
                    links.append(SynergyLink(roles=(a, b), champs=(ua.champ, ub.champ), archetype=archetype, value=value))
    return Lineup(slots=slots, power=power, total=total_power(power), warnings=warnings, synergies=links)


def day_label(run: RunState) -> str:
    if run.stage == "playin":
        return f"Play-In · {PLAYIN_LABEL[run.playin.node]}"
    if run.stage == "swiss":
        w, l = run.swiss.w, run.swiss.l
        return f"Swiss · Round {w + l + 1} · Record {w}–{l}"
    return STAGE_LABEL[run.stage]


def _offer_view(run: RunState, offer: Offer, base: Lineup) -> OfferView:
    team = data.team(run.team)
    assert team is not None
    projections: dict[Role, Projection] = {}
    for role in ROLES:
        slots = dict(run.slots)
        replaced = slots[role]
        slots[role] = Unit(champ=offer.champ, level=offer.level)
        power = team_power(slots, team.players)
        line = power[role]
        assert line is not None
        projections[role] = Projection(
            power=line.total,
            delta=total_power(power) - base.total,
            replaces=replaced.champ if replaced else None,
        )
    best: Role = max(ROLES, key=lambda r: projections[r].delta)

    signatures = []
    for role in ROLES:
        player = team.players[role]
        sigs = signatures_of(player, role)
        if offer.champ in sigs:
            signatures.append(OfferSignature(role=role, player=player, bonus=5 - sigs.index(offer.champ)))

    synergies = []
    for role in ROLES:
        unit = run.slots[role]
        if not unit or role == best:
            continue
        value, archetype = duo_bonus(offer.champ, best, unit.champ, role)
        if value:
            synergies.append(
                OfferSynergy(champ=unit.champ, role=role, value=value, label=duo_label(unit.champ, archetype))
            )

    return OfferView(
        champ=offer.champ,
        level=offer.level,
        power=champion_power(offer.champ, offer.level),
        power_16=champion_power(offer.champ, 16),
        signatures=signatures,
        synergies=synergies,
        projections=projections,
        best_role=best,
    )


def build_view(run_id: str, run: RunState) -> RunView:
    team = data.team(run.team)
    assert team is not None
    ours = lineup(run.slots, team.players)

    opponent = None
    if run.opponent:
        opp_team = data.team(run.opponent.code)
        assert opp_team is not None
        opponent = OpponentView(
            code=run.opponent.code,
            level=run.opponent.level,
            lineup=lineup(dict(run.opponent.slots), opp_team.players),
        )

    offers: list[OfferView] = []
    if isinstance(run.pending, (PendingFirst, PendingPick)):
        offers = [_offer_view(run, o, ours) for o in run.pending.offers]

    return RunView(
        id=run_id,
        team=run.team,
        stage=run.stage,
        day=run.day,
        day_label=day_label(run),
        swiss=run.swiss,
        playin_node=run.playin.node,
        lineup=ours,
        map=run.map,
        reachable=reachable(run),
        opponent=opponent,
        pending=run.pending,
        offers=offers,
        history=run.history,
        result=run.result,
    )


def summary_label(run: RunState) -> str:
    if run.result == "champion":
        return "World Champions"
    if run.result == "eliminated":
        if run.stage == "swiss":
            return f"Out in the Swiss stage ({run.swiss.w}–{run.swiss.l})"
        return f"Out in the {STAGE_LABEL[run.stage]}"
    return f"In progress · {day_label(run)}"
