"""The run: tournament flow, map generation, picks, lane fights and matches.

Every player action goes through `apply`, which either mutates the RunState or raises
IllegalAction. Results are computed when a step starts and stored on `pending`, so a
reload shows the same outcome instead of rolling again."""

from app.game import data
from app.game.data import CHAMPION_NAMES, CHAMPIONS, main_role_pool
from app.game.power import (
    SIGNATURE_TIERS,
    XP_PER_LEVEL,
    champion_parts,
    champion_power,
    clash,
    duo_bonus,
    matchup,
    matchup_note,
    max_level,
    round_half_up,
    signature_bonus,
    signatures_of,
    team_power,
)
from app.game.rng import Rng
from app.game.state import (
    ROLES,
    Action,
    ChooseFirst,
    Continue,
    Enter,
    FightResult,
    LaneSide,
    MapNode,
    MapState,
    MatchRecord,
    MatchResult,
    NextStep,
    Offer,
    Opponent,
    PendingFight,
    PendingFirst,
    PendingMatch,
    PendingPick,
    PendingStage,
    Pick,
    Role,
    RunState,
    Skip,
    StartMatch,
    Swap,
    Unit,
    XpGain,
)

ROW_WIDTHS = (2, 3, 4, 3, 4, 3)
LAST_ROW = len(ROW_WIDTHS) - 1

# A lane fight only teaches the champion who fought it. The rest of the team levels from matches.
LANE_XP = {"win": 1100, "draw": 700, "loss": 350, "forfeit": 0}
MATCH_XP = {True: 950, False: 650}
PLAYIN_XP_SCALE = 0.35  # the Play-In is a warm-up, it should not leave its qualifier far ahead
SKIPPED_DAY_XP = 2000  # about two levels for every Swiss day skipped

# Play-In is a four team double elimination bracket with one qualifier.
# node: (next on a win, next on a loss), None means eliminated.
PLAYIN_ROUTE: dict[str, tuple[str, str | None]] = {
    "UB1": ("UBF", "LB1"),
    "UBF": ("GF", "LBF"),
    "LB1": ("LBF", None),
    "LBF": ("GF", None),
    "GF": ("QUALIFIED", None),
}
PLAYIN_LABEL = {
    "UB1": "Upper bracket round 1",
    "UBF": "Upper bracket final",
    "LB1": "Lower bracket round 1",
    "LBF": "Lower bracket final",
    "GF": "Qualifier final",
}
STAGE_LABEL = {
    "playin": "Play-In",
    "swiss": "Swiss stage",
    "qf": "Quarterfinal",
    "sf": "Semifinal",
    "final": "Final",
}


class IllegalAction(Exception):
    pass


# ---------- levels ----------


def day_level(run: RunState) -> int:
    """The level the world is at on the current match day."""
    if run.stage == "playin":
        return (1, 2, 3, 4)[min(run.playin.played, 3)]
    if run.stage == "swiss":
        return (4, 6, 8, 10, 12)[min(run.swiss.w + run.swiss.l, 4)]
    return {"qf": 14, "sf": 17, "final": 18}[run.stage]


def _opponent_level(run: RunState, code: str) -> int:
    base = day_level(run)
    if run.stage in ("sf", "final"):
        return base
    if run.stage == "playin":
        return base + 2
    strong = run.stage != "playin" and data.team(code).rating >= 4  # type: ignore[union-attr]
    return base + 2 + (1 if strong else 0)


def _avg_level(run: RunState) -> float | None:
    levels = [u.level for u in run.slots.values() if u]
    return sum(levels) / len(levels) if levels else None


