"""Headless runtime check for the dynamic deck respot (deckdecor-config.lua).

Pins the §72 launch-phase contract: the launch statics are struck below the
moment friendly fixed-wing traffic appears low astern of the boat (the CASE I
initial / CASE III straight-in profile), or at the fallback time regardless --
never before the grace, never for high traffic, traffic ahead, helicopters, or
a jet still on deck; a mission without the deckDecor node is a clean no-op.
Whether DCS renders the despawn cleanly on a moving deck is the in-game pass
(checklist B25).
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/deckdecor/deckdecor-config.lua"

STATIC = "CSG 1 deck decor 17 object"
NM = 1852.0


def _boat(x: float = 0.0, z: float = 0.0) -> dict[str, Any]:
    return {
        "name": "CSG 1",
        "side": 2,
        "category": 3,  # SHIP
        "units": [
            {"name": "CVN-71 Theodore Roosevelt", "type": "CVN_71", "x": x, "z": z}
        ],
    }


def _aircraft(
    name: str,
    x: float,
    z: float,
    alt: float,
    airborne: bool = True,
    category: int = 0,
    side: int = 2,
) -> dict[str, Any]:
    return {
        "name": name,
        "side": side,
        "category": category,
        "units": [
            {
                "name": name + "-u1",
                "type": "FA-18C_hornet",
                "x": x,
                "z": z,
                "alt": alt,
                "airborne": airborne,
            }
        ],
    }


def _harness(fallback_min: float = 30.0) -> DcsPluginHarness:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {
                "deckdecor": {
                    "pollS": 10,
                    "graceS": 30,
                    "fallbackMin": fallback_min,
                    "coneDistNm": 4.5,
                    "coneAltFt": 3000,
                    "coneHalfDeg": 50,
                }
            },
            "deckDecor": {
                "boats": [
                    {
                        "group": "CSG 1",
                        "unit": "CVN-71 Theodore Roosevelt",
                        "side": 2,
                        # Steaming due east: astern = due west of the boat.
                        "brc": "90.0",
                        "clearNames": [STATIC],
                    }
                ]
            },
        }
    )
    h.add_group(_boat())
    h.add_static({"name": STATIC})
    return h


def test_clears_on_the_fallback_timer() -> None:
    h = _harness(fallback_min=2.0)
    h.load_plugin_script(PLUGIN)

    h.advance_to(110)
    assert h.records("destroyedStatics") == []

    h.advance_to(140)
    assert h.records("destroyedStatics") == [STATIC]
    # One respot cue to the boat's coalition.
    texts = h.records("texts")
    assert len(texts) == 1 and texts[0]["side"] == 2
    h.assert_no_lua_errors()


def test_clears_when_fixed_wing_traffic_is_low_astern() -> None:
    h = _harness()
    # 3 NM dead astern (west of the east-steaming boat), 800 ft.
    h.add_group(_aircraft("Marshal", x=0.0, z=-3 * NM, alt=250.0))
    h.load_plugin_script(PLUGIN)

    h.advance_to(45)
    assert h.records("destroyedStatics") == [STATIC]
    h.assert_no_lua_errors()


def test_high_ahead_helo_or_deck_traffic_never_clears() -> None:
    h = _harness()
    # High astern (above the cone ceiling).
    h.add_group(_aircraft("HighCap", x=0.0, z=-3 * NM, alt=2500.0))
    # Low but ahead of the boat.
    h.add_group(_aircraft("Departure", x=0.0, z=3 * NM, alt=250.0))
    # A helo low astern (rotary never trips the fixed-wing cone).
    h.add_group(_aircraft("Angel", x=0.0, z=-2 * NM, alt=100.0, category=1))
    # A jet parked on deck (not airborne).
    h.add_group(_aircraft("ColdStart", x=50.0, z=-30.0, alt=20.0, airborne=False))
    h.load_plugin_script(PLUGIN)

    h.advance_to(600)
    assert h.records("destroyedStatics") == []
    h.assert_no_lua_errors()


def test_clear_fires_once_and_survives_a_missing_static() -> None:
    h = _harness(fallback_min=1.0)
    h.load_plugin_script(PLUGIN)
    h.advance_to(120)
    assert h.records("destroyedStatics") == [STATIC]
    # Well past several more polls: no second destroy, no second cue.
    h.advance_to(400)
    assert h.records("destroyedStatics") == [STATIC]
    assert len(h.records("texts")) == 1
    h.assert_no_lua_errors()


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {"deckdecor": {}}})
    h.add_group(_boat())
    h.add_static({"name": STATIC})
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert h.records("destroyedStatics") == []
    assert h.records("texts") == []
    h.assert_no_lua_errors()
