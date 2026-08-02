"""Headless runtime check for the AI recon BDA capture plugin (airecon-config.lua).

The plugin closes the §3/G19 gap that the MOOSE TARS film path is player-only, so
AI-flown recon flights confirmed nothing. It is a pure *ledger writer*: when a watched
AI recon flight closes inside the trigger range of its emitted target, the enemy (RED)
ground/ship units within the capture radius are appended to the shared
``tars_recon_captures`` table -- the exact schema (``{unit, life, type}``) that
``game/debriefing.py`` parses, so an AI capture is treated identically to a player one.

These pins are the contract the debrief depends on:

* the capture fires only on overfly, and exactly once per flight (one-shot);
* a flight that dies before reaching the target confirms nothing;
* only RED units inside the capture radius are recorded, in the debrief's schema;
* ``dirty_state`` is raised so ``dcs_retribution.lua`` flushes the ledger to
  ``state.json`` -- without it the capture never reaches Python;
* the ``captureCap`` option bounds the write;
* a mission with no ``AIRecon`` node is a clean no-op.

The harness models no DCS AI or physics -- whether the AI recon flight actually flies
over its target is the in-game pass (checklist G19).
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/airecon/airecon-config.lua"

NM = 1852.0
TRIGGER_NM = 5.0
CAPTURE_NM = 2.0

# The target the recon flight is fragged against. The plugin reads the emitted
# record as (x = north, y = east) and compares against a unit's (p.x, p.z).
TARGET_X = 100_000.0
TARGET_Z = 50_000.0


def _recon_flight(name: str, x: float, z: float) -> dict[str, Any]:
    """A blue AI recon flight; the plugin only ever reads its lead unit."""
    return {
        "name": name,
        "side": 2,  # BLUE
        "category": 0,  # AIRPLANE
        "units": [{"name": name + "-u1", "type": "MQ-9 Reaper", "x": x, "z": z}],
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
) -> DcsPluginHarness:
    h = DcsPluginHarness()
    options: dict[str, Any] = {
        "triggerRangeNm": TRIGGER_NM,
        "captureRadiusNm": CAPTURE_NM,
        "pollS": poll,
    }
    if cap is not None:
        options["captureCap"] = cap
    h.lua.globals().dcsRetribution = h.to_lua(
        {"plugins": {"airecon": options}, "AIRecon": {"flights": flights}}
    )
    return h


def _ledger(h: DcsPluginHarness) -> list[dict[str, Any]]:
    captures = h.to_python(h.lua.globals().tars_recon_captures)
    if captures is None or captures == {}:
        return []
    assert isinstance(captures, list)
    return captures


def _entry(group: str, **extra: Any) -> dict[str, Any]:
    record = {"group": group, "x": TARGET_X, "y": TARGET_Z}
    record.update(extra)
    return record


def test_overfly_writes_the_debrief_schema_and_flags_dirty_state() -> None:
    h = _harness([_entry("RECON-1", label="SCENIC 1-1 (MQ-9)", target="Haina SA-6")])
    # Parked on top of the target: the first poll is an overfly.
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

    # The crew is told, on the blue net.
    texts = h.records("texts")
    assert len(texts) == 1
    assert texts[0]["side"] == int(h.side.BLUE)
    assert "SCENIC 1-1 (MQ-9)" in texts[0]["text"]
    assert "Haina SA-6" in texts[0]["text"]
    h.assert_no_lua_errors()


def test_capture_is_one_shot_and_stops_polling() -> None:
    h = _harness([_entry("RECON-2")])
    h.add_group(_recon_flight("RECON-2", x=TARGET_X, z=TARGET_Z))
    h.add_group(_red_ground("Depot", x=TARGET_X, z=TARGET_Z + 200.0))
    h.load_plugin_script(PLUGIN)

    h.advance_to(11)
    assert len(_ledger(h)) == 1

    # Loitering over the target must not re-photograph it every poll.
    h.advance_to(300)
    assert len(_ledger(h)) == 1
    assert h.pending_scheduled() == 0
    h.assert_no_lua_errors()


def test_a_flight_shot_down_before_the_target_confirms_nothing() -> None:
    h = _harness([_entry("RECON-3")])
    # Well outside the 5 NM trigger.
    h.add_group(_recon_flight("RECON-3", x=TARGET_X + 40 * NM, z=TARGET_Z))
    h.add_group(_red_ground("Untouched", x=TARGET_X, z=TARGET_Z))
    h.load_plugin_script(PLUGIN)

    h.advance_to(11)
    assert _ledger(h) == []

    # The flight dies en route: the watcher drops it, and nothing is ever banked.
    h.update_unit("RECON-3", {"exists": False})
    h.advance_to(400)
    assert _ledger(h) == []
    assert h.records("texts") == []
    h.assert_no_lua_errors()


def test_only_red_units_inside_the_capture_radius_are_recorded() -> None:
    h = _harness([_entry("RECON-4")])
    h.add_group(_recon_flight("RECON-4", x=TARGET_X, z=TARGET_Z))
    # Inside the 2 NM capture radius.
    h.add_group(_red_ground("InRing", x=TARGET_X + CAPTURE_NM * NM * 0.5, z=TARGET_Z))
    h.add_group(_red_ship("RedBoat", x=TARGET_X, z=TARGET_Z + CAPTURE_NM * NM * 0.5))
    # Outside it -- a nearby site the flight did not photograph.
    h.add_group(
        _red_ground("OutOfRing", x=TARGET_X + CAPTURE_NM * NM * 2.0, z=TARGET_Z)
    )
    # Friendly armour parked on the target is never "enemy BDA".
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