def give_xp(run: RunState, rewards: dict[Role, int]) -> list[XpGain]:
    """Champions more than a level behind the team's best catch up faster (up to double)."""
    filled = [(r, run.slots[r]) for r in ROLES if run.slots[r]]
    if not filled:
        return []
    top = max(u.level for _, u in filled)  # type: ignore[union-attr]
    gains: list[XpGain] = []
    for role, unit in filled:
        assert unit is not None
        amount = rewards.get(role, 0)
        if run.stage == "playin":
            amount = round_half_up(amount * PLAYIN_XP_SCALE)
        if amount <= 0:
            continue
        behind = max(0, top - unit.level - 1)
        gained = round_half_up(amount * (1 + min(1.0, 0.25 * behind)))
        before = unit.level
        cap = max(max_level(role), unit.level)
        unit.xp += gained
        while unit.xp >= XP_PER_LEVEL and unit.level < cap:
            unit.xp -= XP_PER_LEVEL
            unit.level += 1
        if unit.level >= cap:
            unit.xp = 0
        gains.append(XpGain(role=role, champ=unit.champ, before=before, after=unit.level, gained=gained))
    return gains


# ---------- run setup ----------


def new_run(team_code: str, seed: int) -> RunState:
    team = data.team(team_code)
    if team is None:
        raise IllegalAction(f"unknown team {team_code}")
    run = RunState(
        rs=seed & 0xFFFFFFFF,
        team=team_code,
        stage="playin" if team.play_in else "swiss",
        slots={r: None for r in ROLES},
        qualifier=team_code,
    )
    rng = Rng(run)
    play_in_teams = [t.code for t in data.TEAMS if t.play_in]
    run.playin.order = rng.shuffle([c for c in play_in_teams if c != team_code])[:3]
    if not team.play_in:
        run.qualifier = rng.pick(play_in_teams)  # type: ignore[assignment]

    role: Role = rng.pick(ROLES)  # type: ignore[assignment]
    level = 1 if team.play_in else 4
    run.pending = PendingFirst(role=role, level=level, offers=_first_offers(run, rng, role, level))
    return run


def _first_offers(run: RunState, rng: Rng, role: Role, level: int) -> list[Offer]:
    """One early, one mid and one late game option for the opening role, often a signature."""
    player = data.team(run.team).players[role]  # type: ignore[union-attr]
    sigs = signatures_of(player, role)
    pool = main_role_pool(role)
    chosen: list[str] = []
    for focus in ("early", "mid", "late"):
        sig_options = [c for c in sigs if CHAMPIONS[c].focus == focus and role in CHAMPIONS[c].roles and c not in chosen]
        options = [c for c in pool if CHAMPIONS[c].focus == focus and c not in chosen]
        if sig_options and rng.chance(0.5):
            chosen.append(rng.pick(sig_options))  # type: ignore[arg-type]
        elif options:
            chosen.append(rng.pick(options))  # type: ignore[arg-type]
    while len(chosen) < 3:
        champ = rng.pick(pool)
        if champ and champ not in chosen:
            chosen.append(champ)
    return [Offer(champ=c, level=level) for c in chosen]


# ---------- match days ----------


def _start_day(run: RunState) -> None:
    rng = Rng(run)
    run.day += 1
    code = _choose_opponent(run, rng)
    run.faced.append(code)
    level = _opponent_level(run, code)
    run.opponent = Opponent(code=code, level=level, slots=_build_opponent(run, rng, code, level))

    if run.stage in ("sf", "final"):
        # No lane fights before the semifinal and final: everyone jumps to the stage level
        # and the team gets three picks in a row.
        floor = day_level(run)
        for unit in run.slots.values():
            if unit and unit.level < floor:
                unit.level = floor
                unit.xp = 0
        run.map = None
        run.pending = PendingPick(level=floor, offers=_pick_offers(run, rng, floor), draft_left=3)
    else:
        run.map = _generate_map(run, rng)
        run.pending = None


