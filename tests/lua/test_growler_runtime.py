"""Headless runtime check for the growler plugin (growler-config.lua).

Pins the "script errors and the feature silently never starts" invariant plus
the safety contracts: the offensive pulse is ROE-only (WEAPON_HOLD then a
scheduled OPEN_FIRE restore -- emissions are never touched), it waits out the
startup grace, only radar-SAM ("SAM TR") groups are eligible, a defensive spoof
destroys a radar-guided missile inside the bubble, the friendly-fire guard
(a blue Growler never spoofs a blue missile), and a mission with no growler
node is a clean no-op. Determinism: power options scale the dice to certainty
(pk*2 -> clamped >= 100%) or zero, so no test rides math.random.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/growler/growler-config.lua"

# AI.Option.Ground.id.ROE / val.ROE values (mirrored by the stubs).
ROE_OPTION = 0
ROE_OPEN_FIRE = 2
ROE_WEAPON_HOLD = 4


def _jammer_group(name: str, side: int = 2, in_air: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "side": side,
        "category": 0,  # AIRPLANE
        "units": [
            {"name": name + "-1", "type": "EA-18G", "airborne": in_air, "x": 0, "z": 0}
        ],
    }


def _sam_group(name: str, x: float, z: float, radar: bool = True) -> dict[str, Any]:
    unit: dict[str, Any] = {"name": name + "-tr", "type": "SNR_75V", "x": x, "z": z}
    if radar:
        # The stub's hasAttribute reads a map, not a list.
        unit["attributes"] = {"SAM TR": True}
    return {"name": name, "side": 1, "category": 2, "units": [unit]}


def _config(h: DcsPluginHarness, node: dict[str, Any] | None, **options: Any) -> None:
    cfg: dict[str, Any] = {"plugins": {"growler": options}}
    if node is not None:
        cfg["growler"] = node
    h.lua.globals().dcsRetribution = h.to_lua(cfg)


def _jammer_node(
    group: str,
    protected: list[str],
    is_player: bool = False,
    tier: str = "full",
    defensive_power: float = 1.0,
    offensive: bool = True,
) -> dict[str, Any]:
    return {
        "jammers": [
            {
                "groupName": group,
                "side": "2",
                "isPlayer": "1" if is_player else "0",
                "tier": tier,
                "defensivePower": str(defensive_power),
                "offensive": "1" if offensive else "0",
                "protected": [{"groupName": name} for name in protected],
            }
        ]
    }


def _roe_records(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [r for r in h.records("options") if r["option"] == ROE_OPTION]


def test_no_growler_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {"growler": {}}})
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    h.assert_no_lua_errors()
    assert not _roe_records(h)


def test_offensive_pulse_holds_then_restores_after_the_grace() -> None:
    h = DcsPluginHarness()
    h.add_group(_jammer_group("Shadow 1"))
    h.add_group(_sam_group("SA-2", x=10000, z=0))
    _config(
        h,
        _jammer_node("Shadow 1", ["Hammer 1"]),
        startGraceS=60,
        tickSec=10,
        holdSec=20,
        offensivePower=2.0,  # pk clamps to certainty -- no dice in the test
        defensivePower=0,
    )
    h.load_plugin_script(PLUGIN)
    h.assert_no_lua_errors()

    # Inside the grace: nothing held.
    h.advance_to(30)
    assert not _roe_records(h)

    # Past the grace: the radar SAM is pulsed onto WEAPON_HOLD...
    h.advance_to(61)
    holds = [r for r in _roe_records(h) if r["value"] == ROE_WEAPON_HOLD]
    assert holds and holds[0]["group"] == "SA-2"

    # ...and restored to OPEN_FIRE once the hold lapses.
    h.advance_to(120)
    restores = [r for r in _roe_records(h) if r["value"] == ROE_OPEN_FIRE]
    assert restores and restores[0]["group"] == "SA-2"
    h.assert_no_lua_errors()


def test_non_radar_ground_group_is_never_pulsed() -> None:
    h = DcsPluginHarness()
    h.add_group(_jammer_group("Shadow 1"))
    h.add_group(_sam_group("TRUCKS", x=5000, z=0, radar=False))
    _config(
        h,
        _jammer_node("Shadow 1", []),
        startGraceS=10,
        tickSec=10,
        offensivePower=2.0,
        defensivePower=0,
    )
    h.load_plugin_script(PLUGIN)
    h.advance_to(300)
    h.assert_no_lua_errors()
    assert not _roe_records(h)


def test_spoof_destroys_a_missile_inside_the_bubble() -> None:
    h = DcsPluginHarness()
    h.add_group(_jammer_group("Shadow 1"))
    h.add_group(_sam_group("SA-2", x=60000, z=0))
    _config(
        h,
        _jammer_node("Shadow 1", ["Hammer 1"]),
        startGraceS=600,  # offensive stays quiet; this test is the bubble
        defensivePower=2.0,  # 85 * 2 > 100: certain spoof in the inner band
        spoofMinTravelM=0,
        offensivePower=0,
    )
    h.load_plugin_script(PLUGIN)
    h.assert_no_lua_errors()
    # A red SAM shot sitting 400 m from the Growler (inner 500 m band).
    h.fire_shot(
        {
            "weapon": {"typeName": "SA2-missile", "x": 400, "z": 0, "alt": 1000},
            "initiator": "SA-2",
        }
    )
    h.advance_to(10)
    destroyed = h.records("weaponDestroys")
    assert destroyed and destroyed[0]["name"] == "SA2-missile"
    h.assert_no_lua_errors()


def test_a_friendly_missile_is_never_spoofed() -> None:
    h = DcsPluginHarness()
    h.add_group(_jammer_group("Shadow 1"))
    h.add_group(_jammer_group("Hammer 1"))  # blue shooter
    _config(
        h,
        _jammer_node("Shadow 1", ["Hammer 1"]),
        startGraceS=600,
        defensivePower=2.0,
        spoofMinTravelM=0,
        offensivePower=0,
    )
    h.load_plugin_script(PLUGIN)
    # A BLUE-fired missile right on top of the blue Growler: never touched.
    h.fire_shot(
        {
            "weapon": {"typeName": "AMRAAM", "x": 100, "z": 0, "alt": 1000},
            "initiator": "Hammer 1",
        }
    )
    h.advance_to(10)
    assert not h.records("weaponDestroys")
    h.assert_no_lua_errors()


def test_player_jammer_starts_off_and_gets_the_menu() -> None:
    h = DcsPluginHarness()
    h.add_group(_jammer_group("Shadow 1"))
    h.add_group(_sam_group("SA-2", x=10000, z=0))
    _config(
        h,
        _jammer_node("Shadow 1", [], is_player=True),
        startGraceS=10,
        tickSec=10,
        offensivePower=2.0,
        defensivePower=0,
    )
    h.load_plugin_script(PLUGIN)
    h.advance_to(300)
    h.assert_no_lua_errors()
    # Player jamming starts OFF: no pulse without the F10 toggle...
    assert not _roe_records(h)
    # ...and the F10 menu was offered to the group.
    menus = h.records("menus")
    assert any("Growler jamming" in str(m) for m in menus)


def test_defensive_only_tier_never_pulses_a_sam() -> None:
    # An ECM/self-protect/loose jammer (offensive=False) defends the package but
    # never suppresses a radar SAM, no matter how long it's on station.
    h = DcsPluginHarness()
    h.add_group(_jammer_group("Zapper 1"))
    h.add_group(_sam_group("SA-2", x=10000, z=0))
    _config(
        h,
        _jammer_node("Zapper 1", ["Hammer 1"], tier="ecm", offensive=False),
        startGraceS=30,
        tickSec=10,
        offensivePower=2.0,
        defensivePower=0,
    )
    h.load_plugin_script(PLUGIN)
    h.advance_to(300)
    h.assert_no_lua_errors()
    assert not _roe_records(h)


def test_zero_tier_power_never_spoofs() -> None:
    # defensivePower 0 (the tier scalar) zeroes the spoof chance even in the inner
    # band -- the utility gradient bottoms out at "does nothing", never negative.
    h = DcsPluginHarness()
    h.add_group(_jammer_group("Zapper 1"))
    _config(
        h,
        _jammer_node(
            "Zapper 1", ["Hammer 1"], tier="loose", defensive_power=0.0, offensive=False
        ),
        startGraceS=600,
        defensivePower=2.0,  # global is strong; the per-jammer 0 must still win
        spoofMinTravelM=0,
        offensivePower=0,
    )
    h.load_plugin_script(PLUGIN)
    h.fire_shot(
        {
            "weapon": {"typeName": "SA2-missile", "x": 400, "z": 0, "alt": 1000},
            "initiator": "SA-2",
        }
    )
    h.advance_to(10)
    h.assert_no_lua_errors()
    assert not h.records("weaponDestroys")
