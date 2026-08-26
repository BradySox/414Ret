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
        # Refuses both sides: this fixture is the interception case.
        "overflightBlue": "false",
        "overflightRed": "false",
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
    """Only a floored (contested) zone grants a safe altitude."""
    cfg = _config()
    cfg["neutralBorder"]["zones"][0]["floorBlueFt"] = "10000"
    cfg["neutralBorder"]["zones"][0]["floorRedFt"] = "10000"
    h = _setup(cfg)
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


def _point_config() -> dict[str, Any]:
    """A zone whose neutral has no airfield on the map (the Afghanistan case)."""
    cfg = _config()
    zone = cfg["neutralBorder"]["zones"][0]
    del zone["field"]
    zone["spawnX"] = "12000"
    zone["spawnZ"] = "12000"
    zone["spawnAltM"] = "6096"
    zone["originLabel"] = "Pakistan border CAP"
    return cfg


def test_point_spawned_cap_launches_without_an_airfield() -> None:
    # No airbase is registered at all: the whole point is that this neutral has
    # none anywhere on the map.
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(_point_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)

    spawns = [r for r in h.records("spawns") if r.get("base") == "point"]
    assert len(spawns) == 1
    assert spawns[0]["x"] == 12000
    assert spawns[0]["z"] == 12000
    assert spawns[0]["altitude"] == 6096  # MOOSE takes altitude as the Vec3 y
    assert spawns[0]["coalitionId"] == 1  # still opposes the BLUE intruder
    assert spawns[0]["countryId"] == RED_COUNTRY
    h.assert_no_lua_errors()


def test_point_spawned_cap_escalates_and_stands_down() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(_point_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(200)

    attacks = _attack_tasks(h)
    assert attacks and attacks[0]["targetGroupId"] == 42
    assert len(_sam_spawns(h)) == 1
    h.assert_no_lua_errors()


def test_point_spawned_cap_routes_back_to_its_own_station() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(_point_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)
    h.update_unit("Viper 1-1", {"x": 90000, "z": 90000})
    h.advance_to(45 + 130 + 10)

    routes = [r for r in h.records("routes") if isinstance(r, dict)]
    assert routes, "stood-down point CAP was never routed home"
    # Home is its spawn station, not an airbase it does not have.
    assert routes[-1]["x"] == 12000 and routes[-1]["z"] == 12000
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


def test_a_side_that_is_permitted_transit_is_never_intercepted() -> None:
    """Per-side consent: a country open to blue and closed to red must wave one
    through and shadow the other. Turkey in 2022 is exactly this."""
    cfg = _config()
    zone = cfg["neutralBorder"]["zones"][0]
    zone["overflightBlue"] = "true"
    zone["overflightRed"] = "false"

    h = _setup(cfg)
    h.add_group(_intruder("Viper 1-1", 42, side=2))  # BLUE, permitted
    h.add_group(_intruder("Bandit 1", 50, side=1, player=None))  # RED, refused
    h.load_plugin_script(PLUGIN)
    h.advance_to(60)

    spawns = _shadow_spawns(h)
    assert len(spawns) == 1, "only the refused side should be shadowed"
    # Opposing a RED intruder means a BLUE clone.
    assert spawns[0]["coalitionId"] == 2
    h.assert_no_lua_errors()


def test_a_zone_open_to_everyone_never_scans() -> None:
    cfg = _config(sam=False)
    zone = cfg["neutralBorder"]["zones"][0]
    zone["overflightBlue"] = "true"
    zone["overflightRed"] = "true"

    h = _setup(cfg)
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(400)

    assert h.records("spawns") == []
    assert _attack_tasks(h) == []
    h.assert_no_lua_errors()


def test_a_zone_with_no_floor_intercepts_at_any_altitude() -> None:
    """ "If they are hostile then they are hostile" (DM, 2026-08-25). A floor
    means high transit is tolerated; a closed country grants no such height, so
    a zone emitted without one must trip a transit at any altitude."""
    h = _setup(_config())  # the fixture emits no floorBlueFt/floorRedFt
    h.add_group(_intruder("Heavy 7-1", 70, side=2, alt=9000))  # ~30,000 ft
    h.load_plugin_script(PLUGIN)
    h.advance_to(60)

    assert len(_shadow_spawns(h)) == 1, "a closed border let a high transit pass"
    h.assert_no_lua_errors()


def test_the_warning_does_not_offer_an_altitude_that_does_not_exist() -> None:
    """A floorless zone must not radio 'climb above it' -- there is no above."""
    h = _setup(_config())
    h.add_group(_intruder("Viper 1-1", 42, side=2))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)

    texts = [str(r.get("text", "")) for r in h.records("texts") if isinstance(r, dict)]
    warned = [t for t in texts if "violating" in t]
    assert warned, "no warning was issued"
    assert not any("below" in t or "Climb" in t for t in warned)
    h.assert_no_lua_errors()


# -- the alert flight has to be able to reach you -------------------------------
# MEASURED 2026-08-25 (Tacview, Inherent Resolve): Iran's origin is the
# representative point of its clipped polygon, so the pair came up 224 NM behind
# an F-15E, closed to 127 NM in twelve minutes and gave up. A shadow that cannot
# arrive is not a deterrent, and on any country bigger than Kuwait every launch
# was that launch.

