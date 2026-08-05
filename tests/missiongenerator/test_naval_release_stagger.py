"""§81 N1 -- the naval weapons-release stagger, authored at generation.

A modern anti-ship missile out-ranges the whole theatre, so "in range" is true from
t=0 and an unstaggered fleet empties its tubes in the opening minute (the flown
Marianas 2027 Tacview: 374 launches, essentially all inside five minutes). N1 spreads
the releases across a window.

This used to be a plugin that re-derived the fleet ordering at runtime and scheduled
the releases itself. "At time T, set this group's ROE" is exactly what a DCS start
condition expresses, and Python already knows the whole fleet -- so the schedule is
computed here and authored onto each ship as a ``ControlledTask``. These tests drive
the **real** ``set_ship_engagement`` against **real** pydcs ship groups, so what is
asserted is the mission structure DCS will read.

The regressions that matter are the silent ones: a fleet released all at once (the
bug N1 exists to fix), a dry group released anyway (it has nothing to fire), and a
stagger-off mission that stops being byte-identical to the pre-feature behaviour.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from dcs import Mission
from dcs.mapping import Point
from dcs.ships import USS_Arleigh_Burke_IIa
from dcs.task import ControlledTask, OptROE

from game.fourteenth.naval_magazines import (
    NAVAL_RELEASE_WINDOW_END_S,
    NAVAL_RELEASE_WINDOW_START_S,
    naval_release_schedule,
)
from game.missiongenerator.tgogenerator import GroundObjectGenerator
from game.theater import Player

BURKE = "USS_Arleigh_Burke_IIa"


def _ship_tgo(owner_cp: Any, group_name: str) -> Any:
    units = [SimpleNamespace(alive=True, type=SimpleNamespace(id=BURKE))]
    return SimpleNamespace(
        category="ship",
        name=group_name,
        control_point=owner_cp,
        groups=[SimpleNamespace(group_name=group_name, units=units)],
        units=units,
    )


def _game(names: list[str], *, stagger: bool = True, metered: bool = False) -> Any:
    blue_cp = SimpleNamespace(captured=Player.BLUE, ground_objects=[])
    for name in names:
        blue_cp.ground_objects.append(_ship_tgo(blue_cp, name))
    game = SimpleNamespace(
        theater=SimpleNamespace(controlpoints=[blue_cp]),
        settings=SimpleNamespace(
            naval_weapon_release_stagger=stagger,
            naval_magazines=metered,
        ),
    )
    game.naval_magazines = {}
    return game


# ---- the schedule --------------------------------------------------------------------


def test_releases_are_spread_evenly_across_the_window() -> None:
    """Evenly, not rolled independently: a small fleet must not randomly land every
    release in the same few seconds (the §49 stagger lesson)."""
    schedule = naval_release_schedule(_game(["A", "B", "C"]))
    middle = (NAVAL_RELEASE_WINDOW_START_S + NAVAL_RELEASE_WINDOW_END_S) // 2
    assert sorted(schedule.values()) == [
        NAVAL_RELEASE_WINDOW_START_S,
        middle,
        NAVAL_RELEASE_WINDOW_END_S,
    ]


def test_a_lone_group_opens_the_window() -> None:
    assert naval_release_schedule(_game(["A"])) == {"A": NAVAL_RELEASE_WINDOW_START_S}


def test_no_schedule_when_the_stagger_is_off() -> None:
    assert naval_release_schedule(_game(["A", "B"], stagger=False)) == {}


def test_the_schedule_is_deterministic() -> None:
    """It is read once per ship group during generation, so it must not drift."""
    game = _game(["A", "B", "C"])
    assert naval_release_schedule(game) == naval_release_schedule(game)


def test_a_dry_group_is_never_scheduled_for_release() -> None:
    """Nothing to release it for -- it stays at ReturnFire, winchester but able to
    defend itself."""
    game = _game(["Spent", "Loaded"], metered=True)
    game.naval_magazines = {"Spent": 0, "Loaded": 8}
    schedule = naval_release_schedule(game)
    assert "Spent" not in schedule
    assert "Loaded" in schedule


def test_the_stagger_alone_does_not_seed_magazines() -> None:
    """Metering is a separate tier; scheduling must not create campaign state."""
    game = _game(["A", "B"], metered=False)
    naval_release_schedule(game)
    assert game.naval_magazines == {}


# ---- what is authored onto the ship --------------------------------------------------


def _ship_group(mission: Mission, name: str) -> Any:
    return mission.ship_group(
        mission.country("USA"),
        name,
        USS_Arleigh_Burke_IIa,
        position=Point(1000, 1000, mission.terrain),
    )


def _engage(game: Any, name: str) -> Any:
    mission = Mission()
    group = _ship_group(mission, name)
    generator = GroundObjectGenerator.__new__(GroundObjectGenerator)
    generator.game = game
    generator.set_ship_engagement(group)
    return group


def _roe(group: Any) -> list[Any]:
    return [t for t in group.points[0].tasks if isinstance(t, OptROE)]


def _gated(group: Any) -> list[ControlledTask]:
    return [t for t in group.points[0].tasks if isinstance(t, ControlledTask)]


def test_a_staggered_ship_starts_on_return_fire_and_frees_itself_on_time() -> None:
    group = _engage(_game(["A"]), "A")

    assert [t.value for t in _roe(group)] == [OptROE.Values.ReturnFire]
    gated = _gated(group)
    assert len(gated) == 1
    assert gated[0].params["condition"]["time"] == NAVAL_RELEASE_WINDOW_START_S
    freed = gated[0].params["task"]["params"]["action"]["params"]
    assert freed["value"] == OptROE.Values.WeaponFree


def test_stagger_off_is_the_pre_feature_mission() -> None:
    """Weapons-free at t=0 with nothing conditioned -- byte-identical to before N1."""
    group = _engage(_game(["A"], stagger=False), "A")

    assert [t.value for t in _roe(group)] == [OptROE.Values.WeaponFree]
    assert _gated(group) == []


def test_a_dry_ship_is_held_at_return_fire_with_no_release() -> None:
    game = _game(["Spent"], metered=True)
    game.naval_magazines = {"Spent": 0}
    group = _engage(game, "Spent")

    assert [t.value for t in _roe(group)] == [OptROE.Values.ReturnFire]
    assert _gated(group) == [], "a spent magazine must never be released"


def test_a_dry_ship_is_winchester_even_without_the_stagger() -> None:
    """A fleet that spent its tubes in earlier turns must not fight as if freshly
    loaded just because the stagger is off."""
    game = _game(["Spent"], stagger=False, metered=True)
    game.naval_magazines = {"Spent": 0}
    group = _engage(game, "Spent")

    assert [t.value for t in _roe(group)] == [OptROE.Values.ReturnFire]
    assert _gated(group) == []


@pytest.mark.parametrize("metered", [False, True])
def test_a_loaded_ship_is_never_held_when_the_stagger_is_off(metered: bool) -> None:
    game = _game(["Loaded"], stagger=False, metered=metered)
    group = _engage(game, "Loaded")
    assert [t.value for t in _roe(group)] == [OptROE.Values.WeaponFree]


def test_the_authored_mission_still_serializes() -> None:
    mission = Mission()
    group = _ship_group(mission, "A")
    generator = GroundObjectGenerator.__new__(GroundObjectGenerator)
    generator.game = _game(["A"])
    generator.set_ship_engagement(group)
    assert mission.dict() is not None
