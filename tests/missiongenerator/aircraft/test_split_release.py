"""The escort release that survives a human flying the package primary.

Test 7 (2026-08-17): both Growlers escorting a player-led SEAD package formated
on him past the split point and landed at his field instead of recovering on
their own boat. The release is a user flag, and the only thing that raised it
was a RunScript on the primary flight's SPLIT waypoint -- which DCS never runs,
because DCS does not execute route tasks for a client-occupied group.

2026-08-21: the zone that fixed that released them at the JOIN instead, because
a package's join and split are the same base point. See split_release_gate.
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
    split_release_gate,
)

JOIN_ELAPSED = 774
SPLIT_ELAPSED = 2257


def _mission() -> Mission:
    return Mission(terrain=Caucasus())


def _release(
    mission: Mission,
    package: object,
    elapsed: int | None = SPLIT_ELAPSED,
    join_elapsed: int | None = JOIN_ELAPSED,
) -> None:
    create_player_split_release_trigger(
        SimpleNamespace(id=241),  # type: ignore[arg-type]
        package,  # type: ignore[arg-type]
        mission,
        Point(1000, 2000, Caucasus()),
        elapsed,
        join_elapsed,
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


def test_the_inbound_pass_through_the_zone_does_not_release_them() -> None:
    # The whole defect: join and split are the same point, so the zone alone
    # fires on the way IN. The gate must sit past the join by enough that the
    # outbound pass cannot beat it.
    mission = _mission()

    _release(mission, object())

    gate = mission.triggerrules.triggers[-1].rules[1]
    assert isinstance(gate, TimeAfter)
    assert gate.seconds > JOIN_ELAPSED
    assert gate.seconds < SPLIT_ELAPSED
    assert gate.seconds == split_release_gate(JOIN_ELAPSED, SPLIT_ELAPSED)


def test_the_zone_and_its_gate_are_one_condition_not_two_alternatives() -> None:
    # Lua binds `and` tighter than `or`, so `inZone and gate or backstop` is the
    # grouping we want. An Or() anywhere before the gate would make the gate on
    # its own a release.
    mission = _mission()

    _release(mission, object())

    rules = mission.triggerrules.triggers[-1].rules
    assert isinstance(rules[0], PartOfGroupInZone)
    assert isinstance(rules[1], TimeAfter)
    assert isinstance(rules[2], Or)


def test_a_player_who_never_flies_the_zone_still_releases_them() -> None:
    mission = _mission()

    _release(mission, object())

    rules = mission.triggerrules.triggers[-1].rules
    backstop = rules[3]
    assert isinstance(backstop, TimeAfter)
    assert backstop.seconds == SPLIT_ELAPSED + SPLIT_RELEASE_BACKSTOP_S


def test_an_ungateable_release_drops_the_zone_rather_than_firing_early() -> None:
    # No join time means no way to tell the inbound pass from the outbound one.
    # Degrade to the backstop: late is a nuisance, early is a lost escort.
    mission = _mission()

    _release(mission, object(), join_elapsed=None)

    rules = mission.triggerrules.triggers[-1].rules
    assert len(rules) == 1
    assert isinstance(rules[0], TimeAfter)
    assert rules[0].seconds == SPLIT_ELAPSED + SPLIT_RELEASE_BACKSTOP_S
    assert not mission.triggers.zones()


def test_an_unplanned_split_time_leaves_no_trigger_at_all() -> None:
    mission = _mission()

    _release(mission, object(), elapsed=None)

    assert not mission.triggerrules.triggers
    assert not mission.triggers.zones()


def test_a_split_no_later_than_the_join_is_not_gateable() -> None:
    assert split_release_gate(JOIN_ELAPSED, JOIN_ELAPSED) is None
    assert split_release_gate(JOIN_ELAPSED, JOIN_ELAPSED - 1) is None
    assert split_release_gate(None, SPLIT_ELAPSED) is None
    assert split_release_gate(JOIN_ELAPSED, None) is None


def test_one_package_never_stacks_two_release_triggers() -> None:
    mission = _mission()
    package = object()

    _release(mission, package)
    _release(mission, package)

    assert len(mission.triggerrules.triggers) == 1
    assert len(mission.triggers.zones()) == 1