def _choose_opponent(run: RunState, rng: Rng) -> str:
    if run.stage == "playin":
        o1, o2, o3 = run.playin.order
        came = run.playin.came_from
        return {
            "UB1": o1,
            "UBF": o2,
            "LB1": o3,
            "LBF": o3 if came == "UBF" else o2,
            "GF": o1 if came == "UBF" else o2,
        }[run.playin.node]

    pool = [t.code for t in data.TEAMS if (not t.play_in or t.code == run.qualifier) and t.code != run.team]
    options = [c for c in pool if c not in run.faced] or pool
    if run.stage == "swiss":
        return rng.pick(options)  # type: ignore[return-value]
    # Knockouts lean toward the strongest teams, more so the deeper the run goes.
    factor = 1 if run.stage == "qf" else 2
    weighted = [c for c in options for _ in range(1 + data.team(c).rating * factor)]  # type: ignore[union-attr]
    return rng.pick(weighted)  # type: ignore[return-value]


def _build_opponent(run: RunState, rng: Rng, code: str, level: int) -> dict[Role, Unit]:
    """Early on opponents play whatever their players like. The further the run goes, the
    more of their roles are drafted properly: the strongest option at that level among the
    player's signatures and a few meta picks, counting duo synergy with what is already in."""
    team = data.team(code)
    assert team is not None
    stage_round = run.swiss.w + run.swiss.l
    sig_chance = {"playin": 0.25, "swiss": 0.3 + 0.1 * stage_round, "qf": 0.6, "sf": 0.6, "final": 0.6}[run.stage]
    draft_chance = {"playin": 0.0, "swiss": 0.08 * stage_round, "qf": 0.5, "sf": 0.7, "final": 0.85}[run.stage]
    late = run.stage in ("qf", "sf", "final")
    used = {u.champ for u in run.slots.values() if u}
    slots: dict[Role, Unit] = {}
    for role in ROLES:
        player = team.players[role]
        lvl = min(level, max_level(role))
        champ: str | None = None
        if rng.chance(draft_chance):
            sigs = [c for c in signatures_of(player, role) if c not in used]
            meta = rng.shuffle([c for c in main_role_pool(role) if c not in used and c not in sigs])[:4]

            def score(c: str) -> int:
                duo = sum(duo_bonus(c, role, u.champ, r)[0] for r, u in slots.items())
                return champion_power(c, lvl) + signature_bonus(player, role, c) + duo + rng.int(3)

            champ = max(sigs + meta, key=score)
        elif rng.chance(sig_chance):
            sigs = [c for c in signatures_of(player, role) if c not in used]
            # earlier entries are more iconic, so they show up more often
            bag = [c for i, c in enumerate(sigs) for _ in range(SIGNATURE_TIERS[i])]
            champ = rng.pick(bag)
        if champ is None:
            pool = [c for c in main_role_pool(role) if c not in used]
            if late and rng.chance(0.7):
                pool = [c for c in pool if CHAMPIONS[c].focus == "late"] or pool
            champ = rng.pick(pool)
        assert champ is not None
        used.add(champ)
        slots[role] = Unit(champ=champ, level=lvl)
    return slots


def _generate_map(run: RunState, rng: Rng) -> MapState:
    day_lvl = day_level(run)
    filled = [r for r in ROLES if run.slots[r]]
    fight_chance = 0.34 if run.day == 1 else 0.45
    nodes: list[MapNode] = []
    for row, width in enumerate(ROW_WIDTHS):
        if row == 0:
            types = rng.shuffle(["fight", "pick"])
        else:
            types = ["fight" if rng.chance(fight_chance) else "pick" for _ in range(width)]
            if len(set(types)) == 1:
                types[rng.int(width)] = "pick" if types[0] == "fight" else "fight"
        lvl = day_lvl + round_half_up(row * 2 / LAST_ROW)
        for col, kind in enumerate(types):
            node = MapNode(
                id=f"{row}-{col}",
                row=row,
                col=col,
                x=(col + (4 - width) / 2 + 0.5) / 4,  # diamond lattice, at most four wide
                type=kind,  # type: ignore[arg-type]
            )
            if kind == "fight":
                # Early rows fight in lanes you already have someone in.
                if filled and (row <= 1 or rng.chance(0.5)):
                    role: Role = rng.pick(filled)  # type: ignore[assignment]
                else:
                    role = rng.pick(ROLES)  # type: ignore[assignment]
                champ: str = rng.pick(main_role_pool(role))  # type: ignore[assignment]
                level = min(lvl, max_level(role))
                node.role = role
                node.enemy = Unit(champ=champ, level=level)
                node.power = champion_power(champ, level)
            else:
                node.level = lvl + 1
            nodes.append(node)
    for node in nodes:
        if node.row < LAST_ROW:
            node.children = [n.id for n in nodes if n.row == node.row + 1 and abs(n.x - node.x) <= 0.13]
    return MapState(nodes=nodes)


