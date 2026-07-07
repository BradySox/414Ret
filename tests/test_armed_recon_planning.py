"""Armed Recon package composition (414th call): a 4-ship sweep + an auto-added
recon drone + the (threat-gated) SEAD escort.

Three layers are pinned here:
- ``PlanArmedRecon.propose_flights`` proposes a fixed 4-ship ARMED_RECON primary
  plus the common escorts (SEAD/A2A, pruned later if unthreatened).
- ``PackageFulfiller._maybe_plan_tarps_recon`` frags an optional recon flight into
  an ARMED_RECON package (as it already does for Strike/DEAD). On a drone-fielding
  faction the auto-assignable TARPS squadron is the drone, so this is the "1 drone
  in each armed recon package" wiring. It never scrubs the package.
- ``Builder._stand_off_search_point`` pulls the ARMED RECON fly-over point off the
  target area toward the ingress point (the 2026-07-06 flown finding: the search
  point sat dead-centre on the Shirqat FOB's SA-13/ZU-23 garrison), standing off
  past the target's own threat rings while keeping the target inside the hunt zone.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from dcs import Point
from dcs.terrain import Caucasus

from game.ato.flightplans.armedrecon import (
    Builder,
    MIN_SEARCH_STANDOFF,
    SEARCH_STANDOFF_BUFFER,
)
from game.ato.flighttype import FlightType
from game.commander.packagefulfiller import PackageFulfiller
from game.commander.tasks.primitive.armedrecon import PlanArmedRecon
from game.theater.controlpoint import Fob
from game.utils import Distance, meters, nautical_miles


def test_armed_recon_proposes_a_four_ship_sweep_plus_escorts() -> None:
    task = PlanArmedRecon(cast(Any, SimpleNamespace(name="Some CP")))
    task.propose_flights()

    recon = [f for f in task.flights if f.task is FlightType.ARMED_RECON]
    assert len(recon) == 1
    assert recon[0].num_aircraft == 4  # fixed 4-ship, not the 2-4 flight-size roll

    # The common escorts ride along (SEAD escort + A2A), pruned downstream when the
    # route is unthreatened -- on the OIR/Red Tide factions the SEAD escort resolves
    # to the Viper, i.e. "2 SEAD Vipers".
    escort_tasks = {f.task for f in task.flights if f.escort_type is not None}
    assert FlightType.SEAD_ESCORT in escort_tasks
    assert FlightType.ESCORT in escort_tasks


def _fulfiller(auto_add: bool, can_plan_tarps: bool) -> PackageFulfiller:
    ff = PackageFulfiller.__new__(PackageFulfiller)
    ff.auto_add_tarps_recon = auto_add
    ff.air_wing_can_plan = lambda mission_type: (  # type: ignore[method-assign]
        can_plan_tarps and mission_type is FlightType.TARPS
    )
    return ff


def _armed_recon_builder(planned: list[Any]) -> Any:
    primary = SimpleNamespace(flight_type=FlightType.ARMED_RECON)

    def plan_flight(proposed: Any, ignore_range: bool) -> bool:
        planned.append(proposed)
        return True

    return SimpleNamespace(
        package=SimpleNamespace(primary_flight=primary),
        plan_flight=plan_flight,
    )


def test_armed_recon_package_frags_a_recon_drone() -> None:
    planned: list[Any] = []
    ff = _fulfiller(auto_add=True, can_plan_tarps=True)
    builder = _armed_recon_builder(planned)
    # The Armed Recon target is a control point (no warrants_recon gate applies).
    mission = SimpleNamespace(location=SimpleNamespace(name="Mosul"))

    ff._maybe_plan_tarps_recon(
        cast(Any, mission), cast(Any, builder), ignore_range=False
    )

    assert [p.task for p in planned] == [FlightType.TARPS]
    assert planned[0].num_aircraft == 1  # a single recon bird / drone


def test_recon_drone_skipped_when_the_setting_is_off() -> None:
    planned: list[Any] = []
    ff = _fulfiller(auto_add=False, can_plan_tarps=True)
    builder = _armed_recon_builder(planned)
    mission = SimpleNamespace(location=SimpleNamespace(name="Mosul"))

    ff._maybe_plan_tarps_recon(
        cast(Any, mission), cast(Any, builder), ignore_range=False
    )

    assert planned == []  # gated by auto_add_tarps_recon


def test_recon_drone_skipped_when_no_tarps_squadron() -> None:
    planned: list[Any] = []
    ff = _fulfiller(auto_add=True, can_plan_tarps=False)
    builder = _armed_recon_builder(planned)
    mission = SimpleNamespace(location=SimpleNamespace(name="Mosul"))

    ff._maybe_plan_tarps_recon(
        cast(Any, mission), cast(Any, builder), ignore_range=False
    )

    assert planned == []  # no drone/TARPS bird available -> package flies as-is


_TERRAIN = Caucasus()
_TARGET_POS = Point(0, 0, _TERRAIN)


def _standoff_builder(
    target: Any, ingress_pos: Point, zone_nm: int = 10
) -> tuple[Builder, Any]:
    """A Builder + layout pair wired with just what _stand_off_search_point reads."""
    builder = Builder.__new__(Builder)
    builder.flight = cast(Any, SimpleNamespace(package=SimpleNamespace(target=target)))
    builder.settings = cast(
        Any, SimpleNamespace(armed_recon_engagement_range_distance=zone_nm)
    )
    layout = SimpleNamespace(
        ingress=SimpleNamespace(position=ingress_pos),
        targets=[SimpleNamespace(position=target.position)],
    )
    return builder, layout


def _fob(threat_ranges: list[Distance]) -> Fob:
    """A bare Fob control point carrying fake TGOs with the given threat rings."""
    fob = Fob.__new__(Fob)
    fob.position = _TARGET_POS
    fob.connected_objectives = [
        cast(Any, SimpleNamespace(max_threat_range=lambda r=r: r))
        for r in threat_ranges
    ]
    return fob


def _moved_distance(layout: Any) -> float:
    return layout.targets[0].position.distance_to_point(_TARGET_POS)


def test_search_point_stands_off_an_undefended_target_by_the_floor() -> None:
    builder, layout = _standoff_builder(_fob([]), Point(0, 100_000, _TERRAIN))
    builder._stand_off_search_point(cast(Any, layout))

    # No threat rings -> the 5 NM floor, pushed along the target->ingress bearing.
    assert _moved_distance(layout) == pytest.approx(MIN_SEARCH_STANDOFF.meters)
    assert layout.targets[0].position.y > 0  # toward the ingress point


def test_search_point_stands_off_past_the_targets_own_threat_rings() -> None:
    fob = _fob([meters(5_000), meters(10_000)])
    builder, layout = _standoff_builder(fob, Point(0, 100_000, _TERRAIN))
    builder._stand_off_search_point(cast(Any, layout))

    expected = meters(10_000) + SEARCH_STANDOFF_BUFFER  # longest ring + buffer
    assert _moved_distance(layout) == pytest.approx(expected.meters)


def test_search_point_standoff_is_capped_at_the_hunt_zone_radius() -> None:
    # A MERAD-defended target (24 km ring) with a 10 NM engage zone: the standoff
    # caps at the zone radius so the target area stays inside the search zone.
    builder, layout = _standoff_builder(
        _fob([meters(24_000)]), Point(0, 100_000, _TERRAIN), zone_nm=10
    )
    builder._stand_off_search_point(cast(Any, layout))

    assert _moved_distance(layout) == pytest.approx(nautical_miles(10).meters)


def test_search_point_standoff_never_overshoots_the_ingress_point() -> None:
    builder, layout = _standoff_builder(_fob([]), Point(0, 4_000, _TERRAIN))
    builder._stand_off_search_point(cast(Any, layout))

    assert _moved_distance(layout) == pytest.approx(4_000)


def test_target_area_threat_range_reads_the_control_points_tgos() -> None:
    builder, _ = _standoff_builder(
        _fob([meters(2_500), meters(9_000)]), Point(0, 100_000, _TERRAIN)
    )
    assert builder._target_area_threat_range() == meters(9_000)


def test_target_area_threat_range_is_zero_for_a_plain_mission_target() -> None:
    target = SimpleNamespace(position=_TARGET_POS)
    builder, _ = _standoff_builder(cast(Any, target), Point(0, 100_000, _TERRAIN))
    assert builder._target_area_threat_range() == meters(0)
