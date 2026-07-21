"""Blue CAP stations join the §45 F10 support-orbit drawings.

The Hornet's SA page displays only the *selected* DTC CAP point, so the F10
map is the one display that can show the whole friendly orbit picture at once:
one thin labelled racetrack per station (§6 wave duplicates collapsed by the
§74 dedupe), alongside the existing tanker/AEW&C capsules.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from dcs import mapping
from dcs.drawing.drawings import StandardLayer
from dcs.mission import Mission
from dcs.terrain import Caucasus

from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.drawingsgenerator import DrawingsGenerator


def _patrol_flight(
    mission: Mission,
    callsign: str,
    flight_type: FlightType,
    start_xy: tuple[float, float],
    end_xy: tuple[float, float],
) -> Any:
    def wp(waypoint_type: FlightWaypointType, xy: tuple[float, float]) -> Any:
        return SimpleNamespace(
            waypoint_type=waypoint_type,
            position=mapping.Point(xy[0], xy[1], mission.terrain),
        )

    return SimpleNamespace(
        callsign=callsign,
        flight_type=flight_type,
        friendly=SimpleNamespace(is_blue=True),
        group_name=f"{callsign} group",
        aircraft_type=SimpleNamespace(display_name="F/A-18C"),
        waypoints=[
            wp(FlightWaypointType.PATROL_TRACK, start_xy),
            wp(FlightWaypointType.PATROL, end_xy),
        ],
    )


def test_cap_stations_are_drawn_once_per_station() -> None:
    mission = Mission(Caucasus())
    flights = [
        _patrol_flight(mission, "Colt 1", FlightType.BARCAP, (0, 0), (20000, 0)),
        # A relief wave of the same station: jittered, must not draw twice.
        _patrol_flight(mission, "Colt 2", FlightType.BARCAP, (2000, 500), (22000, 500)),
        _patrol_flight(mission, "Uzi 1", FlightType.TARCAP, (90000, 0), (110000, 0)),
        _patrol_flight(
            mission, "Arco 1", FlightType.REFUELING, (0, 90000), (30000, 90000)
        ),
    ]
    mission_data = SimpleNamespace(
        flights=flights, tankers=[], awacs=[], jtacs=[], carriers=[]
    )
    generator = DrawingsGenerator(
        mission, SimpleNamespace(), mission_data  # type: ignore[arg-type]
    )
    generator.generate_support_orbits()

    names = [
        drawing.name
        for drawing in mission.drawings.get_layer(StandardLayer.Blue).objects
    ]
    assert "CAP COLT orbit" in names
    assert names.count("CAP COLT orbit") == 1  # waves collapsed
    assert "CAP UZI orbit" in names
    # The tanker keeps its own (thicker, labelled) capsule from the §45 pass.
    assert "Arco 1 orbit" in names
