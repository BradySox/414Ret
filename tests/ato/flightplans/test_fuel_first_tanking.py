"""``FormationAttackBuilder._refuel_tasking`` is fuel-first and tank-aware (§46).

The old decision ran on internal fuel alone: a jet already carrying two bags was
sent to the tanker before AND after the vul when its real load needed a single
pass. The reworked decision (1) runs the fuel-first tank pass over the members'
loadouts once the sortie route is known -- filling empty tank-capable stations,
then trading a jammer pod for a bag when that saves a tanker pass -- and (2)
counts the external fuel the jet actually carries on both sides of the top-off
math. These tests pin both halves through the real ``_refuel_tasking`` entry.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from dcs import planes

from game import persistency
from game.ato.flightplans.formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from game.ato.flightwaypointtype import FlightWaypointType
from game.ato.loadouts import Loadout
from game.ato.refueltasking import RefuelTasking
from game.data.weapons import Weapon
from game.dcs.aircrafttype import FuelConsumption
from game.fourteenth.range_fuel import is_fuel_tank

_NM = 1852.0  # meters per nautical mile

# taxi=0/min_safe=0 keep the arithmetic against the real Viper internal fuel simple.
_FUEL = FuelConsumption(taxi=0, climb=20.0, cruise=10.0, combat=16.0, min_safe=0)

_VIPER_INTERNAL_KG = planes.F_16C_50.fuel_max  # 3249 kg -> ~7163 lbs

VIPER_TANK_370 = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}"
VIPER_ALQ_184 = "ALQ_184"
VIPER_HARM = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}"


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    # Weapon.with_clsid needs the weapon DB.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16886)


class _Pos:
    def __init__(self, nautical_miles: float) -> None:
        self.x = nautical_miles * _NM

    def distance_to_point(self, other: "_Pos") -> float:
        return abs(self.x - other.x)


class _WP:
    def __init__(self, at_nm: float, kind: FlightWaypointType) -> None:
        self.position = _Pos(at_nm)
        self.waypoint_type = kind


class _Builder(
    FormationAttackBuilder[FormationAttackFlightPlan, FormationAttackLayout]
):
    """Minimal concrete builder: bypass ``IBuilder.__init__`` so we can exercise
    ``_refuel_tasking`` in isolation."""

    def __init__(self, flight: object) -> None:
        self.flight = flight  # type: ignore[assignment]

    def build(self, dump_debug_info: bool = False) -> FormationAttackFlightPlan:
        raise NotImplementedError


def _weapon(clsid: str) -> Weapon:
    weapon = Weapon.with_clsid(clsid)
    assert weapon is not None, f"weapon DB is missing {clsid}"
    return weapon


def _viper_sead_loadout() -> Loadout:
    return Loadout(
        "Retribution SEAD",
        {
            3: _weapon(VIPER_HARM),
            4: _weapon(VIPER_TANK_370),
            5: _weapon(VIPER_ALQ_184),
            6: _weapon(VIPER_TANK_370),
            7: _weapon(VIPER_HARM),
        },
        date=None,
    )


def _flight(members: list[Any]) -> SimpleNamespace:
    # A Viper-shaped fake: the real pydcs pylon tables (so the tank pass sees the
    # real stations) under controlled fuel-rate numbers.
    return SimpleNamespace(
        is_helo=False,
        unit_type=SimpleNamespace(
            fuel_consumption=_FUEL,
            estimated_fuel_consumption=None,
            max_fuel=_VIPER_INTERNAL_KG,
            dcs_unit_type=planes.F_16C_50,
        ),
        iter_members=lambda: iter(members),
        coalition=SimpleNamespace(
            air_wing=SimpleNamespace(can_auto_plan=lambda task: True),
            game=SimpleNamespace(
                settings=SimpleNamespace(
                    auto_range_fuel_tanks=True,
                    fuel_tanks_over_jammers=True,
                )
            ),
        ),
    )


def _viper_sortie() -> tuple[list[_WP], set[_WP], _WP]:
    """A sortie sized so two bags need two passes but three bags need one.

    to_vul = 650 nm * 20 (climb) + 10 nm * 16 (combat) = 13160 lbs, between the
    two-bag usable (~12121) and the three-bag usable (~14131); vul->home is
    120 nm * 10 = 1200 lbs, so the three-bag total (14360) still needs one
    post-vul pass rather than none.
    """
    takeoff = _WP(0, FlightWaypointType.TAKEOFF)
    join = _WP(650, FlightWaypointType.JOIN)
    split = _WP(660, FlightWaypointType.SPLIT)
    landing = _WP(780, FlightWaypointType.LANDING_POINT)
    return [takeoff, join, split, landing], {join, split}, split


def _decide(flight: SimpleNamespace) -> RefuelTasking:
    route, combat_speed, split = _viper_sortie()
    builder = _Builder(flight)
    return builder._refuel_tasking(route, combat_speed, split)  # type: ignore[arg-type]


def test_internal_only_math_would_tank_twice() -> None:
    # Sanity anchor for the scenario: with no members (no loadout, no external
    # fuel, nothing for the tank pass to fit), the sortie is a two-pass problem.
    assert _decide(_flight([])) is RefuelTasking.BOTH


def test_bags_on_the_jet_count_toward_the_tanker_decision() -> None:
    # Four bags of external fuel (no jammer to trade; a fake loadout the tank
    # pass can't improve) cover what internal-only math called a two-pass
    # sortie -- one pass survives.
    loadout = Loadout(
        "Ferry",
        {n: _weapon(VIPER_TANK_370) for n in (1, 2, 8, 9)},
        date=None,
    )
    flight = _flight([SimpleNamespace(loadout=loadout)])

    assert _decide(flight) is not RefuelTasking.BOTH


def test_the_viper_case_end_to_end() -> None:
    # The motivating flight: two wing bags + a centerline ALQ-184, planned
    # pre+post-vul. The fuel-first pass trades the pod for the third bag and the
    # decision lands on a single post-vul pass.
    loadout = _viper_sead_loadout()
    flight = _flight([SimpleNamespace(loadout=loadout)])

    tasking = _decide(flight)

    assert tasking is RefuelTasking.POST_VUL
    centerline = loadout.pylons[5]
    assert centerline is not None and is_fuel_tank(centerline.clsid)
    # The shooters' ordnance is untouched.
    assert loadout.pylons[3] is not None and loadout.pylons[3].clsid == VIPER_HARM
    assert loadout.pylons[7] is not None and loadout.pylons[7].clsid == VIPER_HARM


def test_displacement_toggle_off_keeps_the_pod_and_the_two_passes() -> None:
    loadout = _viper_sead_loadout()
    flight = _flight([SimpleNamespace(loadout=loadout)])
    flight.coalition.game.settings.fuel_tanks_over_jammers = False

    tasking = _decide(flight)

    # Wing bags still count (fuel-aware decision), but with only two bags this
    # sortie stays a two-pass problem and the pod keeps its seat.
    assert tasking is RefuelTasking.BOTH
    centerline = loadout.pylons[5]
    assert centerline is not None and centerline.clsid == VIPER_ALQ_184
