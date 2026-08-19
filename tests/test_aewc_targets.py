"""AEW&C target selection (theaterstate._aewc_targets).

With a front the land anchor stays the stock rear-safe farthest-from-threats CP;
with NO front the support orbit holds AT its target (no FLOT to march against), so
the anchor must be the friendly CP nearest the enemy — the flown Scenic Route
Merged A-50 orbited its rearmost home base 424 NM from the enemy fleet before this.
Carrier targets are unaffected either way.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.commander.theaterstate import _aewc_targets


def _cp(name: str, carrier: bool = False) -> Any:
    return SimpleNamespace(name=name, is_carrier=carrier)


def _finder(
    *,
    fronts: list[Any],
    cps: list[Any],
    farthest: Any,
    closest: Any,
    anchor: Any = None,
    forward_anchor: Any = None,
) -> Any:
    return SimpleNamespace(
        friendly_control_points=lambda: iter(cps),
        front_lines=lambda: iter(fronts),
        farthest_friendly_control_point=lambda: farthest,
        closest_friendly_control_point=lambda: closest,
        # ObjectiveFinder.aewc_land_anchor: the rear pick, biased toward a field
        # that actually hosts an AWACS. Defaults to the stock rear pick here.
        aewc_land_anchor=lambda: farthest if anchor is None else anchor,
        # ObjectiveFinder.forward_aewc_land_anchor: the front-less pick, biased the
        # same way. Defaults to the stock closest pick here.
        forward_aewc_land_anchor=(
            lambda: closest if forward_anchor is None else forward_anchor
        ),
    )


def test_fronted_theater_keeps_the_rear_anchor() -> None:
    boat, rear, forward = _cp("CVN", carrier=True), _cp("Rear"), _cp("Forward")
    finder = _finder(
        fronts=[object()], cps=[boat, rear, forward], farthest=rear, closest=forward
    )
    assert _aewc_targets(finder) == [boat, rear]


def test_fronted_theater_takes_the_awacs_hosting_field() -> None:
    # The anchor the orbit is built around follows the AWACS: a rear field 1.1 NM
    # safer is not worth a 245 NM transit for the wing's only E-3.
    boat, rear, host = _cp("CVN", carrier=True), _cp("Rear"), _cp("AwacsHome")
    finder = _finder(
        fronts=[object()],
        cps=[boat, rear, host],
        farthest=rear,
        closest=host,
        anchor=host,
    )
    assert _aewc_targets(finder) == [boat, host]


def test_frontless_theater_anchors_on_the_forward_field() -> None:
    boat, rear, forward = _cp("CVN", carrier=True), _cp("Rear"), _cp("Forward")
    finder = _finder(
        fronts=[], cps=[boat, rear, forward], farthest=rear, closest=forward
    )
    assert _aewc_targets(finder) == [boat, forward]


def test_frontless_theater_takes_the_awacs_hosting_field() -> None:
    # Test 9 (2026-08-18): a front-less Syria turn anchored on Ben Gurion, the CP
    # nearest the enemy, which hosts no AWACS -- while the wing's only land E-3A
    # sat at Akrotiri and flew 182 NM each way to reach its own orbit. The forward
    # pick is now basing-aware like the rear one.
    boat, forward, host = _cp("CVN", carrier=True), _cp("Forward"), _cp("AwacsHome")
    finder = _finder(
        fronts=[],
        cps=[boat, forward, host],
        farthest=host,
        closest=forward,
        forward_anchor=host,
    )
    assert _aewc_targets(finder) == [boat, host]


# ---- PlanAewc basing-aware squadron preference --------------------------------
#
# The generic ranking measures base-to-target distance, and a carrier can sit
# closer to the land AEW&C anchor than the land AWACS base does (Scenic Route
# Merged: both E-2s tasked, one dragged 160 NM to the land station, both E-3s
# idle). A carrier station prefers that boat's own squadron; a land station the
# nearest land-based AWACS squadron; no such squadron -> None (generic ranking).


def _aewc_sqn(aircraft: str, location: Any, untasked: int = 2) -> Any:
    from game.ato.flighttype import FlightType

    return SimpleNamespace(
        aircraft=aircraft,
        location=location,
        untasked_aircraft=untasked,
        capable_of=lambda task: task is FlightType.AEWC,
    )


def _plan_aewc(target: Any, squadrons: list[Any]) -> Any:
    from game.commander.tasks.primitive.aewc import PlanAewc

    task = PlanAewc(target)
    task._air_wing = SimpleNamespace(  # type: ignore[assignment]
        iter_squadrons=lambda: iter(squadrons)
    )
    return task


class _XY:
    def __init__(self, x: float, y: float) -> None:
        self.x, self.y = x, y

    def distance_to_point(self, other: "_XY") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


def test_land_station_prefers_the_land_awacs() -> None:
    land_target = SimpleNamespace(
        name="Khasab", is_carrier=False, is_fleet=False, position=_XY(0, 0)
    )
    boat = SimpleNamespace(is_carrier=True, is_fleet=True, position=_XY(120_000, 0))
    dhafra = SimpleNamespace(
        is_carrier=False, is_fleet=False, position=_XY(-250_000, 0)
    )
    # The boat is CLOSER to the target than the land base -- the old ranking's trap.
    squadrons = [_aewc_sqn("E-2C", boat), _aewc_sqn("E-3A", dhafra)]
    assert _plan_aewc(land_target, squadrons)._preferred_aewc_type() == "E-3A"


def test_carrier_station_prefers_its_own_squadron() -> None:
    boat = SimpleNamespace(is_carrier=True, is_fleet=True, position=_XY(0, 0))
    dhafra = SimpleNamespace(is_carrier=False, is_fleet=False, position=_XY(10_000, 0))
    squadrons = [_aewc_sqn("E-3A", dhafra), _aewc_sqn("E-2C", boat)]
    assert _plan_aewc(boat, squadrons)._preferred_aewc_type() == "E-2C"


def test_no_matching_basing_falls_back_to_generic_ranking() -> None:
    land_target = SimpleNamespace(
        name="FOB", is_carrier=False, is_fleet=False, position=_XY(0, 0)
    )
    boat = SimpleNamespace(is_carrier=True, is_fleet=True, position=_XY(50_000, 0))
    # All-carrier wing: no land AWACS -> None, the E-2 still covers the land
    # station through the generic ranking.
    assert (
        _plan_aewc(land_target, [_aewc_sqn("E-2C", boat)])._preferred_aewc_type()
        is None
    )
    # And a tasked-out land squadron doesn't count.
    dhafra = SimpleNamespace(is_carrier=False, is_fleet=False, position=_XY(-9_000, 0))
    squadrons = [_aewc_sqn("E-2C", boat), _aewc_sqn("E-3A", dhafra, untasked=0)]
    assert _plan_aewc(land_target, squadrons)._preferred_aewc_type() is None


# ---- ObjectiveFinder._aewc_hosting_anchor -------------------------------------
#
# Where the direction actually lives. Both anchors share one walk over the
# unthreatened land CPs that host a usable AWACS; the rear pick takes the one
# farthest from threats, the forward pick the one nearest.


def _host_cp(name: str, threat_distance: float, hosts_awacs: bool = True) -> Any:
    from game.ato.flighttype import FlightType

    squadrons = (
        [
            SimpleNamespace(
                capable_of=lambda task: task is FlightType.AEWC, untasked_aircraft=2
            )
        ]
        if hosts_awacs
        else []
    )
    return SimpleNamespace(
        name=name,
        is_carrier=False,
        squadrons=squadrons,
        position=SimpleNamespace(name=name, threat_distance=threat_distance),
    )


def _objective_finder(
    cps: list[Any], *, threatened: frozenset[str] = frozenset()
) -> Any:
    from game.commander.objectivefinder import ObjectiveFinder
    from game.theater import Player
    from game.utils import meters

    finder = ObjectiveFinder.__new__(ObjectiveFinder)
    finder.is_player = Player.BLUE
    zones = SimpleNamespace(
        threatened=lambda pos: pos.name in threatened,
        distance_to_threat=lambda pos: meters(pos.threat_distance),
    )
    finder.game = SimpleNamespace(threat_zone_for=lambda _: zones)  # type: ignore[assignment]
    finder.friendly_control_points = lambda: iter(cps)  # type: ignore[method-assign]
    return finder


def test_the_rear_anchor_takes_the_farthest_hosting_field() -> None:
    near, far = _host_cp("Near", 10_000), _host_cp("Far", 300_000)
    assert _objective_finder([near, far])._aewc_hosting_anchor(forward=False) is far


def test_the_forward_anchor_takes_the_nearest_hosting_field() -> None:
    near, far = _host_cp("Near", 10_000), _host_cp("Far", 300_000)
    assert _objective_finder([near, far])._aewc_hosting_anchor(forward=True) is near


def test_a_field_with_no_awacs_is_never_the_anchor() -> None:
    # The test 9 defect: Ben Gurion was nearest the enemy and hosted nothing.
    bare, host = _host_cp("Bare", 10_000, hosts_awacs=False), _host_cp("Host", 300_000)
    finder = _objective_finder([bare, host])
    assert finder._aewc_hosting_anchor(forward=True) is host


def test_a_threatened_field_is_never_the_anchor() -> None:
    exposed, safe = _host_cp("Exposed", 5_000), _host_cp("Safe", 50_000)
    finder = _objective_finder([exposed, safe], threatened=frozenset({"Exposed"}))
    assert finder._aewc_hosting_anchor(forward=True) is safe


def test_no_hosting_field_returns_none_so_each_caller_falls_back() -> None:
    bare = _host_cp("Bare", 10_000, hosts_awacs=False)
    finder = _objective_finder([bare])
    assert finder._aewc_hosting_anchor(forward=True) is None
    assert finder._aewc_hosting_anchor(forward=False) is None
