"""Tests for naval station-keeping racetracks (``GroundObjectGenerator.hold_station``).

A ship TGO with no campaign destination used to generate with a zero-waypoint route,
so it sat motionless on its campaign marker for the whole mission and every hull was a
stationary target. ``hold_station`` gives it an anchor-centred racetrack instead.

The load-bearing property, pinned by ``test_the_anchor_is_the_centre_of_the_track``, is
that the anchor is the CENTRE of the oval rather than a point on it. That is what makes
the group *hold station* -- its mean position stays its campaign position -- instead of
steaming away from its marker, and it is what keeps the drawn threat rings, the campaign
map and the turn-boundary model honest however long the mission runs.

These drive real pydcs ``ShipGroup``s (so the waypoint and task mechanics are the real
ones) against a faked theater, since only ``landmap`` and ``is_in_sea`` are consulted.
"""

from types import SimpleNamespace
from typing import Any, Callable

from dcs import Mission
from dcs.mapping import Point
from dcs.ships import USS_Arleigh_Burke_IIa
from dcs.task import SwitchWaypoint
from dcs.terrain import Caucasus
from dcs.unitgroup import ShipGroup

from game.missiongenerator.tgogenerator import (
    STATION_LEG,
    STATION_WIDTH,
    GroundObjectGenerator,
)
from game.theater.theatergroundobject import ShipGroundObject

#: Somewhere in the middle of the fake ocean, far from any coordinate edge case.
ANCHOR = (100_000.0, 200_000.0)


def _theater(is_in_sea: Callable[[Point], bool], landmap: Any = object()) -> Any:
    return SimpleNamespace(landmap=landmap, is_in_sea=is_in_sea)


def _generator(theater: Any) -> GroundObjectGenerator:
    game = SimpleNamespace(settings=SimpleNamespace(), theater=theater)
    # ShipGroundObject is built without its heavy __init__ (which needs a full
    # ControlPoint graph); hold_station only ever reads the group, not the TGO.
    return GroundObjectGenerator(
        object.__new__(ShipGroundObject), None, game, None, None  # type: ignore[arg-type]
    )


def _ship_group(name: str = "Naval-1", at: tuple[float, float] = ANCHOR) -> ShipGroup:
    mission = Mission(terrain=Caucasus())
    return mission.ship_group(
        mission.country("USA"),
        name,
        USS_Arleigh_Burke_IIa,
        position=Point(at[0], at[1], mission.terrain),
        heading=0,
    )


def _open_ocean() -> Any:
    return _theater(lambda point: True)


def test_a_stationed_group_sails_a_four_corner_circuit() -> None:
    group = _ship_group()
    _generator(_open_ocean()).hold_station(group)

    # Waypoint 1 is the spawn at the centre; 2-5 are the corners of the oval.
    assert len(group.points) == 5


def test_the_anchor_is_the_centre_of_the_track() -> None:
    """The whole point of a racetrack over a circuit: the ship holds station.

    A ring drawn *around* the anchor would have the group steam a full radius clear
    of its marker and read as transiting off station. Centring the oval keeps the
    mean position on the campaign marker.
    """
    group = _ship_group()
    _generator(_open_ocean()).hold_station(group)

    corners = [point.position for point in group.points[1:]]
    mean_x = sum(corner.x for corner in corners) / len(corners)
    mean_y = sum(corner.y for corner in corners) / len(corners)

    assert abs(mean_x - ANCHOR[0]) < 1.0
    assert abs(mean_y - ANCHOR[1]) < 1.0


def test_the_group_never_leaves_its_campaign_area() -> None:
    """The bound that answers "they can't wander off": every point on the track is
    within half the oval's diagonal of the marker, by construction."""
    group = _ship_group()
    anchor = group.points[0].position
    _generator(_open_ocean()).hold_station(group)

    limit = ((STATION_LEG.meters / 2) ** 2 + (STATION_WIDTH.meters / 2) ** 2) ** 0.5
    for point in group.points[1:]:
        assert anchor.distance_to_point(point.position) <= limit + 1.0


#: The shortest air-defence radius among escorts in regular use — the Albatros/Rezky
#: classes, 16 km in the DCS unit data. (A Molniya missile boat is shorter still at
#: 2 km, but a ring that small is not something anyone plans a mission against.)
SHORT_ESCORT_AD_RANGE_M = 16_000.0


