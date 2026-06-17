"""Tests for the SCAR scenario/results bridge (Python side).

The bridge is the spec-§8a integration seam: the generator builds a ScarTasking
per SCAR flight, emits it as a dcsRetribution.Scar Lua table, the SCAR plugin
runs the scenario in-mission, and the outcome flows back through state.json into
the debrief. AI convoys are rare, so the default is to SPAWN a moving HVT; a SCAR
flight against a real surface-to-surface missile site binds to it instead (SCUD,
watch-only). The Lua half needs an in-game pass; here we lock in the Python half
CI can verify: tasking collection, Lua emission, and result parsing.
"""

from datetime import datetime, timedelta
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
    SCAR_WINDOW_S,
    build_scar_taskings,
    populate_scar_lua,
)
from game.theater.theatergroundobject import (
    MissileSiteGroundObject,
    VehicleGroupGroundObject,
)

MISSION_START = datetime(2026, 1, 1, 12, 0, 0)
TOT_OFFSET_S = 900.0  # the package TOT is 15 min after mission start


def _coalition_with_target(
    target: Any, *, extra_types: tuple[FlightType, ...] = ()
) -> Any:
    """A coalition whose single package has a SCAR flight (plus any extra flight
    types) against ``target``, a known enemy country id, and a TOT 15 min in."""
    package = MagicMock()
    package.target = target
    package.time_over_target = MISSION_START + timedelta(seconds=TOT_OFFSET_S)
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
    # No control points -> _nearest_city falls back to the fixed no-strike point.
    game.theater.controlpoints = []
    return game


def _build(game: Any) -> Any:
    return build_scar_taskings(game, MISSION_START)


def test_default_target_yields_spawn_tasking() -> None:
    # Any non-missile target -> spawn the ground picture around the target area.
    target = MagicMock()
    target.position = Point(1000, 2000, None)  # type: ignore[arg-type]
    game = _game_with(_coalition_with_target(target, extra_types=(FlightType.CAS,)))

    taskings = _build(game)

    assert len(taskings) == 1  # the CAS flight is ignored
    tasking = taskings[0]
    assert tasking.variant == "spawn"
    assert tasking.coalition == "blue"  # briefing addressee = the SCAR flight's side
    assert tasking.hvt_country_id == 7  # the enemy (opponent) country
    # Scenario is anchored to the flight's TOT, with the generous window after.
    assert tasking.go_live_s == TOT_OFFSET_S
    assert tasking.window_s == SCAR_WINDOW_S

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


def test_hvt_routes_to_nearest_enemy_city() -> None:
    # With an enemy-held control point present, the HVT flees toward it (the
    # "city") and carries a command vehicle that despawns there on arrival.
    target = MagicMock()
    target.position = Point(0, 0, None)  # type: ignore[arg-type]
    target.control_point.captured = True  # the enemy side
    city = MagicMock()
    city.captured = True  # same side as the target -> enemy-held = a city
    city.position = Point(10000, 0, None)  # type: ignore[arg-type]
    game = _game_with(_coalition_with_target(target))
    game.theater.controlpoints = [city]

    tasking = _build(game)[0]

    assert tasking.command_type  # the command vehicle to despawn in the city
    hvt = next(c for c in tasking.convoys if c.role == "hvt")
    assert (hvt.dest_x, hvt.dest_y) == (10000, 0)  # routed to the city


