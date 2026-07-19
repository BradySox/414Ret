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
    velocity: dict[str, float] | None = None,
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
                "velocity": velocity or {"x": 0.0, "y": 0.0, "z": 0.0},
            }
        ],
    }


def _harness(
    fallback_min: float = 30.0, airboss: dict[str, Any] | None = None
) -> DcsPluginHarness:
    h = DcsPluginHarness()
    plugins: dict[str, Any] = {
        "deckdecor": {
            "pollS": 10,
            "graceS": 30,
            "fallbackMin": fallback_min,
            "airbossMarginS": 300,
            "coneDistNm": 4.5,
            "coneAltFt": 1000,
            "coneHalfDeg": 50,
            "coneClosingKts": 30,
        }
    }
    if airboss is not None:
        plugins["airboss"] = airboss
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": plugins,
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


def test_clears_when_recovery_traffic_runs_in_low_astern() -> None:
    h = _harness()
    # 3 NM dead astern (west of the east-steaming boat), ~800 ft, CLOSING on
    # the boat at ~250 kt (flying east toward it) -- a CASE I/III run-in.
    h.add_group(
        _aircraft(
            "Marshal",
            x=0.0,
            z=-3 * NM,
            alt=250.0,
            velocity={"x": 0.0, "y": 0.0, "z": 130.0},
        )
    )
    h.load_plugin_script(PLUGIN)

    # First qualifying poll at the grace (30 s) arms the debounce; the second
    # (40 s) clears -- a single transient poll never does.
    h.advance_to(35)
    assert h.records("destroyedStatics") == []
    h.advance_to(45)
    assert h.records("destroyedStatics") == [STATIC]
    h.assert_no_lua_errors()


def test_launch_traffic_crossing_astern_never_clears() -> None:
    """The flown false trip (2026-07-18): freshly-launched jets turning back
    past the boat are low and astern but NOT closing -- and climbing traffic
    above 1000 ft is out of the cone entirely."""
    h = _harness()
    # Low astern but flying AWAY from the boat (departing on course).
    h.add_group(
        _aircraft(
            "Outbound",
            x=0.0,
            z=-2 * NM,
            alt=250.0,
            velocity={"x": 0.0, "y": 0.0, "z": -160.0},
        )
    )
    # Astern and closing, but already through 1000 ft (a climbing turnback).
    h.add_group(
        _aircraft(
            "Turnback",
            x=0.0,
            z=-3 * NM,
            alt=500.0,
            velocity={"x": 0.0, "y": 0.0, "z": 150.0},
        )
    )
    h.load_plugin_script(PLUGIN)

    h.advance_to(600)
    assert h.records("destroyedStatics") == []
    h.assert_no_lua_errors()


def test_high_ahead_helo_or_deck_traffic_never_clears() -> None:
    h = _harness()
    closing_east = {"x": 0.0, "y": 0.0, "z": 130.0}
    closing_west = {"x": 0.0, "y": 0.0, "z": -130.0}
    # Closing from astern but far above the cone ceiling.
    h.add_group(
        _aircraft("HighCap", x=0.0, z=-3 * NM, alt=2500.0, velocity=closing_east)
    )
    # Low and closing, but from AHEAD of the boat.
    h.add_group(
        _aircraft("Departure", x=0.0, z=3 * NM, alt=250.0, velocity=closing_west)
    )
    # A helo low astern and closing (rotary never trips the fixed-wing cone).
    h.add_group(
        _aircraft(
            "Angel", x=0.0, z=-2 * NM, alt=100.0, category=1, velocity=closing_east
        )
    )
    # A jet parked on deck (not airborne).
    h.add_group(_aircraft("ColdStart", x=50.0, z=-30.0, alt=20.0, airborne=False))
    h.load_plugin_script(PLUGIN)

    h.advance_to(600)
    assert h.records("destroyedStatics") == []
    h.assert_no_lua_errors()


def test_airboss_recovery_window_pulls_the_clear_forward() -> None:
    """With the sibling airboss plugin present (it is default ON), the deck
    must be clean before its scheduled recovery window opens -- window start
    minus the margin beats a later fallback timer."""
    # Window opens at 10 min; margin 300 s -> deadline 300 s, far before the
    # 30-min fallback.
    h = _harness(airboss={"windowStartOption": 10})
    h.load_plugin_script(PLUGIN)

    h.advance_to(290)
    assert h.records("destroyedStatics") == []
    h.advance_to(320)
    assert h.records("destroyedStatics") == [STATIC]
    h.assert_no_lua_errors()


def test_airboss_window_deadline_is_floored_at_the_grace() -> None:
    """A window earlier than the margin can reach never produces an instant
    or pre-grace clear -- the deadline floors at grace + one poll."""
    h = _harness(airboss={"windowStartOption": 1})  # 60 s - 300 s margin < 0
    h.load_plugin_script(PLUGIN)

    h.advance_to(20)
    assert h.records("destroyedStatics") == []
    # Floor is graceS (30) + pollS (10) = 40 s; the first post-grace poll
    # past the floor clears.
    h.advance_to(60)
    assert h.records("destroyedStatics") == [STATIC]
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
