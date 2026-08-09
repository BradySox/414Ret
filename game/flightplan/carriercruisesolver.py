"""Solve carrier heading and speed for a requested wind over deck.

Headings use the repository convention: 0 degrees is north and headings increase
clockwise.  Wind direction follows DCS convention and is the direction the wind
blows toward.  The returned apparent-wind components are expressed as the
wind-from vector (carrier velocity minus ambient wind), down the angled deck.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

DEFAULT_WIND_OVER_DECK = 25.0


class CarrierCruiseMode(Enum):
    EXACT = "exact"
    WEAK_WIND_APPROXIMATION = "weak_wind_approximation"
    HIGH_WIND_SPEED_CLAMP = "high_wind_speed_clamp"


@dataclass(frozen=True)
class CarrierCruiseResult:
    heading: float
    carrier_speed: float
    wind_over_deck: float
    down_deck_component: float
    crosswind_component: float
    mode: CarrierCruiseMode


def solve_carrier_cruise(
    wind_direction: float,
    wind_speed: float,
    deck_angle: float,
    target_wind_over_deck: float = DEFAULT_WIND_OVER_DECK,
) -> CarrierCruiseResult:
    """Return a carrier vector producing the requested wind over deck in knots."""
    target = max(0.0, target_wind_over_deck)
    wind = max(0.0, wind_speed)
    angle = math.radians(deck_angle)
    threshold = target * abs(math.sin(angle))

    if wind < threshold and threshold > 0.0:
        heading = _normalize_heading(wind_direction + 180.0)
        speed = max(0.0, target - wind)
        down_deck = target * math.cos(angle)
        crosswind = target * math.sin(angle)
        return CarrierCruiseResult(
            heading,
            speed,
            math.hypot(down_deck, crosswind),
            down_deck,
            crosswind,
            CarrierCruiseMode.WEAK_WIND_APPROXIMATION,
        )

    if wind == 0.0:
        heading = _normalize_heading(wind_direction + 180.0)
        return CarrierCruiseResult(
            heading,
            target,
            target,
            target * math.cos(angle),
            target * math.sin(angle),
            (
                CarrierCruiseMode.EXACT
                if angle == 0.0
                else CarrierCruiseMode.WEAK_WIND_APPROXIMATION
            ),
        )

    cross_term = target * math.sin(angle)
    along_speed_squared = wind * wind - cross_term * cross_term
    solved_speed = target * math.cos(angle) - math.sqrt(max(0.0, along_speed_squared))
    if solved_speed < 0.0:
        heading = _normalize_heading(wind_direction + 180.0 - deck_angle)
        return CarrierCruiseResult(
            heading,
            0.0,
            wind,
            wind,
            0.0,
            CarrierCruiseMode.HIGH_WIND_SPEED_CLAMP,
        )

    offset = math.degrees(math.asin(max(-1.0, min(1.0, cross_term / wind))))
    heading = _normalize_heading(wind_direction + 180.0 - offset)
    return CarrierCruiseResult(
        heading,
        solved_speed,
        target,
        target,
        0.0,
        CarrierCruiseMode.EXACT,
    )


def _normalize_heading(heading: float) -> float:
    return heading % 360.0