BIG_SQUARE = [
    {"x": "0", "y": "0"},
    {"x": "600000", "y": "0"},
    {"x": "600000", "y": "600000"},
    {"x": "0", "y": "600000"},
]

STANDOFF_M = 46300


def _big_country(**overrides: Any) -> dict[str, Any]:
    cfg = _config()
    zone = cfg["neutralBorder"]["zones"][0]
    zone["border"] = BIG_SQUARE
    zone.update(overrides)
    return cfg


def _sep(spawn: dict[str, Any], x: float, z: float) -> float:
    return ((spawn["x"] - x) ** 2 + (spawn["z"] - z) ** 2) ** 0.5


def test_a_distant_intruder_gets_a_shadow_within_reach() -> None:
    """The field is 400 km away, so the alert flight comes up near the intruder
    instead of launching a stern chase it can never win."""
    h = _setup(_big_country())
    h.add_group(_intruder("BLUE 1", 1, 2, x=420000, z=420000, alt=2000))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)
    spawns = [r for r in h.records("spawns") if r.get("base") == "point"]
    assert len(spawns) == 1, "no air-spawned shadow for a distant intruder"
    assert _sep(spawns[0], 420000, 420000) <= STANDOFF_M + 1
    # And it is not simply sitting on top of the intruder either.
    assert _sep(spawns[0], 420000, 420000) > STANDOFF_M * 0.9
    # Still the opposing coalition -- the mechanism that lets it fire at all.
    assert spawns[0]["coalitionId"] == 1
    assert spawns[0]["countryId"] == RED_COUNTRY


def test_a_near_intruder_still_scrambles_off_the_runway() -> None:
    """Inside the stand-off the origin is used as it stands, so a small country
    launches from its own field rather than materialising in mid-air."""
    h = _setup(_big_country())
    h.add_group(_intruder("BLUE 1", 1, 2, x=12000, z=12000, alt=2000))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)
    assert len(_shadow_spawns(h)) == 1, "near intruder did not draw a field scramble"
    assert [r for r in h.records("spawns") if r.get("base") == "point"] == []


def test_the_shadow_launches_from_inside_the_country() -> None:
    """The stand-off point is on the line to the origin, so it is inside the
    border for any intruder that is -- the polygon is what makes the alert
    flight national rather than an ambush staged over the neighbour."""
    h = _setup(_big_country())
    h.add_group(_intruder("BLUE 1", 1, 2, x=590000, z=300000, alt=2000))
    h.load_plugin_script(PLUGIN)
    h.advance_to(45)
    spawns = [r for r in h.records("spawns") if r.get("base") == "point"]
    assert len(spawns) == 1
    assert 0 <= spawns[0]["x"] <= 600000
    assert 0 <= spawns[0]["z"] <= 600000


# -- the F10 draw --------------------------------------------------------------


def _drawn(cfg: dict[str, Any]) -> DcsPluginHarness:
    cfg["plugins"]["neutralborder"]["drawBorders"] = True
    h = _setup(cfg)
    h.load_plugin_script(PLUGIN)
    return h


def test_the_border_is_filled_by_triangles_not_by_the_freeform() -> None:
    """DCS draws a concave freeform's outline and refuses its fill, and a
    national border is about as concave as a shape gets -- every zone came out a
    bare line on the Iraq map. The fill is MOOSE's triangulation; the freeform
    carries only the outline, and must ask for no fill of its own."""
    h = _drawn(_config())
    fills = h.records("zoneFills")
    assert len(fills) == 1, "the border was never filled"
    assert fills[0]["alpha"] > 0
    assert fills[0]["coalition"] == -1, "fill must be visible to both sides"
    assert len(fills[0]["points"]) == len(SQUARE)
    outlines = [r for r in h.records("markups") if r["shape"] == 7]
    assert len(outlines) == 1
    assert outlines[0]["fill"] is not None and outlines[0]["fill"][3] == 0.0


def test_the_outline_does_not_repeat_its_first_vertex() -> None:
    """DCS closes a freeform itself. Repeating vertex one adds a zero-length
    edge, which is the other half of why the fill never rendered."""
    h = _drawn(_config())
    outline = [r for r in h.records("markups") if r["shape"] == 7][0]
    assert len(outline["points"]) == len(SQUARE)
    first, last = outline["points"][0], outline["points"][-1]
    assert (first["x"], first["z"]) != (last["x"], last["z"])


def test_an_open_neutral_and_a_closed_one_do_not_draw_alike() -> None:
    """Shade answers "will this intercept me", so the one that will is the one
    that gets a real fill."""
    closed = _drawn(_config())
    cfg = _config()
    cfg["neutralBorder"]["zones"][0]["overflightBlue"] = "true"
    cfg["neutralBorder"]["zones"][0]["overflightRed"] = "true"
    permits = _drawn(cfg)
    assert closed.records("zoneFills")[0]["alpha"] > (
        permits.records("zoneFills")[0]["alpha"]
    )
