"""Headless runtime check for the GPS-jamming plugin (gpsjamming-config.lua).

Pins the whole loop: a satellite-guided store released inside a live enemy
jammer's bubble is destroyed just short of impact and detonated off the aimpoint;
a laser weapon, a store outside the bubble, a store fired by the jammer's OWN
side, and a store whose jammer has already been killed all fly untouched.

The destroy + the explosion are the observables. The harness models no DCS
weapon aerodynamics -- a store here descends at a constant commanded rate -- so
whether a real JDAM's terminal profile trips the gate before impact is what the
in-game pass confirms. Degradation is made deterministic here with
degradeChancePct=100 (and 0 for the never-degrade case).
"""

from __future__ import annotations

import math
from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/gpsjamming/gpsjamming-config.lua"

# The jammer sits at the origin with a 10 km bubble; the target is under it.
JAMMER_X, JAMMER_Z = 0.0, 0.0
REACH_M = 10000.0
MISS_M = 300.0


def _blue_striker(name: str = "Hammer") -> dict[str, Any]:
    return {
        "name": name,
        "side": 2,  # BLUE
        "category": 0,  # AIRPLANE
        "units": [
            {
                "name": name + "-1",
                "type": "F/A-18C_hornet",
                "x": 0.0,
                "z": 0.0,
                "alt": 7000,
                "airborne": True,
            }
        ],
    }


def _red_striker(name: str = "Molot") -> dict[str, Any]:
    spec = _blue_striker(name)
    spec["side"] = 1  # RED
    spec["units"][0]["type"] = "Su-25T"
    return spec


def _jammer_group(name: str = "Haina jammer grp", alive: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "side": 1,  # RED-owned
        "category": 2,  # GROUND
        "units": [
            {
                "name": "0001 | GPS jammer",
                "type": "GPS_Spoofer_Red",
                "x": JAMMER_X,
                "z": JAMMER_Z,
                "life": 100 if alive else 0,
            }
        ],
    }


def _load(
    h: DcsPluginHarness,
    *,
    sites: list[dict[str, Any]] | None = None,
    patterns: list[str] | None = None,
    **opts: Any,
) -> None:
    base: dict[str, Any] = {
        "degradeChancePct": 100,  # deterministic: every store inside the bubble is spoofed
        "startGraceS": 10,
        "trackStepS": 1,
        "terminalAglFt": 100,
        "missPower": 400,
    }
    base.update(opts)
    if sites is None:
        sites = [
            {
                "name": "Haina jammer",
                "coalition": "red",
                "x": str(JAMMER_X),
                "y": str(JAMMER_Z),
                "reachM": str(REACH_M),
                "missRadiusM": str(MISS_M),
                "units": ["0001 | GPS jammer"],
            }
        ]
    cfg: dict[str, Any] = {
        "plugins": {"gpsjamming": base},
        "gpsJamming": {
            "sites": sites,
            "weaponPatterns": patterns or ["GBU-31", "GBU-38", "AGM-154"],
        },
    }
    h.lua.globals().dcsRetribution = h.to_lua(cfg)
    h.load_plugin_script(PLUGIN)


def _release(
    h: DcsPluginHarness,
    *,
    x: float = 0.0,
    z: float = 0.0,
    alt: float = 6000.0,
    wtype: str = "GBU-31",
    shooter: str = "Hammer",
    descent: float = 200.0,
    warhead: dict[str, Any] | None = None,
) -> None:
    """Drop a store that descends at `descent` m/s toward (x, z).

    `warhead` models what DCS reports on the weapon descriptor; None models a
    store with a thin descriptor (a mod weapon), which must fall back.
    """
    weapon: dict[str, Any] = {
        "typeName": wtype,
        "x": x,
        "z": z,
        "alt": alt,
        "velocity": {"x": 0.0, "y": -descent, "z": 0.0},
    }
    if warhead is not None:
        weapon["warhead"] = warhead
    h.fire_shot({"weapon": weapon, "initiator": shooter})


def _miss_distance(boom: dict[str, Any]) -> float:
    return math.sqrt((boom["x"] - 0.0) ** 2 + (boom["z"] - 0.0) ** 2)


# -- the core loop ------------------------------------------------------------


def test_a_jdam_released_over_the_jammer_is_put_down_off_the_aimpoint() -> None:
    h = DcsPluginHarness()
    h.add_group(_blue_striker())
    h.add_group(_jammer_group())
    _load(h)
    h.advance_to(20)  # past the startup grace
    _release(h)  # 6000 m at 200 m/s -> ~30 s of fall

    h.advance_to(60)
    assert h.records("weaponDestroys"), "the spoofed store must be removed in flight"
    booms = h.records("explosions")
    assert len(booms) == 1, "exactly one off-target detonation"
    assert booms[0]["power"] == 400
    # It landed off the aimpoint, but inside the site's miss radius.
    offset = _miss_distance(booms[0])
    assert 0 < offset <= MISS_M + 1e-6
    h.assert_no_lua_errors()