def _node(run: RunState, node_id: str) -> MapNode:
    assert run.map is not None
    for node in run.map.nodes:
        if node.id == node_id:
            return node
    raise IllegalAction(f"no node {node_id}")


def reachable(run: RunState) -> list[str]:
    m = run.map
    if m is None or run.pending is not None or run.result is not None:
        return []
    if m.current == "start":
        return [n.id for n in m.nodes if n.row == 0]
    if m.current == "match":
        return []
    node = _node(run, m.current)
    return ["match"] if node.row == LAST_ROW else list(node.children)


# ---------- picks ----------


def _pick_offers(run: RunState, rng: Rng, level: int) -> list[Offer]:
    taken = {u.champ for u in run.slots.values() if u}
    if run.opponent:
        taken |= {u.champ for u in run.opponent.slots.values()}
    team = data.team(run.team)
    assert team is not None
    offers: list[str] = []

    def add(champ: str | None) -> None:
        if champ and champ not in taken and champ not in offers:
            offers.append(champ)

    empty = [r for r in ROLES if not run.slots[r]]
    if empty:
        role: Role = rng.pick(empty)  # type: ignore[assignment]
        add(rng.pick([c for c in main_role_pool(role) if c not in taken]))
    if rng.chance(0.35):
        role = rng.pick(ROLES)  # type: ignore[assignment]
        add(rng.pick([c for c in signatures_of(team.players[role], role) if c not in taken and c not in offers]))
    guard = 0
    while len(offers) < 3 and guard < 200:
        add(rng.pick(CHAMPION_NAMES))
        guard += 1
    return [Offer(champ=c, level=level) for c in offers]


def _after_pick(run: RunState) -> None:
    pending = run.pending
    assert isinstance(pending, PendingPick)
    if pending.draft_left > 0:
        pending.draft_left -= 1
        if pending.draft_left > 0:
            pending.offers = _pick_offers(run, Rng(run), pending.level)
            return
    run.pending = None


# ---------- fights and matches ----------


def _fight(run: RunState, node: MapNode) -> FightResult:
    assert node.role and node.enemy
    role, enemy = node.role, node.enemy
    unit = run.slots[role]
    theirs_base = champion_power(enemy.champ, enemy.level)
    theirs_parts = champion_parts(enemy.champ, enemy.level)
    if unit is None:
        return FightResult(
            role=role, champ=None, level=None, enemy=enemy, ours=0, theirs=theirs_base,
            ours_parts=[], theirs_parts=theirs_parts, matchup=0, outcome="forfeit", xp=[],
        )

    line = team_power(run.slots, data.team(run.team).players)[role]  # type: ignore[union-attr]
    assert line is not None
    m = matchup(unit.champ, enemy.champ)
    ours = line.total + max(0, m)
    theirs = theirs_base + max(0, -m)
    outcome = "win" if ours > theirs else "loss" if ours < theirs else "draw"
    lane_xp = LANE_XP[outcome] + (100 * max(0, enemy.level - unit.level) if outcome == "win" else 0)
    level_before = unit.level
    xp = give_xp(run, {role: lane_xp})
    return FightResult(
        role=role, champ=unit.champ, level=level_before, enemy=enemy, ours=ours, theirs=theirs,
        ours_parts=line.parts, theirs_parts=theirs_parts, matchup=m, outcome=outcome, xp=xp,  # type: ignore[arg-type]
        matchup_note=matchup_note(unit.champ, enemy.champ) if m > 0 else matchup_note(enemy.champ, unit.champ) if m < 0 else "",
    )


