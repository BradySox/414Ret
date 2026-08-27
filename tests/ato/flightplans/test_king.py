"""The King: a hand-fragged fixed-wing CSAR flight gets an on-scene orbit.

The C-130J carries an explicit ``CSAR: 5`` entry so the "King" on-scene commander
can be flown by a player (``resources/units/aircraft/C-130J-30.yaml``). Three places
said that was supported and one made it impossible: ``CsarFlightPlan.Builder``
raised for any non-helo, which killed the hand-fragged King with "Could not create
flight" as surely as it killed an auto-planned one.

Fixed-wing CSAR now dispatches to ``KingFlightPlan`` instead. These pin the split,
because the failure it replaced was a dialog box in front of a player who had
already picked their survivor, their airframe and their squadron.
"""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest
from dcs import Point
from dcs.terrain import Caucasus

import game.ato.flightplans.king as king
from game.ato.flightplans.csar import Builder as CsarBuilder
from game.ato.flightplans.flightplanbuildertypes import FlightPlanBuilderTypes
from game.ato.flightplans.king import (
    Builder as KingBuilder,
    MINIMUM_DISTANCE,
    ON_SCENE_DISTANCE,
    THREAT_BUFFER,
)
from game.ato.flighttype import FlightType
from game.utils import Distance, feet, knots, meters, nautical_miles

TERRAIN = Caucasus()


def _point(x: float, y: float) -> Point:
    return Point(x, y, TERRAIN)


#: The survivor. Everything else is positioned relative to them.
SURVIVOR = _point(100_000, 0)


class _FakeWaypointBuilder:
    """Duck-typed WaypointBuilder returning attribute-bearing stub waypoints."""

    def __init__(self, flight: Any) -> None:
        self.flight = flight
        self.get_patrol_altitude = feet(20000)

    @staticmethod
    def _wp(name: str, position: Point) -> SimpleNamespace:
        return SimpleNamespace(name=name, position=position, alt=feet(20000))

    def takeoff(self, departure: Any) -> SimpleNamespace:
        return self._wp("TAKEOFF", departure.position)

    def land(self, arrival: Any) -> SimpleNamespace:
        return self._wp("LAND", arrival.position)

    def divert(self, divert: Any) -> None:
        return None

    def bullseye(self) -> SimpleNamespace:
        return self._wp("BULLSEYE", _point(0, 0))

    def nav_path(self, a: Point, b: Point, altitude: Distance) -> list[Any]:
        return []

    def race_track(
        self, start: Point, end: Point, altitude: Distance
    ) -> tuple[SimpleNamespace, SimpleNamespace]:
        return (
            self._wp("RACETRACK START", start),
            self._wp("RACETRACK END", end),
        )


def _flight(threatened: bool, threat_distance: Distance) -> Any:
    """A CSAR flight against SURVIVOR, with the nearest threat boundary due east."""

    threat_zone = SimpleNamespace(
        threatened=lambda position: threatened,
        closest_boundary=lambda position: position.point_from_heading(
            90, threat_distance.meters
        ),
    )
    return SimpleNamespace(
        flight_type=FlightType.CSAR,
        is_helo=False,
        unit_type=SimpleNamespace(
            preferred_patrol_speed=lambda altitude: knots(250),
        ),
        departure=SimpleNamespace(position=_point(0, 0)),
        arrival=SimpleNamespace(position=_point(0, 0)),
        divert=None,
        package=SimpleNamespace(
            target=SimpleNamespace(name="Enigma 1-1 Alpha", position=SURVIVOR)
        ),
        coalition=SimpleNamespace(
            game=SimpleNamespace(settings=SimpleNamespace()),
            opponent=SimpleNamespace(threat_zone=threat_zone),
        ),
    )