def test_the_firing_flight_is_told_once() -> None:
    h = DcsPluginHarness()
    h.add_group(_blue_striker())
    h.add_group(_jammer_group())
    _load(h)
    h.advance_to(20)
    _release(h)
    _release(h)  # a second store from the same flight

    h.advance_to(60)
    cues = [t for t in h.records("texts") if "GPS DENIED" in t["text"]]
    assert len(cues) == 1, "one cue per flight, not one per bomb"
    assert len(h.records("explosions")) == 2, "but both stores still go long"
    h.assert_no_lua_errors()


def test_the_miss_grows_with_jamming_strength() -> None:
    """A store clipping the fringe is nudged; one over the emitter is thrown clear."""
    fringe = DcsPluginHarness()
    fringe.add_group(_blue_striker())
    fringe.add_group(_jammer_group())
    _load(fringe)
    fringe.advance_to(20)
    # 9.5 km out of a 10 km bubble -> strength 0.05.
    _release(fringe, x=9500.0)
    fringe.advance_to(60)
    fringe_offset = math.sqrt(
        (fringe.records("explosions")[0]["x"] - 9500.0) ** 2
        + fringe.records("explosions")[0]["z"] ** 2
    )

    # Over the emitter -> strength 1.0, the full miss radius.
    assert fringe_offset <= MISS_M
    assert fringe_offset < MISS_M * 0.45, "a fringe store should barely be pushed"
    fringe.assert_no_lua_errors()


# -- everything that must NOT be touched --------------------------------------


def test_a_laser_weapon_is_never_jammed() -> None:
    h = DcsPluginHarness()
    h.add_group(_blue_striker())
    h.add_group(_jammer_group())
    _load(h)
    h.advance_to(20)
    _release(h, wtype="GBU-12")  # laser-guided: not in the pattern list

    h.advance_to(60)
    assert h.records("weaponDestroys") == []
    assert h.records("explosions") == []
    h.assert_no_lua_errors()


def test_a_store_released_outside_the_bubble_is_untouched() -> None:
    h = DcsPluginHarness()
    h.add_group(_blue_striker())
    h.add_group(_jammer_group())
    _load(h)
    h.advance_to(20)
    _release(h, x=25000.0)  # 25 km from a 10 km jammer

    h.advance_to(60)
    assert h.records("explosions") == []
    h.assert_no_lua_errors()


def test_a_jammer_never_degrades_its_own_sides_weapons() -> None:
    """Symmetric: the site degrades the OPPOSING coalition only."""
    h = DcsPluginHarness()
    h.add_group(_red_striker())
    h.add_group(_jammer_group())  # red-owned, and the shooter is red
    _load(h)
    h.advance_to(20)
    _release(h, shooter="Molot")

    h.advance_to(60)
    assert h.records("explosions") == []
    h.assert_no_lua_errors()


def test_the_jammer_dies_on_its_own_not_on_its_groups() -> None:
    """The intended laydown puts the jammer in a site WITH a radar (so the site
    shows on RWR and takes HARMs). Liveness must therefore be per-UNIT: kill the
    jammer truck and the jamming stops, even though its group-mates survive.

    A group-level check would keep denying GPS on the strength of the surviving
    radar beside the wreck of the actual jammer -- unkillable jamming.
    """
    h = DcsPluginHarness()
    h.add_group(_blue_striker())
    h.add_group(
        {
            "name": "Haina jammer grp",
            "side": 1,
            "category": 2,
            "units": [
                # The jammer itself: destroyed.
                {
                    "name": "0001 | GPS jammer",
                    "type": "GPS_Spoofer_Red",
                    "x": JAMMER_X,
                    "z": JAMMER_Z,
                    "life": 0,
                },
                # Its RWR/HARM-visible radar, still very much alive.
                {
                    "name": "0002 | RD-75",
                    "type": "RD_75",
                    "x": JAMMER_X + 60,
                    "z": JAMMER_Z,
                    "life": 100,
                },
            ],
        }
    )
    _load(h)
    h.advance_to(20)
    _release(h)

    h.advance_to(60)
    assert (
        h.records("explosions") == []
    ), "a dead jammer must stop denying GPS even when its group survives"
    h.assert_no_lua_errors()


def test_killing_the_jammer_restores_accuracy_in_the_same_mission() -> None:
    h = DcsPluginHarness()
    h.add_group(_blue_striker())
    h.add_group(_jammer_group(alive=False))  # struck before this release
    _load(h)
    h.advance_to(20)
    _release(h)

    h.advance_to(60)
    assert h.records("explosions") == [], "a dead jammer denies nothing"
    h.assert_no_lua_errors()


