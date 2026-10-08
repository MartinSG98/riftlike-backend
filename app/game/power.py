"""Champion power, team bonuses, lane matchups and the match clash."""

import math
from functools import lru_cache

from app.game.data import CHAMPIONS, SIGNATURES, archetype_of, main_role_pool, synergy_of
from app.game.rng import Rng, Seed, fnv1a
from app.game.state import ROLES, ClashStep, PowerLine, PowerPart, Role, Unit

XP_PER_LEVEL = 1000
OFF_ROLE_PENALTY = 6
MONO_DAMAGE_PENALTY = 3


def round_half_up(x: float) -> int:
    return math.floor(x + 0.5)


def max_level(role: Role) -> int:
    return 20 if role == "TOP" else 18


def base_power(level: int) -> int:
    return 20 + 2 * (level - 1)


def focus_mod(focus: str, level: int) -> int:
    """Early champions start ahead and fall off, late ones start behind and end on top."""
    t = (level - 1) / 17
    if focus == "early":
        return round_half_up(6 - 12 * t)
    if focus == "late":
        return round_half_up(-4 + 15 * t)
    return round_half_up(2 * math.sin(math.pi * min(t, 1)))


def champion_power(champ: str, level: int) -> int:
    return base_power(level) + focus_mod(CHAMPIONS[champ].focus, level)


def champion_parts(champ: str, level: int) -> list[PowerPart]:
    """The breakdown of a champion on its own, with no player or team around it."""
    parts = [PowerPart(label=f"Level {level}", value=base_power(level), kind="level")]
    focus = CHAMPIONS[champ].focus
    value = focus_mod(focus, level)
    if value:
        parts.append(PowerPart(label=f"{focus.capitalize()} game", value=value, kind="focus"))
    return parts


@lru_cache
def signatures_of(player: str, role: Role) -> tuple[str, ...]:
    if player in SIGNATURES:
        return tuple(SIGNATURES[player])
    rng = Rng(Seed(fnv1a(f"{player}|{role}")))
    return tuple(rng.shuffle(main_role_pool(role))[:5])


def signature_bonus(player: str, role: Role, champ: str) -> int:
    sigs = signatures_of(player, role)
    return 5 - sigs.index(champ) if champ in sigs else 0


def pair_weight(a: Role, b: Role) -> int:
    pair = {a, b}
    if pair == {"BOT", "SUP"}:
        return 3
    if pair == {"JGL", "MID"}:
        return 2
    return 1


def duo_bonus(a: str, role_a: Role, b: str, role_b: Role) -> tuple[int, str | None]:
    """The synergy `a` gets from `b` in these two slots, already weighted for the pair, and
    the archetype's name when the bonus comes from one. A hand-picked duo takes precedence."""
    weight = pair_weight(role_a, role_b)
    named = synergy_of(a, b)
    if named:
        return named * weight, None
    archetype = archetype_of(a, role_a, b, role_b)
    if archetype:
        return archetype.value * weight, archetype.name
    return 0, None


def duo_label(partner: str, archetype: str | None) -> str:
    return f"{archetype} with {partner}" if archetype else f"With {partner}"


# How one class does into another in a lane, from the first one's side. Read both ways, so
# a fighter into a tank is +2 and a tank into a fighter is -2.
_CLASS_EDGE = {
    ("Fighter", "Tank"): 2,
    ("Fighter", "Enchanter"): 1,
    ("Assassin", "Mage"): 1,
    ("Assassin", "Marksman"): 2,
    ("Assassin", "Enchanter"): 1,
    ("Mage", "Tank"): 1,
    ("Mage", "Fighter"): 1,
    ("Marksman", "Tank"): 1,
    ("Tank", "Enchanter"): 1,
    ("Tank", "Assassin"): 1,
}
_RANGED = {"Mage", "Marksman", "Enchanter"}
_FOCUS_ORDER = {"early": 0, "mid": 1, "late": 2}
_QUIRK = (-1, 0, 0, 1)
MATCHUP_CAP = 5


def matchup_reasons(a: str, b: str) -> list[tuple[str, int]]:
    """Why `a` is ahead of or behind `b` in a lane, as (reason, value) pairs from `a`'s side.
    Each piece is antisymmetric, so matchup(b, a) == -matchup(a, b)."""
    if a == b:
        return []
    ca, cb = CHAMPIONS[a], CHAMPIONS[b]
    reasons: list[tuple[str, int]] = []

    tempo = _FOCUS_ORDER[cb.focus] - _FOCUS_ORDER[ca.focus]
    if tempo:
        reasons.append(("stronger early" if tempo > 0 else "weaker early", tempo))

    edge = _CLASS_EDGE.get((ca.cls, cb.cls), 0) - _CLASS_EDGE.get((cb.cls, ca.cls), 0)
    if edge:
        reasons.append((f"{ca.cls.lower()} into {cb.cls.lower()}", edge))

    ranged = int(ca.cls in _RANGED) - int(cb.cls in _RANGED)
    if ranged:
        reasons.append(("ranged into melee" if ranged > 0 else "melee into ranged", ranged))

    # A small stable nudge per pair, so two champions of the same type still differ.
    first, second = sorted((a, b))
    quirk = _QUIRK[fnv1a(f"{first}>{second}") % len(_QUIRK)]
    if quirk:
        reasons.append(("matchup quirks", quirk if a == first else -quirk))
    return reasons


