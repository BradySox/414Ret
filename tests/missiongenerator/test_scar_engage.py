"""SCAR ("Sandy") patrol engages ground threats (rescue rework, in-game fix).

An AI SCAR flight previously got no engage task on its racetrack (only CAP did),
so it just orbited and never reacted (in-game finding 2026-06-27).
``RaceTrackBuilder._engage_targets_task`` now gives SCAR a GROUND engage task while
CAP keeps air and rescue craft (Combat SAR) keep a pure orbit.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from dcs.task import EngageTargets

from game.ato.flighttype import FlightType
from game.missiongenerator.aircraft.waypoints.racetrack import RaceTrackBuilder
from game.utils import nautical_miles


def _engage(flight_type: FlightType) -> Any:
    builder = RaceTrackBuilder.__new__(RaceTrackBuilder)
    builder.flight = cast(Any, SimpleNamespace(flight_type=flight_type))
    fp = SimpleNamespace(engagement_distance=nautical_miles(5))
    return builder._engage_targets_task(cast(Any, fp))


def test_scar_patrol_gets_a_ground_engage_task() -> None:
    assert isinstance(_engage(FlightType.SCAR), EngageTargets)


def test_cap_patrol_keeps_an_air_engage_task() -> None:
    assert isinstance(_engage(FlightType.BARCAP), EngageTargets)


def test_scar_and_cap_engage_different_targets() -> None:
    # SCAR engages ground, CAP engages air -> the tasks must differ.
    assert _engage(FlightType.SCAR).params != _engage(FlightType.BARCAP).params


def test_rescue_craft_and_awacs_keep_a_pure_orbit() -> None:
    # Combat SAR helo/King fly defensive transport; AEW&C just orbits. No engage.
    assert _engage(FlightType.COMBAT_SAR) is None
    assert _engage(FlightType.AEWC) is None
