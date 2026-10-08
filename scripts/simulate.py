"""Play many runs with a simple greedy bot and print how far they get.
Used to tune the numbers in app/game/engine.py.

    python -m scripts.simulate 500
"""

import sys
from collections import Counter

from app.game import engine
from app.game.state import (
    ChooseFirst,
    Continue,
    Enter,
    PendingFirst,
    PendingPick,
    Pick,
    RunState,
    Skip,
    StartMatch,
)
from app.game.views import build_view


def bot_step(run: RunState) -> None:
    view = build_view("sim", run)
    pending = run.pending
    if isinstance(pending, PendingFirst):
        best = max(view.offers, key=lambda o: o.projections[pending.role].power + (o.power_16 - o.power) / 4)
        engine.apply(run, ChooseFirst(type="choose_first", champ=best.champ))
    elif isinstance(pending, PendingPick):
        best = max(view.offers, key=lambda o: o.projections[o.best_role].delta)
        if best.projections[best.best_role].delta > 0:
            engine.apply(run, Pick(type="pick", champ=best.champ, role=best.best_role))
        else:
            engine.apply(run, Skip(type="skip"))
    elif pending is not None:
        engine.apply(run, Continue(type="continue"))
    elif run.map is None:
        engine.apply(run, StartMatch(type="start_match"))
    else:
        engine.apply(run, Enter(type="enter", node=choose_node(run, view)))


def choose_node(run: RunState, view) -> str:
    options = view.reachable
    if options == ["match"]:
        return "match"
    nodes = {n.id: n for n in run.map.nodes}  # type: ignore[union-attr]
    empty = any(not u for u in run.slots.values())

    def score(node_id: str) -> float:
        node = nodes[node_id]
        if node.type == "pick":
            return 3 if empty else 1
        line = view.lineup.power[node.role]
        if line is None:
            return -5
        return 2 if line.total >= (node.power or 0) else -1

    return max(options, key=score)


def play(seed: int, team: str) -> RunState:
    run = engine.new_run(team, seed)
    for _ in range(2000):
        if run.result:
            break
        bot_step(run)
    return run


def outcome(run: RunState) -> str:
    if run.result == "champion":
        return "champion"
    if run.stage == "swiss":
        return f"swiss {run.swiss.w}-{run.swiss.l}"
    return run.stage


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    for team in ("GEN", "LYON", "FUR"):
        results = Counter(outcome(play(seed, team)) for seed in range(count))
        print(team, dict(sorted(results.items(), key=lambda kv: -kv[1])))
