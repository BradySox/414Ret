"""Support-package F10 orbit markers (DrawingsGenerator.generate_support_orbits).

At generation, each blue tanker / AEW&C orbit is painted as a labelled racetrack on
the F10 map so pilots can find their support in flight. Uses a real pydcs Mission (so
the pydcs add_oblong / add_text_box calls are exercised) + duck flight/support data.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from dcs import Point
from dcs.drawing.drawings import StandardLayer
from dcs.mission import Mission
from dcs.terrain import Caucasus

from game.ato.flighttype import FlightType
from game.ato.flightwaypointtype import FlightWaypointType
from game.missiongenerator.drawingsgenerator import DrawingsGenerator
from game.theater.player import Player

_XY = tuple[float, float]


def _racetrack_waypoints(terrain: Any, start_xy: _XY, end_xy: _XY) -> list[Any]:
    return [
        SimpleNamespace(
            waypoint_type=FlightWaypointType.PATROL_TRACK,
            position=Point(*start_xy, terrain),
        ),
        SimpleNamespace(
            waypoint_type=FlightWaypointType.PATROL,
            position=Point(*end_xy, terrain),
        ),
    ]


def _flight(
    terrain: Any,
    *,
    flight_type: FlightType,
    coalition: Player,
    callsign: str,
    group: str,
    start: _XY,
    end: _XY,
    type_name: str,
) -> Any:
    return SimpleNamespace(
        flight_type=flight_type,
        friendly=coalition,
        waypoints=_racetrack_waypoints(terrain, start, end),
        group_name=group,
        callsign=callsign,
        aircraft_type=SimpleNamespace(display_name=type_name),
    )


def _objects(mission: Mission) -> list[Any]:
    return mission.drawings.get_layer(StandardLayer.Blue).objects


def test_tanker_orbit_drawn_with_label() -> None:
    m = Mission(Caucasus())
    tanker = _flight(
        m.terrain,
        flight_type=FlightType.REFUELING,
        coalition=Player.BLUE,
        callsign="ARCO",
        group="Tanker 1",
        start=(0.0, 0.0),
        end=(40000.0, 0.0),
        type_name="KC-135",
    )
    info = SimpleNamespace(group_name="Tanker 1", freq="251.0", tacan="51Y")
    mission_data = SimpleNamespace(tankers=[info], awacs=[], flights=[tanker])

    gen = DrawingsGenerator(m, SimpleNamespace(), mission_data)  # type: ignore[arg-type]
    gen.generate_support_orbits()

    names = [o.name for o in _objects(m)]
    assert "ARCO orbit" in names  # the racetrack
    assert "ARCO label" in names  # the label
    label = next(o for o in _objects(m) if o.name == "ARCO label")
    for bit in ("ARCO", "KC-135", "251.0", "51Y"):
        assert bit in label.text


def test_awacs_orbit_drawn_without_tacan() -> None:
    m = Mission(Caucasus())
    awacs = _flight(
        m.terrain,
        flight_type=FlightType.AEWC,
        coalition=Player.BLUE,
        callsign="MAGIC",
        group="AWACS 1",
        start=(0.0, 0.0),
        end=(0.0, 50000.0),
        type_name="E-3A",
    )
    info = SimpleNamespace(group_name="AWACS 1", freq="252.0")  # no TACAN
    mission_data = SimpleNamespace(tankers=[], awacs=[info], flights=[awacs])

    gen = DrawingsGenerator(m, SimpleNamespace(), mission_data)  # type: ignore[arg-type]
    gen.generate_support_orbits()

    label = next(o for o in _objects(m) if o.name == "MAGIC label")
    assert "MAGIC" in label.text and "252.0" in label.text
    assert "TCN" not in label.text


def test_non_support_and_enemy_flights_are_skipped() -> None:
    m = Mission(Caucasus())
    striker = _flight(
        m.terrain,
        flight_type=FlightType.STRIKE,
        coalition=Player.BLUE,
        callsign="UZI",
        group="Strike 1",
        start=(0.0, 0.0),
        end=(1000.0, 0.0),
        type_name="F-16C",
    )
    red_tanker = _flight(
        m.terrain,
        flight_type=FlightType.REFUELING,
        coalition=Player.RED,
        callsign="BORT",
        group="Red Tanker",
        start=(0.0, 0.0),
        end=(40000.0, 0.0),
        type_name="IL-78",
    )
    mission_data = SimpleNamespace(tankers=[], awacs=[], flights=[striker, red_tanker])

    gen = DrawingsGenerator(m, SimpleNamespace(), mission_data)  # type: ignore[arg-type]
    gen.generate_support_orbits()

    assert _objects(m) == []


def test_none_mission_data_is_a_noop() -> None:
    m = Mission(Caucasus())
    gen = DrawingsGenerator(m, SimpleNamespace(), None)  # type: ignore[arg-type]
    gen.generate_support_orbits()
    assert _objects(m) == []