def match_label(run: RunState) -> str:
    if run.stage == "playin":
        return f"Play-In · {PLAYIN_LABEL[run.playin.node]}"
    if run.stage == "swiss":
        return f"Swiss · Round {run.swiss.w + run.swiss.l + 1}"
    return STAGE_LABEL[run.stage]


def _play_match(run: RunState) -> MatchResult:
    assert run.opponent is not None
    team = data.team(run.team)
    opp = data.team(run.opponent.code)
    assert team and opp
    our_lines = team_power(run.slots, team.players)
    their_lines = team_power(dict(run.opponent.slots), opp.players)

    ours: list[LaneSide] = []
    theirs: list[LaneSide] = []
    for role in ROLES:
        u = run.slots[role]
        line = our_lines[role]
        ours.append(LaneSide(role=role, champ=u.champ if u else None, level=u.level if u else None,
                             player=team.players[role], power=line.total if line else 0,
                             parts=line.parts if line else []))
        e = run.opponent.slots[role]
        their_line = their_lines[role]
        theirs.append(LaneSide(role=role, champ=e.champ, level=e.level, player=opp.players[role],
                               power=their_line.total if their_line else 0,
                               parts=their_line.parts if their_line else []))
    for a, b in zip(ours, theirs):
        if a.champ and b.champ:
            m = matchup(a.champ, b.champ)
            if m > 0:
                a.power += m
                a.counter = m
                a.counter_note = matchup_note(a.champ, b.champ)
            elif m < 0:
                b.power -= m
                b.counter = -m
                b.counter_note = matchup_note(b.champ, a.champ)

    steps, win, left = clash([s.power for s in ours], [s.power for s in theirs])
    label = match_label(run)
    xp = give_xp(run, {r: MATCH_XP[win] for r in ROLES})
    run.history.append(MatchRecord(stage=run.stage, label=label, opponent=opp.code, win=win))
    nxt = _record_result(run, win)
    return MatchResult(opponent=opp.code, label=label, ours=ours, theirs=theirs, steps=steps,
                       win=win, left=left, xp=xp, next=nxt)


def _record_result(run: RunState, win: bool) -> NextStep:
    """Update the bracket and say what happens after this match."""
    if run.stage == "playin":
        node = run.playin.node
        nxt = PLAYIN_ROUTE[node][0 if win else 1]
        run.playin.played += 1
        if nxt is None:
            return NextStep(kind="out", label="Eliminated in the Play-In")
        if nxt == "QUALIFIED":
            return NextStep(kind="stage", stage="swiss", label="Qualified for the Swiss stage")
        run.playin.came_from = node
        run.playin.node = nxt
        return NextStep(kind="day", label=f"Next: {PLAYIN_LABEL[nxt]}")

    if run.stage == "swiss":
        if win:
            run.swiss.w += 1
        else:
            run.swiss.l += 1
        w, l = run.swiss.w, run.swiss.l
        if w == 3:
            return NextStep(kind="stage", stage="qf", skipped=5 - (w + l), label=f"Through to the Quarterfinals at {w}–{l}")
        if l == 3:
            return NextStep(kind="out", label=f"Eliminated in the Swiss stage at {w}–{l}")
        return NextStep(kind="day", label=f"Next: Swiss round {w + l + 1}, record {w}–{l}")

    if not win:
        return NextStep(kind="out", label=f"Eliminated in the {STAGE_LABEL[run.stage]}")
    if run.stage == "final":
        return NextStep(kind="champion", label="World Champions")
    following = "sf" if run.stage == "qf" else "final"
    return NextStep(kind="stage", stage=following, label=f"Through to the {STAGE_LABEL[following]}")  # type: ignore[arg-type]