def test_the_startup_grace_holds_jamming() -> None:
    h = DcsPluginHarness()
    h.add_group(_blue_striker())
    h.add_group(_jammer_group())
    _load(h, startGraceS=300)
    _release(h, alt=3000.0)  # would reach the deck ~t+15 s, well inside the grace

    h.advance_to(120)
    assert h.records("explosions") == []
    h.assert_no_lua_errors()


def test_a_zero_chance_roll_lets_every_store_through() -> None:
    h = DcsPluginHarness()
    h.add_group(_blue_striker())
    h.add_group(_jammer_group())
    _load(h, degradeChancePct=0)
    h.advance_to(20)
    _release(h)

    h.advance_to(60)
    assert h.records("explosions") == []
    h.assert_no_lua_errors()


def test_a_mission_with_no_jamming_data_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.add_group(_blue_striker())
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {"gpsjamming": {}}})
    h.load_plugin_script(PLUGIN)
    h.advance_to(20)
    _release(h)

    h.advance_to(120)
    assert h.records("explosions") == []
    assert h.records("weaponDestroys") == []
    h.assert_no_lua_errors()


def test_a_fast_store_is_caught_before_impact() -> None:
    """The terminal gate is predictive: a store covering 400 m per sample must
    still be destroyed in the air, not detonate on the aimpoint between ticks."""
    h = DcsPluginHarness()
    h.add_group(_blue_striker())
    h.add_group(_jammer_group())
    _load(h, trackStepS=2, terminalAglFt=100)  # 100 ft floor, 800 m per step
    h.advance_to(20)
    _release(h, alt=8000.0, descent=400.0)

    h.advance_to(80)
    destroys = h.records("weaponDestroys")
    assert destroys, "a fast store must still be caught in the air"
    assert len(h.records("explosions")) == 1
    h.assert_no_lua_errors()


# -- the miss detonates with the weapon's OWN warhead --------------------------


def test_a_big_bomb_craters_harder_than_a_small_one() -> None:
    """A 2000 lb JDAM and a 500 lb JDAM must not make the same bang.

    The miss uses the store's real explosive mass (`desc.warhead.explosiveMass`),
    so the crater scales with what was actually dropped.
    """
    powers = {}
    for wtype, explosive in (("GBU-31", 429.0), ("GBU-38", 87.0)):
        h = DcsPluginHarness()
        h.add_group(_blue_striker())
        h.add_group(_jammer_group())
        _load(h)
        h.advance_to(20)
        _release(h, wtype=wtype, warhead={"explosiveMass": explosive})
        h.advance_to(60)
        booms = h.records("explosions")
        assert len(booms) == 1, f"{wtype} should produce one miss detonation"
        powers[wtype] = booms[0]["power"]
        h.assert_no_lua_errors()

    assert powers["GBU-31"] == 429.0
    assert powers["GBU-38"] == 87.0
    assert powers["GBU-31"] > powers["GBU-38"]


def test_the_scale_option_trims_the_miss_detonation() -> None:
    h = DcsPluginHarness()
    h.add_group(_blue_striker())
    h.add_group(_jammer_group())
    _load(h, missPowerScalePct=50)
    h.advance_to(20)
    _release(h, warhead={"explosiveMass": 400.0})

    h.advance_to(60)
    assert h.records("explosions")[0]["power"] == 200.0
    h.assert_no_lua_errors()


def test_explosive_mass_is_preferred_over_total_warhead_mass() -> None:
    """`explosiveMass` is the TNT-equivalent filler, which is the unit
    trigger.action.explosion wants; `mass` is the whole warhead and is only the
    next best thing."""
    h = DcsPluginHarness()
    h.add_group(_blue_striker())
    h.add_group(_jammer_group())
    _load(h)
    h.advance_to(20)
    _release(h, warhead={"explosiveMass": 87.0, "mass": 241.0})

    h.advance_to(60)
    assert h.records("explosions")[0]["power"] == 87.0
    h.assert_no_lua_errors()


def test_a_store_with_no_warhead_data_falls_back_to_the_flat_power() -> None:
    """A mod store with a thin descriptor must still make a bang -- the
    pre-scaling behaviour exactly, so this can only ever add fidelity."""
    h = DcsPluginHarness()
    h.add_group(_blue_striker())
    h.add_group(_jammer_group())
    _load(h, missPower=400)
    h.advance_to(20)
    _release(h)  # no warhead in the descriptor

    h.advance_to(60)
    assert h.records("explosions")[0]["power"] == 400
    h.assert_no_lua_errors()
