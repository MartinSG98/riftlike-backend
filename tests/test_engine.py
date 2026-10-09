import pytest

from app.game import engine
from app.game.data import CHAMPIONS, SIGNATURES, TEAMS, main_role_pool, synergy_of
from app.game.power import champion_power, clash, focus_mod, matchup, signatures_of
from app.game.state import ROLES, Continue, Enter, PendingFirst, Swap
from scripts.simulate import play


def test_every_named_champion_exists():
    for player, champs in SIGNATURES.items():
        for champ in champs:
            assert champ in CHAMPIONS, f"{player}: {champ}"


def test_every_role_has_early_mid_and_late_options():
    for role in ROLES:
        focuses = {CHAMPIONS[c].focus for c in main_role_pool(role)}
        assert focuses == {"early", "mid", "late"}, role


def test_career_signatures_drive_the_bonuses():
    from app.game.data import CAREER_SIGNATURES
    from app.game.power import SIGNATURE_TIERS, signature_bonus

    assert len(CAREER_SIGNATURES) == sum(len(t.players) for t in TEAMS)
    for team in TEAMS:
        for role, player in team.players.items():
            sigs = signatures_of(player, role)
            assert sigs == tuple(CAREER_SIGNATURES[player][: len(SIGNATURE_TIERS)])
            assert all(c in CHAMPIONS for c in sigs)
            assert [signature_bonus(player, role, c) for c in sigs] == list(SIGNATURE_TIERS[: len(sigs)])
    assert "Kled" in signatures_of("BrokenBlade", "TOP")


def test_generated_signatures_are_stable_and_in_role():
    first = signatures_of("SomeRookie", "JGL")
    assert first == signatures_of("SomeRookie", "JGL")
    assert len(first) == 5
    assert all(c in main_role_pool("JGL") for c in first)


def test_focus_curve_shapes():
    assert focus_mod("early", 1) > focus_mod("early", 18)
    assert focus_mod("late", 1) < focus_mod("late", 18)
    assert champion_power("Azir", 16) > champion_power("Akshan", 16)


def test_matchup_is_antisymmetric():
    for a, b in [("Azir", "Kassadin"), ("Jinx", "Draven"), ("Lee Sin", "Viego")]:
        assert matchup(a, b) == -matchup(b, a)
    assert matchup("Azir", "Azir") == 0


def test_counters_follow_tempo_and_class():
    from app.game.power import MATCHUP_CAP, matchup_note

    assert matchup("Kled", "Ornn") >= 3
    assert "fighter into tank" in matchup_note("Kled", "Ornn")
    assert "stronger early" in matchup_note("Kled", "Ornn")
    assert matchup_note("Ornn", "Kled") == "" or matchup("Ornn", "Kled") < 0
    for role in ROLES:
        pool = main_role_pool(role)
        assert all(abs(matchup(a, b)) <= MATCHUP_CAP for a in pool for b in pool)


def test_synergy_is_symmetric():
    assert synergy_of("Xayah", "Rakan") == synergy_of("Rakan", "Xayah") == 2


def test_archetypes_only_fire_in_their_own_slots():
    from app.game.power import duo_bonus

    assert duo_bonus("Kalista", "BOT", "Leona", "SUP") == (3, "Lane bullies")
    assert duo_bonus("Leona", "SUP", "Kalista", "BOT") == (3, "Lane bullies")
    assert duo_bonus("Leona", "BOT", "Kalista", "SUP") == (0, None)
    assert duo_bonus("Sejuani", "JGL", "Orianna", "MID") == (2, None)  # hand-picked, not the archetype


def test_hand_picked_duos_take_precedence_over_archetypes():
    from app.game.power import duo_bonus

    # Kalista and Rell would also be lane bullies, the named duo decides
    assert duo_bonus("Kalista", "BOT", "Rell", "SUP") == (3, None)
    assert duo_bonus("Ezreal", "BOT", "Leona", "SUP") == (-3, None)


