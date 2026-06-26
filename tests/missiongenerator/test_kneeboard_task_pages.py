from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from dcs.vehicles import AirDefence

from game.ato.flighttype import FlightType
from game.missiongenerator.kneeboard import KneeboardGenerator, SeadTaskPage
from game.missiongenerator.scarluadata import ScarTasking
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

    def heading_between_point(self, other: Any) -> float:
        return 0.0

    def distance_to_point(self, other: Any) -> float:
        return 0.0


def _bullseye() -> Any:
    return SimpleNamespace(position=_DummyPosition("bullseye"))


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


def test_dead_task_page_consolidates_to_single_site_cue() -> None:
    # DEAD uses the cue view even with EXACT intel, but the cue is now ONE bullseye
    # for the center of the site (not one per unit), so the per-unit table carries no
    # cue/coords column.
    flight = _flight(FlightType.DEAD, TargetIntelPrecision.EXACT)
    flight.package.target = SimpleNamespace(position=_DummyPosition("site center"))
    page = SeadTaskPage(flight, _bullseye(), False)

    assert page._use_target_area_cues is True
    assert (
        page._bullseye_cue_for(flight.package.target.position) == "Bullseye 000 for 0"
    )

    # target_info_row is the EXACT (SEAD) path now: steerpoint + coords, no cue.
    row = page.target_info_row(_target("N 35 00 00 E 36 00 00"), 3)
    assert row[0] == "3"
    assert row[1] == "SA-6 STR"
    assert row[3] == "N 35 00 00 E 36 00 00"


def _kneeboard_generator(taskings: list[ScarTasking]) -> KneeboardGenerator:
    mission = SimpleNamespace(start_time=SimpleNamespace(hour=12))
    game = SimpleNamespace(settings=SimpleNamespace(generate_dark_kneeboard=False))
    return KneeboardGenerator(mission, game, taskings)  # type: ignore[arg-type]


def test_scar_tasking_is_matched_to_its_flight_by_target() -> None:
    # The kneeboard links a SCAR flight to its tasking by the identity of the package
    # target (same generation pass), so the right signature lands on the right page.
    target = object()
    mine = ScarTasking(
        tasking_id="blue-scar-1",
        variant="spawn",
        target_id=id(target),
        signature_text="1x SA-9 + 1x command vehicle + 2x truck",
    )
    theirs = ScarTasking(
        tasking_id="blue-scar-2", variant="spawn", target_id=id(object())
    )
    gen = _kneeboard_generator([theirs, mine])

    flight = SimpleNamespace(package=SimpleNamespace(target=target))
    assert gen._scar_tasking_for(flight) is mine  # type: ignore[arg-type]

    # A target with no tasking (or a flight with no target) resolves to None.
    stray = SimpleNamespace(package=SimpleNamespace(target=object()))
    assert gen._scar_tasking_for(stray) is None  # type: ignore[arg-type]
    none_target = SimpleNamespace(package=SimpleNamespace(target=None))
    assert gen._scar_tasking_for(none_target) is None  # type: ignore[arg-type]


def test_sead_task_page_keeps_exact_coords_with_exact_intel() -> None:
    page = SeadTaskPage(
        _flight(FlightType.SEAD, TargetIntelPrecision.EXACT), _bullseye(), False
    )

    row = page.target_info_row(_target("N 35 00 00 E 36 00 00"), 3)

    assert row[0] == "3"
    assert row[3] == "N 35 00 00 E 36 00 00"
