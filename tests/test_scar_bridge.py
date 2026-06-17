"""Tests for the SCAR scenario/results bridge (Python side).

The bridge is the spec-§8a integration seam: the generator builds a ScarTasking
per SCAR flight, emits it as a dcsRetribution.Scar Lua table, the SCAR plugin
runs the scenario in-mission, and the outcome flows back through state.json into
the debrief. AI convoys are rare, so the default is to SPAWN a moving HVT; a SCAR
flight against a real surface-to-surface missile site binds to it instead (SCUD,
watch-only). The Lua half needs an in-game pass; here we lock in the Python half
CI can verify: tasking collection, Lua emission, and result parsing.
"""

from typing import Any
from unittest.mock import MagicMock

from dcs.mapping import Point

from game.ato.flighttype import FlightType
from game.debriefing import StateData
from game.missiongenerator.luagenerator import LuaData
from game.missiongenerator.scarluadata import (
    SCAR_CLUTTER_COUNT,
    SCAR_DECOY_SIGNATURES,
    SCAR_HVT_SIGNATURE,
    SCAR_THREAT_LAYDOWN,
    build_scar_taskings,
    populate_scar_lua,
)
from game.theater.theatergroundobject import MissileSiteGroundObject


def _coalition_with_target(
    target: Any, *, extra_types: tuple[FlightType, ...] = ()
) -> Any:
    """A coalition whose single package has a SCAR flight (plus any extra flight
    types) against ``target``, with a known enemy country id."""
    package = MagicMock()
    package.target = target
    package.flights = [MagicMock(flight_type=FlightType.SCAR)] + [
        MagicMock(flight_type=ft) for ft in extra_types
    ]
    coalition = MagicMock()
    coalition.opponent.faction.country.id = 7
    coalition.ato.packages = [package]
    return coalition


def _game_with(*coalitions: Any) -> Any:
    game = MagicMock()
    game.coalitions = list(coalitions)
    return game


def test_default_target_yields_spawn_tasking() -> None:
    # Any non-missile target -> spawn the ground picture around the target area.
    target = MagicMock()
    target.position = Point(1000, 2000, None)  # type: ignore[arg-type]
    game = _game_with(_coalition_with_target(target, extra_types=(FlightType.CAS,)))

    taskings = build_scar_taskings(game)

    assert len(taskings) == 1  # the CAS flight is ignored
    tasking = taskings[0]
    assert tasking.variant == "spawn"
    assert tasking.hvt_country_id == 7  # the enemy (opponent) country

    # One HVT (full signature) + decoys + clutter + threat units.
    roles = [c.role for c in tasking.convoys]
    assert roles.count("hvt") == 1
    assert roles.count("decoy") == len(SCAR_DECOY_SIGNATURES)
    assert roles.count("clutter") == SCAR_CLUTTER_COUNT
    assert roles.count("threat") == len(SCAR_THREAT_LAYDOWN)

    hvts = [c for c in tasking.convoys if c.role == "hvt"]
    assert hvts[0].unit_types == SCAR_HVT_SIGNATURE
    # Every decoy is a strict partial signature — never the full element set.
    for decoy in (c for c in tasking.convoys if c.role == "decoy"):
        assert decoy.unit_types != SCAR_HVT_SIGNATURE
        assert len(decoy.unit_types) < len(SCAR_HVT_SIGNATURE)

    # Threats are stationary (dest == spawn) and untracked.
    for threat in (c for c in tasking.convoys if c.role == "threat"):
        assert (threat.dest_x, threat.dest_y) == (threat.spawn_x, threat.spawn_y)


def test_missile_site_target_yields_missile_tasking() -> None:
    site = MagicMock(spec=MissileSiteGroundObject)
    site.groups = [MagicMock(group_name="SCUD-1"), MagicMock(group_name="SCUD-2")]
    game = _game_with(_coalition_with_target(site))

    taskings = build_scar_taskings(game)

    assert len(taskings) == 1
    assert taskings[0].variant == "missile"
    assert taskings[0].target_groups == ("SCUD-1", "SCUD-2")


def test_empty_without_scar_flights() -> None:
    target = MagicMock()
    target.position = Point(0, 0, None)  # type: ignore[arg-type]
    coalition = _coalition_with_target(target)
    # Replace the SCAR flight with a non-SCAR one.
    coalition.ato.packages[0].flights = [MagicMock(flight_type=FlightType.CAS)]
    assert build_scar_taskings(_game_with(coalition)) == []


def test_populate_scar_lua_emits_spawn_fields() -> None:
    target = MagicMock()
    target.position = Point(1000, 2000, None)  # type: ignore[arg-type]
    taskings = build_scar_taskings(_game_with(_coalition_with_target(target)))

    root = LuaData("dcsRetribution")
    populate_scar_lua(root, taskings)
    serialized = root.serialize()

    assert "Scar" in serialized
    assert "taskingId" in serialized
    assert "scar-1" in serialized
    assert "spawn" in serialized
    assert "hvtCountryId" in serialized
    assert "convoys" in serialized
    assert "role" in serialized
    assert "hvt" in serialized
    assert "spawnX" in serialized
    assert SCAR_HVT_SIGNATURE[0] in serialized  # the SA-9 type appears


def test_populate_scar_lua_emits_missile_groups() -> None:
    site = MagicMock(spec=MissileSiteGroundObject)
    site.groups = [MagicMock(group_name="SCUD-1")]
    taskings = build_scar_taskings(_game_with(_coalition_with_target(site)))

    root = LuaData("dcsRetribution")
    populate_scar_lua(root, taskings)
    serialized = root.serialize()

    assert "missile" in serialized
    assert "targetGroups" in serialized
    assert "SCUD-1" in serialized
    assert "convoys" not in serialized  # spawn fields omitted for missile


def test_state_data_parses_scar_results() -> None:
    unit_map = MagicMock()
    data = {
        "scar_results": {
            "scar-1": {"status": "success"},
            "scar-2": {"status": "launched"},
            "scar-3": "active",  # tolerate a bare status string
        }
    }
    state = StateData.from_json(data, unit_map)
    assert state.scar_results == {
        "scar-1": "success",
        "scar-2": "launched",
        "scar-3": "active",
    }


def test_state_data_scar_results_default_empty() -> None:
    unit_map = MagicMock()
    # Lua serializes an empty table as [], which must parse to {} not crash.
    state = StateData.from_json({"scar_results": []}, unit_map)
    assert state.scar_results == {}
    state = StateData.from_json({}, unit_map)
    assert state.scar_results == {}
