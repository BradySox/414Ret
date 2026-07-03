"""Headless runtime smoke tests for the vietnamops Lua plugin.

First user of the lupa harness (tests/lua/harness.py): loads the real
resources/plugins/vietnamops/vietnamops-config.lua into a Lua 5.1 interpreter
against a faked DCS sandbox, drives the virtual mission clock, and asserts the
plugin's observable behavior -- the config gates, the Arc Light release logic,
the flak envelope, and the airbase-harassment grace period + player-field
exclusion double-guard. These are the guarantees an in-game pass would
otherwise be the first to exercise.
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/vietnamops/vietnamops-config.lua"

NM_TO_M = 1852
FT_TO_M = 0.3048
LB_TO_KG = 0.453592


@pytest.fixture
def harness() -> DcsPluginHarness:
    return DcsPluginHarness()


def bomber(
    harness: DcsPluginHarness, name: str, x: float, z: float, **unit: Any
) -> None:
    harness.add_group(
        {
            "name": name,
            "side": 2,  # BLUE
            "category": 0,  # AIRPLANE
            "units": [
                {
                    "name": f"{name}-1",
                    "type": "B-52H",
                    "x": x,
                    "z": z,
                    "alt": 9000,
                    "airborne": True,
                    **unit,
                }
            ],
        }
    )


class TestPluginGate:
    def test_inert_without_vietnam_ops_data(self, harness: DcsPluginHarness) -> None:
        """No VietnamOps table -> the plugin logs a skip and schedules nothing."""
        harness.lua.globals().dcsRetribution = harness.to_lua({"plugins": {}})
        harness.load_plugin_script(PLUGIN)
        assert harness.pending_scheduled() == 0
        assert any("skipping" in line for line in harness.records("infos"))
        harness.assert_no_lua_errors()

    def test_inert_with_empty_suite(self, harness: DcsPluginHarness) -> None:
        """VietnamOps present but every feature absent -> nothing arms."""
        harness.set_retribution_config(vietnam_ops={})
        harness.load_plugin_script(PLUGIN)
        assert harness.pending_scheduled() == 0
        harness.assert_no_lua_errors()


class TestArcLight:
    def strikes(self, group: str) -> dict[str, Any]:
        return {"arcLight": {"strikes": [{"group": group, "x": 0, "y": 0}]}}

    def test_carpet_fires_when_bomber_reaches_release_range(
        self, harness: DcsPluginHarness
    ) -> None:
        # Bomber 2 NM out, inside the default 3 NM release range, inbound the origin.
        bomber(harness, "ARCLIGHT", x=2 * NM_TO_M, z=0)
        harness.set_retribution_config(vietnam_ops=self.strikes("ARCLIGHT"))
        harness.load_plugin_script(PLUGIN)

        harness.advance_to(60)  # first poll at t=5; carpet walks over ~3.5 s

        explosions = harness.records("explosions")
        assert len(explosions) == 14 * 5, "the full 14x5 carpet should land"
        # Impacts carry the default 660 lb TNT power, converted to kg.
        assert explosions[0]["power"] == pytest.approx(660 * LB_TO_KG)
        # The carpet lands on the target, not on the bomber: every impact within
        # the carpet footprint (half of 6000 ft length + jitter) of the origin.
        reach = (6000 / 2) * FT_TO_M + 100
        for impact in explosions:
            assert math.hypot(impact["x"], impact["z"]) <= reach
        assert any("ARC LIGHT" in t["text"] for t in harness.records("texts"))
        harness.assert_no_lua_errors()

    def test_carpet_is_one_shot(self, harness: DcsPluginHarness) -> None:
        bomber(harness, "ARCLIGHT", x=2 * NM_TO_M, z=0)
        harness.set_retribution_config(vietnam_ops=self.strikes("ARCLIGHT"))
        harness.load_plugin_script(PLUGIN)

        harness.advance_to(600)  # many poll cycles

        assert len(harness.records("explosions")) == 14 * 5
        harness.assert_no_lua_errors()

    def test_no_carpet_outside_release_range(self, harness: DcsPluginHarness) -> None:
        bomber(harness, "ARCLIGHT", x=10 * NM_TO_M, z=0)
        harness.set_retribution_config(vietnam_ops=self.strikes("ARCLIGHT"))
        harness.load_plugin_script(PLUGIN)

        harness.advance_to(120)

        assert harness.records("explosions") == []
        harness.assert_no_lua_errors()

    def test_dead_bomber_never_fires(self, harness: DcsPluginHarness) -> None:
        """A bomber killed before the run-in must not release -- losses stay native."""
        bomber(harness, "ARCLIGHT", x=2 * NM_TO_M, z=0, life=0)
        harness.set_retribution_config(vietnam_ops=self.strikes("ARCLIGHT"))
        harness.load_plugin_script(PLUGIN)

        harness.advance_to(120)

        assert harness.records("explosions") == []
        harness.assert_no_lua_errors()

    def test_malformed_strike_entry_degrades_quietly(
        self, harness: DcsPluginHarness
    ) -> None:
        """A record without coordinates is skipped, never a scripting error."""
        harness.set_retribution_config(
            vietnam_ops={"arcLight": {"strikes": [{"group": "ARCLIGHT"}]}}
        )
        harness.load_plugin_script(PLUGIN)
        harness.advance_to(120)
        assert harness.records("explosions") == []
        harness.assert_no_lua_errors()


class TestFlakGauntlet:
    def arm(self, harness: DcsPluginHarness) -> None:
        harness.set_retribution_config(vietnam_ops={"flak": {"enabled": True}})
        harness.load_plugin_script(PLUGIN)

    def aaa_site(self, harness: DcsPluginHarness) -> None:
        harness.add_group(
            {
                "name": "RED-AAA",
                "side": 1,  # RED
                "category": 2,  # GROUND
                "units": [
                    {
                        "name": "RED-AAA-1",
                        "type": "ZU-23",
                        "x": 0,
                        "z": 0,
                        "attributes": {"AAA": True},
                    }
                ],
            }
        )

    def plane(self, harness: DcsPluginHarness, alt: float) -> None:
        harness.add_group(
            {
                "name": "BLUE-CAS",
                "side": 2,
                "category": 0,
                "units": [
                    {
                        "name": "BLUE-CAS-1",
                        "type": "A-1H",
                        "x": 1000,
                        "z": 0,
                        "alt": alt,
                        "airborne": True,
                        "velocity": {"x": 120, "y": 0, "z": 0},
                    }
                ],
            }
        )

    def test_aircraft_in_envelope_draws_bursts(self, harness: DcsPluginHarness) -> None:
        self.aaa_site(harness)
        self.plane(harness, alt=1500)  # ~5000 ft AGL, well inside the envelope
        self.arm(harness)

        harness.advance_to(30)  # several 2.5 s flak ticks

        bursts = harness.records("explosions")
        assert bursts, "an aircraft inside an alive gun's envelope must draw flak"
        # Barrage bursts scatter around the aircraft, never on it: each within the
        # loosest miss distance (1000 ft) + the 40 m altitude jitter of its position.
        for burst in bursts:
            offset = math.hypot(burst["x"] - 1000, burst["z"] - 0)
            assert offset <= 1000 * FT_TO_M * 1.4 + 1
        harness.assert_no_lua_errors()

    def test_aircraft_above_ceiling_is_safe(self, harness: DcsPluginHarness) -> None:
        self.aaa_site(harness)
        self.plane(harness, alt=6000)  # ~19700 ft, above the 15000 ft default ceiling
        self.arm(harness)

        harness.advance_to(30)

        assert harness.records("explosions") == []
        harness.assert_no_lua_errors()

    def test_no_guns_no_flak(self, harness: DcsPluginHarness) -> None:
        self.plane(harness, alt=1500)
        self.arm(harness)

        harness.advance_to(30)

        assert harness.records("explosions") == []
        harness.assert_no_lua_errors()


class TestAirbaseHarassment:
    def arm(
        self,
        harness: DcsPluginHarness,
        fields: list[dict[str, Any]],
        excluded: list[str],
    ) -> None:
        harness.set_retribution_config(
            vietnam_ops={
                "airbaseHarassment": {"fields": fields, "excludedFields": excluded}
            }
        )
        harness.load_plugin_script(PLUGIN)

    def test_grace_period_holds_fire(self, harness: DcsPluginHarness) -> None:
        self.arm(
            harness,
            fields=[{"name": "Kutaisi", "x": 0, "y": 0, "coalition": "BLUE"}],
            excluded=[],
        )

        harness.advance_to(299)  # inside the default 300 s grace

        assert harness.records("explosions") == []
        harness.assert_no_lua_errors()

    def test_barrage_lands_after_grace(self, harness: DcsPluginHarness) -> None:
        self.arm(
            harness,
            fields=[{"name": "Kutaisi", "x": 0, "y": 0, "coalition": "BLUE"}],
            excluded=[],
        )

        # Grace 300 s + first randomized cadence (<= 1.5 * 240 s) is due by 660 s.
        harness.advance_to(700)

        barrage = harness.records("explosions")
        assert barrage, "a watched field must draw fire once the grace expires"
        assert all(b["t"] >= 300 for b in barrage)
        # Impacts scatter over the ramp: within the 850 ft dispersion radius.
        for impact in barrage:
            assert math.hypot(impact["x"], impact["z"]) <= 850 * FT_TO_M + 1
        assert any("Incoming" in t["text"] for t in harness.records("texts"))
        harness.assert_no_lua_errors()

    def test_excluded_player_field_is_never_shelled(
        self, harness: DcsPluginHarness
    ) -> None:
        """The Lua-side double-guard: even if Python leaks a player field into the
        target list, the excludedFields list must keep it safe."""
        self.arm(
            harness,
            fields=[
                {"name": "Kutaisi", "x": 0, "y": 0, "coalition": "BLUE"},
                {"name": "Batumi", "x": 100000, "y": 100000, "coalition": "BLUE"},
            ],
            excluded=["Batumi"],
        )

        harness.advance_to(3600)  # a full hour of cadences

        barrage = harness.records("explosions")
        assert barrage
        for impact in barrage:
            distance_from_batumi = math.hypot(
                impact["x"] - 100000, impact["z"] - 100000
            )
            assert distance_from_batumi > 10000, "the excluded field drew fire"
        harness.assert_no_lua_errors()
