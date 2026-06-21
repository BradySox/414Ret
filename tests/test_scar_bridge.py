"""Tests for the SCAR scenario/results bridge (Python side).

The bridge is the spec-§8a integration seam: the generator builds a ScarTasking
per SCAR flight, emits it as a dcsRetribution.Scar Lua table, the SCAR plugin
runs the scenario in-mission, and the outcome flows back through state.json into
the debrief. AI convoys are rare, so the default is to SPAWN a moving HVT; a SCAR
flight against a real surface-to-surface missile site binds to it instead (SCUD,
watch-only). The Lua half needs an in-game pass; here we lock in the Python half
CI can verify: tasking collection, Lua emission, and result parsing.
"""

import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from dcs.mapping import Point

from game.ato.flighttype import FlightType
from game.debriefing import StateData
from game.missiongenerator.luagenerator import LuaData
from game.missiongenerator.scarluadata import (
    SCAR_CLUTTER_COUNT,
    SCAR_COMMAND,
    SCAR_DECOY_SIGNATURES,
    SCAR_HVT_SIGNATURE,
    SCAR_MIN_FLEE_M,
    SCAR_SOF_CAPTURE_RADIUS_M,
    SCAR_SOF_LEAD_FRAC,
    SCAR_THREAT_LAYDOWN,
    SCAR_WINDOW_S,
    build_scar_taskings,
    populate_scar_lua,
)
from game.theater import Player
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
    coalition.player = Player.BLUE
    coalition.opponent.faction.country.id = 7  # enemy (HVT) country
    coalition.faction.country.id = 2  # friendly (SOF) country
    coalition.ato.packages = [package]
    return coalition


def _game_with(*coalitions: Any) -> Any:
    game = MagicMock()
    game.coalitions = list(coalitions)
    # No control points -> _nearest_city falls back to the fixed no-strike point.
    game.theater.controlpoints = []
    # Phase 2a SOF ambush is gated behind this; default OFF for the base tests.
    game.settings.scar_command_post_intel = False
    # Land-snap is a no-op unless a point is in the sea; keep test coords exact.
    game.theater.is_in_sea.return_value = False
    return game


def _give_sof_pool(game: Any, count: int = 2) -> Any:
    """Phase 2c: turn the feature on and stock `count` bought SOF teams in a
    friendly base so the pool gate opens. Returns the SOF GroundUnitType."""
    from game.dcs.groundunittype import GroundUnitType
    from game.missiongenerator.scarluadata import SCAR_SOF_UNIT_BLUE

    game.settings.scar_command_post_intel = True
    unit = GroundUnitType.named(SCAR_SOF_UNIT_BLUE)
    coalition = game.coalitions[0]
    cp = MagicMock()
    cp.captured = coalition.player  # friendly-held -> counted by _sof_asset
    cp.base.armor = {unit: count}
    game.theater.controlpoints = list(game.theater.controlpoints) + [cp]
    return unit


def _plan_sof_insert(game: Any, package_index: int = 0) -> None:
    """Phase 2c-2: frag a SOF insert flight onto an existing SCAR package so the
    team is delivered. Without this, a stocked pool alone yields no drop."""
    package = game.coalitions[0].ato.packages[package_index]
    package.flights = list(package.flights) + [MagicMock(flight_type=FlightType.SOF)]


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
    assert tasking.tasking_id == "blue-scar-1"
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


def test_decoys_are_scattered_not_on_one_ring() -> None:
    # Decoys/clutter must spread across the area at varied ranges, not sit on a
    # single fixed-radius ring (which read as an obviously artificial circle).
    target = MagicMock()
    target.position = Point(1000, 2000, None)  # type: ignore[arg-type]
    tasking = _build(_game_with(_coalition_with_target(target)))[0]

    support = [c for c in tasking.convoys if c.role in ("decoy", "clutter")]
    assert len(support) >= 3
    radii = {round(math.hypot(c.spawn_x - 1000.0, c.spawn_y - 2000.0)) for c in support}
    assert len(radii) > 1  # not all equidistant from the area center


