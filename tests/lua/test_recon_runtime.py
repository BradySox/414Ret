"""Headless runtime check for the unified recon BDA plugin (recon-config.lua).

This plugin replaced BOTH the MOOSE ``Ops.TARS`` player film path and the AI-only
``airecon`` capture on 2026-08-05. It is a pure *ledger writer*: when a watched recon
flight -- player OR AI, one rule for both -- closes inside the trigger range of its
emitted target, the enemy (RED) ground/ship units within the effective sensor radius are
appended to the shared ``tars_recon_captures`` table, in the exact schema
(``{unit, life, type}``) ``game/debriefing.py`` parses.

Pins that the debrief depends on:

* the capture fires only on overfly, and exactly once per flight (one-shot);
* a flight that dies before reaching the target confirms nothing;
* only RED units inside the effective radius are recorded, in the debrief's schema;
* ``dirty_state`` is raised so ``dcs_retribution.lua`` flushes the ledger to
  ``state.json`` -- without it the capture never reaches Python;
* ``captureCap`` bounds the write;
* no ``Recon`` node is a clean no-op.

Pins on the rebuild's new behaviour:

* **the cue is held until the flight LANDS** (DM call) -- you get the read-out when the
  take is home, not while still over the target;
* **the capture is NOT held until landing**, deliberately: missions routinely end before
  flights land, so gating the take on touchdown would silently destroy most recon. The
  asymmetry is the design, and these two tests exist to stop someone "fixing" it;
* **altitude degrades the sensor** -- a high fast pass brings home less than a proper
  recon profile;
* **cloud cover degrades it too**, from the campaign's own weather.

The harness models no DCS AI or physics -- whether a recon flight actually flies its
profile over the target is the in-game pass (checklist G19).
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/recon/recon-config.lua"

NM = 1852.0
TRIGGER_NM = 5.0
SENSOR_NM = 2.0

TARGET_X = 100_000.0
TARGET_Z = 50_000.0


def _recon_flight(name: str, x: float, z: float, alt: float = 0.0) -> dict[str, Any]:
    """A blue recon flight; the plugin only ever reads its lead unit."""
    return {
        "name": name,
        "side": 2,  # BLUE
        "category": 0,  # AIRPLANE
        # NOTE: the harness's UnitFake:getPoint() reads `alt`, NOT `y` -- `y` is the
        # vertical component it RETURNS. Passing "y" here silently leaves the unit at
        # sea level, which makes any altitude assertion pass for the wrong reason.
        "units": [
            {"name": name + "-u1", "type": "MQ-9 Reaper", "x": x, "z": z, "alt": alt}
        ],
    }


def _red_ground(name: str, x: float, z: float, life: float = 3.0) -> dict[str, Any]:
    return {
        "name": name,
        "side": 1,  # RED
        "category": 2,  # GROUND
        "units": [
            {
                "name": name + "-u1",
                "type": "SA-6 Kub LN 2P25",
                "x": x,
                "z": z,
                "life": life,
            }
        ],
    }


def _red_ship(name: str, x: float, z: float) -> dict[str, Any]:
    return {
        "name": name,
        "side": 1,  # RED
        "category": 3,  # SHIP
        "units": [
            {"name": name + "-u1", "type": "MOLNIYA", "x": x, "z": z, "life": 5.0}
        ],
    }


def _harness(
    flights: list[dict[str, Any]],
    *,
    poll: int = 10,
    cap: int | None = None,
    cloud_factor: float = 1.0,
) -> DcsPluginHarness:
    h = DcsPluginHarness()
    options: dict[str, Any] = {"triggerRangeNm": TRIGGER_NM, "pollS": poll}
    if cap is not None:
        options["captureCap"] = cap
    h.lua.globals().dcsRetribution = h.to_lua(
        {
            "plugins": {"recon": options},
            "Recon": {"cloudFactor": str(cloud_factor), "flights": flights},
        }
    )
    return h


def _ledger(h: DcsPluginHarness) -> list[dict[str, Any]]:
    captures = h.to_python(h.lua.globals().tars_recon_captures)
    if captures is None or captures == {}:
        return []
    assert isinstance(captures, list)
    return captures


def _entry(group: str, **extra: Any) -> dict[str, Any]:
    record = {"group": group, "x": TARGET_X, "y": TARGET_Z, "sensorNm": SENSOR_NM}
    record.update(extra)
    return record


def test_overfly_writes_the_debrief_schema_and_flags_dirty_state() -> None:
    h = _harness([_entry("RECON-1", label="SCENIC 1-1 (MQ-9)", target="Haina SA-6")])
    h.add_group(_recon_flight("RECON-1", x=TARGET_X, z=TARGET_Z))
    h.add_group(_red_ground("SA6-Site", x=TARGET_X + 500.0, z=TARGET_Z, life=3.0))
    h.load_plugin_script(PLUGIN)

    h.advance_to(11)

    captured = _ledger(h)
    assert len(captured) == 1
    # The exact schema game/debriefing.py parses -- drifting any key silently
    # breaks the BDA hand-off to Python.
    assert set(captured[0]) == {"unit", "life", "type"}
    assert captured[0]["unit"] == "SA6-Site-u1"
    assert captured[0]["type"] == "SA-6 Kub LN 2P25"
    assert captured[0]["life"] == 3.0

    # Without dirty_state the ledger never reaches state.json.
    assert h.lua.globals().dirty_state is True
    h.assert_no_lua_errors()


# --- the cue is held until landing -------------------------------------------


def test_no_cue_over_the_target() -> None:
    """You do not get the BDA read-out while still overhead."""
    h = _harness([_entry("RECON-CUE", label="SCENIC 1-1 (MQ-9)", target="Haina SA-6")])
    h.add_group(_recon_flight("RECON-CUE", x=TARGET_X, z=TARGET_Z))
    h.add_group(_red_ground("SA6-Site", x=TARGET_X + 500.0, z=TARGET_Z))
    h.load_plugin_script(PLUGIN)

    h.advance_to(11)

    assert _ledger(h), "the capture itself must still happen on overfly"
    assert h.records("texts") == [], "the cue must wait for landing"
    h.assert_no_lua_errors()


def test_the_cue_fires_when_the_flight_lands() -> None:
    h = _harness([_entry("RECON-CUE", label="SCENIC 1-1 (MQ-9)", target="Haina SA-6")])
    h.add_group(_recon_flight("RECON-CUE", x=TARGET_X, z=TARGET_Z))
    h.add_group(_red_ground("SA6-Site", x=TARGET_X + 500.0, z=TARGET_Z))
    h.load_plugin_script(PLUGIN)
    h.advance_to(11)

    h.fire_land("RECON-CUE")

    texts = h.records("texts")
    assert len(texts) == 1
    assert texts[0]["side"] == int(h.side.BLUE)
    assert "SCENIC 1-1 (MQ-9)" in texts[0]["text"]
    assert "Haina SA-6" in texts[0]["text"]
    h.assert_no_lua_errors()


def test_the_cue_is_delivered_only_once() -> None:
    h = _harness([_entry("RECON-CUE", label="SCENIC 1-1")])
    h.add_group(_recon_flight("RECON-CUE", x=TARGET_X, z=TARGET_Z))
    h.add_group(_red_ground("SA6-Site", x=TARGET_X + 500.0, z=TARGET_Z))
    h.load_plugin_script(PLUGIN)
    h.advance_to(11)

    h.fire_land("RECON-CUE")
    h.fire_land(
        "RECON-CUE"
    )  # a second touchdown (bounce, or a wingman) must not re-cue

    assert len(h.records("texts")) == 1
    h.assert_no_lua_errors()


def test_a_landing_by_an_unrelated_flight_cues_nothing() -> None:
    h = _harness([_entry("RECON-CUE")])
    h.add_group(_recon_flight("RECON-CUE", x=TARGET_X, z=TARGET_Z))
    h.add_group(_recon_flight("SOME-STRIKER", x=TARGET_X + 90 * NM, z=TARGET_Z))
    h.add_group(_red_ground("SA6-Site", x=TARGET_X + 500.0, z=TARGET_Z))
    h.load_plugin_script(PLUGIN)
    h.advance_to(11)

    h.fire_land("SOME-STRIKER")

    assert h.records("texts") == []
    h.assert_no_lua_errors()


def test_the_capture_counts_even_if_the_flight_never_lands() -> None:
    """The deliberate asymmetry -- do NOT "fix" this to match the cue.

    Missions routinely end before flights land (the player quits after their own
    sortie), so gating the take on touchdown would silently destroy most recon.
    """
    h = _harness([_entry("RECON-NOLAND")])
    h.add_group(_recon_flight("RECON-NOLAND", x=TARGET_X, z=TARGET_Z))
    h.add_group(_red_ground("SA6-Site", x=TARGET_X + 500.0, z=TARGET_Z))
    h.load_plugin_script(PLUGIN)

    h.advance_to(600)  # never lands, mission just runs on

    assert len(_ledger(h)) == 1
    assert h.lua.globals().dirty_state is True
    h.assert_no_lua_errors()


# --- sensor degradation -------------------------------------------------------


def test_a_high_pass_captures_less_than_a_low_one() -> None:
    """Altitude degrades the sensor: fly the profile or bring home less."""

    def captured_at(alt_m: float) -> int:
        h = _harness([_entry("RECON-ALT")])
        h.add_group(_recon_flight("RECON-ALT", x=TARGET_X, z=TARGET_Z, alt=alt_m))
        # A ring of targets spread across the sensor radius, so shrinking the
        # effective radius provably drops the outer ones.
        for i in range(1, 10):
            h.add_group(
                _red_ground(
                    f"Ring-{i}", x=TARGET_X + SENSOR_NM * NM * (i / 10.0), z=TARGET_Z
                )
            )
        h.load_plugin_script(PLUGIN)
        h.advance_to(11)
        h.assert_no_lua_errors()
        return len(_ledger(h))

    low = captured_at(3_000.0)  # inside the optimal band -> full radius
    high = captured_at(12_000.0)  # at the ceiling -> minimum factor
    assert low > high, f"expected a high pass to capture less ({low} vs {high})"


def test_cloud_cover_degrades_the_take() -> None:
    def captured_with(cloud_factor: float) -> int:
        h = _harness([_entry("RECON-WX")], cloud_factor=cloud_factor)
        h.add_group(_recon_flight("RECON-WX", x=TARGET_X, z=TARGET_Z))
        for i in range(1, 10):
            h.add_group(
                _red_ground(
                    f"Ring-{i}", x=TARGET_X + SENSOR_NM * NM * (i / 10.0), z=TARGET_Z
                )
            )
        h.load_plugin_script(PLUGIN)
        h.advance_to(11)
        h.assert_no_lua_errors()
        return len(_ledger(h))

    clear = captured_with(1.0)
    overcast = captured_with(0.25)
    assert clear > overcast, f"expected cloud to cost take ({clear} vs {overcast})"


# --- unchanged contract -------------------------------------------------------


def test_capture_is_one_shot_and_stops_polling() -> None:
    h = _harness([_entry("RECON-2")])
    h.add_group(_recon_flight("RECON-2", x=TARGET_X, z=TARGET_Z))
    h.add_group(_red_ground("Depot", x=TARGET_X, z=TARGET_Z + 200.0))
    h.load_plugin_script(PLUGIN)

    h.advance_to(11)
    assert len(_ledger(h)) == 1

    h.advance_to(300)
    assert len(_ledger(h)) == 1
    assert h.pending_scheduled() == 0
    h.assert_no_lua_errors()


def test_a_flight_shot_down_before_the_target_confirms_nothing() -> None:
    h = _harness([_entry("RECON-3")])
    h.add_group(_recon_flight("RECON-3", x=TARGET_X + 40 * NM, z=TARGET_Z))
    h.add_group(_red_ground("Untouched", x=TARGET_X, z=TARGET_Z))
    h.load_plugin_script(PLUGIN)

    h.advance_to(11)
    assert _ledger(h) == []

    h.update_unit("RECON-3", {"exists": False})
    h.advance_to(400)
    assert _ledger(h) == []
    assert h.records("texts") == []
    h.assert_no_lua_errors()


def test_only_red_units_inside_the_sensor_radius_are_recorded() -> None:
    h = _harness([_entry("RECON-4")])
    h.add_group(_recon_flight("RECON-4", x=TARGET_X, z=TARGET_Z))
    h.add_group(_red_ground("InRing", x=TARGET_X + SENSOR_NM * NM * 0.5, z=TARGET_Z))
    h.add_group(_red_ship("RedBoat", x=TARGET_X, z=TARGET_Z + SENSOR_NM * NM * 0.5))
    h.add_group(_red_ground("OutOfRing", x=TARGET_X + SENSOR_NM * NM * 2.0, z=TARGET_Z))
    h.add_group(
        {
            "name": "BlueArmour",
            "side": 2,
            "category": 2,
            "units": [
                {
                    "name": "BlueArmour-u1",
                    "type": "M-1 Abrams",
                    "x": TARGET_X,
                    "z": TARGET_Z,
                }
            ],
        }
    )
    h.load_plugin_script(PLUGIN)

    h.advance_to(11)

    names = sorted(c["unit"] for c in _ledger(h))
    assert names == ["InRing-u1", "RedBoat-u1"]
    h.assert_no_lua_errors()


def test_capture_cap_bounds_the_write() -> None:
    h = _harness([_entry("RECON-5")], cap=3)
    h.add_group(_recon_flight("RECON-5", x=TARGET_X, z=TARGET_Z))
    for i in range(10):
        h.add_group(_red_ground(f"Bunched-{i}", x=TARGET_X + float(i), z=TARGET_Z))
    h.load_plugin_script(PLUGIN)

    h.advance_to(11)
    assert len(_ledger(h)) == 3
    h.assert_no_lua_errors()


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}})
    h.add_group(_red_ground("Ignored", x=TARGET_X, z=TARGET_Z))
    h.load_plugin_script(PLUGIN)

    h.advance_to(600)
    assert _ledger(h) == []
    assert h.pending_scheduled() == 0
    h.assert_no_lua_errors()
