"""Long-range carrier strike planning (414th) — guard + selection logic.

The full package build (Hornet strike + A-6 tanker + E-2, forced through the range
gate with ignore_range) is exercised end-to-end by the engine probe on the real COIN
campaign; these lock the pure guards/selection so a regression can't silently return
the boat to idle: off-switch, coalition gate, carrier discovery, squadron pick, the
already-planned guard, and the ROE-respecting nearest-target choice.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import game.fourteenth.carrier_ops as co
from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType


def _sqn(*, location: Any, aircraft: str, owned: int, capable: set[FlightType]) -> Any:
    return SimpleNamespace(
        location=location,
        aircraft=SimpleNamespace(display_name=aircraft),
        owned_aircraft=owned,
        name=aircraft,
        capable_of=lambda task, cap=capable: task in cap,
    )


def _coalition(
    *,
    on: bool = True,
    blue: bool = True,
    squadrons: list[Any],
    cps: list[Any],
    packages: list[Any] | None = None,
) -> Any:
    return SimpleNamespace(
        player=SimpleNamespace(is_blue=blue),
        game=SimpleNamespace(
            settings=SimpleNamespace(long_range_carrier_ops=on),
            theater=SimpleNamespace(controlpoints=cps),
        ),
        air_wing=SimpleNamespace(iter_squadrons=lambda: iter(squadrons)),
        ato=SimpleNamespace(packages=packages or []),
    )


def _carrier(name: str = "CVN-71", player: Any = None) -> Any:
    return SimpleNamespace(is_carrier=True, captured=player, name=name)


def test_off_switch_is_a_noop() -> None:
    added: list[Any] = []
    coal = _coalition(on=False, squadrons=[], cps=[])
    coal.ato.add_package = added.append
    co.plan_carrier_strike(coal, None, SimpleNamespace())  # type: ignore[arg-type]
    assert added == []


def test_red_coalition_is_a_noop() -> None:
    added: list[Any] = []
    coal = _coalition(blue=False, squadrons=[], cps=[])
    coal.ato.add_package = added.append
    co.plan_carrier_strike(coal, None, SimpleNamespace())  # type: ignore[arg-type]
    assert added == []


def test_friendly_carrier_discovery() -> None:
    player = SimpleNamespace(is_blue=True)
    boat = _carrier(player=player)
    land = SimpleNamespace(is_carrier=False, captured=player, name="Kandahar")
    enemy_boat = _carrier(name="Kuznetsov", player=SimpleNamespace(is_blue=False))
    coal = _coalition(squadrons=[], cps=[land, enemy_boat, boat])
    coal.player = player
    found = co._friendly_carrier(coal)
    assert found is not None
    assert found.name == "CVN-71"


def test_carrier_squadron_picks_capable_stocked_biggest() -> None:
    boat = _carrier()
    hornet_big = _sqn(
        location=boat, aircraft="F/A-18C", owned=6, capable={FlightType.STRIKE}
    )
    hornet_small = _sqn(
        location=boat, aircraft="F/A-18C(2)", owned=2, capable={FlightType.STRIKE}
    )
    empty = _sqn(
        location=boat, aircraft="F/A-18C(0)", owned=0, capable={FlightType.STRIKE}
    )
    landbased = _sqn(
        location=SimpleNamespace(),
        aircraft="A-10C",
        owned=8,
        capable={FlightType.STRIKE},
    )
    incapable = _sqn(location=boat, aircraft="E-2C", owned=1, capable={FlightType.AEWC})
    coal = _coalition(
        squadrons=[hornet_small, empty, landbased, incapable, hornet_big], cps=[]
    )
    picked = co._carrier_squadron(coal, boat, FlightType.STRIKE)
    assert picked is not None
    assert picked.aircraft.display_name == "F/A-18C"  # biggest carrier strike squadron
    aewc = co._carrier_squadron(coal, boat, FlightType.AEWC)
    assert aewc is not None
    assert aewc.aircraft.display_name == "E-2C"


def test_already_planned_guard() -> None:
    boat = _carrier()
    strike = SimpleNamespace(departure=boat, flight_type=FlightType.STRIKE)
    sead = SimpleNamespace(departure=boat, flight_type=FlightType.SEAD)
    coal_clear = _coalition(
        squadrons=[], cps=[], packages=[SimpleNamespace(flights=[sead])]
    )
    coal_planned = _coalition(
        squadrons=[], cps=[], packages=[SimpleNamespace(flights=[strike])]
    )
    assert co._already_planned_from(coal_clear, boat) is False  # SEAD doesn't count
    assert co._already_planned_from(coal_planned, boat) is True


def _tgo(*, x: float, category: str = "ammo", alive: bool = True) -> Any:
    return SimpleNamespace(
        position=SimpleNamespace(x=x, y=0.0),
        category=category,
        units=[SimpleNamespace(alive=alive)],
    )


def test_nearest_target_prefers_the_nearest_alive_cache(monkeypatch: Any) -> None:
    boat = _carrier()
    boat.position = SimpleNamespace(x=0.0, distance_to_point=lambda p: abs(p.x))
    near_cache = _tgo(x=100.0)
    far_cache = _tgo(x=300.0)
    dead_cache = _tgo(x=50.0, alive=False)  # nearer, but dead -> skipped
    red_cp = SimpleNamespace(
        captured=SimpleNamespace(is_red=True),
        ground_objects=[far_cache, dead_cache, near_cache],
    )
    blue_cp = SimpleNamespace(
        captured=SimpleNamespace(is_red=False), ground_objects=[_tgo(x=1.0)]
    )
    game = SimpleNamespace(theater=SimpleNamespace(controlpoints=[red_cp, blue_cp]))
    monkeypatch.setattr(
        co, "plan_carrier_strike", co.plan_carrier_strike
    )  # keep import warm
    target = co._nearest_legal_strike_target(game, boat)  # type: ignore[arg-type]
    # nearest ALIVE cache (x=50 is dead; the blue cache at x=1 is enemy-filtered).
    assert target is near_cache


class _Pt:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def new_in_same_map(self, x: float, y: float) -> "_Pt":
        return _Pt(x, y)


def _refuel_wp(x: float, y: float) -> Any:
    return SimpleNamespace(
        name="REFUEL", waypoint_type=FlightWaypointType.REFUEL, position=_Pt(x, y)
    )


def _orbit_wp(name: str, x: float, y: float) -> Any:
    return SimpleNamespace(
        name=name, waypoint_type=FlightWaypointType.NAV, position=_Pt(x, y)
    )


def _flight(*, ftype: FlightType, departure: Any, waypoints: list[Any]) -> Any:
    f = SimpleNamespace(
        flight_type=ftype,
        departure=departure,
        flight_plan=SimpleNamespace(waypoints=waypoints),
        refuel_point_override=None,
        recreated=0,
    )

    def recreate(dump: bool = False, _f: Any = f) -> None:
        _f.recreated += 1
        # Emulate the builder honoring the override: move the REFUEL waypoint onto it.
        for wp in _f.flight_plan.waypoints:
            if wp.waypoint_type is FlightWaypointType.REFUEL:
                wp.position = _f.refuel_point_override

    f.recreate_flight_plan = recreate
    return f


def test_route_carrier_flights_to_buddy_tanker() -> None:
    player = SimpleNamespace(is_blue=True)
    boat = _carrier(player=player)
    land = SimpleNamespace(is_carrier=False, captured=player, name="Kandahar")

    # The buddy A-6 holds a racetrack centered at (100, 0).
    tanker = _flight(
        ftype=FlightType.REFUELING,
        departure=boat,
        waypoints=[
            _orbit_wp("RACETRACK START", 80.0, 0.0),
            _orbit_wp("RACETRACK END", 120.0, 0.0),
        ],
    )
    strike = _flight(
        ftype=FlightType.STRIKE, departure=boat, waypoints=[_refuel_wp(90.0, 0.0)]
    )
    strike_pkg = SimpleNamespace(
        primary_task=FlightType.STRIKE, flights=[strike, tanker]
    )

    # A commander SEAD package off the boat with a dry refuel point far up-range.
    sead = _flight(
        ftype=FlightType.SEAD_SWEEP, departure=boat, waypoints=[_refuel_wp(900.0, 0.0)]
    )
    # A land-based flight that must be left alone.
    land_bai = _flight(
        ftype=FlightType.BAI, departure=land, waypoints=[_refuel_wp(900.0, 0.0)]
    )
    sead_pkg = SimpleNamespace(primary_task=FlightType.BAI, flights=[sead, land_bai])

    coal = _coalition(squadrons=[], cps=[boat], packages=[strike_pkg, sead_pkg])
    coal.player = player

    co.route_carrier_flights_to_buddy_tanker(coal)

    # The SEAD Sweep off the boat is pinned onto the A-6 orbit center (100, 0).
    assert sead.refuel_point_override is not None
    assert (sead.refuel_point_override.x, sead.refuel_point_override.y) == (100.0, 0.0)
    assert sead.recreated == 1
    assert sead.flight_plan.waypoints[0].position.x == 100.0
    # The strike flight (in-package tanker) and the land flight are untouched.
    assert strike.refuel_point_override is None
    assert land_bai.refuel_point_override is None
    assert land_bai.recreated == 0
