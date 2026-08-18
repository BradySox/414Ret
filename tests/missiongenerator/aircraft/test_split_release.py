"""The escort release that survives a human flying the package primary.

Test 7 (2026-08-17): both Growlers escorting a player-led SEAD package formated
on him past the split point and landed at his field instead of recovering on
their own boat. The release is a user flag, and the only thing that raised it
was a RunScript on the primary flight's SPLIT waypoint -- which DCS never runs,
because DCS does not execute route tasks for a client-occupied group.
"""

from __future__ import annotations

from types import SimpleNamespace

from dcs import Mission, Point
from dcs.action import SetFlag
from dcs.condition import Or, PartOfGroupInZone, TimeAfter
from dcs.terrain import Caucasus

from game.missiongenerator.aircraft.waypoints._helper import (
    SPLIT_RELEASE_BACKSTOP_S,
    SPLIT_RELEASE_ZONE_RADIUS_M,
    create_player_split_release_trigger,
)


def _mission() -> Mission:
    return Mission(terrain=Caucasus())


def _release(mission: Mission, package: object, elapsed: int | None = 1800) -> None:
    create_player_split_release_trigger(
        SimpleNamespace(id=241),  # type: ignore[arg-type]
        package,  # type: ignore[arg-type]
        mission,
        Point(1000, 2000, Caucasus()),
        elapsed,
    )


def test_the_primary_flight_reaching_its_split_point_releases_the_escorts() -> None:
    mission = _mission()
    package = object()

    _release(mission, package)

    trigger = mission.triggerrules.triggers[-1]
    zone = mission.triggers.zones()[-1]
    assert zone.radius == SPLIT_RELEASE_ZONE_RADIUS_M
    # Never drawn: the player has no business seeing a bubble round his own
    # egress turn point.
    assert zone.hidden is True
    in_zone = trigger.rules[0]
    assert isinstance(in_zone, PartOfGroupInZone)
    assert in_zone.group == 241
    assert in_zone.zone == zone.id
    action = trigger.actions[0]
    assert isinstance(action, SetFlag)
    assert action.flag == f"split-{id(package)}"


def test_a_player_who_never_flies_the_zone_still_releases_them() -> None:
    mission = _mission()

    _release(mission, object(), elapsed=1800)

    rules = mission.triggerrules.triggers[-1].rules
    assert isinstance(rules[1], Or)
    backstop = rules[2]
    assert isinstance(backstop, TimeAfter)
    assert backstop.seconds == 1800 + SPLIT_RELEASE_BACKSTOP_S


def test_an_unplanned_split_time_leaves_the_zone_as_the_only_release() -> None:
    mission = _mission()

    _release(mission, object(), elapsed=None)

    rules = mission.triggerrules.triggers[-1].rules
    assert len(rules) == 1
    assert isinstance(rules[0], PartOfGroupInZone)


def test_one_package_never_stacks_two_release_triggers() -> None:
    mission = _mission()
    package = object()

    _release(mission, package)
    _release(mission, package)

    assert len(mission.triggerrules.triggers) == 1
    assert len(mission.triggers.zones()) == 1