def test_red_tasking_keeps_red_coalition_and_id() -> None:
    target = MagicMock()
    target.position = Point(1000, 2000, None)  # type: ignore[arg-type]
    coalition = _coalition_with_target(target)
    coalition.player = Player.RED
    coalition.opponent.faction.country.id = 2
    coalition.faction.country.id = 1

    tasking = _build(_game_with(coalition))[0]

    assert tasking.coalition == "red"
    assert tasking.tasking_id == "red-scar-1"


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
    # Far enough away (>= SCAR_MIN_FLEE_M) to be a real chase, so it stays the dest.
    city.position = Point(30000, 0, None)  # type: ignore[arg-type]
    game = _game_with(_coalition_with_target(armor))
    game.theater.controlpoints = [city]

    tasking = _build(game)[0]

    assert tasking.variant == "armor"
    assert tasking.target_groups == ("ARMOR-1",)  # binds the REAL group
    assert (tasking.dest_x, tasking.dest_y) == (30000, 0)  # flees to the city
    assert tasking.flee_speed_ms > 0
    # The hunted column gets a command vehicle so the player can ID the HVT; it
    # rides with the real group and flees to the same dest at the flee pace.
    assert tasking.command_type == SCAR_COMMAND
    command = [c for c in tasking.convoys if c.role == "command"]
    assert len(command) == 1
    assert command[0].unit_types == (SCAR_COMMAND,)
    assert (command[0].dest_x, command[0].dest_y) == (30000, 0)
    assert command[0].speed_ms == tasking.flee_speed_ms
    # Decoys/clutter are mixed in (spawned fakes), like the convoy variant.
    roles = [c.role for c in tasking.convoys]
    assert "decoy" in roles
    assert roles.count("clutter") == SCAR_CLUTTER_COUNT
    # Decoys are strict partials of the FULL signature (real armor + command
    # vehicle): some carry a command vehicle too, but none is the full set — so
    # the player must match the whole signature, not just spot the antenna.
    full_sig = ("T-55", "T-55", "Ural-375", SCAR_COMMAND)
    decoys = [c for c in tasking.convoys if c.role == "decoy"]
    assert decoys
    for decoy in decoys:
        assert decoy.unit_types != full_sig
        assert all(u in full_sig for u in decoy.unit_types)
    assert any(SCAR_COMMAND in d.unit_types for d in decoys)


def test_armor_with_immobile_unit_falls_back_to_spawn() -> None:
    # A "real armor group" that includes a towed/immobile unit (a flak gun) can't
    # all flee — binding it strands the immobile unit (2026-06-20 feedback: "flak
    # gun in the target group was not mobile"). Such a target is routed to the
    # fully-mobile spawned picture instead of bound.
    armor = MagicMock(spec=VehicleGroupGroundObject)
    armor.groups = [
        MagicMock(
            units=[
                MagicMock(type=MagicMock(id="BTR-80")),
                MagicMock(type=MagicMock(id="KS-19")),  # towed AAA: cannot drive
            ],
            group_name="ARMOR-IMMOBILE",
        )
    ]
    armor.position = Point(0, 0, None)  # type: ignore[arg-type]
    armor.control_point = MagicMock(captured=True)
    game = _game_with(_coalition_with_target(armor))

    tasking = _build(game)[0]

    assert tasking.variant == "spawn"  # not bound as armor
    assert tasking.target_groups == ()  # the immobile real group is NOT bound
    # The spawned HVT is the fully-mobile canned picture (no KS-19 to strand).
    hvt = next(c for c in tasking.convoys if c.role == "hvt")
    assert "KS-19" not in hvt.unit_types


