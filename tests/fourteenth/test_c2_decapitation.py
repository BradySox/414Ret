"""Command-center decapitation -> degraded enemy planning (§52, Features A1+A2).

Locks the coupling: a side's dead command centers scale its planner
unpredictability up (0 when off / intact), the health fraction is exact, the SITREP
status line reads the enemy network, and a C2-less campaign is a no-op. A2 locks
the offensive package-count throttle: the cap shrinks with C2 health (floored,
None when off/intact), and the HTN root stops offering the offensive middle once
the side's planned offensive packages reach it -- reactive prefix and recovery
tail are never throttled.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from game.ato.flighttype import FlightType
from game.commander.tasks.compound.nextaction import PlanNextAction
from game.fourteenth.c2_decapitation import (
    FULL_OFFENSIVE_PACKAGE_CAP,
    MAX_DECAP_UNPREDICTABILITY,
    MIN_OFFENSIVE_PACKAGES,
    c2_health,
    c2_status_line,
    offensive_package_cap,
    unpredictability_bonus,
)
from game.theater import Player


def _tgo(category: str, *alive: bool) -> Any:
    units = [SimpleNamespace(alive=a) for a in alive]
    return SimpleNamespace(category=category, groups=[SimpleNamespace(units=units)])


def _coalition(player: Player) -> Any:
    return SimpleNamespace(player=player)


def _theater(cps: list[Any]) -> Any:
    return SimpleNamespace(controlpoints=cps)


def _cp(owner: Player, tgos: list[Any]) -> Any:
    return SimpleNamespace(captured=owner, ground_objects=tgos)


def _settings(on: bool = True) -> Any:
    return SimpleNamespace(c2_decapitation_effects=on)


RED = _coalition(Player.RED)


def test_health_is_the_alive_fraction_of_own_command_centers() -> None:
    theater = _theater(
        [
            _cp(
                Player.RED, [_tgo("commandcenter", True), _tgo("commandcenter", False)]
            ),
            _cp(Player.RED, [_tgo("commandcenter", True)]),
            # A blue-owned CC and a non-C2 red TGO are both ignored.
            _cp(Player.BLUE, [_tgo("commandcenter", True)]),
            _cp(Player.RED, [_tgo("aa", True)]),
        ]
    )
    # 2 of 3 red command centers alive.
    assert c2_health(cast(Any, RED), cast(Any, theater)) == 2 / 3


def test_no_command_centers_is_full_health() -> None:
    theater = _theater([_cp(Player.RED, [_tgo("aa", True)])])
    assert c2_health(cast(Any, RED), cast(Any, theater)) == 1.0


def test_bonus_scales_with_the_dead_fraction() -> None:
    intact = _theater([_cp(Player.RED, [_tgo("commandcenter", True)])])
    half = _theater(
        [_cp(Player.RED, [_tgo("commandcenter", True), _tgo("commandcenter", False)])]
    )
    dead = _theater([_cp(Player.RED, [_tgo("commandcenter", False)])])

    assert unpredictability_bonus(cast(Any, RED), cast(Any, intact), _settings()) == 0
    assert unpredictability_bonus(
        cast(Any, RED), cast(Any, half), _settings()
    ) == round(0.5 * MAX_DECAP_UNPREDICTABILITY)
    assert (
        unpredictability_bonus(cast(Any, RED), cast(Any, dead), _settings())
        == MAX_DECAP_UNPREDICTABILITY
    )


def test_bonus_is_zero_when_the_feature_is_off() -> None:
    dead = _theater([_cp(Player.RED, [_tgo("commandcenter", False)])])
    assert (
        unpredictability_bonus(cast(Any, RED), cast(Any, dead), _settings(on=False))
        == 0
    )


def _game(theater: Any, on: bool = True) -> Any:
    return SimpleNamespace(
        theater=theater,
        settings=_settings(on),
        coalition_for=lambda _p: RED,
    )


def test_status_line_reports_a_degraded_enemy_network() -> None:
    theater = _theater(
        [_cp(Player.RED, [_tgo("commandcenter", True), _tgo("commandcenter", False)])]
    )
    line = c2_status_line(cast(Any, _game(theater)), Player.RED)
    assert line == "1/2 command posts operational"


def test_status_line_is_none_when_intact_off_or_c2_less() -> None:
    intact = _theater([_cp(Player.RED, [_tgo("commandcenter", True)])])
    assert c2_status_line(cast(Any, _game(intact)), Player.RED) is None
    degraded = _theater([_cp(Player.RED, [_tgo("commandcenter", False)])])
    assert c2_status_line(cast(Any, _game(degraded, on=False)), Player.RED) is None
    c2_less = _theater([_cp(Player.RED, [_tgo("aa", True)])])
    assert c2_status_line(cast(Any, _game(c2_less)), Player.RED) is None


# --- §52 A2: the offensive package-count throttle ---


def test_offensive_package_cap_scales_with_health_and_floors() -> None:
    half = _theater(
        [_cp(Player.RED, [_tgo("commandcenter", True), _tgo("commandcenter", False)])]
    )
    dead = _theater([_cp(Player.RED, [_tgo("commandcenter", False)])])
    assert offensive_package_cap(cast(Any, RED), cast(Any, half), _settings()) == max(
        MIN_OFFENSIVE_PACKAGES, round(0.5 * FULL_OFFENSIVE_PACKAGE_CAP)
    )
    assert (
        offensive_package_cap(cast(Any, RED), cast(Any, dead), _settings())
        == MIN_OFFENSIVE_PACKAGES
    )


def test_offensive_package_cap_is_none_when_off_intact_or_c2_less() -> None:
    intact = _theater([_cp(Player.RED, [_tgo("commandcenter", True)])])
    assert offensive_package_cap(cast(Any, RED), cast(Any, intact), _settings()) is None
    dead = _theater([_cp(Player.RED, [_tgo("commandcenter", False)])])
    assert (
        offensive_package_cap(cast(Any, RED), cast(Any, dead), _settings(on=False))
        is None
    )
    c2_less = _theater([_cp(Player.RED, [_tgo("aa", True)])])
    assert (
        offensive_package_cap(cast(Any, RED), cast(Any, c2_less), _settings()) is None
    )


def _planner_state(ccs: list[bool], planned: list[FlightType], on: bool = True) -> Any:
    """A fake TheaterState for the HTN-root throttle gate.

    ``ccs`` is the aliveness of RED's command centers; ``planned`` is the
    primary task of each package already on RED's ATO this planning run."""
    settings = SimpleNamespace(c2_decapitation_effects=on)
    theater = _theater([_cp(Player.RED, [_tgo("commandcenter", a) for a in ccs])])
    game = SimpleNamespace(settings=settings)
    ato = SimpleNamespace(
        packages=[SimpleNamespace(primary_task=t) for t in planned],
    )
    coalition = SimpleNamespace(player=Player.RED, game=game, ato=ato)
    return SimpleNamespace(
        context=SimpleNamespace(settings=settings, coalition=coalition, theater=theater)
    )


