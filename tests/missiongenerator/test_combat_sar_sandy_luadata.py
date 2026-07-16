"""Sandy (FlightType.SCAR) group names feed into dcsRetribution.CombatSAR.sandys.

Sandy previously wasn't part of the CombatSAR data table at all -- the runtime had
no way to know which groups were the rescue-escort flights, so it could never
dynamically retask one toward a live ejection (see 414th-features.md §15 gotcha
and docs/dev/design/414th-scar-rescue-rework-notes.md). This locks the bucketing
(a SCAR flight lands in the sandys bucket, never in the rescue/king buckets), the
emission (the node carries a "sandys" list of group names), and the blue-only rule
(red flights are ignored; no red node is ever emitted -- squadron call 2026-07-01).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.ato.flighttype import FlightType
from game.missiongenerator.luagenerator import LuaData, LuaItem, LuaValue, LuaGenerator
from game.missiongenerator.missiondata import CombatSarTemplates


def _string_list(item: LuaItem | None) -> list[str]:
    assert item is not None
    value = item.value
    assert isinstance(value, LuaValue)
    assert isinstance(value.value, list)
    return value.value


def _key_values(item: LuaItem) -> list[LuaValue]:
    value = item.value
    assert isinstance(value, list)
    return value


def _scalar(item: LuaItem | None) -> Any:
    assert item is not None
    value = item.value
    assert isinstance(value, LuaValue)
    return value.value


def _templates(
    *,
    parked: list[str] | None = None,
    helo_group: str | None = "CombatSAR On-Demand Rescue",
) -> CombatSarTemplates:
    return CombatSarTemplates(
        delivery_field="Balad",
        parked_helos=parked or [],
        helo_group=helo_group,
    )


def _fd(
    group_name: str, flight_type: FlightType, *, is_blue: bool, helo: bool = False
) -> Any:
    return SimpleNamespace(
        group_name=group_name,
        flight_type=flight_type,
        friendly=SimpleNamespace(is_blue=is_blue),
        aircraft_type=SimpleNamespace(helicopter=helo),
        combat_sar_king=None,
        departure=SimpleNamespace(airfield_name="Kutaisi"),
    )


def _coalition(country_id: int) -> Any:
    return SimpleNamespace(
        opponent=SimpleNamespace(
            faction=SimpleNamespace(country=SimpleNamespace(id=country_id))
        ),
        pending_csars=[],
    )


def _generator(
    flights: list[Any],
    *,
    auto_combat_sar: bool = False,
    combat_sar_templates: Any = None,
    force_capture: bool = False,
    easy_rescue: bool = False,
) -> LuaGenerator:
    gen = LuaGenerator.__new__(LuaGenerator)
    gen.mission_data = SimpleNamespace(  # type: ignore[assignment]
        flights=flights, combat_sar_templates=combat_sar_templates
    )
    gen.game = SimpleNamespace(  # type: ignore[assignment]
        settings=SimpleNamespace(
            auto_combat_sar=auto_combat_sar,
            scar_command_post_intel=False,
            combat_sar_test_force_capture=force_capture,
            combat_sar_test_easy_rescue=easy_rescue,
        ),
        blue=_coalition(49),
        red=_coalition(2),
    )
    # Bypass pilot-template generation (needs a real Mission/theater) -- it's
    # separate, pre-existing logic unrelated to this Sandy-bucketing change.
    gen._generate_combat_sar_pilot_template = lambda coalition: "Combat SAR Downed Pilot"  # type: ignore[method-assign]
    return gen


def test_sandy_flight_lands_in_the_sandys_list_not_rescue_or_kings() -> None:
    flights = [
        _fd("Jolly-1", FlightType.COMBAT_SAR, is_blue=True, helo=True),
        _fd("King-1", FlightType.COMBAT_SAR, is_blue=True, helo=False),
        _fd("Sandy-1", FlightType.SCAR, is_blue=True),
        _fd("Sandy-2", FlightType.SCAR, is_blue=True),
    ]
    gen = _generator(flights)
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    combat_sar = lua_data.get_item("CombatSAR")
    assert combat_sar is not None
    assert _string_list(combat_sar.get_item("sandys")) == ["Sandy-1", "Sandy-2"]
    # Sandy never leaks into the rescueHelos or kings lists.
    assert _string_list(combat_sar.get_item("rescueHelos")) == ["Jolly-1"]
    kings_item = combat_sar.get_item("kings")
    assert isinstance(kings_item, LuaData)
    kings_objects = kings_item.objects
    assert len(kings_objects) == 1
    assert any(
        v.key == "group" and v.value == "King-1" for v in _key_values(kings_objects[0])
    )


def test_no_sandy_flights_emits_an_empty_list() -> None:
    flights = [_fd("Jolly-1", FlightType.COMBAT_SAR, is_blue=True, helo=True)]
    gen = _generator(flights)
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    combat_sar = lua_data.get_item("CombatSAR")
    assert combat_sar is not None
    assert _string_list(combat_sar.get_item("sandys")) == []


def test_red_flights_are_ignored_and_no_red_node_is_emitted() -> None:
    # Squadron call 2026-07-01: red flies no CSAR. Even if red COMBAT_SAR/SCAR
    # flights exist (an old save), the emitter ignores them -- no red node means
    # the plugin registers no red survivors and spawns no BLUE snatch party.
    flights = [
        _fd("RedJolly-1", FlightType.COMBAT_SAR, is_blue=False, helo=True),
        _fd("RedSandy-1", FlightType.SCAR, is_blue=False),
        _fd("BlueJolly-1", FlightType.COMBAT_SAR, is_blue=True, helo=True),
    ]
    gen = _generator(flights)
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    combat_sar = lua_data.get_item("CombatSAR")
    assert combat_sar is not None
    assert _string_list(combat_sar.get_item("rescueHelos")) == ["BlueJolly-1"]
    assert _string_list(combat_sar.get_item("sandys")) == []
    assert combat_sar.get_item("red") is None


def test_red_only_flights_still_emit_the_blue_node() -> None:
    # Red flights are ignored, but the BLUE node is emitted regardless (2026-07-10:
    # the ledger runs off the downed pilot, not off a rescue asset) -- with empty
    # buckets and no autoSpawn, so the plugin runs the capture race only.
    flights = [_fd("RedJolly-1", FlightType.COMBAT_SAR, is_blue=False, helo=True)]
    gen = _generator(flights)
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    node = lua_data.get_item("CombatSAR")
    assert node is not None
    assert _string_list(node.get_item("rescueHelos")) == []
    assert _scalar(node.get_item("autoSpawn")) == "false"
    assert node.get_item("red") is None


def test_autospawn_arms_the_cold_template_with_no_player_package() -> None:
    # Scenario C, bare ramp: no player CSAR package, auto_combat_sar on, no parked
    # helo, a cold clone template exists -> the runtime clones it on demand.
    gen = _generator([], auto_combat_sar=True, combat_sar_templates=_templates())
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    node = lua_data.get_item("CombatSAR")
    assert node is not None
    assert _scalar(node.get_item("autoSpawn")) == "true"
    assert _scalar(node.get_item("heloTemplate")) == "CombatSAR On-Demand Rescue"
    assert _scalar(node.get_item("farp")) == "Balad"
    assert node.get_item("parkedHelos") is None  # no parked helos this mission
    assert _string_list(node.get_item("rescueHelos")) == []  # no player helos


def test_autospawn_prefers_parked_ramp_helos_and_keeps_the_template_fallback() -> None:
    # Scenario C, populated ramp: real parked helos (tracked) are emitted preferred,
    # and the cold template rides along as the fallback when they're exhausted.
    gen = _generator(
        [],
        auto_combat_sar=True,
        combat_sar_templates=_templates(parked=["Balad Helo 1", "Balad Helo 2"]),
    )
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    node = lua_data.get_item("CombatSAR")
    assert node is not None
    assert _scalar(node.get_item("autoSpawn")) == "true"
    assert _string_list(node.get_item("parkedHelos")) == [
        "Balad Helo 1",
        "Balad Helo 2",
    ]
    assert _scalar(node.get_item("heloTemplate")) == "CombatSAR On-Demand Rescue"


def test_autospawn_with_parked_helos_and_no_template() -> None:
    # The clone template can be absent (no parking was free) while parked ramp helos
    # still provide the rescue -> parkedHelos emitted, no heloTemplate.
    gen = _generator(
        [],
        auto_combat_sar=True,
        combat_sar_templates=_templates(parked=["Balad Helo 1"], helo_group=None),
    )
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    node = lua_data.get_item("CombatSAR")
    assert node is not None
    assert _string_list(node.get_item("parkedHelos")) == ["Balad Helo 1"]
    assert node.get_item("heloTemplate") is None


def test_player_package_suppresses_autospawn_and_arms_no_clone() -> None:
    # The player fragged a RESCUE HELO -> no AI clone is armed, and the
    # ledger runs off the player's own helo.
    flights = [_fd("Jolly-1", FlightType.COMBAT_SAR, is_blue=True, helo=True)]
    gen = _generator(flights, auto_combat_sar=True, combat_sar_templates=_templates())
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    node = lua_data.get_item("CombatSAR")
    assert node is not None
    assert _scalar(node.get_item("autoSpawn")) == "false"
    assert node.get_item("heloTemplate") is None  # no on-demand clone with a package
    assert _string_list(node.get_item("rescueHelos")) == ["Jolly-1"]


def test_bare_sandy_does_not_suppress_autospawn() -> None:
    # Squadron call 2026-07-15 (from the flown Red Tide M1, where one player Sandy
    # escort with no helo behind it silently disabled ALL rescue): only a
    # rescue-CAPABLE flight suppresses the AI spawn. A bare SCAR Sandy can't pick
    # anyone up -> the AI helo still arms, and the Sandy escorts it.
    flights = [_fd("Sandy-1", FlightType.SCAR, is_blue=True, helo=False)]
    gen = _generator(flights, auto_combat_sar=True, combat_sar_templates=_templates())
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    node = lua_data.get_item("CombatSAR")
    assert node is not None
    assert _scalar(node.get_item("autoSpawn")) == "true"
    assert _scalar(node.get_item("heloTemplate")) == "CombatSAR On-Demand Rescue"
    assert _string_list(node.get_item("sandys")) == ["Sandy-1"]
    assert _string_list(node.get_item("rescueHelos")) == []


def test_bare_king_does_not_suppress_autospawn() -> None:
    # Same call for a King-only plan: the C-130 tracks the survivor but can't land
    # for him -> the AI helo still arms alongside it.
    flights = [_fd("King-1", FlightType.COMBAT_SAR, is_blue=True, helo=False)]
    gen = _generator(flights, auto_combat_sar=True, combat_sar_templates=_templates())
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    node = lua_data.get_item("CombatSAR")
    assert node is not None
    assert _scalar(node.get_item("autoSpawn")) == "true"
    assert _scalar(node.get_item("heloTemplate")) == "CombatSAR On-Demand Rescue"
    kings_item = node.get_item("kings")
    assert isinstance(kings_item, LuaData)
    assert len(kings_item.objects) == 1
    assert any(
        v.key == "group" and v.value == "King-1"
        for v in _key_values(kings_item.objects[0])
    )
    assert _string_list(node.get_item("rescueHelos")) == []


def test_node_emitted_even_with_auto_off_and_no_player_package() -> None:
    # 2026-07-10 squadron call: no rescue capability does NOT skip the node -- the
    # snatch race must still run (a pilot nobody can come for is MORE capturable).
    # The flown 2026-07-10 test caught exactly this: auto-CSAR off + a Sandy-only
    # package -> no snatch AI, no capture, the comms-jam gate never armed.
    gen = _generator([], auto_combat_sar=False, combat_sar_templates=_templates())
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    node = lua_data.get_item("CombatSAR")
    assert node is not None
    assert _scalar(node.get_item("autoSpawn")) == "false"
    assert node.get_item("heloTemplate") is None  # auto off -> no clone armed
    assert _string_list(node.get_item("rescueHelos")) == []


def test_node_emitted_when_auto_on_but_no_template_and_no_player_package() -> None:
    # auto_combat_sar on but the coalition owns no CSAR-capable helo (no template)
    # and nothing was fragged -> no auto-spawn, but the ledger/capture race still runs.
    gen = _generator([], auto_combat_sar=True, combat_sar_templates=None)
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    node = lua_data.get_item("CombatSAR")
    assert node is not None
    assert _scalar(node.get_item("autoSpawn")) == "false"
    assert node.get_item("heloTemplate") is None


def test_test_flags_absent_by_default() -> None:
    # Both thumb-on-the-scale toggles OFF -> the node carries neither flag, so normal
    # play is unchanged (the plugin's own defaults/options drive the capture race).
    flights = [_fd("Jolly-1", FlightType.COMBAT_SAR, is_blue=True, helo=True)]
    gen = _generator(flights)
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    node = lua_data.get_item("CombatSAR")
    assert node is not None
    assert node.get_item("testForceCapture") is None
    assert node.get_item("testEasyRescue") is None


def test_force_capture_flag_emitted_when_on() -> None:
    flights = [_fd("Jolly-1", FlightType.COMBAT_SAR, is_blue=True, helo=True)]
    gen = _generator(flights, force_capture=True)
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    node = lua_data.get_item("CombatSAR")
    assert node is not None
    assert _scalar(node.get_item("testForceCapture")) == "true"
    assert node.get_item("testEasyRescue") is None


def test_easy_rescue_flag_emitted_when_on() -> None:
    flights = [_fd("Jolly-1", FlightType.COMBAT_SAR, is_blue=True, helo=True)]
    gen = _generator(flights, easy_rescue=True)
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    node = lua_data.get_item("CombatSAR")
    assert node is not None
    assert _scalar(node.get_item("testEasyRescue")) == "true"
    assert node.get_item("testForceCapture") is None


def test_persistent_survivors_emitted_from_the_downed_pilot_ledger() -> None:
    # Persistent evaders (2026-07-10): game.downed_pilots entries reach the node as
    # persistentSurvivors {name, x, y} so the plugin re-spawns them at mission start.
    from game.fourteenth.downed_pilots import DownedPilot

    gen = _generator([])
    gen.game.downed_pilots = [
        DownedPilot(unit_name="Enfield 1-1 | F-14B", x=1000.0, y=-2000.0),
    ]
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    node = lua_data.get_item("CombatSAR")
    assert node is not None
    evaders = node.get_item("persistentSurvivors")
    assert isinstance(evaders, LuaData)
    assert len(evaders.objects) == 1
    values = {v.key: v.value for v in _key_values(evaders.objects[0])}
    assert values == {"name": "Enfield 1-1 | F-14B", "x": "1000.0", "y": "-2000.0"}


def test_no_persistent_survivors_item_with_an_empty_ledger() -> None:
    gen = _generator([])  # fake game has no downed_pilots attr at all (old save)
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    node = lua_data.get_item("CombatSAR")
    assert node is not None
    assert node.get_item("persistentSurvivors") is None


def _faction_with_infantry(ids: list[str]) -> Any:
    units = [SimpleNamespace(dcs_unit_type=SimpleNamespace(id=ident)) for ident in ids]
    return SimpleNamespace(infantry_with_class=lambda unit_class: iter(units))


def test_survivor_template_skips_crew_served_weapons() -> None:
    # The INFANTRY unit class also carries mortars/tripod guns; on OIR the first
    # pick was the 2B11, so every downed pilot rendered as a mortar tube (2026-07-06
    # flown-session Tacview). The survivor must be a unit that reads as a person.
    faction = _faction_with_infantry(["2B11 mortar", "Soldier M249"])
    assert LuaGenerator.survivor_unit_type(faction).id == "Soldier M249"


def test_survivor_template_falls_back_to_the_vanilla_soldier() -> None:
    from dcs.vehicles import Infantry

    faction = _faction_with_infantry(["2B11 mortar"])  # no human-shaped infantry
    assert LuaGenerator.survivor_unit_type(faction) is Infantry.Soldier_M4
