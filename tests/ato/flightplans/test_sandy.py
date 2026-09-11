"""The Sandy: a rescue escort gets a track over the survivor, not over the FLOT.

The rescue package had no way to express an armed escort. ``CasFlightPlan`` raises
``InvalidObjectiveLocation`` unless the package target is a ``FrontLine``, and a
rescue package's target is a ``DownedPilot`` -- so an A-10 or an Apache fragged to
cover a pickup could not be planned at all.

These pin the three things that make the role work: it is reachable from a
survivor, the track is centred on them, and it stays out of the auto-planner.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from dcs import Point
from dcs.terrain import Caucasus

import game.ato.flightplans.sandy as sandy
from game.ato.flightplans.cas import Builder as CasBuilder
from game.ato.flightplans.flightplanbuildertypes import FlightPlanBuilderTypes
from game.ato.flightplans.invalidobjectivelocation import InvalidObjectiveLocation
from game.ato.flightplans.sandy import (
    Builder as SandyBuilder,
    ENGAGEMENT_RANGE,
    INGRESS_DISTANCE,
    TRACK_HALF_LENGTH,
)
from game import persistency
from game.ato.flighttype import FlightType
from game.dcs.aircrafttype import AircraftType
from game.squadrons.downedpilot import DownedPilot
from game.squadrons.pilot import Pilot
from game.theater.player import Player
from game.utils import Distance, feet, meters

TERRAIN = Caucasus()


def _point(x: float, y: float) -> Point:
    return Point(x, y, TERRAIN)


#: The survivor. The departure field is at the origin, so home is due south.
SURVIVOR = _point(100_000, 0)


def _downed_pilot(position: Point = SURVIVOR) -> DownedPilot:
    squadron = MagicMock()
    squadron.coalition.downed_pilots = []
    downed = DownedPilot(
        pilot=Pilot("Rescuee"),
        squadron=squadron,
        _position=position,
        player=Player.BLUE,
        turn_downed=1,
        turns_remaining=3,
        was_player=True,
        aircraft_name="A-10C Thunderbolt II",
    )
    squadron.coalition.downed_pilots.append(downed)
    return downed


class _FakeWaypointBuilder:
    """Duck-typed WaypointBuilder returning attribute-bearing stub waypoints."""

    def __init__(self, flight: Any) -> None:
        self.flight = flight
        self.get_combat_altitude = feet(10000)

    @staticmethod
    def _wp(name: str, position: Point) -> SimpleNamespace:
        return SimpleNamespace(
            name=name,
            position=position,
            alt=feet(10000),
            pretty_name="",
            description="",
        )

    def takeoff(self, departure: Any) -> SimpleNamespace:
        return self._wp("TAKEOFF", departure.position)

    def land(self, arrival: Any) -> SimpleNamespace:
        return self._wp("LAND", arrival.position)

    def divert(self, divert: Any) -> None:
        return None

    def bullseye(self) -> SimpleNamespace:
        return self._wp("BULLSEYE", _point(0, 0))

    def nav_path(
        self, a: Point, b: Point, altitude: Distance, agl: bool = False
    ) -> list[Any]:
        return []

    def cas(self, position: Point, altitude: Distance) -> SimpleNamespace:
        return self._wp("CAS", position)

    def ingress(self, kind: Any, position: Point, target: Any) -> SimpleNamespace:
        return self._wp("INGRESS", position)


def _flight(target: Any, helicopter: bool = False) -> Any:
    return SimpleNamespace(
        flight_type=FlightType.SANDY,
        is_helo=helicopter,
        unit_type=SimpleNamespace(
            dcs_unit_type=SimpleNamespace(helicopter=helicopter),
        ),
        departure=SimpleNamespace(position=_point(0, 0)),
        arrival=SimpleNamespace(position=_point(0, 0)),
        divert=None,
        package=SimpleNamespace(target=target),
        coalition=SimpleNamespace(game=SimpleNamespace(settings=SimpleNamespace())),
    )


def _layout(flight: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(sandy, "WaypointBuilder", _FakeWaypointBuilder)
    return SandyBuilder(cast(Any, flight)).layout(False)


def _track_centre(layout: Any) -> Point:
    start = layout.patrol_start.position
    end = layout.patrol_end.position
    return _point((start.x + end.x) / 2, (start.y + end.y) / 2)


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def test_a_sandy_is_planned_as_a_sandy() -> None:
    flight = _flight(_downed_pilot())
    assert FlightPlanBuilderTypes.for_flight(cast(Any, flight)) is SandyBuilder


def test_cas_still_gets_the_front_line_plan() -> None:
    flight = _flight(_downed_pilot())
    flight.flight_type = FlightType.CAS
    assert FlightPlanBuilderTypes.for_flight(cast(Any, flight)) is CasBuilder


def test_a_sandy_needs_a_survivor(monkeypatch: pytest.MonkeyPatch) -> None:
    # The plan is anchored on a downed pilot; anything else is a planning error
    # rather than a track drawn around the wrong thing.
    flight = _flight(SimpleNamespace(name="Front line", position=SURVIVOR))
    with pytest.raises(InvalidObjectiveLocation):
        _layout(flight, monkeypatch)


# ---------------------------------------------------------------------------
# Track geometry -- the survivor has to stay inside the engagement zone
# ---------------------------------------------------------------------------


def test_the_track_is_centred_on_the_survivor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = _layout(_flight(_downed_pilot()), monkeypatch)
    offset = meters(SURVIVOR.distance_to_point(_track_centre(layout)))
    assert offset.meters == pytest.approx(0, abs=1)


def test_both_legs_stay_inside_the_engagement_zone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # If a leg end fell outside the zone the flight would spend half the circuit
    # not covering the pickup.
    layout = _layout(_flight(_downed_pilot()), monkeypatch)
    for waypoint in (layout.patrol_start, layout.patrol_end):
        reach = meters(SURVIVOR.distance_to_point(waypoint.position))
        assert reach.nautical_miles == pytest.approx(
            TRACK_HALF_LENGTH.nautical_miles, abs=0.1
        )
        assert reach.meters < ENGAGEMENT_RANGE.meters


def test_the_run_in_does_not_overfly_the_pickup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Ingress on the departure side, and the first leg is the near one, so the
    # flight turns onto the track instead of crossing the survivor to reach it.
    layout = _layout(_flight(_downed_pilot()), monkeypatch)
    ingress = layout.ingress.position
    assert meters(SURVIVOR.distance_to_point(ingress)).nautical_miles == pytest.approx(
        INGRESS_DISTANCE.nautical_miles, abs=0.1
    )
    # Pydcs terrain coordinates are x=north: home is at the origin, so the ingress
    # sits south of the survivor.
    assert ingress.x < SURVIVOR.x
    assert layout.patrol_start.position.distance_to_point(
        ingress
    ) <= layout.patrol_end.position.distance_to_point(ingress)


def test_the_legs_cross_the_run_in(monkeypatch: pytest.MonkeyPatch) -> None:
    # Laid across the run-in rather than along it, so the circuit passes over the
    # survivor twice instead of driving out and back.
    layout = _layout(_flight(_downed_pilot()), monkeypatch)
    start = layout.patrol_start.position
    end = layout.patrol_end.position
    assert start.x == pytest.approx(SURVIVOR.x, abs=1)
    assert end.x == pytest.approx(SURVIVOR.x, abs=1)
    assert (start.y - SURVIVOR.y) * (end.y - SURVIVOR.y) < 0


# ---------------------------------------------------------------------------
# The role stays a hand-fragged one
# ---------------------------------------------------------------------------


@pytest.fixture
def _aircraft_registry(tmp_path: Path) -> None:
    # AircraftType loads the unit data files, which reach for the saved-games
    # folder; point it at a throwaway dir so the registry can populate.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16887)


def test_a_survivor_offers_the_sandy_tasking() -> None:
    assert FlightType.SANDY in set(_downed_pilot().mission_types(Player.BLUE))


def test_the_warthog_and_the_apache_carry_the_role_unchecked(
    _aircraft_registry: None,
) -> None:
    # Capability comes from the yaml, and secondary_tasks is what keeps it out of
    # the auto-assignable set: nothing in the HTN proposes a Sandy, so an airframe
    # that auto-assigned it would only ever be held back from work it could do.
    for name in (
        "A-10A Thunderbolt II",
        "A-10C Thunderbolt II (Suite 3)",
        "A-10C Thunderbolt II (Suite 7)",
        "AH-64D Apache Longbow (AI)",
    ):
        aircraft = AircraftType.named(name)
        assert aircraft.capable_of(FlightType.SANDY), name
        assert FlightType.SANDY in aircraft.secondary_tasks, name


def test_an_airframe_that_never_flew_sandy_is_not_capable(
    _aircraft_registry: None,
) -> None:
    assert not AircraftType.named("F-16CM Fighting Falcon (Block 50)").capable_of(
        FlightType.SANDY
    )
