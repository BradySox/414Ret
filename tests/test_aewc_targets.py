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
# Where the direction actually lives. Both anchors share one walk over the LAND
# CPs that host a usable AWACS; an unthreatened field beats a threatened one, the
# rear pick takes the one farthest from threats and the forward pick the nearest.


def _host_cp(
    name: str,
    threat_distance: float,
    hosts_awacs: bool = True,
    hosts: Any = None,
    fleet: bool = False,
) -> Any:
    from game.ato.flighttype import FlightType

    capability = hosts if hosts is not None else FlightType.AEWC
    squadrons = (
        [
            SimpleNamespace(
                capable_of=lambda task: task is capability, untasked_aircraft=2
            )
        ]
        if hosts_awacs
        else []
    )
    return SimpleNamespace(
        name=name,
        is_carrier=False,
        is_fleet=fleet,
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


def test_an_unthreatened_field_beats_a_threatened_one() -> None:
    exposed, safe = _host_cp("Exposed", 5_000), _host_cp("Safe", 50_000)
    finder = _objective_finder([exposed, safe], threatened=frozenset({"Exposed"}))
    assert finder._aewc_hosting_anchor(forward=True) is safe


def test_no_hosting_field_returns_none_so_each_caller_falls_back() -> None:
    bare = _host_cp("Bare", 10_000, hosts_awacs=False)
    finder = _objective_finder([bare])
    assert finder._aewc_hosting_anchor(forward=True) is None
    assert finder._aewc_hosting_anchor(forward=False) is None


# ---- tanker stations (2026-08-19) ---------------------------------------------


def test_every_carrier_gets_its_own_tanker_station_plus_one_ashore() -> None:
    from game.commander.theaterstate import _refueling_targets

    boat, spare, ashore = (
        _cp("CVN", carrier=True),
        _cp("CVN-2", carrier=True),
        _cp("Base"),
    )
    finder = SimpleNamespace(
        friendly_control_points=lambda: iter([boat, spare, ashore]),
        tanker_land_anchor=lambda: ashore,
    )
    assert _refueling_targets(finder) == [boat, spare, ashore]  # type: ignore[arg-type]


def test_the_tanker_land_anchor_takes_a_tanker_hosting_field() -> None:
    # Test 9 follow-up: the stock pick was the CP nearest the enemy and hosted no
    # tanker, leaving the KC-135 151 NM and the carrier A-6E 173 NM from station.
    from game.ato.flighttype import FlightType

    bare = _host_cp("Bare", 10_000, hosts_awacs=False)
    host = _host_cp("TankerHome", 300_000, hosts=FlightType.REFUELING)
    finder = _objective_finder([bare, host])
    assert finder._support_hosting_anchor(FlightType.REFUELING, forward=True) is host


# ---- the land anchor must be land (test 36, 2026-09-17) -----------------------
#
# Every blue field on Long Road to H3 turn 1 sat inside red's threat zone, so the
# hosting walk found nothing and the anchor fell back to the generic farthest-CP
# pick, which filtered only off-map spawns. It came back LHA-1 Tarawa, 3.29 NM from
# CVN-71: CVN-71's one E-2C squadron flew two racetracks 14.9 NM apart.


def test_an_lha_is_never_the_land_anchor() -> None:
    # Lha never overrides is_carrier, so the old is_carrier filter let it through.
    lha = _host_cp("LHA", 900_000, fleet=True)
    field = _host_cp("Field", 10_000)
    finder = _objective_finder([lha, field])
    assert finder._aewc_hosting_anchor(forward=False) is field
    assert finder._land_support_fallback(forward=False) is field


def test_with_every_field_threatened_the_shallowest_host_is_taken() -> None:
    # distance_to_threat is unsigned: inside the zone it is the DEPTH. The old
    # rear pick maximised it and chose the field deepest in enemy airspace.
    shallow = _host_cp("Shallow", 5_000)
    deep = _host_cp("Deep", 60_000)
    finder = _objective_finder(
        [shallow, deep], threatened=frozenset({"Shallow", "Deep"})
    )
    assert finder._aewc_hosting_anchor(forward=False) is shallow
    assert finder._aewc_hosting_anchor(forward=True) is shallow


def test_a_threatened_host_is_used_rather_than_none() -> None:
    # Incirlik held the E-3A with two untasked jets and was skipped as threatened.
    only = _host_cp("Incirlik", 20_000)
    finder = _objective_finder([only], threatened=frozenset({"Incirlik"}))
    assert finder._aewc_hosting_anchor(forward=False) is only


def test_a_threatened_host_is_skipped_while_any_field_is_clear() -> None:
    # The threatened-host rule is for a theatre with no clear field at all. With one
    # clear field, a threatened host's orbit is laid from the nearest edge with no
    # guarantee it clears a second zone; the clear field's fallback orbit does. The
    # walk returns None and the caller falls back to the clear field, as before.
    host = _host_cp("ThreatenedHost", 18_500)
    clear = _host_cp("ClearNoAwacs", 395_000, hosts_awacs=False)
    finder = _objective_finder([host, clear], threatened=frozenset({"ThreatenedHost"}))
    assert finder._aewc_hosting_anchor(forward=False) is None
    assert finder._land_support_fallback(forward=False) is clear


def test_an_all_fleet_wing_has_no_land_anchor() -> None:
    boats = [_host_cp("CVN", 900_000, fleet=True), _host_cp("LHA", 5, fleet=True)]
    finder = _objective_finder(boats)
    assert finder._aewc_hosting_anchor(forward=False) is None
    assert finder._land_support_fallback(forward=False) is None
    assert finder._land_support_fallback(forward=True) is None


def test_no_land_anchor_leaves_the_carriers_alone() -> None:
    boat = _cp("CVN", carrier=True)
    finder = SimpleNamespace(
        friendly_control_points=lambda: iter([boat]),
        front_lines=lambda: iter([object()]),
        aewc_land_anchor=lambda: None,
    )
    assert _aewc_targets(finder) == [boat]  # type: ignore[arg-type]


def test_an_anchor_already_in_the_list_is_not_added_twice() -> None:
    # Latent on brady.retribution turn 3: the old fallback returned CVN-71, already
    # a carrier target. Only the hosting walk finding Incirlik first hid it.
    boat = _cp("CVN", carrier=True)
    finder = SimpleNamespace(
        friendly_control_points=lambda: iter([boat]),
        front_lines=lambda: iter([object()]),
        aewc_land_anchor=lambda: boat,
    )
    assert _aewc_targets(finder) == [boat]  # type: ignore[arg-type]


def test_the_tanker_list_is_deduped_the_same_way() -> None:
    from game.commander.theaterstate import _refueling_targets

    boat = _cp("CVN", carrier=True)
    for anchor in (boat, None):
        finder = SimpleNamespace(
            friendly_control_points=lambda: iter([boat]),
            tanker_land_anchor=lambda anchor=anchor: anchor,
        )
        assert _refueling_targets(finder) == [boat]  # type: ignore[arg-type]