def _layout(flight: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(king, "WaypointBuilder", _FakeWaypointBuilder)
    return KingBuilder(cast(Any, flight)).layout()


def _orbit_centre(layout: Any) -> Point:
    """Midpoint of the racetrack, which is what the geometry is anchored on."""
    start = layout.patrol_start.position
    end = layout.patrol_end.position
    return _point((start.x + end.x) / 2, (start.y + end.y) / 2)


# ---------------------------------------------------------------------------
# Dispatch -- the bug this file exists for
# ---------------------------------------------------------------------------


def test_fixed_wing_csar_is_planned_as_a_king() -> None:
    flight = _flight(threatened=False, threat_distance=nautical_miles(200))
    assert FlightPlanBuilderTypes.for_flight(cast(Any, flight)) is KingBuilder


def test_helicopter_csar_still_flies_the_pickup_plan() -> None:
    flight = _flight(threatened=False, threat_distance=nautical_miles(200))
    flight.is_helo = True
    assert FlightPlanBuilderTypes.for_flight(cast(Any, flight)) is CsarBuilder


# ---------------------------------------------------------------------------
# Orbit geometry
# ---------------------------------------------------------------------------


def test_uncrowded_orbit_holds_off_on_the_side_away_from_the_threat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Threat boundary 200 nm east, so nothing crowds the orbit.
    layout = _layout(
        _flight(threatened=False, threat_distance=nautical_miles(200)), monkeypatch
    )
    centre = _orbit_centre(layout)

    distance = meters(SURVIVOR.distance_to_point(centre))
    assert distance.nautical_miles == pytest.approx(
        ON_SCENE_DISTANCE.nautical_miles, abs=0.1
    )
    # Pydcs terrain coordinates are x=north, y=east. The threat boundary is due
    # east of the survivor, so a smaller y is the away side.
    assert centre.y < SURVIVOR.y


def test_a_near_threat_pulls_the_orbit_in_toward_the_survivor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Boundary 18 nm away: 18 - 10 = 8 nm, closer than the 15 nm standoff.
    layout = _layout(
        _flight(threatened=False, threat_distance=nautical_miles(18)), monkeypatch
    )
    distance = meters(SURVIVOR.distance_to_point(_orbit_centre(layout)))
    assert distance.nautical_miles == pytest.approx(8, abs=0.1)


def test_the_orbit_never_sits_on_top_of_the_survivor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A boundary closer than the buffer would compute a negative standoff.
    layout = _layout(
        _flight(threatened=False, threat_distance=nautical_miles(2)), monkeypatch
    )
    distance = meters(SURVIVOR.distance_to_point(_orbit_centre(layout)))
    assert distance.nautical_miles == pytest.approx(
        MINIMUM_DISTANCE.nautical_miles, abs=0.1
    )


def test_a_survivor_inside_a_ring_pushes_the_orbit_outside_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The one non-negotiable: an unarmed turboprop does not orbit under a SAM."""
    edge = nautical_miles(30)
    layout = _layout(_flight(threatened=True, threat_distance=edge), monkeypatch)
    centre = _orbit_centre(layout)

    distance = meters(SURVIVOR.distance_to_point(centre))
    assert distance.nautical_miles == pytest.approx(
        (edge + THREAT_BUFFER).nautical_miles, abs=0.1
    )
    # Toward the boundary (east, so a larger y) -- the nearest edge is the way out.
    assert centre.y > SURVIVOR.y


def test_the_racetrack_legs_stay_at_one_distance_from_the_survivor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legs run tangential, so the King does not drive in and out of the threat."""
    layout = _layout(
        _flight(threatened=False, threat_distance=nautical_miles(200)), monkeypatch
    )
    start = meters(SURVIVOR.distance_to_point(layout.patrol_start.position))
    end = meters(SURVIVOR.distance_to_point(layout.patrol_end.position))
    assert start.nautical_miles == pytest.approx(end.nautical_miles, abs=0.1)


# ---------------------------------------------------------------------------
# On-station window
# ---------------------------------------------------------------------------


def test_the_king_holds_a_real_on_station_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flight = _flight(threatened=False, threat_distance=nautical_miles(200))
    layout = _layout(flight, monkeypatch)
    plan = king.KingFlightPlan(cast(Any, flight), layout)
    assert plan.patrol_duration > timedelta(0)
    assert plan.patrol_speed == knots(250)