def matchup(a: str, b: str) -> int:
    """Lane advantage of `a` over `b`, between -5 and +5."""
    total = sum(value for _, value in matchup_reasons(a, b))
    return max(-MATCHUP_CAP, min(MATCHUP_CAP, total))


def matchup_note(a: str, b: str) -> str:
    """The reasons `a` counters `b`, in words, for the side that gets the bonus."""
    return ", ".join(reason for reason, value in matchup_reasons(a, b) if value > 0)


def lane_matchups(champ: str, role: Role) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    """Champions that can play `role` which `champ` counters, and those that counter it.
    Both lists hold (champion, bonus) pairs, strongest first."""
    rivals = [c for c, info in CHAMPIONS.items() if c != champ and role in info.roles]
    values = [(c, matchup(champ, c)) for c in rivals]
    counters = sorted(((c, v) for c, v in values if v > 0), key=lambda cv: (-cv[1], cv[0]))
    countered_by = sorted(((c, -v) for c, v in values if v < 0), key=lambda cv: (-cv[1], cv[0]))
    return counters, countered_by


def team_power(slots: dict[Role, Unit | None], players: dict[Role, str]) -> dict[Role, PowerLine | None]:
    filled = [r for r in ROLES if slots.get(r)]
    damage = {CHAMPIONS[slots[r].champ].dmg for r in filled}  # type: ignore[union-attr]
    mono = next(iter(damage)) if len(filled) == 5 and len(damage) == 1 and "MX" not in damage else None

    out: dict[Role, PowerLine | None] = {}
    for role in ROLES:
        unit = slots.get(role)
        if unit is None:
            out[role] = None
            continue
        champ = CHAMPIONS[unit.champ]
        focus = focus_mod(champ.focus, unit.level)
        parts = [PowerPart(label=f"Level {unit.level}", value=base_power(unit.level), kind="level")]
        if focus:
            parts.append(PowerPart(label=f"{champ.focus.capitalize()} game", value=focus, kind="focus"))
        if role not in champ.roles:
            parts.append(PowerPart(label="Off-role", value=-OFF_ROLE_PENALTY, kind="offrole"))
        sig = signature_bonus(players[role], role, unit.champ)
        if sig:
            parts.append(PowerPart(label=f"{players[role]} signature", value=sig, kind="signature"))
        for other in filled:
            if other == role:
                continue
            partner = slots[other].champ  # type: ignore[union-attr]
            value, archetype = duo_bonus(unit.champ, role, partner, other)
            if value:
                parts.append(PowerPart(label=duo_label(partner, archetype), value=value, kind="synergy"))
        if mono:
            parts.append(PowerPart(label=f"Full {mono} team", value=-MONO_DAMAGE_PENALTY, kind="comp"))

        total = max(1, sum(p.value for p in parts))
        base = base_power(unit.level) + focus
        out[role] = PowerLine(total=total, base=base, bonus=total - base, parts=parts)
    return out


def total_power(lines: dict[Role, PowerLine | None]) -> int:
    return sum(line.total for line in lines.values() if line)


def clash(ours: list[int], theirs: list[int]) -> tuple[list[ClashStep], bool, int]:
    """Lanes fight top to bottom. The stronger side wins the clash and carries what it has
    left into the next enemy. Returns the steps, whether we won, and the winner's leftover.

    Every clash takes the same amount off both sides, so the side with more total power
    always wins. The order decides the story, not the result. A dead even match goes to
    the opponent."""
    n = len(ours)
    i = j = 0
    a, b = ours[0], theirs[0]
    steps: list[ClashStep] = []
    while i < n and j < n:
        if a > b:
            steps.append(ClashStep(ours=i, theirs=j, ours_power=a, theirs_power=b, winner="us", left=a - b))
            a -= b
            j += 1
            b = theirs[j] if j < n else 0
        elif b > a:
            steps.append(ClashStep(ours=i, theirs=j, ours_power=a, theirs_power=b, winner="them", left=b - a))
            b -= a
            i += 1
            a = ours[i] if i < n else 0
        else:
            steps.append(ClashStep(ours=i, theirs=j, ours_power=a, theirs_power=b, winner="tie", left=0))
            i += 1
            j += 1
            a = ours[i] if i < n else 0
            b = theirs[j] if j < n else 0
    if i < n:
        return steps, True, a + sum(ours[i + 1 :])
    if j < n:
        return steps, False, b + sum(theirs[j + 1 :])
    return steps, False, 0