def _advance(run: RunState, nxt: NextStep) -> None:
    run.pending = None
    if nxt.kind == "champion":
        run.result = "champion"
        return
    if nxt.kind == "out":
        run.result = "eliminated"
        return
    if nxt.kind == "day":
        _start_day(run)
        return
    assert nxt.stage is not None
    previous = run.stage
    run.stage = nxt.stage
    xp = give_xp(run, {r: SKIPPED_DAY_XP * nxt.skipped for r in ROLES}) if nxt.skipped else []
    run.map = None
    run.opponent = None
    run.pending = PendingStage(from_stage=previous, to_stage=nxt.stage, skipped=nxt.skipped, xp=xp)


def _start_match(run: RunState) -> None:
    if run.map is not None:
        if "match" not in reachable(run):
            raise IllegalAction("walk the map down to the match first")
        run.map.current = "match"
        run.map.path.append("match")
    elif run.pending is not None or run.opponent is None:
        raise IllegalAction("finish the current step first")
    run.pending = PendingMatch(result=_play_match(run))


# ---------- actions ----------


def apply(run: RunState, action: Action) -> None:
    if run.result is not None:
        raise IllegalAction("this run is over")
    pending = run.pending

    if isinstance(action, ChooseFirst):
        if not isinstance(pending, PendingFirst):
            raise IllegalAction("the first champion is already chosen")
        if action.champ not in [o.champ for o in pending.offers]:
            raise IllegalAction("that champion was not offered")
        run.slots[pending.role] = Unit(champ=action.champ, level=pending.level)
        run.pending = None
        _start_day(run)

    elif isinstance(action, Enter):
        if pending is not None or run.map is None:
            raise IllegalAction("finish the current step first")
        if action.node not in reachable(run):
            raise IllegalAction("that node is not reachable from here")
        if action.node == "match":
            _start_match(run)
            return
        node = _node(run, action.node)
        run.map.current = node.id
        run.map.path.append(node.id)
        if node.type == "fight":
            run.pending = PendingFight(node=node.id, result=_fight(run, node))
        else:
            avg = _avg_level(run)
            level = node.level or 1
            if avg is not None:
                level = max(level, round_half_up(avg) - 1)
            level = min(level, 18)
            run.pending = PendingPick(node=node.id, level=level, offers=_pick_offers(run, Rng(run), level))

    elif isinstance(action, Pick):
        if not isinstance(pending, PendingPick):
            raise IllegalAction("there is nothing to pick right now")
        offer = next((o for o in pending.offers if o.champ == action.champ), None)
        if offer is None:
            raise IllegalAction("that champion was not offered")
        run.slots[action.role] = Unit(champ=offer.champ, level=offer.level)
        _after_pick(run)

    elif isinstance(action, Skip):
        if not isinstance(pending, PendingPick):
            raise IllegalAction("there is nothing to skip right now")
        _after_pick(run)

    elif isinstance(action, Swap):
        if pending is not None and not isinstance(pending, PendingPick):
            raise IllegalAction("roles can only be swapped between steps")
        run.slots[action.a], run.slots[action.b] = run.slots[action.b], run.slots[action.a]

    elif isinstance(action, StartMatch):
        if run.map is not None:
            raise IllegalAction("walk the map down to the match")
        _start_match(run)

    elif isinstance(action, Continue):
        if isinstance(pending, PendingFight):
            run.pending = None
        elif isinstance(pending, PendingStage):
            run.pending = None
            _start_day(run)
        elif isinstance(pending, PendingMatch):
            _advance(run, pending.result.next)
        else:
            raise IllegalAction("make a choice first")
