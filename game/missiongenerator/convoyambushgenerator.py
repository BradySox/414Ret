"""Convoy ambush spring -> native DCS triggers (§50).

The runtime half of the convoy ambush feature. The turn-boundary force model
(``game/fourteenth/convoy_ambush.py``) has already rolled each active blue supply convoy
for an ambush and, where the roll hit, seeded real, ``map_hidden`` red ambush teams along
its road, recording each pairing on ``game.convoy_ambush_state``. This generator arms
those pairings **at generation time**, using DCS's own trigger engine:

* the team is authored dug in -- ``OptAlarmState`` green + ``OptROE`` weapons-hold on
  waypoint 0, the same idiom :meth:`TgoGenerator.set_ship_engagement` uses for fleets;
* a hidden circular trigger zone is placed on the ambush point;
* one ``TriggerOnce`` -- "the grace period has elapsed AND part of *this* convoy is in
  *that* zone" -- raises a per-ambush flag and fires the "troops in contact" cue + F10
  mark;
* each team's waypoint 0 also carries flag-gated ``ControlledTask`` options that flip it
  to alarm-red / weapons-free the moment that flag is raised.

**Why this is not a Lua plugin.** It used to be: a ``convoyambush`` plugin polled every
15 s, walking every unit of every convoy to measure range to every ambush. That is a
re-implementation of the trigger engine DCS already runs, and it cost a plugin the host
could untick -- which silently disabled the feature whatever the setting said (the §36
lesson), which is why the plugin had to be preseeded into seven campaigns. Authoring the
same behaviour costs no runtime, no plugin dependency and no campaign preseed, and DCS
evaluates the zone continuously instead of once every 15 s.

**ROE / cue only -- this owns no kills.** The convoy and the ambushers are real, tracked
units, so whatever the firefight resolves is reconciled natively at debrief (dead convoy
units never arrive; dead ambushers are a real red ground loss). All that is authored here
is *when* a dug-in team opens up. A team whose convoy never reaches it stays dug in and
silent: the ambush is a surprise the column drives into, never an announced objective.

Fully guarded -- feature off, no recorded pairing, a team whose units are all dead, or a
convoy that was not generated this mission (its transfer completed) and nothing is
authored for that pairing.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from dcs.action import Coalition, MarkToCoalition, MessageToCoalition, SetFlag
from dcs.condition import PartOfGroupInZone, TimeAfter
from dcs.mission import Mission
from dcs.task import ControlledTask, OptAlarmState, OptROE
from dcs.translation import String
from dcs.triggers import Event, TriggerOnce
from dcs.unitgroup import Group

if TYPE_CHECKING:
    from game import Game

#: Metres from the ambush point at which the convoy springs the trap. Matches the
#: retired plugin's default trigger radius, so the feel is unchanged.
AMBUSH_TRIGGER_RADIUS_M = 6000

#: Seconds after mission start before an ambush can spring, so nothing opens up while
#: the player is still in the pit.
AMBUSH_START_GRACE_S = 120

#: Seconds the "troops in contact" cue stays on screen.
AMBUSH_CUE_SECONDS = 20

#: F10 mark ids are a single global namespace shared with every other feature that marks
#: the map. This base is the one the retired plugin used, so nothing else moves.
AMBUSH_MARK_ID_BASE = 73100

#: ``AI.Option.Ground.val.ALARM_STATE`` -- 1 green (dug in), 2 red (sprung). The same
#: literals ``TgoGenerator`` already writes.
_ALARM_GREEN = 1
_ALARM_RED = 2


class ConvoyAmbushGenerator:
    """Authors the §50 ambush springs as DCS trigger rules."""

    def __init__(self, mission: Mission, game: "Game") -> None:
        self.mission = mission
        self.game = game

    def generate(self) -> None:
        if not getattr(self.game.settings, "convoy_ambush", False):
            return
        state = getattr(self.game, "convoy_ambush_state", None)
        if not isinstance(state, dict):
            return

        armed = 0
        for record in state.get("ambushes", []):
            if not isinstance(record, dict):
                continue
            if self._arm_ambush(record, armed):
                armed += 1
        if armed:
            logging.info("Armed %d convoy ambush(es) as DCS triggers", armed)

    def _arm_ambush(self, record: dict[str, Any], index: int) -> bool:
        """Author one pairing. Returns whether it was armed."""
        tgo = self._tgo_by_id(record.get("tgo_id"))
        if tgo is None:
            return False
        position = getattr(tgo, "position", None)
        if position is None or not hasattr(position, "x"):
            return False

        convoy_name = record.get("convoy")
        if not convoy_name:
            return False
        # The convoy may simply not exist this mission -- its transfer completed, or
        # convoy generation is disabled for performance. Then nobody can drive into
        # the ambush and there is nothing to author.
        convoy_group = self.mission.find_group(str(convoy_name))
        if convoy_group is None:
            return False

        teams = self._team_groups(tgo)
        if not teams:
            return False

        flag = f"ambush-{tgo.id}"
        zone = self.mission.triggers.add_triggerzone(
            position,
            radius=AMBUSH_TRIGGER_RADIUS_M,
            # Never drawn for the player: the whole feature depends on the ambush
            # being a surprise the column drives into.
            hidden=True,
            name=f"Convoy ambush {index + 1}",
        )

        for team in teams:
            self._dig_in(team, flag)

        trigger = TriggerOnce(Event.NoEvent, f"Convoy ambush {index + 1}")
        trigger.add_condition(TimeAfter(AMBUSH_START_GRACE_S))
        # Deliberately the convoy's OWN group, not "any blue unit": a player who
        # happens to overfly the ambush must not spring it.
        trigger.add_condition(PartOfGroupInZone(convoy_group.id, zone.id))
        trigger.add_action(SetFlag(flag))
        trigger.add_action(
            MessageToCoalition(
                Coalition.Blue,
                String(
                    "TROOPS IN CONTACT -- a friendly convoy is under ambush. "
                    "Support welcome."
                ),
                AMBUSH_CUE_SECONDS,
            )
        )
        trigger.add_action(
            MarkToCoalition(
                AMBUSH_MARK_ID_BASE + index,
                zone.id,
                Coalition.Blue,
                String("Convoy ambush"),
            )
        )
        self.mission.triggerrules.triggers.append(trigger)
        return True

    def _dig_in(self, group: Group[Any, Any], flag: str) -> None:
        """Author a team's dug-in state plus its flag-gated spring.

        The two plain options apply at mission start (dug in and silent). The two
        ``ControlledTask``s sit dormant on the same waypoint until the ambush flag is
        raised, then flip the team to alarm-red / weapons-free -- the ME's own
        "start condition" mechanism, which the fork already flies for the escort split
        (``joinpoint.configure_escort_tasks`` uses the mirror-image stop condition).
        """
        tasks = group.points[0].tasks
        tasks.append(OptAlarmState(_ALARM_GREEN))
        tasks.append(OptROE(OptROE.Values.WeaponHold))

        spring_alarm = ControlledTask(OptAlarmState(_ALARM_RED))
        spring_alarm.start_if_user_flag(flag, True)
        tasks.append(spring_alarm)

        spring_roe = ControlledTask(OptROE(OptROE.Values.WeaponFree))
        spring_roe.start_if_user_flag(flag, True)
        tasks.append(spring_roe)

    def _team_groups(self, tgo: Any) -> list[Group[Any, Any]]:
        """The ambush TGO's generated DCS groups that still hold an alive unit.

        A fully dead team has nothing to spring. A group the mission never generated
        is skipped rather than raising -- the ambush simply arms with whatever metal
        is actually on the map.
        """
        groups: list[Group[Any, Any]] = []
        for theater_group in getattr(tgo, "groups", []):
            name = getattr(theater_group, "group_name", None)
            if not name:
                continue
            if not any(
                getattr(unit, "alive", False)
                for unit in getattr(theater_group, "units", [])
            ):
                continue
            group = self.mission.find_group(str(name))
            if group is not None and group.points:
                groups.append(group)
        return groups

    def _tgo_by_id(self, tgo_id: Optional[str]) -> Any:
        if tgo_id is None:
            return None
        for cp in self.game.theater.controlpoints:
            for tgo in cp.ground_objects:
                if str(tgo.id) == str(tgo_id):
                    return tgo
        return None
