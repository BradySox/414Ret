"""Headless runtime checks for the redscramble plugin (redscramble-config.lua).

Pins the "script errors and the feature silently never starts" invariant plus the
behaviour contract of the host F10 bandit spawner (§61): the menu is built only for
the configured host player names (per-group, on slot-in or the periodic sweep) or
coalition-wide when none are configured; a menu press clones the picked template at
the picked base (air spawn, QRA profile: field elevation + AGL, scramble speed),
sets it weapons free, announces to the presser, and the GCI loop then vectors the
bandits onto the nearest airborne BLUE player via a hard AttackGroup task; a
mission with no redScramble node is a clean no-op. The DCS AI's actual behaviour
on the AttackGroup task is in-game-only (checklist B14).
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/redscramble/redscramble-config.lua"


def _config(
    host_players: str = "",
    takeoff: str = "air",
    bases: list[dict[str, Any]] | None = None,
    templates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "plugins": {
            "redscramble": {
                "hostPlayers": host_players,
                "takeoff": takeoff,
                "vectorIntervalS": 45,
            }
        },
        "redScramble": {
            "templates": templates
            or [{"group": "RedScramble|MiG-29S", "label": "MiG-29S"}],
            "bases": bases or [{"name": "Wittstock"}],
        },
    }


def _blue_player_group(
    name: str, gid: int, player: str | None = "Brady", airborne: bool = True
) -> dict[str, Any]:
    return {
        "name": name,
        "id": gid,
        "side": 2,  # BLUE
        "category": 0,  # AIRPLANE
        "units": [
            {
                "name": name + "-1",
                "type": "FA-18C_hornet",
                "x": 0,
                "z": 0,
                "alt": 6000,
                "airborne": airborne,
                "playerName": player,
            }
        ],
    }


def _menu_records(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [r for r in h.records("menus") if isinstance(r, dict)]


def _command(h: DcsPluginHarness, path: str, gid: int | None = None) -> Any:
    for record in _menu_records(h):
        if record.get("path") == path and (gid is None or record.get("gid") == gid):
            return record["fn"]
    raise AssertionError(f"menu command {path!r} (gid={gid}) not found")


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.set_retribution_config(plugin_options={"redscramble": {"hostPlayers": "Brady"}})
    h.load_plugin_script(PLUGIN)
    h.advance_to(120)
    assert _menu_records(h) == []
    h.assert_no_lua_errors()


def test_host_name_gates_the_menu_to_that_players_group() -> None:
    h = DcsPluginHarness()
    h.add_airbase({"name": "Wittstock", "x": 10000, "z": 5000, "side": 1})
    h.add_group(_blue_player_group("Viper 1-1", 42, player="Brady"))
    h.add_group(_blue_player_group("Hawg 2-1", 43, player="SomeoneElse"))
    h.lua.globals().dcsRetribution = h.to_lua(_config(host_players="Brady"))
    h.load_plugin_script(PLUGIN)

    # Nothing is coalition-wide when host names are configured.
    assert not any("side" in r for r in _menu_records(h))

    h.fire_birth("Viper 1-1")
    h.fire_birth("Hawg 2-1")

    gids = {r.get("gid") for r in _menu_records(h)}
    assert gids == {42}
    roots = [r for r in _menu_records(h) if r["path"] == "HOST: Red Scramble"]
    assert len(roots) == 1 and roots[0]["gid"] == 42
    h.assert_no_lua_errors()


def test_fragment_matches_the_changing_prefix_name_convention() -> None:
    # The 414th convention: "<flight> 1-x | Flash" -- the prefix changes every
    # event, the tag is static. hostPlayers is a plain substring match, so
    # configuring the tag alone gates the menu whatever the prefix (and the
    # pattern-magic "|"/"-" in the name must not break the match).
    h = DcsPluginHarness()
    h.add_airbase({"name": "Wittstock", "x": 10000, "z": 5000, "side": 1})
    h.add_group(_blue_player_group("Viper 1-1", 42, player="Viper 1-1 | Flash"))
    h.add_group(_blue_player_group("Hawg 2-1", 43, player="Hawg 2-1 | Dagger"))
    h.lua.globals().dcsRetribution = h.to_lua(_config(host_players="Flash"))
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Viper 1-1")
    h.fire_birth("Hawg 2-1")

    assert {r.get("gid") for r in _menu_records(h)} == {42}
    h.assert_no_lua_errors()


def test_the_sweep_catches_a_host_seated_before_load() -> None:
    h = DcsPluginHarness()
    h.add_airbase({"name": "Wittstock", "x": 10000, "z": 5000, "side": 1})
    h.add_group(_blue_player_group("Viper 1-1", 42, player="brady"))  # case-insensitive
    h.lua.globals().dcsRetribution = h.to_lua(_config(host_players=" Brady , Wing2 "))
    h.load_plugin_script(PLUGIN)

    assert _menu_records(h) == []  # no birth fired; menu waits for the sweep
    h.advance_to(35)
    assert {r.get("gid") for r in _menu_records(h)} == {42}
    h.assert_no_lua_errors()


def test_empty_host_names_builds_the_coalition_menu() -> None:
    h = DcsPluginHarness()
    h.add_airbase({"name": "Wittstock", "x": 10000, "z": 5000, "side": 1})
    h.lua.globals().dcsRetribution = h.to_lua(_config(host_players=""))
    h.load_plugin_script(PLUGIN)

    records = _menu_records(h)
    assert any(
        r.get("side") == 2 and r["path"] == "HOST: Red Scramble" for r in records
    )
    h.assert_no_lua_errors()


def test_scramble_spawns_at_the_base_and_vectors_onto_the_player() -> None:
    h = DcsPluginHarness()
    h.add_airbase({"name": "Wittstock", "x": 10000, "z": 5000, "side": 1})
    h.add_group(_blue_player_group("Viper 1-1", 42, player="Brady"))
    h.lua.globals().dcsRetribution = h.to_lua(_config(host_players="Brady"))
    h.load_plugin_script(PLUGIN)
    h.fire_birth("Viper 1-1")

    _command(h, "MiG-29S x2", gid=42)()

    spawns = h.records("spawns")
    assert len(spawns) == 1
    spawn = spawns[0]
    assert spawn["template"] == "RedScramble|MiG-29S"
    assert spawn["base"] == "Wittstock"
    assert spawn["takeoff"] == 1  # SPAWN.Takeoff.Air
    assert spawn["grouping"] == 2
    assert spawn["altitude"] == 760  # terrain 0 + the QRA scramble AGL
    assert spawn["speedKt"] == 300

    # Weapons free at spawn, and the host got their feedback card.
    assert any(r["option"] == "WeaponFree" for r in h.records("roe"))
    announcements = [t for t in h.records("texts") if t.get("groupId") == 42]
    assert any("RED SCRAMBLE" in t["text"] for t in announcements)

    # The GCI loop hard-tasks the bandits onto the airborne player's group.
    h.advance_to(10)
    tasks = h.records("controllerTasks")
    assert len(tasks) == 1
    assert tasks[0]["taskId"] == "AttackGroup"
    assert tasks[0]["targetGroupId"] == 42
    assert tasks[0]["group"].startswith("HOSTILE SCRAMBLE MiG-29S#")

    # Same target next cycle -> no re-task (the attack geometry is not reset).
    h.advance_to(60)
    assert len(h.records("controllerTasks")) == 1
    h.assert_no_lua_errors()


def test_four_ship_command_and_repeat_presses_get_unique_clones() -> None:
    h = DcsPluginHarness()
    h.add_airbase({"name": "Wittstock", "x": 10000, "z": 5000, "side": 1})
    h.add_group(_blue_player_group("Viper 1-1", 42, player="Brady"))
    h.lua.globals().dcsRetribution = h.to_lua(_config(host_players="Brady"))
    h.load_plugin_script(PLUGIN)
    h.fire_birth("Viper 1-1")

    _command(h, "MiG-29S x4", gid=42)()
    _command(h, "MiG-29S x4", gid=42)()

    spawns = h.records("spawns")
    assert [s["grouping"] for s in spawns] == [4, 4]
    names = {t["group"] for t in h.records("roe")}
    assert len(names) == 2  # two distinct clone groups
    h.assert_no_lua_errors()


def test_emergency_command_picks_the_base_nearest_the_airborne_player() -> None:
    h = DcsPluginHarness()
    # Player airborne at (0, 0); Rechlin is closer than Wittstock.
    h.add_airbase({"name": "Wittstock", "x": 200000, "z": 200000, "side": 1})
    h.add_airbase({"name": "Rechlin", "x": 30000, "z": 10000, "side": 1})
    h.add_group(_blue_player_group("Viper 1-1", 42, player="Brady"))
    h.lua.globals().dcsRetribution = h.to_lua(
        _config(
            host_players="Brady",
            bases=[{"name": "Wittstock"}, {"name": "Rechlin"}],
        )
    )
    h.load_plugin_script(PLUGIN)
    h.fire_birth("Viper 1-1")

    _command(h, "EMERGENCY: bandits toward the flight", gid=42)()

    spawns = h.records("spawns")
    assert len(spawns) == 1
    assert spawns[0]["base"] == "Rechlin"
    assert spawns[0]["grouping"] == 2
    h.assert_no_lua_errors()


def test_menu_caps_the_base_list_at_nine() -> None:
    h = DcsPluginHarness()
    bases = [{"name": f"Base{i:02d}"} for i in range(1, 13)]
    for base in bases:
        h.add_airbase({"name": base["name"], "x": 0, "z": 0, "side": 1})
    h.lua.globals().dcsRetribution = h.to_lua(_config(host_players="", bases=bases))
    h.load_plugin_script(PLUGIN)

    paths = {r["path"] for r in _menu_records(h)}
    assert "Base09" in paths
    assert "Base10" not in paths and "Base12" not in paths
    h.assert_no_lua_errors()