def test_armor_target_binds_real_group_and_flees_to_city() -> None:
    # A SCAR flight against a real armor group binds it (no spawned fakes): the
    # real group flees to the nearest city, success = killed / fail = it arrives.
    armor = MagicMock(spec=VehicleGroupGroundObject)
    # A mixed group so a partial-signature decoy can be derived.
    armor.groups = [
        MagicMock(
            units=[
                MagicMock(type=MagicMock(id="T-55")),
                MagicMock(type=MagicMock(id="T-55")),
                MagicMock(type=MagicMock(id="Ural-375")),
            ],
            group_name="ARMOR-1",
        )
    ]
    armor.position = Point(0, 0, None)  # type: ignore[arg-type]
    armor.control_point = MagicMock(captured=True)  # the enemy side
    city = MagicMock()
    city.captured = True  # same side as the target -> enemy-held = a city
    city.position = Point(8000, 0, None)  # type: ignore[arg-type]
    game = _game_with(_coalition_with_target(armor))
    game.theater.controlpoints = [city]

    tasking = _build(game)[0]

    assert tasking.variant == "armor"
    assert tasking.target_groups == ("ARMOR-1",)  # binds the REAL group
    assert (tasking.dest_x, tasking.dest_y) == (8000, 0)  # flees to the city
    assert tasking.flee_speed_ms > 0
    # Decoys/clutter are mixed in (spawned fakes), like the convoy variant.
    roles = [c.role for c in tasking.convoys]
    assert "decoy" in roles
    assert roles.count("clutter") == SCAR_CLUTTER_COUNT
    # A decoy is a strict partial of the real armor signature.
    real_sig = ("T-55", "T-55", "Ural-375")
    for decoy in (c for c in tasking.convoys if c.role == "decoy"):
        assert decoy.unit_types != real_sig
        assert all(u in real_sig for u in decoy.unit_types)


def test_missile_site_target_races_to_a_firing_position() -> None:
    site = MagicMock(spec=MissileSiteGroundObject)
    site.groups = [MagicMock(group_name="SCUD-1"), MagicMock(group_name="SCUD-2")]
    site.position = Point(0, 0, None)  # type: ignore[arg-type]
    site.control_point = MagicMock(captured=True)  # the enemy side
    target_cp = MagicMock()
    target_cp.captured = False  # opposite side -> the SCUD's target city
    target_cp.position = Point(20000, 0, None)  # type: ignore[arg-type]
    game = _game_with(_coalition_with_target(site))
    game.theater.controlpoints = [target_cp]

    tasking = _build(game)[0]

    assert tasking.variant == "missile"
    assert tasking.target_groups == ("SCUD-1", "SCUD-2")
    # Races a capped distance toward the target city, and fires at that city.
    assert tasking.dest_x > 0  # moved toward the target (+x / north)
    assert tasking.flee_speed_ms > 0
    assert (tasking.fire_target_x, tasking.fire_target_y) == (20000, 0)


def test_empty_without_scar_flights() -> None:
    target = MagicMock()
    target.position = Point(0, 0, None)  # type: ignore[arg-type]
    coalition = _coalition_with_target(target)
    # Replace the SCAR flight with a non-SCAR one.
    coalition.ato.packages[0].flights = [MagicMock(flight_type=FlightType.CAS)]
    assert _build(_game_with(coalition)) == []


def test_populate_scar_lua_emits_spawn_fields() -> None:
    target = MagicMock()
    target.position = Point(1000, 2000, None)  # type: ignore[arg-type]
    taskings = _build(_game_with(_coalition_with_target(target)))

    root = LuaData("dcsRetribution")
    populate_scar_lua(root, taskings)
    serialized = root.serialize()

    assert "Scar" in serialized
    assert "taskingId" in serialized
    assert "scar-1" in serialized
    assert "spawn" in serialized
    assert "hvtCountryId" in serialized
    assert "coalition" in serialized  # briefing addressee emitted
    assert "goLive" in serialized  # scenario timing emitted
    assert "window" in serialized
    assert "convoys" in serialized
    assert "role" in serialized
    assert "hvt" in serialized
    assert "spawnX" in serialized
    assert "speed" in serialized  # per-convoy pacing
    assert "commandType" in serialized  # command vehicle that despawns in the city
    assert SCAR_HVT_SIGNATURE[0] in serialized  # the SA-9 type appears


def test_populate_scar_lua_emits_missile_groups() -> None:
    site = MagicMock(spec=MissileSiteGroundObject)
    site.groups = [MagicMock(group_name="SCUD-1")]
    site.position = Point(0, 0, None)  # type: ignore[arg-type]
    site.control_point = MagicMock(captured=True)
    taskings = _build(_game_with(_coalition_with_target(site)))

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
