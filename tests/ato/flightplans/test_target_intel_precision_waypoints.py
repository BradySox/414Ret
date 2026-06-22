"""Target-intel-precision shaping of per-unit target waypoints.

Under Approximate intel a DEAD/SEAD flight collapses its per-emitter target
points into a single fuzzed target-area waypoint (mobile SAMs relocate, so the
player must visually acquire). Strike always keeps exact per-unit points because
its targets are fixed installations (buildings, bunkers, bridges) that don't
move. Exact intel keeps the per-unit points for everyone.
"""

from types import SimpleNamespace
from typing import Any

from dcs.mapping import Point
from dcs.terrain import Caucasus

from game.ato.flightplans.dead import Builder as DeadBuilder
from game.ato.flightplans.sead import Builder as SeadBuilder
from game.ato.flightplans.waypointbuilder import StrikeTarget, WaypointBuilder
from game.settings.settings import TargetIntelPrecision
from game.theater.controlpoint import OffMapSpawn, Player
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import SamGroundObject
from game.utils import Heading, nautical_miles


def _sam() -> SamGroundObject:
    location = PresetLocation(
        name="loc", position=Point(0, 0, None), heading=Heading(0)  # type: ignore
    )
    control_point = OffMapSpawn(
        name="cp",
        position=Point(0, 0, None),  # type: ignore
        theater=None,  # type: ignore
        starts_blue=Player.BLUE,
    )
    return SamGroundObject(
        name="test", location=location, control_point=control_point, task=None
    )


def _make_builder(builder: Any, precision: TargetIntelPrecision) -> Any:
    """Configure a DEAD/SEAD Builder (with __init__ skipped) for a layout() call.

    Stubs out _build to capture what layout() forwards, and strike_targets_for to
    stand in for the per-unit list, so the test only exercises the precision gate.
    """
    builder.settings = SimpleNamespace(target_intel_precision=precision)
    builder.flight = SimpleNamespace(package=SimpleNamespace(target=_sam()))
    builder._build = lambda ingress, targets: ("built", targets)
    builder.strike_targets_for = lambda location: ["t0", "t1"]
    return builder


def test_dead_keeps_per_unit_points_under_exact() -> None:
    builder = _make_builder(
        DeadBuilder.__new__(DeadBuilder), TargetIntelPrecision.EXACT
    )
    assert builder.layout() == ("built", ["t0", "t1"])


def test_dead_collapses_to_area_under_approximate() -> None:
    builder = _make_builder(
        DeadBuilder.__new__(DeadBuilder), TargetIntelPrecision.APPROXIMATE
    )
    # None makes _build fall back to a single target-area waypoint.
    assert builder.layout() == ("built", None)


def test_sead_keeps_per_unit_points_under_exact() -> None:
    builder = _make_builder(
        SeadBuilder.__new__(SeadBuilder), TargetIntelPrecision.EXACT
    )
    assert builder.layout() == ("built", ["t0", "t1"])


def test_sead_collapses_to_area_under_approximate() -> None:
    builder = _make_builder(
        SeadBuilder.__new__(SeadBuilder), TargetIntelPrecision.APPROXIMATE
    )
    assert builder.layout() == ("built", None)


def _waypoint_builder(precision: TargetIntelPrecision) -> Any:
    wb: Any = WaypointBuilder.__new__(WaypointBuilder)
    wb.settings = SimpleNamespace(target_intel_precision=precision)
    wb._approximate_target_positions = {}
    return wb


def _strike_target() -> StrikeTarget:
    # A plain object (not a TheaterGroup/Unit) so the anchor falls back to .position.
    unit = SimpleNamespace(position=Point(0, 0, Caucasus()), id=1, name="ln")
    return StrikeTarget("ln #0", unit)  # type: ignore[arg-type]


def test_strike_point_is_exact_even_under_approximate() -> None:
    wb = _waypoint_builder(TargetIntelPrecision.APPROXIMATE)
    target = _strike_target()
    wp = wb.strike_point(target)
    assert wp.position == target.target.position


def test_dead_point_is_fuzzed_under_approximate() -> None:
    wb = _waypoint_builder(TargetIntelPrecision.APPROXIMATE)
    target = _strike_target()
    wp = wb.dead_point(target)
    anchor = target.target.position
    offset = anchor.distance_to_point(wp.position)
    # Fuzzed 1-3 NM off the true position so the player can't fly straight to it.
    assert nautical_miles(1).meters - 1 <= offset <= nautical_miles(3).meters + 1


def test_dead_point_is_exact_under_exact() -> None:
    wb = _waypoint_builder(TargetIntelPrecision.EXACT)
    target = _strike_target()
    wp = wb.dead_point(target)
    assert wp.position == target.target.position
