"""Champion power, team bonuses, lane matchups and the match clash."""

import math
from functools import lru_cache

from app.game.data import CHAMPIONS, SIGNATURES, main_role_pool, synergy_of
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


_MATCHUP_TABLE = (-2, -1, -1, 0, 0, 0, 1, 1, 2)


def matchup(a: str, b: str) -> int:
    """Lane advantage of `a` over `b`. Stable and antisymmetric, so matchup(b, a) == -matchup(a, b)."""
    if a == b:
        return 0
    first, second = sorted((a, b))
    value = _MATCHUP_TABLE[fnv1a(f"{first}>{second}") % len(_MATCHUP_TABLE)]
    return value if a == first else -value


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
            value = synergy_of(unit.champ, partner)
            if value:
                parts.append(
                    PowerPart(label=f"With {partner}", value=value * pair_weight(role, other), kind="synergy")
                )
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
