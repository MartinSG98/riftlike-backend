"""Shared game types."""

from typing import Literal

Role = Literal["TOP", "JGL", "MID", "BOT", "SUP"]
Stage = Literal["playin", "swiss", "qf", "sf", "final"]
ROLES: tuple[Role, ...] = ("TOP", "JGL", "MID", "BOT", "SUP")
