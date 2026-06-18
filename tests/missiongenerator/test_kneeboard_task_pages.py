from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from dcs.vehicles import AirDefence

from game.ato.flighttype import FlightType
from game.missiongenerator.kneeboard import SeadTaskPage
from game.settings.settings import TargetIntelPrecision


class _DummyPosition:
    def __init__(self, location: str) -> None:
        self.location = location
        self.x = 0.0
        self.y = 0.0

    def latlng(self) -> SimpleNamespace:
        return SimpleNamespace(
            format_dms=lambda include_decimal_seconds=True: self.location
        )


def _flight(flight_type: FlightType, precision: TargetIntelPrecision) -> Any:
    settings = SimpleNamespace(target_intel_precision=precision)
    return SimpleNamespace(
        flight_type=flight_type,
        squadron=SimpleNamespace(
            coalition=SimpleNamespace(game=SimpleNamespace(settings=settings))
        ),
        package=SimpleNamespace(target=None),
    )


def _target(location: str) -> Any:
    return SimpleNamespace(
        type=SimpleNamespace(name="SA-6 STR", id=AirDefence.Kub_1S91_str.id),
        name="Tracking Radar",
        position=_DummyPosition(location),
    )


def test_dead_task_page_uses_cue_even_with_exact_intel() -> None:
    page = SeadTaskPage(_flight(FlightType.DEAD, TargetIntelPrecision.EXACT), False)

    row = page.target_info_row(_target("N 35 00 00 E 36 00 00"), {})

    assert row[3] == "Search around target area waypoint"


def test_sead_task_page_keeps_exact_coords_with_exact_intel() -> None:
    page = SeadTaskPage(_flight(FlightType.SEAD, TargetIntelPrecision.EXACT), False)

    row = page.target_info_row(_target("N 35 00 00 E 36 00 00"), {})

    assert row[3] == "N 35 00 00 E 36 00 00"
