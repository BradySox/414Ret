"""§50 convoy ambush -- the spring, authored as native DCS triggers.

Locks the generation half of the feature (the force-model half is
``tests/fourteenth/test_convoy_ambush.py``). These drive a **real** ``dcs.Mission`` with
real vehicle groups rather than mocks, so what is asserted is the actual mission structure
DCS will read: the dug-in options, the flag-gated ``ControlledTask`` spring, the trigger
zone, and the trigger's conditions/actions -- plus that the whole thing still serializes.

The behaviour these pin used to live in a Lua plugin polling every 15 s. The important
regressions to catch here are the ones that would silently un-arm an ambush: a spring that
is not gated on the ambush's own flag (every ambush fires at once), a condition on the
coalition rather than the convoy's own group (a passing player springs the trap), or a
missing dug-in option (the team opens up on arrival and telegraphs itself).
"""

from __future__ import annotations

from typing import Any, Optional

import pytest
from dcs import Mission
from dcs.action import MarkToCoalition, MessageToCoalition, SetFlag
from dcs.condition import PartOfGroupInZone, TimeAfter
from dcs.mapping import Point
from dcs.task import ControlledTask, OptAlarmState, OptROE
from dcs.vehicles import Armor

from game.missiongenerator.convoyambushgenerator import (
    AMBUSH_START_GRACE_S,
    AMBUSH_TRIGGER_RADIUS_M,
    ConvoyAmbushGenerator,
)

# ---- fakes (only the campaign side; the mission is real) -----------------------------


class _FakeUnit:
    def __init__(self, alive: bool = True) -> None:
        self.alive = alive


class _FakeTheaterGroup:
    def __init__(self, group_name: str, alive: bool = True) -> None:
        self.group_name = group_name
        self.units = [_FakeUnit(alive)]


class _FakeTgo:
    def __init__(
        self, tgo_id: str, position: Point, groups: list[_FakeTheaterGroup]
    ) -> None:
        self.id = tgo_id
        self.position = position
        self.groups = groups


class _FakeControlPoint:
    def __init__(self, ground_objects: list[_FakeTgo]) -> None:
        self.ground_objects = ground_objects


class _FakeGame:
    def __init__(self, tgos: list[_FakeTgo], ambushes: list[dict[str, Any]]) -> None:
        self.settings = type("S", (), {"convoy_ambush": True})()
        self.theater = type("T", (), {"controlpoints": [_FakeControlPoint(tgos)]})()
        self.convoy_ambush_state = {"ambushes": ambushes}


# ---- fixture -------------------------------------------------------------------------


def _mission_with(
    team_names: list[str] = ["Ambush 1"],
    convoy_name: Optional[str] = "Convoy 001",
) -> tuple[Mission, list[Any]]:
    mission = Mission()
    usa = mission.country("USA")
    russia = mission.country("Russia")
    if convoy_name is not None:
        mission.vehicle_group(
            usa,
            convoy_name,
            Armor.M_1_Abrams,
            position=Point(1000, 1000, mission.terrain),
            group_size=2,
        )
    teams = [
        mission.vehicle_group(
            russia,
            name,
            Armor.BTR_80,
            position=Point(50000, 50000, mission.terrain),
        )
        for name in team_names
    ]
    return mission, teams


def _build(
    mission: Mission,
    *,
    team_names: list[str] = ["Ambush 1"],
    convoy: Optional[str] = "Convoy 001",
    alive: bool = True,
    enabled: bool = True,
) -> _FakeGame:
    tgo = _FakeTgo(
        "tgo-7",
        Point(50000, 50000, mission.terrain),
        [_FakeTheaterGroup(name, alive) for name in team_names],
    )
    game = _FakeGame([tgo], [{"tgo_id": "tgo-7", "convoy": convoy}] if convoy else [])
    if not enabled:
        game.settings.convoy_ambush = False
    return game


def _flag_of(mission: Mission) -> Any:
    """The ambush flag the first trigger raises."""
    for action in mission.triggerrules.triggers[0].actions:
        if isinstance(action, SetFlag):
            return action.flag
    raise AssertionError("no SetFlag action on the ambush trigger")


def _run(mission: Mission, game: _FakeGame) -> None:
    ConvoyAmbushGenerator(mission, game).generate()  # type: ignore[arg-type]


# ---- the spring ----------------------------------------------------------------------


def test_ambush_authors_one_zone_and_one_trigger() -> None:
    mission, _ = _mission_with()
    _run(mission, _build(mission))

    assert len(mission.triggers.zones()) == 1
    assert mission.triggers.zones()[0].radius == AMBUSH_TRIGGER_RADIUS_M
    assert len(mission.triggerrules.triggers) == 1


