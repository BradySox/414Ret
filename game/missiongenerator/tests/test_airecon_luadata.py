"""AI recon auto-capture emitter -> dcsRetribution.AIRecon.

The MOOSE TARS film path is player-only, so AI recon flights never confirmed BDA
(checklist G19). This emitter feeds the `airecon` plugin the AI-flown, player-coalition
recon flights + their targets. The invariants that must hold: a *player*-crewed flight is
never emitted (it films via F10), a *red* recon flight is never emitted (only the human
coalition's recon feeds the BDA ledger), a non-recon MANNED flight is ignored, a **drone
is emitted regardless of task** (a drone is always filming), and an absent-target or empty
flight list yields no node (the plugin then no-ops).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.ato import FlightType
from game.missiongenerator.aireconluadata import populate_ai_recon_lua
from game.missiongenerator.luagenerator import LuaData
from game.theater import Player

REAPER = "MQ-9 Reaper"
VIPER = "F-16C_50"  # a manned combat jet -- never a sensor unless tasked TARPS


def _flight(
    flight_type: FlightType,
    group_name: str,
    *,
    ai: bool = True,
    friendly: Player = Player.BLUE,
    has_target: bool = True,
    aircraft_id: str = VIPER,
) -> Any:
    target = (
        SimpleNamespace(position=SimpleNamespace(x=1000.0, y=2000.0))
        if has_target
        else SimpleNamespace(position=None)
    )
    return SimpleNamespace(
        flight_type=flight_type,
        group_name=group_name,
        client_units=[] if ai else [object()],  # non-empty = a human is aboard
        friendly=friendly,
        aircraft_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(id=aircraft_id)),
        package=SimpleNamespace(target=target),
    )


def _emit(flights: list[Any]) -> str:
    root = LuaData("dcsRetribution")
    game = SimpleNamespace()  # unused by the emitter
    mission_data = SimpleNamespace(flights=flights)
    populate_ai_recon_lua(root, game, mission_data)  # type: ignore[arg-type]
    return root.create_operations_lua()


def test_ai_blue_tarps_flight_is_emitted() -> None:
    lua = _emit([_flight(FlightType.TARPS, "BLOODHOUND TARPS")])
    assert "AIRecon" in lua
    assert "BLOODHOUND TARPS" in lua


def test_player_crewed_tarps_flight_is_not_emitted() -> None:
    # A human in the recon slot films via the F10 TARS menu -- never auto-captured.
    lua = _emit([_flight(FlightType.TARPS, "PLAYER TARPS", ai=False)])
    assert "AIRecon" not in lua


def test_red_recon_flight_is_not_emitted() -> None:
    # Only the human coalition's recon feeds the player BDA ledger.
    lua = _emit([_flight(FlightType.TARPS, "RED TARPS", friendly=Player.RED)])
    assert "AIRecon" not in lua


def test_non_recon_manned_flight_is_ignored() -> None:
    # A manned combat jet is not a sensor unless tasked TARPS.
    lua = _emit([_flight(FlightType.STRIKE, "STRIKE FLIGHT")])
    assert "AIRecon" not in lua


def test_a_drone_films_regardless_of_task() -> None:
    # A drone is always a sensor: it feeds BDA home whether it is on CAS, riding a
    # strike as the JTAC, or off on its own -- not only when tasked TARPS.
    for task in (
        FlightType.CAS,
        FlightType.BAI,
        FlightType.STRIKE,
        FlightType.DEAD,
        FlightType.ARMED_RECON,
    ):
        lua = _emit([_flight(task, "REAPER OVERWATCH", aircraft_id=REAPER)])
        assert "AIRecon" in lua and "REAPER OVERWATCH" in lua, task


def test_a_player_crewed_drone_is_not_auto_captured() -> None:
    lua = _emit(
        [_flight(FlightType.CAS, "PLAYER REAPER", ai=False, aircraft_id=REAPER)]
    )
    assert "AIRecon" not in lua


def test_a_red_drone_is_not_emitted() -> None:
    lua = _emit(
        [_flight(FlightType.CAS, "RED REAPER", friendly=Player.RED, aircraft_id=REAPER)]
    )
    assert "AIRecon" not in lua


def test_flight_without_a_target_is_skipped() -> None:
    lua = _emit([_flight(FlightType.TARPS, "NO TARGET TARPS", has_target=False)])
    assert "AIRecon" not in lua


def test_only_eligible_flights_are_emitted_from_a_mix() -> None:
    lua = _emit(
        [
            _flight(FlightType.TARPS, "AI BLUE TARPS"),  # emitted
            _flight(FlightType.TARPS, "PLAYER TARPS", ai=False),  # skipped (human)
            _flight(
                FlightType.TARPS, "RED TARPS", friendly=Player.RED
            ),  # skipped (red)
            _flight(FlightType.STRIKE, "STRIKE FLIGHT"),  # skipped (not recon)
        ]
    )
    assert "AI BLUE TARPS" in lua
    assert "PLAYER TARPS" not in lua
    assert "RED TARPS" not in lua
    assert "STRIKE FLIGHT" not in lua
