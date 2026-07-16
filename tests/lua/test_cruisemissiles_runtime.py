"""Headless runtime check for the cruise-missile plugin (cruisemissiles-config.lua).

Pins the "script errors and the feature silently never starts" invariant plus the
§63 safety contract: an auto raid fires inside its launch window (pinned to a
degenerate min==max window here for determinism) as a FireAtPoint
with the cruise-missile weapon flag; the emitted magazine is a hard per-group cap
shared by raids and the F10 call-for-fire; expenditure mirrors into
``cruise_missiles_state`` (dirty-flagged) for the turn-boundary debit; a dead ship
fires nothing; a mission with no cruiseMissiles node is a clean no-op.

The defender launch wake (the 2026-07-16 flown intercept-gap fix — nothing in DCS
wakes a defender for a weapon object on its own) is pinned too: a launch sets
opposing ground AD groups near the aimpoint to alarm-state RED, stands them back
down to AUTO after the flight window, never touches far/friendly/non-AD groups,
and honors its kill switch.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/cruisemissiles/cruisemissiles-config.lua"

CRUISE_FLAG = 2097152


def _ship_group(name: str, side: int, x: float = 0.0, z: float = 0.0) -> dict[str, Any]:
    return {
        "name": name,
        "side": side,
        "category": 3,  # SHIP
        "units": [
            {"name": name + "-1", "type": "USS_Arleigh_Burke_IIa", "x": x, "z": z}
        ],
    }


def _config(
    ships: list[dict[str, Any]],
    raids: list[dict[str, Any]] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    node: dict[str, Any] = {"ships": ships}
    if raids is not None:
        node["raids"] = raids
    return {
        "plugins": {"cruisemissiles": options or {}},
        "cruiseMissiles": node,
    }


def _menu_records(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [r for r in h.records("menus") if isinstance(r, dict)]


def _command(h: DcsPluginHarness, path_prefix: str) -> tuple[Any, Any]:
    for record in _menu_records(h):
        if str(record.get("path", "")).startswith(path_prefix) and "fn" in record:
            return record["fn"], record.get("arg")
    raise AssertionError(f"menu command {path_prefix!r} not found")


def _state(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return h.to_python(h.lua.globals().cruise_missiles_state) or []


def test_auto_raid_fires_after_the_delay_with_the_cruise_flag() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("CVBG | Burke", int(h.side.BLUE)))
    h.lua.globals().dcsRetribution = h.to_lua(
        _config(
            ships=[{"group": "CVBG | Burke", "coalition": "blue", "remaining": "24"}],
            # Values arrive as strings from the emitter; the plugin tonumber()s.
            raids=[
                {
                    "group": "CVBG | Burke",
                    "coalition": "blue",
                    "target": "Division HQ",
                    "x": "60000.0",
                    "y": "1000.0",
                    "count": "4",
                }
            ],
            # A degenerate window (min == max) pins the launch moment.
            options={"raidDelayMinS": 30, "raidDelayMaxS": 30},
        )
    )
    h.load_plugin_script(PLUGIN)

    # Nothing launches before the window opens.
    h.advance_to(29)
    assert h.records("firedTasks") == []

    h.advance_to(31)
    tasks = h.records("firedTasks")
    assert len(tasks) == 1
    task = tasks[0]
    assert task["group"] == "CVBG | Burke"
    assert task["x"] == 60000.0 and task["y"] == 1000.0
    assert task["rounds"] == 4
    # The weapon flag is what makes a Tomahawk ship ripple missiles, not guns.
    assert task["weaponType"] == CRUISE_FLAG

    # Both sides are cued: missiles away for blue, a vague launch warning for red.
    texts = h.records("texts")
    assert any(
        t["side"] == int(h.side.BLUE) and "CRUISE MISSILES AWAY" in t["text"]
        for t in texts
    )
    assert any(
        t["side"] == int(h.side.RED) and "LAUNCH WARNING" in t["text"] for t in texts
    )

    # Expenditure mirrors into the debrief channel for the magazine debit.
    assert _state(h) == [{"group": "CVBG | Burke", "fired": 4}]
    assert h.lua.globals().dirty_state == True  # noqa: E712
    h.assert_no_lua_errors()


def test_raid_launches_stay_inside_the_window_and_legacy_option_opens_it() -> None:
    # Each raid schedules at its own random moment inside the launch window
    # (the SCUD-style stagger, so several groups never ripple simultaneously).
    # Randomness is bounded, not pinned: assert window compliance only.
    h = DcsPluginHarness()
    h.add_group(_ship_group("A Burke", int(h.side.BLUE)))
    h.add_group(_ship_group("B Burke", int(h.side.BLUE), x=5000.0))
    h.lua.globals().dcsRetribution = h.to_lua(
        _config(
            ships=[
                {"group": "A Burke", "coalition": "blue", "remaining": "24"},
                {"group": "B Burke", "coalition": "blue", "remaining": "24"},
            ],
            raids=[
                {
                    "group": "A Burke",
                    "coalition": "blue",
                    "target": "A",
                    "x": "1.0",
                    "y": "2.0",
                    "count": "2",
                },
                {
                    "group": "B Burke",
                    "coalition": "blue",
                    "target": "B",
                    "x": "3.0",
                    "y": "4.0",
                    "count": "2",
                },
            ],
            # The legacy raidDelayS option still opens the window;
            # raidDelayMaxS closes it.
            options={"raidDelayS": 20, "raidDelayMaxS": 40},
        )
    )
    h.load_plugin_script(PLUGIN)

    # Nothing may launch before the window opens...
    h.advance_to(19)
    assert h.records("firedTasks") == []

    # ...and every raid must have launched by the time it closes.
    h.advance_to(41)
    assert sorted(t["group"] for t in h.records("firedTasks")) == [
        "A Burke",
        "B Burke",
    ]
    h.assert_no_lua_errors()


def test_the_magazine_caps_the_salvo_and_a_dry_ship_never_fires() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("Low Burke", int(h.side.BLUE)))
    h.add_group(_ship_group("Dry Burke", int(h.side.BLUE), x=5000.0))
    h.lua.globals().dcsRetribution = h.to_lua(
        _config(
            ships=[
                {"group": "Low Burke", "coalition": "blue", "remaining": "2"},
                {"group": "Dry Burke", "coalition": "blue", "remaining": "0"},
            ],
            raids=[
                {
                    "group": "Low Burke",
                    "coalition": "blue",
                    "target": "A",
                    "x": "1.0",
                    "y": "2.0",
                    "count": "6",
                },
                {
                    "group": "Dry Burke",
                    "coalition": "blue",
                    "target": "B",
                    "x": "3.0",
                    "y": "4.0",
                    "count": "6",
                },
            ],
            options={"raidDelayMinS": 10, "raidDelayMaxS": 10},
        )
    )
    h.load_plugin_script(PLUGIN)
    h.advance_to(60)

    tasks = h.records("firedTasks")
    assert [(t["group"], t["rounds"]) for t in tasks] == [("Low Burke", 2)]
    assert _state(h) == [{"group": "Low Burke", "fired": 2}]
    h.assert_no_lua_errors()


def test_a_dead_ship_fires_nothing() -> None:
    h = DcsPluginHarness()
    # The launching group is never added -> GROUP:FindByName finds nothing.
    h.lua.globals().dcsRetribution = h.to_lua(
        _config(
            ships=[{"group": "Ghost Burke", "coalition": "blue", "remaining": "24"}],
            raids=[
                {
                    "group": "Ghost Burke",
                    "coalition": "blue",
                    "target": "A",
                    "x": "1.0",
                    "y": "2.0",
                    "count": "4",
                }
            ],
            options={"raidDelayMinS": 10, "raidDelayMaxS": 10},
        )
    )
    h.load_plugin_script(PLUGIN)
    h.advance_to(60)
    assert h.records("firedTasks") == []
    assert _state(h) == []
    h.assert_no_lua_errors()


def test_player_call_for_fire_hits_the_last_marker_and_spends_the_budget() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("CVBG | Burke", int(h.side.BLUE)))
    h.lua.globals().dcsRetribution = h.to_lua(
        _config(
            ships=[{"group": "CVBG | Burke", "coalition": "blue", "remaining": "5"}],
            options={"playerSalvoSize": 4},
        )
    )
    h.load_plugin_script(PLUGIN)

    # The blue coalition got the call-for-fire menu (red owns no ships).
    roots = [r for r in _menu_records(h) if r["path"] == "Cruise Missile Strike"]
    assert [r["side"] for r in roots] == [int(h.side.BLUE)]

    # No marker yet -> a nag, no launch.
    fire, side = _command(h, "Fire at last F10 map marker")
    fire(side)
    assert h.records("firedTasks") == []
    assert any("place an F10 map marker" in t["text"] for t in h.records("texts"))

    # Latest blue marker wins; the salvo fires at it with the cruise flag.
    h.harness.markPanels = h.to_lua(
        [
            {
                "idx": 1,
                "coalition": int(h.side.BLUE),
                "pos": {"x": 10.0, "y": 0, "z": 20.0},
            },
            {
                "idx": 2,
                "coalition": int(h.side.BLUE),
                "pos": {"x": 70000.0, "y": 0, "z": 8000.0},
            },
        ]
    )
    fire(side)
    tasks = h.records("firedTasks")
    assert len(tasks) == 1
    assert tasks[0]["x"] == 70000.0 and tasks[0]["y"] == 8000.0
    assert tasks[0]["rounds"] == 4
    assert tasks[0]["weaponType"] == CRUISE_FLAG

    # Second call: only 1 missile left -> the salvo shrinks to the budget.
    fire(side)
    tasks = h.records("firedTasks")
    assert [t["rounds"] for t in tasks] == [4, 1]
    assert _state(h) == [{"group": "CVBG | Burke", "fired": 5}]

    # Third call: magazine dry -> no further launch, a dry-magazine nag instead.
    fire(side)
    assert [t["rounds"] for t in h.records("firedTasks")] == [4, 1]
    assert any(
        "no ship with missiles in range" in t["text"] for t in h.records("texts")
    )
    h.assert_no_lua_errors()


def test_marker_text_number_sizes_the_salvo() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("CVBG | Burke", int(h.side.BLUE)))
    h.lua.globals().dcsRetribution = h.to_lua(
        _config(
            ships=[{"group": "CVBG | Burke", "coalition": "blue", "remaining": "24"}],
            options={"playerSalvoSize": 4},
        )
    )
    h.load_plugin_script(PLUGIN)
    fire, side = _command(h, "Fire at last F10 map marker")

    def mark(text: Any) -> None:
        h.harness.markPanels = h.to_lua(
            [
                {
                    "idx": 1,
                    "coalition": int(h.side.BLUE),
                    "pos": {"x": 100.0, "y": 0, "z": 200.0},
                    "text": text,
                }
            ]
        )

    # A bare number in the marker text orders exactly that salvo...
    mark("6")
    fire(side)
    # ...and the user's literal "#N and nothing else" form works too.
    mark(" #2 ")
    fire(side)
    # Any other text (a normal target label) falls back to the default salvo,
    # as do a bare "#", a zero, and a mixed label containing digits.
    mark("TGT Alpha bunker 3")
    fire(side)
    mark("#")
    fire(side)
    mark("0")
    fire(side)

    assert [t["rounds"] for t in h.records("firedTasks")] == [6, 2, 4, 4, 4]
    # A big ask never exceeds the magazine: 24 - (6+2+4+4+4) = 4 left.
    mark("#99")
    fire(side)
    assert [t["rounds"] for t in h.records("firedTasks")][-1] == 4
    assert _state(h) == [{"group": "CVBG | Burke", "fired": 24}]
    h.assert_no_lua_errors()


def test_magazine_status_reads_the_stock() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("CVBG | Burke", int(h.side.BLUE)))
    h.lua.globals().dcsRetribution = h.to_lua(
        _config(
            ships=[{"group": "CVBG | Burke", "coalition": "blue", "remaining": "7"}]
        )
    )
    h.load_plugin_script(PLUGIN)
    status, side = _command(h, "Magazine status")
    status(side)
    assert any(
        "Cruise missile magazines" in t["text"] and "7 missile(s)" in t["text"]
        for t in h.records("texts")
    )
    h.assert_no_lua_errors()


ALARM_STATE = 9
ALARM_AUTO = 0
ALARM_RED = 2


def _ad_group(
    name: str, side: int, x: float, z: float, ad: bool = True
) -> dict[str, Any]:
    return {
        "name": name,
        "side": side,
        "category": 2,  # GROUND
        "units": [
            {
                "name": name + "-1",
                "type": "Tor 9A331" if ad else "Ural-375",
                "x": x,
                "z": z,
                "attributes": {"Air Defence": True} if ad else {},
            }
        ],
    }


def _alarm_records(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [r for r in h.records("options") if r.get("option") == ALARM_STATE]


def test_launch_wakes_opposing_ad_near_the_aimpoint_then_stands_it_down() -> None:
    h = DcsPluginHarness()
    # Shooter at the origin; aimpoint 60 km north -> ~300 s flight at the assumed
    # 200 m/s, so the RED hold should lapse around 30 + 300 + 300 = 630 s.
    h.add_group(_ship_group("CVBG | Burke", int(h.side.BLUE)))
    # Red AD sitting on the target (the flown SLUG case), red AD far beyond the
    # wake radius, a red non-AD group on the target, and a BLUE AD near it —
    # only the first may wake.
    h.add_group(_ad_group("SLUG (SHORAD)", int(h.side.RED), 60500.0, 1200.0))
    h.add_group(_ad_group("FAR (SHORAD)", int(h.side.RED), 160000.0, 1000.0))
    h.add_group(_ad_group("ARMOR", int(h.side.RED), 60200.0, 900.0, ad=False))
    h.add_group(_ad_group("OWN (SHORAD)", int(h.side.BLUE), 60300.0, 800.0))
    h.lua.globals().dcsRetribution = h.to_lua(
        _config(
            ships=[{"group": "CVBG | Burke", "coalition": "blue", "remaining": "24"}],
            raids=[
                {
                    "group": "CVBG | Burke",
                    "coalition": "blue",
                    "target": "Division HQ",
                    "x": "60000.0",
                    "y": "1000.0",
                    "count": "6",
                }
            ],
            options={"raidDelayMinS": 30, "raidDelayMaxS": 30},
        )
    )
    h.load_plugin_script(PLUGIN)

    h.advance_to(31)
    assert len(h.records("firedTasks")) == 1
    # Only the near, opposing, AD-attributed group went RED.
    records = _alarm_records(h)
    assert [(r["group"], r["value"]) for r in records] == [("SLUG (SHORAD)", ALARM_RED)]

    # Long after the salvo has arrived, the group stands back down to AUTO.
    h.advance_to(700)
    records = _alarm_records(h)
    assert [(r["group"], r["value"]) for r in records] == [
        ("SLUG (SHORAD)", ALARM_RED),
        ("SLUG (SHORAD)", ALARM_AUTO),
    ]
    h.assert_no_lua_errors()


def test_call_for_fire_wakes_defenders_too_and_the_kill_switch_holds() -> None:
    # The wake hangs off the shared fire path, so the F10 marker call wakes the
    # defense identically — and defenderWake=false disables the whole sweep.
    for wake_enabled in (True, False):
        h = DcsPluginHarness()
        h.add_group(_ship_group("CVBG | Burke", int(h.side.BLUE)))
        h.add_group(_ad_group("PD (SHORAD)", int(h.side.RED), 70200.0, 8100.0))
        h.lua.globals().dcsRetribution = h.to_lua(
            _config(
                ships=[
                    {"group": "CVBG | Burke", "coalition": "blue", "remaining": "24"}
                ],
                options={"defenderWake": wake_enabled},
            )
        )
        h.load_plugin_script(PLUGIN)
        h.harness.markPanels = h.to_lua(
            [
                {
                    "idx": 1,
                    "coalition": int(h.side.BLUE),
                    "pos": {"x": 70000.0, "y": 0, "z": 8000.0},
                }
            ]
        )
        fire, side = _command(h, "Fire at last F10 map marker")
        fire(side)
        assert len(h.records("firedTasks")) == 1
        expected = [("PD (SHORAD)", ALARM_RED)] if wake_enabled else []
        assert [(r["group"], r["value"]) for r in _alarm_records(h)] == expected
        h.assert_no_lua_errors()


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}})
    h.load_plugin_script(PLUGIN)
    h.advance_to(600)
    assert h.records("firedTasks") == []
    assert _menu_records(h) == []
    h.assert_no_lua_errors()