def test_trigger_waits_for_the_grace_and_this_convoys_own_group() -> None:
    """A coalition-wide condition would let a passing player spring the trap; the
    grace stops anything opening up while the player is still in the pit."""
    mission, _ = _mission_with()
    _run(mission, _build(mission))

    trigger = mission.triggerrules.triggers[0]
    zone = mission.triggers.zones()[0]
    convoy = mission.find_group("Convoy 001")
    assert convoy is not None

    times = [c for c in trigger.rules if isinstance(c, TimeAfter)]
    in_zone = [c for c in trigger.rules if isinstance(c, PartOfGroupInZone)]
    assert len(times) == 1 and times[0].seconds == AMBUSH_START_GRACE_S
    assert len(in_zone) == 1
    assert in_zone[0].group == convoy.id
    assert in_zone[0].zone == zone.id


def test_trigger_raises_the_flag_and_cues_the_player() -> None:
    mission, _ = _mission_with()
    _run(mission, _build(mission))

    actions = mission.triggerrules.triggers[0].actions
    assert any(isinstance(a, SetFlag) for a in actions)
    assert any(isinstance(a, MessageToCoalition) for a in actions)
    assert any(isinstance(a, MarkToCoalition) for a in actions)


def test_team_is_dug_in_and_springs_on_its_own_flag() -> None:
    """Weapons-hold + alarm-green immediately; weapons-free + alarm-red only once the
    ambush's own flag is raised."""
    mission, teams = _mission_with()
    _run(mission, _build(mission))

    tasks = teams[0].points[0].tasks
    plain = [t for t in tasks if not isinstance(t, ControlledTask)]
    gated = [t for t in tasks if isinstance(t, ControlledTask)]

    assert any(
        isinstance(t, OptROE) and t.value == OptROE.Values.WeaponHold for t in plain
    )
    assert any(isinstance(t, OptAlarmState) and t.value == 1 for t in plain)

    assert len(gated) == 2
    flag = _flag_of(mission)
    for task in gated:
        assert task.params["condition"]["userFlag"] == str(flag)
        assert task.params["condition"]["userFlagValue"] is True


def test_each_ambush_gets_its_own_flag() -> None:
    """Two ambushes sharing a flag would spring together -- the gauntlet would fire
    all at once the moment the convoy reached the first team."""
    mission = Mission()
    usa, russia = mission.country("USA"), mission.country("Russia")
    mission.vehicle_group(
        usa,
        "Convoy 001",
        Armor.M_1_Abrams,
        position=Point(1000, 1000, mission.terrain),
        group_size=2,
    )
    for name in ("Ambush 1", "Ambush 2"):
        mission.vehicle_group(
            russia,
            name,
            Armor.BTR_80,
            position=Point(50000, 50000, mission.terrain),
        )
    tgos = [
        _FakeTgo(
            f"tgo-{i}",
            Point(50000 + i, 50000, mission.terrain),
            [_FakeTheaterGroup(name)],
        )
        for i, name in enumerate(("Ambush 1", "Ambush 2"))
    ]
    game = _FakeGame(
        tgos,
        [
            {"tgo_id": "tgo-0", "convoy": "Convoy 001"},
            {"tgo_id": "tgo-1", "convoy": "Convoy 001"},
        ],
    )
    _run(mission, game)

    assert len(mission.triggerrules.triggers) == 2
    flags = {
        action.flag
        for trigger in mission.triggerrules.triggers
        for action in trigger.actions
        if isinstance(action, SetFlag)
    }
    assert len(flags) == 2


def test_all_teams_of_one_ambush_share_that_ambushs_flag() -> None:
    mission, teams = _mission_with(team_names=["Ambush 1", "Ambush 1b"])
    _run(mission, _build(mission, team_names=["Ambush 1", "Ambush 1b"]))

    flag = _flag_of(mission)
    for team in teams:
        gated = [t for t in team.points[0].tasks if isinstance(t, ControlledTask)]
        assert gated, "every team of the ambush must carry the spring"
        assert all(t.params["condition"]["userFlag"] == str(flag) for t in gated)


def test_the_zone_is_hidden() -> None:
    """A visible circle on the ambush point would telegraph the whole feature."""
    mission, _ = _mission_with()
    _run(mission, _build(mission))
    assert mission.triggers.zones()[0].hidden is True


def test_the_mission_still_serializes() -> None:
    """ControlledTask-wrapped options and the trigger rules must survive pydcs
    serialization -- a mission that cannot be written is worse than no ambush."""
    mission, _ = _mission_with()
    _run(mission, _build(mission))
    assert mission.dict()["trig"] is not None


# ---- guards --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"enabled": False}, id="setting off"),
        pytest.param({"alive": False}, id="team already dead"),
        pytest.param({"convoy": None}, id="no pairing recorded"),
    ],
)
def test_guards_author_nothing(kwargs: dict[str, Any]) -> None:
    mission, teams = _mission_with()
    _run(mission, _build(mission, **kwargs))

    assert mission.triggerrules.triggers == []
    assert mission.triggers.zones() == []
    assert teams[0].points[0].tasks == []


def test_a_convoy_that_was_never_generated_authors_nothing() -> None:
    """The transfer completed (or convoy generation is off): nobody can drive into
    the ambush, so there is nothing to arm -- and no crash."""
    mission, teams = _mission_with(convoy_name=None)
    _run(mission, _build(mission))

    assert mission.triggerrules.triggers == []
    assert teams[0].points[0].tasks == []