def test_armor_too_close_city_is_extended_to_min_flee() -> None:
    # When the nearest enemy city is closer than SCAR_MIN_FLEE_M, the bound group
    # would have almost no run (in-game feedback: target + hide point on top of
    # each other). The dest is projected out along the city axis to the minimum so
    # the player always gets a real chase (the spawn variant already runs 15 NM).
    armor = MagicMock(spec=VehicleGroupGroundObject)
    armor.groups = [
        MagicMock(units=[MagicMock(type=MagicMock(id="T-55"))], group_name="A1")
    ]
    armor.position = Point(0, 0, None)  # type: ignore[arg-type]
    armor.control_point = MagicMock(captured=True)
    city = MagicMock()
    city.captured = True
    city.position = Point(5000, 0, None)  # type: ignore[arg-type]  # 5 km << 15 NM
    game = _game_with(_coalition_with_target(armor))
    game.theater.controlpoints = [city]

    tasking = _build(game)[0]

    assert tasking.variant == "armor"
    # Same direction as the city (+x), but extended out to the minimum run.
    assert tasking.dest_y == 0
    assert tasking.dest_x == SCAR_MIN_FLEE_M


def _armor_to_far_city() -> Any:
    armor = MagicMock(spec=VehicleGroupGroundObject)
    armor.groups = [
        MagicMock(units=[MagicMock(type=MagicMock(id="T-55"))], group_name="A1")
    ]
    armor.position = Point(0, 0, None)  # type: ignore[arg-type]
    armor.control_point = MagicMock(captured=True)
    city = MagicMock(captured=True)
    city.position = Point(30000, 0, None)  # type: ignore[arg-type]  # >= min flee
    game = _game_with(_coalition_with_target(armor))
    game.theater.controlpoints = [city]
    return game


def test_no_sof_ambush_when_feature_off() -> None:
    # scar_command_post_intel defaults OFF -> no SOF team is planned at all.
    tasking = _build(_armor_to_far_city())[0]
    assert tasking.sof_radius_m == 0.0


def test_no_sof_ambush_when_pool_empty() -> None:
    # Feature ON but the side owns no SOF teams -> no drop (finite-pool gate).
    game = _armor_to_far_city()
    game.settings.scar_command_post_intel = True  # but no SOF stocked
    _plan_sof_insert(game)
    tasking = _build(game)[0]
    assert tasking.sof_radius_m == 0.0


def test_no_sof_drop_without_a_planned_insert() -> None:
    # Feature ON and a team in stock, but no SOF insert fragged -> no drop. The
    # team is delivered by the player-flown insert, not automatically (Phase 2c-2).
    game = _armor_to_far_city()
    _give_sof_pool(game)
    tasking = _build(game)[0]
    assert tasking.sof_radius_m == 0.0


def test_sof_pool_caps_drops_per_turn() -> None:
    # One SOF team, two SCAR targets -> only the first gets a drop.
    armor = MagicMock(spec=VehicleGroupGroundObject)
    armor.groups = [
        MagicMock(units=[MagicMock(type=MagicMock(id="T-55"))], group_name="A1")
    ]
    armor.position = Point(0, 0, None)  # type: ignore[arg-type]
    armor.control_point = MagicMock(captured=True)
    coalition = _coalition_with_target(armor)
    second = MagicMock()
    second.target = MagicMock(position=Point(60000, 60000, None))  # type: ignore[arg-type]
    second.time_over_target = MISSION_START + timedelta(seconds=TOT_OFFSET_S)
    second.flights = [MagicMock(flight_type=FlightType.SCAR)]
    coalition.ato.packages = [coalition.ato.packages[0], second]
    game = _game_with(coalition)
    _give_sof_pool(game, count=1)
    # Both targets are fragged a SOF insert, so the cap (not the frag gate) is what
    # limits the drops to one.
    _plan_sof_insert(game, package_index=0)
    _plan_sof_insert(game, package_index=1)

    taskings = _build(game)
    with_sof = [t for t in taskings if t.sof_radius_m > 0]
    assert len(taskings) == 2
    assert len(with_sof) == 1  # capped at the single available team