def _method_names(state: Any) -> list[str]:
    task = PlanNextAction(aircraft_cold_start=False)
    return [type(m[0]).__name__ for m in task.each_valid_method(cast(Any, state))]


def test_throttle_closes_the_offensive_middle_at_the_cap() -> None:
    # 1 of 2 CCs dead -> cap 6. Six offensive packages planned: the offensive
    # methods stop being offered, but the reactive prefix and the recovery tail
    # are untouched (the §17 boundary).
    state = _planner_state([True, False], [FlightType.STRIKE] * 6)
    names = _method_names(state)
    assert "AttackBuildings" not in names
    assert "CaptureBases" not in names
    assert names[:3] == ["TheaterSupport", "ProtectAirSpace", "DefendBases"]
    assert names[-1] == "RecoverySupport"


def test_throttle_leaves_offense_open_below_the_cap() -> None:
    state = _planner_state([True, False], [FlightType.STRIKE] * 5)
    assert "AttackBuildings" in _method_names(state)


def test_reactive_and_ambiguous_packages_never_eat_the_cap() -> None:
    # BARCAP (reactive), CAS and DEAD (ambiguous -- planned defensively too) are
    # excluded from the count, so a defensive-heavy ATO never trips the throttle.
    planned = [FlightType.BARCAP, FlightType.CAS, FlightType.DEAD] * 4
    state = _planner_state([True, False], planned)
    assert "AttackBuildings" in _method_names(state)


def test_no_throttle_when_intact_or_off() -> None:
    state = _planner_state([True], [FlightType.STRIKE] * 20)
    assert "AttackBuildings" in _method_names(state)
    state = _planner_state([False], [FlightType.STRIKE] * 20, on=False)
    assert "AttackBuildings" in _method_names(state)