def test_the_station_stays_small_against_a_ship_threat_ring() -> None:
    """The measurement that sets the size of the oval, pinned so it cannot drift.

    The map draws a ship's threat ring at its marker, so displacement from the marker
    is straight error in that ring. The first cut of this feature used an 8 x 2 NM
    oval, whose 4.1 NM reach was 48% of the ring below and several times a Molniya's
    entire 2 km engagement radius — a hull could sit wholly outside its own drawn
    ring. Keep the reach a small fraction of the shortest ring that matters.
    """
    reach = ((STATION_LEG.meters / 2) ** 2 + (STATION_WIDTH.meters / 2) ** 2) ** 0.5

    assert reach <= 0.25 * SHORT_ESCORT_AD_RANGE_M


def test_the_circuit_loops_back_to_the_first_corner() -> None:
    group = _ship_group()
    _generator(_open_ocean()).hold_station(group)

    tasks = [
        task for task in group.points[-1].tasks if isinstance(task, SwitchWaypoint)
    ]
    assert len(tasks) == 1
    params = tasks[0].params["action"]["params"]
    # Back to the first corner, never to waypoint 1: waypoint 1 is the spawn at the
    # centre of the oval and is only the one-time run-out onto station.
    assert params["goToWaypointIndex"] == 2
    assert params["fromWaypointIndex"] == len(group.points)


def test_a_landlocked_group_stays_put() -> None:
    """A ship authored alongside in a harbour keeps today's stationary behaviour
    rather than steaming into the pier -- DCS naval AI does no land avoidance."""
    group = _ship_group()
    _generator(_theater(lambda point: False)).hold_station(group)

    assert len(group.points) == 1
    assert group.points[0].tasks == []


def test_no_landmap_leaves_the_group_stationary() -> None:
    """Without a landmap nothing can be validated, so no track is laid at all."""
    group = _ship_group()
    _generator(_theater(lambda point: True, landmap=None)).hold_station(group)

    assert len(group.points) == 1


def test_land_reorients_the_track_rather_than_beaching_the_group() -> None:
    """Legs are sampled along their whole length, so the track ends up oriented
    along whatever water the group actually has -- which is what a real station in
    a strait looks like.

    Here the only sea is a channel narrower than the oval is long but wider than it
    is broad, so the long axis has to lie along the channel: laid across it, the ends
    would ground.
    """
    channel_half_width = 1_500.0
    # The premise only holds while the channel is between the oval's half-width and
    # its half-length; otherwise every orientation fits (or none does) and the test
    # would pass without proving anything.
    assert STATION_WIDTH.meters / 2 < channel_half_width < STATION_LEG.meters / 2

    def is_in_sea(point: Point) -> bool:
        return abs(point.y - ANCHOR[1]) < channel_half_width

    group = _ship_group()
    _generator(_theater(is_in_sea)).hold_station(group)

    assert len(group.points) == 5
    for point in group.points[1:]:
        assert is_in_sea(point.position)


def test_a_group_whose_own_spawn_is_not_open_water_stays_put() -> None:
    """The run-out leg starts at the spawn, so the spawn itself must validate as
    sea. If the landmap cannot confirm the group is afloat -- a marker inside a
    harbour polygon, say -- it keeps today's stationary behaviour."""
    group = _ship_group()
    # Sea everywhere except a small disc around the group itself.
    _generator(
        _theater(
            lambda point: point.distance_to_point(group.points[0].position) > 800.0
        )
    ).hold_station(group)

    assert len(group.points) == 1


def test_the_track_is_stable_across_regeneration() -> None:
    """Re-rolling a turn must re-derive the same station, not reshuffle the fleet."""
    first = _ship_group()
    second = _ship_group()
    _generator(_open_ocean()).hold_station(first)
    _generator(_open_ocean()).hold_station(second)

    assert [(p.position.x, p.position.y) for p in first.points] == [
        (p.position.x, p.position.y) for p in second.points
    ]


def test_different_groups_get_different_orientations() -> None:
    """Otherwise a whole fleet steams in parallel like a parade."""
    orientations = set()
    for name in ("Naval-1", "Naval-2", "Naval-3", "Naval-4", "Naval-5"):
        group = _ship_group(name=name)
        _generator(_open_ocean()).hold_station(group)
        first_corner = group.points[1].position
        orientations.add(round(first_corner.x - ANCHOR[0], 3))

    assert len(orientations) > 1
