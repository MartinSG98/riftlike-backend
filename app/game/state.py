"""Shared game types."""

from typing import Literal

from pydantic import BaseModel

Role = Literal["TOP", "JGL", "MID", "BOT", "SUP"]
Stage = Literal["playin", "swiss", "qf", "sf", "final"]
ROLES: tuple[Role, ...] = ("TOP", "JGL", "MID", "BOT", "SUP")


class Unit(BaseModel):
    champ: str
    level: int
    xp: int = 0


class PowerPart(BaseModel):
    label: str
    value: int
    kind: Literal["level", "focus", "offrole", "signature", "synergy", "comp"]


class PowerLine(BaseModel):
    total: int
    base: int  # level plus focus curve
    bonus: int  # everything else: signature, synergy, off-role, composition
    parts: list[PowerPart]


class ClashStep(BaseModel):
    ours: int  # lane index of our fighter
    theirs: int
    ours_power: int
    theirs_power: int
    winner: Literal["us", "them", "tie"]
    left: int
