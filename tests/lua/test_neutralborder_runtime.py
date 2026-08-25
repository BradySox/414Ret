"""Headless runtime checks for the neutralborder plugin (§96).

Pins the "script errors and the feature silently never starts" invariant plus
the behaviour contract of the border watch: a group inside the polygon below the
floor is warned and shadowed (the shadow spawning on the intruder's OPPOSING
coalition at return-fire); a player who stays past the engage dwell, or who
releases a weapon inside the border after the warning, is engaged via a hard
AttackGroup task on the raw controller and the SAM template wakes; AI intruders
are shadowed but never engaged; a high transit trips nothing; leaving before
escalation stands the shadow down. The DCS AI's actual shadow/attack flying is
in-game-only (checklist B100/B101).
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/neutralborder/neutralborder-config.lua"

RED_COUNTRY = 34
BLUE_COUNTRY = 2

# A 20 km square with the neutral field at its center. Vertices are terrain XY
# strings, the emitter contract (the plugin tonumber()s everything).
SQUARE = [
    {"x": "0", "y": "0"},
    {"x": "20000", "y": "0"},
    {"x": "20000", "y": "20000"},
    {"x": "0", "y": "20000"},
]


def _config(sam: bool = True, floor_ft: str = "10000") -> dict[str, Any]:
    zone: dict[str, Any] = {
        "country": "Lebanon",
        "field": "Rayak",
        "floorFt": floor_ft,
        "fighterTemplate": "NeutralBorder|Lebanon|MiG-29A",
        "redCountryId": str(RED_COUNTRY),
        "blueCountryId": str(BLUE_COUNTRY),
        "border": SQUARE,
    }
    if sam:
        zone["samTemplate"] = "NeutralBorder|Lebanon|SAM"
    return {
        "plugins": {
            "neutralborder": {
                "warnDwellS": 30,
                "engageDwellS": 180,
                "scanIntervalS": 10,
                "vectorIntervalS": 45,
                "maxShadows": 2,
                "drawBorders": False,
            }
        },
        "neutralBorder": {"zones": [zone]},
    }


def _intruder(
    name: str,
    gid: int,
    side: int,
    player: str | None = "Brady",
    x: float = 5000,
    z: float = 5000,
    alt: float = 2000,
) -> dict[str, Any]:
    return {
        "name": name,
        "id": gid,
        "side": side,
        "category": 0,  # AIRPLANE
        "units": [
            {
                "name": name + "-1",
                "type": "FA-18C_hornet",
                "x": x,
                "z": z,
                "alt": alt,
                "airborne": True,
                "playerName": player,
            }
        ],
    }


def _setup(cfg: dict[str, Any]) -> DcsPluginHarness:
    h = DcsPluginHarness()
    h.add_airbase({"name": "Rayak", "x": 10000, "z": 10000, "elev": 900, "side": 0})
    h.lua.globals().dcsRetribution = h.to_lua(cfg)
    return h


def _shadow_spawns(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [r for r in h.records("spawns") if r.get("base") == "Rayak"]


def _sam_spawns(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [r for r in h.records("spawns") if r.get("base") == "template"]


def _attack_tasks(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [
        r
        for r in h.records("controllerTasks")
        if isinstance(r, dict) and r.get("taskId") == "AttackGroup"
    ]


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.set_retribution_config(plugin_options={"neutralborder": {"warnDwellS": 30}})
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert h.records("spawns") == []
    h.assert_no_lua_errors()


def test_blue_player_is_warned_and_shadowed_by_a_red_clone() -> None:
    h = _setup(_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)

    spawns = _shadow_spawns(h)
    assert len(spawns) == 1
    assert spawns[0]["coalitionId"] == 1  # opposing a BLUE intruder = RED
    assert spawns[0]["countryId"] == RED_COUNTRY
    assert spawns[0]["takeoff"] == 1  # air spawn, the QRA profile

    texts = [r for r in h.records("texts") if isinstance(r, dict)]
    assert any("violating" in str(r.get("text", "")) for r in texts)

    roe = [r for r in h.records("roe") if isinstance(r, dict)]
    assert any(r.get("option") == "ReturnFire" for r in roe)
    # Not escalated yet: no weapons free, no attack task, no SAM.
    assert not any(r.get("option") == "WeaponFree" for r in roe)
    assert _attack_tasks(h) == []
    assert _sam_spawns(h) == []
    h.assert_no_lua_errors()


def test_red_intruder_gets_a_blue_clone() -> None:
    h = _setup(_config())
    h.add_group(_intruder("Bandit 1", 50, side=1, player=None))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)

    spawns = _shadow_spawns(h)
    assert len(spawns) == 1
    assert spawns[0]["coalitionId"] == 2  # opposing a RED intruder = BLUE
    assert spawns[0]["countryId"] == BLUE_COUNTRY
    h.assert_no_lua_errors()


def test_player_dwell_escalates_attack_task_and_sam() -> None:
    h = _setup(_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(200)

    roe = [r for r in h.records("roe") if isinstance(r, dict)]
    assert any(r.get("option") == "WeaponFree" for r in roe)
    attacks = _attack_tasks(h)
    assert attacks and attacks[0]["targetGroupId"] == 42
    sam = _sam_spawns(h)
    assert len(sam) == 1
    assert sam[0]["coalitionId"] == 1  # the SAM opposes the blue escalator
    h.assert_no_lua_errors()


def test_ai_intruder_is_shadowed_but_never_engaged() -> None:
    h = _setup(_config())
    h.add_group(_intruder("Strike 9-1", 60, side=2, player=None))
    h.load_plugin_script(PLUGIN)
    h.advance_to(400)

    assert len(_shadow_spawns(h)) == 1
    roe = [r for r in h.records("roe") if isinstance(r, dict)]
    assert not any(r.get("option") == "WeaponFree" for r in roe)
    assert _attack_tasks(h) == []
    assert _sam_spawns(h) == []
    h.assert_no_lua_errors()


def test_high_transit_above_the_floor_trips_nothing() -> None:
    h = _setup(_config())
    # 10,000 ft floor = 3048 m; the transit crosses at 5000 m.
    h.add_group(_intruder("Heavy 7-1", 70, side=2, alt=5000))
    h.load_plugin_script(PLUGIN)
    h.advance_to(400)

    assert h.records("spawns") == []
    h.assert_no_lua_errors()


def test_weapon_release_inside_escalates_after_warning() -> None:
    h = _setup(_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)  # warned + shadowed, not yet engaged
    assert _attack_tasks(h) == []

    h.fire_shot(
        {
            "weapon": {
                "typeName": "AGM-65D",
                "x": 5000,
                "z": 5000,
                "alt": 2000,
                "velocity": 300,
                "vanishAt": 999,
            },
            "initiator": "Viper 1-1",
        }
    )
    h.advance_to(60)

    attacks = _attack_tasks(h)
    assert attacks and attacks[0]["targetGroupId"] == 42
    assert len(_sam_spawns(h)) == 1
    h.assert_no_lua_errors()


def test_leaving_before_escalation_stands_the_shadow_down() -> None:
    h = _setup(_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)
    assert len(_shadow_spawns(h)) == 1

    # Exit the polygon well above the grace period and watch the RTB + despawn.
    h.update_unit("Viper 1-1", {"x": 90000, "z": 90000})
    h.advance_to(45 + 130 + 10)  # exit grace (120 s) + a scan

    routes = [r for r in h.records("routes") if isinstance(r, dict)]
    assert routes, "stood-down shadow was never routed home"
    h.advance_to(45 + 130 + 10 + 310)  # the despawn timer
    destroys = h.records("destroys")
    assert destroys, "stood-down shadow was never despawned"
    # Never escalated on the way out.
    assert _attack_tasks(h) == []
    h.assert_no_lua_errors()
