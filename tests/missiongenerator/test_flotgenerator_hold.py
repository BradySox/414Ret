"""Front-line groups must actually fight.

Two independent causes, both found by juanjux/dcs-retribution#79 and both live
here: a negative hold normalised to nearly 24 hours of Hold, and defenders were
made to wait for the *enemy's* CAS before they were allowed to move or return
fire. ``Hold`` is a running task, so neither red alert nor a manual attack order
in the ME dislodges a group stuck this way.
"""

from datetime import timedelta
from types import SimpleNamespace
from typing import Any

from game.ground_forces.combat_stance import CombatStance
from game.missiongenerator.flotgenerator import FlotGenerator
from game.utils import Heading


class _Waypoint:
    def __init__(self) -> None:
        self.tasks: list[Any] = []

    def add_task(self, task: Any) -> None:
        self.tasks.append(task)


class _Group:
    def __init__(self) -> None:
        self.position = SimpleNamespace(point_from_heading=lambda deg, dist: None)
        self.waypoint = _Waypoint()
        self.points = [SimpleNamespace(position=None)]
        self.extra_waypoints: list[Any] = []

    def add_waypoint(self, point: Any, action: Any = None) -> _Waypoint:
        if action is not None:
            self.extra_waypoints.append(point)
        return self.waypoint


def _hold_stop_seconds(duration: timedelta) -> int:
    group = _Group()
    # _set_reform_waypoint touches no instance state, so an unbound call is enough.
    FlotGenerator._set_reform_waypoint(
        None, group, Heading.from_degrees(0), duration  # type: ignore[arg-type]
    )
    (hold,) = group.waypoint.tasks
    return int(hold.params["stopCondition"]["duration"])


def test_a_negative_hold_does_not_become_a_day_long_hold() -> None:
    # timedelta(-60s).seconds is 86340: a CAS package whose TOT lands before
    # mission start immobilised the group for 23h59m.
    assert _hold_stop_seconds(timedelta(seconds=-60)) == 0


def test_a_positive_hold_is_passed_through() -> None:
    assert _hold_stop_seconds(timedelta(minutes=7)) == 420


def _duration_requested(stance: CombatStance) -> timedelta:
    captured: list[timedelta] = []
    fake = SimpleNamespace(
        _earliest_tot_on_flot=lambda player: timedelta(minutes=30),
        _set_reform_waypoint=lambda g, h, d: captured.append(d),
        add_morale_trigger=lambda g, h: None,
    )
    to_cp = SimpleNamespace(
        coalition=SimpleNamespace(player=SimpleNamespace(opponent=None)),
        position=SimpleNamespace(
            distance_to_point=lambda p: 0.0,
            random_point_within=lambda a, b: None,
        ),
    )
    fake.conflict = SimpleNamespace(
        theater=SimpleNamespace(nearest_land_pos=lambda p: None)
    )
    fake.wpt_pointaction = object()
    FlotGenerator._plan_apc_atgm_action(
        fake, stance, _Group(), Heading.from_degrees(0), to_cp  # type: ignore[arg-type]
    )
    return captured[0]


def test_a_defender_does_not_wait_for_the_enemys_cas() -> None:
    assert _duration_requested(CombatStance.DEFENSIVE) == timedelta()


def test_an_attacker_still_waits_for_its_own_air_support() -> None:
    assert _duration_requested(CombatStance.AGGRESSIVE) == timedelta(minutes=30)
