"""Tests for the in-app fuel-plan readout (§46 UI surfacing).

The brief must tell the same story as the kneeboard ladder and the tanker
decision: same per-leg walk, tanker top-offs applied at REFUEL waypoints, the
walk ends at the landing point (divert/bullseye reference waypoints are not
flown legs), and external fuel counts the tanks on the loadout shown.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

import pytest

from game import persistency
from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.loadouts import Loadout
from game.data.weapons import Weapon
from game.dcs.aircrafttype import FuelConsumption
from game.fourteenth.fuel_brief import FuelBrief, fuel_brief_for, fuel_brief_text
from game.utils import KG_TO_LBS

VIPER_TANK_370 = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}"

_FUEL = FuelConsumption(taxi=200, climb=30.0, cruise=10.0, combat=16.0, min_safe=1500)
_INTERNAL_KG = 10000.0 / KG_TO_LBS  # 10,000 lbs internal


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    # Weapon.with_clsid needs the weapon DB.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16887)


def _wp(kind: FlightWaypointType = FlightWaypointType.NAV) -> Any:
    return SimpleNamespace(waypoint_type=kind)


def _flight(
    waypoints: list[Any],
    *,
    per_leg: float = 1000.0,
    members: Optional[list[Any]] = None,
    measured: FuelConsumption | None = _FUEL,
    estimated: FuelConsumption | None = None,
) -> Any:
    return SimpleNamespace(
        unit_type=SimpleNamespace(
            fuel_consumption=measured,
            estimated_fuel_consumption=estimated,
            max_fuel=_INTERNAL_KG,
        ),
        fuel=_INTERNAL_KG,
        iter_members=lambda: iter(members or ()),
        flight_plan=SimpleNamespace(
            waypoints=waypoints,
            fuel_consumption_between_points=lambda a, b, consumption=None: per_leg,
        ),
    )


def _tank_loadout(count: int) -> Loadout:
    tank = Weapon.with_clsid(VIPER_TANK_370)
    assert tank is not None
    return Loadout("Ferry", {n: tank for n in range(1, count + 1)}, date=None)


def test_burn_reserve_and_margin() -> None:
    # takeoff -> nav -> landing: two legs of 1000 plus 200 taxi.
    flight = _flight(
        [_wp(FlightWaypointType.TAKEOFF), _wp(), _wp(FlightWaypointType.LANDING_POINT)]
    )

    brief = fuel_brief_for(flight)

    assert brief is not None
    assert brief.burn_lbs == 200 + 2000
    assert brief.reserve_lbs == 1500
    # 10000 - 200 taxi - 2000 legs - 1500 reserve.
    assert brief.margin_lbs == pytest.approx(10000 - 200 - 2000 - 1500)
    assert brief.refuel_passes == 0
    assert not brief.is_short


def test_refuel_waypoint_tops_off_and_counts_a_pass() -> None:
    flight = _flight(
        [
            _wp(FlightWaypointType.TAKEOFF),
            _wp(FlightWaypointType.REFUEL),
            _wp(FlightWaypointType.LANDING_POINT),
        ]
    )

    brief = fuel_brief_for(flight)

    assert brief is not None
    assert brief.refuel_passes == 1
    # Topped off at the tanker, one leg home: 10000 - 1000 - 1500 reserve.
    assert brief.margin_lbs == pytest.approx(10000 - 1000 - 1500)


def test_walk_stops_at_the_landing_point() -> None:
    # A trailing (bullseye-style) reference waypoint after landing must not
    # burn fuel.
    flight = _flight(
        [
            _wp(FlightWaypointType.TAKEOFF),
            _wp(FlightWaypointType.LANDING_POINT),
            _wp(FlightWaypointType.BULLSEYE),
        ]
    )

    brief = fuel_brief_for(flight)

    assert brief is not None
    assert brief.burn_lbs == 200 + 1000  # taxi + the single flown leg


def test_external_tanks_count_toward_the_margin() -> None:
    waypoints = [
        _wp(FlightWaypointType.TAKEOFF),
        _wp(),
        _wp(FlightWaypointType.LANDING_POINT),
    ]
    dry = fuel_brief_for(_flight(waypoints))
    loadout = _tank_loadout(2)
    bagged = fuel_brief_for(_flight(waypoints), loadout)

    assert dry is not None and bagged is not None
    assert bagged.tank_count == 2
    assert bagged.external_lbs == pytest.approx(2 * 370 * 6.7, rel=0.01)
    assert bagged.margin_lbs == pytest.approx(dry.margin_lbs + bagged.external_lbs)


def test_defaults_to_the_driest_member() -> None:
    # Mixed loadouts: the brief mirrors the tanker decision and uses the driest.
    waypoints = [
        _wp(FlightWaypointType.TAKEOFF),
        _wp(FlightWaypointType.LANDING_POINT),
    ]
    members = [
        SimpleNamespace(loadout=_tank_loadout(3)),
        SimpleNamespace(loadout=_tank_loadout(1)),
    ]
    brief = fuel_brief_for(_flight(waypoints, members=members))

    assert brief is not None
    assert brief.tank_count == 1


def test_no_fuel_model_returns_none_and_estimate_is_flagged() -> None:
    waypoints = [
        _wp(FlightWaypointType.TAKEOFF),
        _wp(FlightWaypointType.LANDING_POINT),
    ]
    assert fuel_brief_for(_flight(waypoints, measured=None, estimated=None)) is None

    estimated = fuel_brief_for(_flight(waypoints, measured=None, estimated=_FUEL))
    assert estimated is not None and estimated.estimated

    measured = fuel_brief_for(_flight(waypoints))
    assert measured is not None and not measured.estimated


def test_text_rendering() -> None:
    assert "no fuel model" in fuel_brief_text(None)

    healthy = FuelBrief(
        internal_lbs=10000,
        external_lbs=4958,
        tank_count=2,
        burn_lbs=9000,
        reserve_lbs=1500,
        refuel_passes=1,
        margin_lbs=4458,
        estimated=False,
    )
    text = fuel_brief_text(healthy)
    assert "2 tanks" in text
    assert "1 tanker pass" in text
    assert "+4,458" in text
    assert "short" not in text

    short = FuelBrief(
        internal_lbs=10000,
        external_lbs=0,
        tank_count=0,
        burn_lbs=12000,
        reserve_lbs=1500,
        refuel_passes=0,
        margin_lbs=-3500,
        estimated=True,
    )
    text = fuel_brief_text(short)
    assert "(estimated)" in text
    assert "no tanker" in text
    assert "-3,500" in text
    assert "short of getting home" in text
