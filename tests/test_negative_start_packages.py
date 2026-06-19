"""Regression tests for the "past start times" warning (QTopPanel).

A defensive air patrol (BARCAP/TARCAP) is meant to be on-station at mission start,
so a cold-start spin-up that begins before mission start is expected -- and a
player-occupied cold-start BARCAP (10-min player startup allowance vs the 2-min AI
estimate the scheduler reserves) would otherwise trip the warning every turn. For
CAP the check uses takeoff time (ignoring the ground spin-up); other tasks keep the
startup-before-mission-start rule.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

from game.ato.flighttype import FlightType
from qt_ui.widgets.QTopPanel import QTopPanel

NOW = datetime(2020, 1, 1, 12, 0, 0)


def _flight(*, takeoff: datetime, startup: datetime) -> Any:
    return SimpleNamespace(
        state=SimpleNamespace(is_waiting_for_start=True),
        flight_plan=SimpleNamespace(
            takeoff_time=lambda: takeoff,
            startup_time=lambda: startup,
        ),
    )


def _package(task: FlightType, flights: list[Any]) -> Any:
    return SimpleNamespace(
        primary_task=task, flights=flights, target=SimpleNamespace(name="X")
    )


def _panel(packages: list[Any]) -> Any:
    panel: Any = QTopPanel.__new__(QTopPanel)
    panel.game_model = SimpleNamespace(
        ato_model=SimpleNamespace(ato=SimpleNamespace(packages=packages))
    )
    return panel


def test_cold_start_cap_not_flagged_for_pre_mission_spinup() -> None:
    # Player cold-start BARCAP: spin-up begins before mission start, takeoff after.
    flight = _flight(
        takeoff=NOW + timedelta(minutes=5), startup=NOW - timedelta(minutes=8)
    )
    panel = _panel([_package(FlightType.BARCAP, [flight])])
    assert panel.negative_start_packages(NOW) == []


def test_cap_flagged_when_it_cannot_even_take_off_in_time() -> None:
    # Takeoff itself is before mission start -> genuinely unachievable, still warn.
    flight = _flight(
        takeoff=NOW - timedelta(minutes=1), startup=NOW - timedelta(minutes=11)
    )
    pkg = _package(FlightType.TARCAP, [flight])
    assert _panel([pkg]).negative_start_packages(NOW) == [pkg]


def test_strike_still_flagged_on_startup_before_mission_start() -> None:
    # Non-CAP keeps the original startup-before-mission-start rule.
    flight = _flight(
        takeoff=NOW + timedelta(minutes=5), startup=NOW - timedelta(minutes=2)
    )
    pkg = _package(FlightType.STRIKE, [flight])
    assert _panel([pkg]).negative_start_packages(NOW) == [pkg]


def test_strike_not_flagged_when_startup_after_mission_start() -> None:
    flight = _flight(
        takeoff=NOW + timedelta(minutes=10), startup=NOW + timedelta(minutes=1)
    )
    pkg = _package(FlightType.STRIKE, [flight])
    assert _panel([pkg]).negative_start_packages(NOW) == []
