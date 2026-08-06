"""Recon BDA capture emitter -> dcsRetribution.Recon.

Replaces the AI-only emitter that fed the old `airecon` plugin. The MOOSE `Ops.TARS`
film path was cut on 2026-08-05, so this now feeds ONE plugin covering both crews.

The load-bearing change is that a **player-crewed flight is emitted too**: the F10 film
menu that used to serve players is gone, so excluding them here would leave a human recon
sortie confirming nothing at all. `test_player_crewed_tarps_flight_is_emitted` is the
regression guard for exactly that, and it is the direct inverse of the assertion the old
suite made.

The rest of the contract is unchanged: a *red* recon flight is never emitted (only the
human coalition's recon feeds the BDA ledger), a non-recon MANNED flight is ignored, a
**drone is emitted regardless of task** (a drone is always filming), and an absent-target
or empty flight list yields no node (the plugin then no-ops).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from game.ato import FlightType
from game.missiongenerator.luagenerator import LuaData
from game.missiongenerator.reconluadata import (
    DRONE_SENSOR_RADIUS_NM,
    TARPS_POD_RADIUS_NM,
    populate_recon_lua,
)
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
        SimpleNamespace(position=SimpleNamespace(x=1000.0, y=2000.0), name="Shirqat")
        if has_target
        else SimpleNamespace(position=None, name="Shirqat")
    )
    return SimpleNamespace(
        flight_type=flight_type,
        group_name=group_name,
        callsign="Myna11",
        client_units=[] if ai else [object()],
        friendly=friendly,
        aircraft_type=SimpleNamespace(
            dcs_unit_type=SimpleNamespace(id=aircraft_id),
            display_name=aircraft_id,
        ),
        package=SimpleNamespace(target=target),
    )


def _game(cloud_density: Optional[int] = None) -> Any:
    clouds = (
        SimpleNamespace(density=cloud_density) if cloud_density is not None else None
    )
    return SimpleNamespace(
        conditions=SimpleNamespace(weather=SimpleNamespace(clouds=clouds))
    )


def _emit(flights: list[Any], game: Any = None) -> str:
    root = LuaData("dcsRetribution")
    mission_data = SimpleNamespace(flights=flights)
    populate_recon_lua(root, game or _game(), mission_data)  # type: ignore[arg-type]
    return root.create_operations_lua()


def test_ai_blue_tarps_flight_is_emitted() -> None:
    lua = _emit([_flight(FlightType.TARPS, "BLOODHOUND TARPS")])
    assert "Recon" in lua
    assert "BLOODHOUND TARPS" in lua


def test_player_crewed_tarps_flight_is_emitted() -> None:
    """The rebuild's whole point, and the inverse of the old suite's assertion.

    With MOOSE TARS cut there is no F10 film menu, so a human recon sortie only
    confirms anything if it is emitted here.
    """
    lua = _emit([_flight(FlightType.TARPS, "PLAYER TARPS", ai=False)])
    assert "PLAYER TARPS" in lua


def test_player_and_ai_recon_are_emitted_identically() -> None:
    """One mechanism for both crews -- they must not differ in the emitted shape."""
    ai = _emit([_flight(FlightType.TARPS, "RECON FLIGHT")])
    player = _emit([_flight(FlightType.TARPS, "RECON FLIGHT", ai=False)])
    assert ai == player


def test_emitted_record_carries_a_display_label_and_target_name() -> None:
    lua = _emit([_flight(FlightType.TARPS, "BLOODHOUND TARPS", aircraft_id=REAPER)])
    assert "Myna11 (MQ-9 Reaper)" in lua
    assert "Shirqat" in lua


def test_tarps_tasking_carries_the_pod_sensor_radius() -> None:
    lua = _emit([_flight(FlightType.TARPS, "POD FLIGHT", aircraft_id=REAPER)])
    assert str(TARPS_POD_RADIUS_NM) in lua


def test_an_untasked_drone_carries_the_smaller_ball_radius() -> None:
    lua = _emit([_flight(FlightType.CAS, "BALL FLIGHT", aircraft_id=REAPER)])
    assert str(DRONE_SENSOR_RADIUS_NM) in lua


def test_red_recon_flight_is_not_emitted() -> None:
    lua = _emit([_flight(FlightType.TARPS, "RED TARPS", friendly=Player.RED)])
    assert "Recon" not in lua


def test_non_recon_manned_flight_is_ignored() -> None:
    lua = _emit([_flight(FlightType.STRIKE, "STRIKE FLIGHT")])
    assert "Recon" not in lua


def test_a_drone_films_regardless_of_task() -> None:
    for task in (
        FlightType.CAS,
        FlightType.BAI,
        FlightType.STRIKE,
        FlightType.DEAD,
        FlightType.ARMED_RECON,
    ):
        lua = _emit([_flight(task, "REAPER OVERWATCH", aircraft_id=REAPER)])
        assert "Recon" in lua and "REAPER OVERWATCH" in lua, task


def test_a_red_drone_is_not_emitted() -> None:
    lua = _emit(
        [_flight(FlightType.CAS, "RED REAPER", friendly=Player.RED, aircraft_id=REAPER)]
    )
    assert "Recon" not in lua


def test_flight_without_a_target_is_skipped() -> None:
    lua = _emit([_flight(FlightType.TARPS, "NO TARGET TARPS", has_target=False)])
    assert "Recon" not in lua


# --- weather gating -----------------------------------------------------------
#
# The fork models an evolving sky (§47) and consults it when planning (§67); recon
# ignored it entirely, which is the one mission the weather most obviously governs.


def test_clear_sky_leaves_the_sensor_at_full_reach() -> None:
    lua = _emit([_flight(FlightType.TARPS, "CLEAR")], _game(cloud_density=0))
    assert "1.0" in lua


def test_overcast_degrades_the_sensor_but_never_to_zero() -> None:
    lua = _emit([_flight(FlightType.TARPS, "SOUP")], _game(cloud_density=10))
    # 1.0 - 0.75 * 1.0 == 0.25: filthy weather still brings something home, because a
    # hard zero reads as the feature being broken rather than as bad weather.
    assert "0.25" in lua


def test_absent_weather_data_is_treated_as_clear() -> None:
    lua = _emit([_flight(FlightType.TARPS, "NO WX")], SimpleNamespace())
    assert "Recon" in lua


def test_the_cloud_factor_survives_serialization_alongside_the_flight_list() -> None:
    """Guards the §81 LuaData trap.

    ``LuaData.serialize`` silently DROPS a node's ``add_key_value`` entries when the
    node also carries child items -- the bug that kept §81's `stagger`/`metered`
    switches out of the miz entirely while the list beside them survived. ``Recon``
    has a ``flights`` child, so ``cloudFactor`` has to be emitted as a named child
    item; if anyone converts it back to a key/value it vanishes and the weather gate
    silently stops working.
    """
    lua = _emit([_flight(FlightType.TARPS, "WX")], _game(cloud_density=4))
    assert "cloudFactor" in lua
    assert "0.7" in lua  # 1.0 - 0.75 * 0.4


def test_only_eligible_flights_are_emitted_from_a_mix() -> None:
    lua = _emit(
        [
            _flight(FlightType.TARPS, "AI BLUE TARPS"),  # emitted
            _flight(FlightType.TARPS, "PLAYER TARPS", ai=False),  # emitted (rebuild)
            _flight(FlightType.TARPS, "RED TARPS", friendly=Player.RED),  # skipped
            _flight(FlightType.STRIKE, "STRIKE FLIGHT"),  # skipped (not recon)
        ]
    )
    assert "AI BLUE TARPS" in lua
    assert "PLAYER TARPS" in lua
    assert "RED TARPS" not in lua
    assert "STRIKE FLIGHT" not in lua