def test_most_lineups_have_a_synergy():
    import random

    from app.game.power import duo_bonus

    rng = random.Random(3)
    pools = {r: main_role_pool(r) for r in ROLES}
    hits = 0
    for _ in range(3000):
        team = {r: rng.choice(pools[r]) for r in ROLES}
        pairs = [(a, b) for i, a in enumerate(ROLES) for b in ROLES[i + 1 :]]
        hits += any(duo_bonus(team[a], a, team[b], b)[0] for a, b in pairs)
    assert hits / 3000 > 0.45


@pytest.mark.parametrize(
    "ours, theirs",
    [([30, 28, 26, 31, 24], [27, 33, 25, 29, 22]), ([0, 0, 40, 40, 40], [30, 30, 30, 30, 30]), ([20] * 5, [20] * 5)],
)
def test_clash_is_decided_by_total_power(ours, theirs):
    _, win, _ = clash(ours, theirs)
    assert win == (sum(ours) > sum(theirs))


def test_new_run_starts_with_a_first_pick():
    run = engine.new_run("GEN", 7)
    assert isinstance(run.pending, PendingFirst)
    assert run.stage == "swiss"
    assert {o.level for o in run.pending.offers} == {4}


def test_play_in_team_starts_in_the_play_in():
    run = engine.new_run("FUR", 7)
    assert run.stage == "playin"
    assert len(run.playin.order) == 3 and "FUR" not in run.playin.order


def test_unreachable_nodes_are_rejected():
    run = engine.new_run("T1", 3)
    engine.apply(run, engine.ChooseFirst(type="choose_first", champ=run.pending.offers[0].champ))
    deep = next(n.id for n in run.map.nodes if n.row == 3)
    with pytest.raises(engine.IllegalAction):
        engine.apply(run, Enter(type="enter", node=deep))
    with pytest.raises(engine.IllegalAction):
        engine.apply(run, Continue(type="continue"))


def test_swap_moves_champions_between_roles():
    run = engine.new_run("T1", 3)
    role = run.pending.role
    engine.apply(run, engine.ChooseFirst(type="choose_first", champ=run.pending.offers[0].champ))
    other = next(r for r in ROLES if r != role)
    engine.apply(run, Swap(type="swap", a=role, b=other))
    assert run.slots[role] is None and run.slots[other] is not None


def test_lane_fights_only_level_the_champion_in_that_lane():
    from app.game.state import PendingFight
    from scripts.simulate import bot_step

    checked = 0
    for seed in range(20):
        run = engine.new_run("T1", seed)
        for _ in range(300):
            if run.result:
                break
            if isinstance(run.pending, PendingFight):
                r = run.pending.result
                assert all(g.role == r.role for g in r.xp)
                assert len(r.xp) == (0 if r.outcome == "forfeit" else 1)
                checked += 1
            bot_step(run)
    assert checked > 20


def test_results_carry_the_power_breakdown_behind_every_number():
    from app.game.state import PendingFight, PendingMatch
    from scripts.simulate import bot_step

    run = engine.new_run("GEN", 11)
    seen_fight = seen_match = False
    for _ in range(400):
        if run.result or (seen_fight and seen_match):
            break
        if isinstance(run.pending, PendingFight) and run.pending.result.outcome != "forfeit":
            r = run.pending.result
            assert sum(p.value for p in r.ours_parts) + max(0, r.matchup) == r.ours
            assert sum(p.value for p in r.theirs_parts) + max(0, -r.matchup) == r.theirs
            seen_fight = True
        if isinstance(run.pending, PendingMatch):
            for lane in run.pending.result.ours + run.pending.result.theirs:
                if lane.champ:
                    assert sum(p.value for p in lane.parts) + lane.counter == lane.power
            seen_match = True
        bot_step(run)
    assert seen_fight and seen_match


def test_same_seed_plays_the_same_run():
    a = play(42, "GEN")
    b = play(42, "GEN")
    assert a.model_dump() == b.model_dump()


@pytest.mark.parametrize("team", [t.code for t in TEAMS])
def test_bot_runs_finish_for_every_team(team):
    for seed in range(5):
        run = play(seed, team)
        assert run.result in ("champion", "eliminated")
        assert run.history
