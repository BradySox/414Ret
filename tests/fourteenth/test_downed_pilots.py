"""Persistent downed pilots (§21 extension, 2026-07-10 squadron call).

An un-rescued, un-captured survivor goes MIA instead of dying at debrief,
re-spawns next mission, and rolls a DEPTH-weighted capture at every turn
boundary (near the front they keep evading; deep behind the lines enemy search
parties find them -> POW). Deliberately no death clock -- the roll is the clock.
These lock the ledger record/retire logic, the depth curve, the friendly-ground
walk-home, the roll -> POW handoff, and the SITREP lines.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from game.fourteenth import downed_pilots
from game.fourteenth.downed_pilots import (
    BASE_CAPTURE_CHANCE,
    DEEP_DEPTH_NM,
    DownedPilot,
    MAX_CAPTURE_CHANCE,
    NEAR_DEPTH_NM,
    capture_chance,
    mia_sitrep_lines,
    pilot_from_ledger,
    record_downed_pilots,
    resolve_downed_pilots,
)
from game.squadrons.pilot import Pilot, PilotStatus
from game.theater import Player

NM = 1852.0


class _Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def distance_to_point(self, other: "_Point") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


def _cp(x: float, y: float, player: Player, name: str = "Base") -> Any:
    return SimpleNamespace(
        position=_Point(x, y), captured=player, name=name, id=uuid4()
    )


def _game(
    cps: list[Any],
    fronts: list[Any] | None = None,
    *,
    persistence: bool = True,
    turn: int = 2,
) -> Any:
    messages: list[tuple[str, str]] = []
    game = SimpleNamespace(
        theater=SimpleNamespace(
            controlpoints=list(cps),
            conflicts=lambda: list(fronts or []),
        ),
        settings=SimpleNamespace(combat_sar_persistent_pilots=persistence),
        blue=SimpleNamespace(pending_pow_recoveries=[], player=Player.BLUE),
        point_in_world=lambda x, y: _Point(x, y),
        turn=turn,
        downed_pilots=[],
        messages=messages,
    )
    game.message = lambda title, text="": messages.append((title, text))
    return game


def _flying(pilot: Pilot, unit_type: str = "F-14B") -> Any:
    return SimpleNamespace(pilot=pilot, flight=SimpleNamespace(unit_type=unit_type))


def _debriefing(
    survivors: list[Any] | None = None,
    rescues: list[str] | None = None,
    captures: list[Any] | None = None,
    flight_map: dict[str, Any] | None = None,
) -> Any:
    fm = flight_map or {}
    return cast(
        Any,
        SimpleNamespace(
            state_data=SimpleNamespace(
                combat_sar_rescues=list(rescues or []),
                combat_sar_captures=list(captures or []),
                combat_sar_survivors=list(survivors or []),
                minefields_state=[],
            ),
            unit_map=SimpleNamespace(flight=lambda name: fm.get(name)),
        ),
    )


# --- The depth curve ------------------------------------------------------------


def test_capture_chance_endpoints() -> None:
    assert capture_chance(0.0) == BASE_CAPTURE_CHANCE
    assert capture_chance(NEAR_DEPTH_NM) == BASE_CAPTURE_CHANCE
    assert capture_chance(DEEP_DEPTH_NM) == MAX_CAPTURE_CHANCE
    assert capture_chance(200.0) == MAX_CAPTURE_CHANCE


def test_capture_chance_scales_linearly_between_the_depths() -> None:
    midpoint = (NEAR_DEPTH_NM + DEEP_DEPTH_NM) / 2
    expected = (BASE_CAPTURE_CHANCE + MAX_CAPTURE_CHANCE) / 2
    assert capture_chance(midpoint) == pytest.approx(expected)
    assert capture_chance(10.0) < capture_chance(30.0)


# --- Recording at mission-results commit -----------------------------------------


def test_new_survivor_goes_mia_and_joins_ledger() -> None:
    game = _game([_cp(0, 0, Player.RED)])
    pilot = Pilot("Capt Mitchell")
    debriefing = _debriefing(
        survivors=[("Enfield 1-1 | F-14B", 100.0, 200.0)],
        flight_map={"Enfield 1-1 | F-14B": _flying(pilot)},
    )

    record_downed_pilots(game, debriefing)

    assert pilot.status is PilotStatus.MIA
    assert len(game.downed_pilots) == 1
    entry = game.downed_pilots[0]
    assert entry.unit_name == "Enfield 1-1 | F-14B"
    assert (entry.x, entry.y) == (100.0, 200.0)
    assert entry.pilot is pilot
    assert entry.turn_downed == game.turn
    assert pilot_from_ledger(game, "Enfield 1-1 | F-14B") is pilot


def test_recording_is_gated_by_the_setting() -> None:
    # Toggle off = the pre-feature behaviour: no ledger entry, the pilot's fate is
    # commit_air_losses' (which also gates its MIA sparing on the setting).
    game = _game([_cp(0, 0, Player.RED)], persistence=False)
    pilot = Pilot("Capt Mitchell")
    debriefing = _debriefing(
        survivors=[("Enfield 1-1 | F-14B", 100.0, 200.0)],
        flight_map={"Enfield 1-1 | F-14B": _flying(pilot)},
    )

    record_downed_pilots(game, debriefing)

    assert game.downed_pilots == []
    assert pilot.status is PilotStatus.Active


def test_untracked_survivor_is_not_recorded() -> None:
    game = _game([_cp(0, 0, Player.RED)])
    debriefing = _debriefing(survivors=[("ghost_unit", 1.0, 2.0)], flight_map={})

    record_downed_pilots(game, debriefing)

    assert game.downed_pilots == []


def test_rescued_evader_returns_to_the_roster() -> None:
    game = _game([_cp(0, 0, Player.RED)])
    pilot = Pilot("Capt Mitchell")
    pilot.go_missing()
    game.downed_pilots.append(
        DownedPilot("Enfield 1-1 | F-14B", 1.0, 2.0, pilot=pilot, turn_downed=1)
    )
    debriefing = _debriefing(rescues=["Enfield 1-1 | F-14B"])

    record_downed_pilots(game, debriefing)

    assert game.downed_pilots == []
    assert pilot.status is PilotStatus.Active


def test_captured_evader_is_retired_from_the_ledger() -> None:
    # The POW hold itself is record_pow_captures' job (which resolves the pilot
    # from this ledger before record_downed_pilots retires the entry).
    game = _game([_cp(0, 0, Player.RED)])
    pilot = Pilot("Capt Mitchell")
    pilot.go_missing()
    game.downed_pilots.append(
        DownedPilot("Enfield 1-1 | F-14B", 1.0, 2.0, pilot=pilot, turn_downed=1)
    )
    debriefing = _debriefing(captures=[("Enfield 1-1 | F-14B", 1.0, 2.0, "blue")])

    record_downed_pilots(game, debriefing)

    assert game.downed_pilots == []


def test_still_unresolved_evader_keeps_its_single_entry() -> None:
    # A prior-turn evader re-reported by the plugin (still down at mission end)
    # keeps its existing entry -- never duplicated, turn_downed unchanged.
    game = _game([_cp(0, 0, Player.RED)])
    pilot = Pilot("Capt Mitchell")
    pilot.go_missing()
    game.downed_pilots.append(
        DownedPilot("Enfield 1-1 | F-14B", 1.0, 2.0, pilot=pilot, turn_downed=1)
    )
    debriefing = _debriefing(
        survivors=[("Enfield 1-1 | F-14B", 1.0, 2.0)],
        flight_map={},
    )

    record_downed_pilots(game, debriefing)

    assert len(game.downed_pilots) == 1
    assert game.downed_pilots[0].turn_downed == 1
    assert pilot.status is PilotStatus.MIA


# --- The turn-boundary resolution -------------------------------------------------


def test_evader_on_friendly_ground_walks_home() -> None:
    blue_cp = _cp(1000.0, 0.0, Player.BLUE, name="Fulda")
    red_cp = _cp(100 * NM, 0.0, Player.RED)
    game = _game([blue_cp, red_cp])
    pilot = Pilot("Capt Mitchell")
    pilot.go_missing()
    game.downed_pilots.append(
        DownedPilot("Enfield 1-1 | F-14B", 0.0, 0.0, pilot=pilot, turn_downed=1)
    )

    resolve_downed_pilots(game)

    assert game.downed_pilots == []
    assert pilot.status is PilotStatus.Active
    assert game.blue.pending_pow_recoveries == []


def test_deep_evader_is_captured_and_becomes_a_pow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    red_cp = _cp(1000.0, 0.0, Player.RED, name="Haina")
    blue_cp = _cp(200 * NM, 0.0, Player.BLUE)
    game = _game([red_cp, blue_cp], turn=5)
    pilot = Pilot("Capt Mitchell")
    pilot.go_missing()
    game.downed_pilots.append(
        DownedPilot("Enfield 1-1 | F-14B", 0.0, 0.0, pilot=pilot, turn_downed=1)
    )
    # 200 NM from the nearest friendly reference -> the 90% deep odds; a 0.5 roll
    # is under that, so the search party finds him.
    monkeypatch.setattr(downed_pilots._RNG, "random", lambda: 0.5)

    resolve_downed_pilots(game)

    assert game.downed_pilots == []
    assert pilot.status is PilotStatus.POW
    assert len(game.blue.pending_pow_recoveries) == 1
    entry = game.blue.pending_pow_recoveries[0]
    assert entry.airframe_unit_name == "Enfield 1-1 | F-14B"
    assert entry.captured_turn == 5
    assert entry.holding_cp_id == red_cp.id  # nearest enemy field holds the POW


def test_near_front_evader_keeps_evading_with_no_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    red_cp = _cp(1000.0, 0.0, Player.RED)
    front = SimpleNamespace(position=_Point(3 * NM, 0.0))
    game = _game([red_cp], fronts=[front])
    pilot = Pilot("Capt Mitchell")
    pilot.go_missing()
    game.downed_pilots.append(
        DownedPilot("Enfield 1-1 | F-14B", 0.0, 0.0, pilot=pilot, turn_downed=1)
    )
    # 3 NM behind the front -> the 10% near odds; a 0.5 roll survives it. There is
    # deliberately NO expiry: many turns of surviving rolls never write him off.
    monkeypatch.setattr(downed_pilots._RNG, "random", lambda: 0.5)

    for _ in range(10):
        resolve_downed_pilots(game)

    assert len(game.downed_pilots) == 1
    assert pilot.status is PilotStatus.MIA
    assert game.blue.pending_pow_recoveries == []


def test_resolve_is_a_noop_with_an_empty_ledger() -> None:
    game = _game([_cp(0, 0, Player.RED)])
    resolve_downed_pilots(game)
    assert game.downed_pilots == []


# --- SITREP ----------------------------------------------------------------------


def test_mia_sitrep_lines_name_place_and_clock() -> None:
    game = _game([_cp(1000.0, 0.0, Player.RED, name="Haina")], turn=3)
    pilot = Pilot("Capt Mitchell")
    game.downed_pilots.append(
        DownedPilot("Enfield 1-1 | F-14B", 0.0, 0.0, pilot=pilot, turn_downed=1)
    )
    game.downed_pilots.append(
        DownedPilot("Uzi 1-1 | F-16C", 0.0, 0.0, aircraft="F-16C", turn_downed=3)
    )

    lines = mia_sitrep_lines(game)

    assert lines == [
        "Capt Mitchell — evading near Haina (2 turns down)",
        "The F-16C pilot — evading near Haina (downed this turn)",
    ]