def test_armor_sof_ambush_when_feature_on() -> None:
    game = _armor_to_far_city()
    sof_unit = _give_sof_pool(game)
    _plan_sof_insert(game)

    tasking = _build(game)[0]

    assert tasking.sof_radius_m == SCAR_SOF_CAPTURE_RADIUS_M
    assert tasking.sof_country_id == 2  # the FRIENDLY side (not the enemy, 7)
    # SOF sits SCAR_SOF_LEAD_FRAC of the way from the HVT (origin 0,0) to dest.
    assert tasking.sof_x == tasking.dest_x * SCAR_SOF_LEAD_FRAC
    assert tasking.sof_y == 0.0
    # The bought unit's DCS type is emitted for the Lua to spawn.
    assert tasking.sof_unit_type == sof_unit.dcs_unit_type.id


def test_spawn_sof_ambush_on_the_hvt_route_when_feature_on() -> None:
    target = MagicMock()
    target.position = Point(1000, 2000, None)  # type: ignore[arg-type]
    game = _game_with(_coalition_with_target(target))
    _give_sof_pool(game)
    _plan_sof_insert(game)

    tasking = _build(game)[0]

    assert tasking.variant == "spawn"
    assert tasking.sof_radius_m == SCAR_SOF_CAPTURE_RADIUS_M
    assert tasking.sof_country_id == 2
    # SOF lies on the HVT convoy's spawn->dest line at the lead fraction.
    hvt = next(c for c in tasking.convoys if c.role == "hvt")
    assert (
        tasking.sof_x == hvt.spawn_x + (hvt.dest_x - hvt.spawn_x) * SCAR_SOF_LEAD_FRAC
    )
    assert (
        tasking.sof_y == hvt.spawn_y + (hvt.dest_y - hvt.spawn_y) * SCAR_SOF_LEAD_FRAC
    )


def test_sof_fields_emitted_to_lua_only_when_enabled() -> None:
    target = MagicMock()
    target.position = Point(1000, 2000, None)  # type: ignore[arg-type]

    # Disabled (default): no SOF fields in the serialized table.
    off = LuaData("dcsRetribution")
    populate_scar_lua(off, _build(_game_with(_coalition_with_target(target))))
    assert "sofX" not in off.serialize()

    # Enabled + a SOF team in stock + an insert fragged: SOF point + friendly
    # country + unit type emitted.
    game = _game_with(_coalition_with_target(target))
    _give_sof_pool(game)
    _plan_sof_insert(game)
    on = LuaData("dcsRetribution")
    populate_scar_lua(on, _build(game))
    serialized = on.serialize()
    assert "sofX" in serialized
    assert "sofCountryId" in serialized
    assert "sofUnitType" in serialized


def test_offshore_flee_dest_is_snapped_to_land() -> None:
    # Coastal targets can put the flee dest (or HVT spawn) in the sea, where ground
    # units can't path (in-game finding 2026-06-18). Such points are pulled to land.
    game = _armor_to_far_city()  # dest would be the city at (30000, 0)
    game.theater.is_in_sea.return_value = True
    game.theater.nearest_land_pos.return_value = Point(12345, 678, None)  # type: ignore[arg-type]

    tasking = _build(game)[0]

    assert (tasking.dest_x, tasking.dest_y) == (12345, 678)  # snapped onto land
    # The spawned support columns are snapped too.
    for convoy in tasking.convoys:
        assert (convoy.spawn_x, convoy.spawn_y) == (12345, 678)


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
    assert "blue-scar-1" in serialized
    assert "spawn" in serialized
    assert "hvtCountryId" in serialized
    assert "coalition" in serialized  # briefing addressee emitted
    assert "centerX" in serialized  # search-area center for the F10 mark
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
    assert state.sof_strandings == []
    state = StateData.from_json({}, unit_map)
    assert state.scar_results == {}
    assert state.sof_strandings == []


