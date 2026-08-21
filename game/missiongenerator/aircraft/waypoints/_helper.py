from typing import Any, Optional

from dcs import Mission
from dcs.action import SetFlag
from dcs.condition import Or, PartOfGroupInZone, TimeAfter
from dcs.mapping import Point
from dcs.task import ControlledTask
from dcs.triggers import TriggerOnce, Event
from dcs.unitgroup import FlyingGroup

from game.ato import Package


def create_stop_orbit_trigger(
    orbit: ControlledTask, package: Package, mission: Mission, elapsed: int
) -> None:
    orbit.stop_if_user_flag(id(package), True)
    orbits = [
        x
        for x in mission.triggerrules.triggers
        if x.comment == f"StopOrbit{id(package)}"
    ]
    if not any(orbits):
        stop_trigger = TriggerOnce(Event.NoEvent, f"StopOrbit{id(package)}")
        stop_condition = TimeAfter(elapsed)
        stop_action = SetFlag(id(package))
        stop_trigger.add_condition(stop_condition)
        stop_trigger.add_action(stop_action)
        mission.triggerrules.triggers.append(stop_trigger)


# The escorted flight is never exactly on its SPLIT point when the escort should
# let go, and a human cuts corners an AI would fly; 8 NM is wide enough to catch a
# sloppy egress without releasing over the target.
SPLIT_RELEASE_ZONE_RADIUS_M = 15000
# Backstop for a player who never flies through the zone at all (diverts, parks,
# goes home a different way). Long enough that it does not steal an escort from a
# player who is merely slow.
SPLIT_RELEASE_BACKSTOP_S = 900


def split_release_gate(
    planned_join_elapsed: Optional[int], planned_split_elapsed: Optional[int]
) -> Optional[int]:
    """Earliest mission time at which the release zone may fire.

    A package's JOIN and SPLIT are the SAME base point -- PackageWaypoints.create
    derives both from one join_point and only perturbs each by up to 1 nm -- so the
    primary flies the release zone twice, inbound at join and outbound at split.
    Measured 2026-08-21: the escorts were pushed at the INBOUND pass and turned for
    home from the join, calling their own split waypoint index on the radio.

    Time is the axis that separates the two passes. The gate is the midpoint of the
    planned join-to-split leg, which the outbound pass cannot reach without flying
    the whole route at twice the planned speed.
    """
    if planned_join_elapsed is None or planned_split_elapsed is None:
        return None
    if planned_split_elapsed <= planned_join_elapsed:
        return None
    return planned_join_elapsed + (planned_split_elapsed - planned_join_elapsed) // 2


def create_player_split_release_trigger(
    group: FlyingGroup[Any],
    package: Package,
    mission: Mission,
    position: Point,
    planned_split_elapsed: Optional[int],
    planned_join_elapsed: Optional[int],
) -> None:
    """Release a package's escorts when a PLAYER-flown primary flight splits.

    DCS never runs a client-occupied group's route tasks, so the ``setUserFlag``
    script that SplitPointBuilder puts on the primary flight's SPLIT waypoint
    never fires when the human is flying that flight: the escorts stay on their
    Escort ControlledTask and follow the player home instead of recovering at
    their own base (test 7, 2026-08-17 -- both Growlers landed at the player's
    field, not the boat). Mission triggers run whoever is in the cockpit, so
    mirror the flag here.

    Releasing LATE costs the player an escort that follows him home; releasing
    EARLY costs him the escort over the target. Every degrade here is therefore
    toward late: with no gate to tell the inbound pass from the outbound one
    (see split_release_gate) the zone is dropped and the backstop stands alone.
    """
    comment = f"SplitRelease{id(package)}"
    if any(x.comment == comment for x in mission.triggerrules.triggers):
        return

    gate = split_release_gate(planned_join_elapsed, planned_split_elapsed)
    backstop = (
        planned_split_elapsed + SPLIT_RELEASE_BACKSTOP_S
        if planned_split_elapsed is not None
        else None
    )
    if gate is None and backstop is None:
        return

    trigger = TriggerOnce(Event.NoEvent, comment)
    if gate is not None:
        zone = mission.triggers.add_triggerzone(
            position,
            radius=SPLIT_RELEASE_ZONE_RADIUS_M,
            hidden=True,
            name=f"Split release {id(package)}",
        )
        trigger.add_condition(PartOfGroupInZone(group.id, zone.id))
        trigger.add_condition(TimeAfter(gate))
        if backstop is not None:
            trigger.add_condition(Or())
    if backstop is not None:
        trigger.add_condition(TimeAfter(backstop))
    trigger.add_action(SetFlag(f"split-{id(package)}"))
    mission.triggerrules.triggers.append(trigger)