def test_state_data_parses_sof_strandings() -> None:
    # A failed area whose SOF team survived carries sofStrandedX/Y; that surfaces
    # as a (taskingId, x, y) stranding for the next-turn CSAR objective.
    unit_map = MagicMock()
    state = StateData.from_json(
        {
            "scar_results": {
                "blue-scar-1": {
                    "status": "failed",
                    "sofStrandedX": 1500.0,
                    "sofStrandedY": -250.0,
                },
                "blue-scar-2": {"status": "captured"},
                "blue-scar-3": {"status": "failed"},
            }
        },
        unit_map,
    )
    assert state.sof_strandings == [("blue-scar-1", 1500.0, -250.0)]


def test_lua_capture_requires_a_live_sof_group() -> None:
    script = Path("resources/plugins/scar/scar_414_init.lua").read_text(
        encoding="utf-8"
    )
    capture_check = script.split("local function hvt_in_sof_zone(area)", maxsplit=1)[
        1
    ].split("local function despawn_command(area)", maxsplit=1)[0]
    assert "area.sofGroup == nil" in capture_check
    assert "Group.getByName(area.sofGroup)" in capture_check
    assert "sof_group:getSize()" in capture_check


def test_lua_spawn_sof_prefers_a_delivered_team_then_falls_back() -> None:
    # Phase 2c-2 hybrid: spawn_sof binds capture to a player-delivered team near
    # the ambush point when one exists, and only scripted-spawns a fallback
    # otherwise. The detection skips our own SCAR- spawns.
    script = Path("resources/plugins/scar/scar_414_init.lua").read_text(
        encoding="utf-8"
    )
    spawn_sof = script.split("local function spawn_sof(area)", maxsplit=1)[1].split(
        "local function hvt_in_fail_zone(area)", maxsplit=1
    )[0]
    # Prefers the delivered team and returns before the scripted spawn.
    assert "find_delivered_sof(area)" in spawn_sof
    assert "area.sofGroup = delivered" in spawn_sof
    # The detector scans friendly ground groups and excludes our own spawns.
    detector = script.split("local function find_delivered_sof(area)", maxsplit=1)[
        1
    ].split("local function spawn_sof(area)", maxsplit=1)[0]
    assert "coalition.getGroups" in detector
    assert 'string.sub(gname, 1, 5) ~= "SCAR-"' in detector


def test_lua_botched_capture_reports_a_stranded_team() -> None:
    # Phase 2c-3: a failed area whose SOF team is still alive tags its position so
    # the generator can stand up a next-turn CSAR objective.
    script = Path("resources/plugins/scar/scar_414_init.lua").read_text(
        encoding="utf-8"
    )
    report = script.split("local function report_stranded_sof(area)", maxsplit=1)[
        1
    ].split("local function scar_check()", maxsplit=1)[0]
    assert "entry.sofStrandedX = pos.x" in report
    assert "entry.sofStrandedY = pos.z" in report
    # The failed branches call it (only a surviving team tags a position).
    assert script.count("report_stranded_sof(area)") >= 3


def test_lua_movement_is_proximity_gated() -> None:
    # A-10 feedback 2026-06-20: the target should start moving when the package
    # reaches the area (proximity), not at mission start — so a slow push doesn't
    # hunt a target that's already gone. The picture still SPAWNS at mission start
    # (the puzzle is present); only the movement + fail clock are gated.
    script = Path("resources/plugins/scar/scar_414_init.lua").read_text(
        encoding="utf-8"
    )
    assert "SCAR_PROXIMITY_M" in script
    assert "local function package_near(area)" in script
    assert "coalition.getGroups" in script
    # Activation routes the parked movers and opens the fail clock from then.
    activate = script.split("local function activate_movement(area)", maxsplit=1)[
        1
    ].split("local function scar_check(", maxsplit=1)[0]
    assert "area.movers" in activate
    assert "area.activated = true" in activate
    assert "area.deadline = timer.getTime()" in activate
    # Convoys spawn PARKED (single waypoint at speed 0), to be routed on activation.
    spawn = script.split("local function spawn_convoy", maxsplit=1)[1].split(
        "local function find_delivered_sof", maxsplit=1
    )[0]
    assert '["speed"] = 0,' in spawn
