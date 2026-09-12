"""Headless runtime check for the King's on-scene systems (KingOnScene.lua).

Pins the contract of §100: the menu exists only for a player-flown King; a fix
comes from DF cuts (one cut is a bearing, two cuts far enough apart are a fix,
inside pod range with line of sight the fix snaps exact); the threat sweep runs
around the fix and reports a class and a rough position, closest first, capped;
the picture goes to player-crewed rescue flights only and never pushes a task
onto anyone. The harness models no terrain, so line of sight is a switch.
"""

from __future__ import annotations

import math
from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/opscsar/KingOnScene.lua"

BLUE = 2
RED = 1
AIRPLANE = 0
GROUND = 2
NM = 1852.0

KING_GID = 42
SANDY_GID = 43
JOLLY_GID = 44
SURVIVOR = (20 * NM, 0.0)  # 20 nm north of the origin


def _aircraft(
    name: str, gid: int, x: float, z: float, player: str | None, side: int = BLUE
) -> dict[str, Any]:
    return {
        "name": name,
        "id": gid,
        "side": side,
        "category": AIRPLANE,
        "units": [
            {
                "name": name + "-1",
                "type": "C-130J-30",
                "x": x,
                "z": z,
                "alt": 6000,
                "airborne": True,
                "playerName": player,
            }
        ],
    }


def _survivor(name: str = "Ivan Doe") -> dict[str, Any]:
    return {
        "name": "CSAR " + name,
        "id": 900,
        "side": BLUE,
        "category": GROUND,
        "units": [
            {
                "name": "CSAR " + name + " Unit #1",
                "type": "Soldier M4",
                "x": SURVIVOR[0],
                "z": SURVIVOR[1],
            }
        ],
    }


def _ground(
    name: str, dx: float, dz: float, attribute: str | None, side: int = RED
) -> dict[str, Any]:
    unit: dict[str, Any] = {
        "name": name + "-1",
        "type": "T-72B",
        "x": SURVIVOR[0] + dx,
        "z": SURVIVOR[1] + dz,
    }
    if attribute:
        unit["attributes"] = {attribute: True}
    return {"name": name, "side": side, "category": GROUND, "units": [unit]}


def _config(
    h: DcsPluginHarness,
    flights: list[dict[str, Any]] | None,
    survivor_id: str = "pilot-1",
) -> None:
    cfg: dict[str, Any] = {
        "plugins": {},
        "CSAR": {
            "beaconHz": "260000",
            "downedPilots": [
                {
                    "id": survivor_id,
                    "x": str(SURVIVOR[0]),
                    "z": str(SURVIVOR[1]),
                    "coalition": "blue",
                    "description": "Ivan Doe",
                    "aircraft": "F/A-18C",
                    "groupName": "CSAR Ivan Doe",
                    "unitName": "CSAR Ivan Doe Unit #1",
                }
            ],
        },
    }
    if flights is not None:
        cfg["CSAR"]["rescueFlights"] = flights
    h.lua.globals().dcsRetribution = h.to_lua(cfg)


def _king(player: bool = True, survivor_id: str = "pilot-1") -> dict[str, Any]:
    return {
        "groupName": "King 1",
        "role": "king",
        "side": "blue",
        "player": "true" if player else "false",
        "survivorId": survivor_id,
    }


def _rescue(group: str, role: str, side: str = "blue") -> dict[str, Any]:
    return {
        "groupName": group,
        "role": role,
        "side": side,
        "player": "true",
        "survivorId": "pilot-1",
    }


def _menu_records(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [r for r in h.records("menus") if isinstance(r, dict)]


def _command(h: DcsPluginHarness, path: str, gid: int = KING_GID) -> Any:
    for record in _menu_records(h):
        if record.get("path") == path and record.get("gid") == gid:
            return record["fn"]
    raise AssertionError(f"menu command {path!r} (gid={gid}) not found")


def _texts_for(h: DcsPluginHarness, gid: int) -> list[str]:
    return [t["text"] for t in h.records("texts") if t.get("groupId") == gid]


def _marks_for(h: DcsPluginHarness, gid: int) -> list[dict[str, Any]]:
    return [m for m in h.records("marks") if m.get("groupId") == gid]


def _live_marks_for(h: DcsPluginHarness, gid: int) -> list[dict[str, Any]]:
    removed = set(h.records("removedMarks"))
    return [m for m in _marks_for(h, gid) if m["id"] not in removed]


def _distance(m: dict[str, Any], point: tuple[float, float]) -> float:
    return math.hypot(m["x"] - point[0], m["z"] - point[1])


def _boot(
    h: DcsPluginHarness,
    king_at: tuple[float, float] = (0.0, 0.0),
    extra_flights: list[dict[str, Any]] | None = None,
    player: bool = True,
) -> None:
    _config(h, [_king(player)] + (extra_flights or []))
    h.add_group(
        _aircraft(
            "King 1", KING_GID, king_at[0], king_at[1], "Brady" if player else None
        )
    )
    h.add_group(_survivor())
    h.load_plugin_script(PLUGIN)
    h.advance_to(30)


def _move_king(h: DcsPluginHarness, x: float, z: float) -> None:
    h.update_unit("King 1", {"x": x, "z": z})


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_no_rescue_flights_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    _config(h, flights=None)
    h.add_group(_aircraft("King 1", KING_GID, 0, 0, "Brady"))
    h.load_plugin_script(PLUGIN)
    h.advance_to(60)
    assert _menu_records(h) == []
    h.assert_no_lua_errors()


def test_an_ai_king_gets_no_menu() -> None:
    h = DcsPluginHarness()
    _boot(h, player=False)
    h.advance_to(60)
    assert _menu_records(h) == []
    h.assert_no_lua_errors()


def test_a_player_king_gets_the_on_scene_menu_and_the_survivor() -> None:
    h = DcsPluginHarness()
    _boot(h)
    paths = {r["path"] for r in _menu_records(h) if r.get("gid") == KING_GID}
    assert {
        "KING | On-Scene Commander",
        "Survivor status",
        "Take DF cut on the beacon",
        "Threat sweep around the fix",
        "Pass picture to",
        "Clear my marks",
    } <= paths
    welcome = _texts_for(h, KING_GID)[0]
    assert "Ivan Doe" in welcome and "260 kHz" in welcome
    h.assert_no_lua_errors()


# ---------------------------------------------------------------------------
# The fix
# ---------------------------------------------------------------------------


def test_one_cut_is_a_bearing_not_a_fix() -> None:
    h = DcsPluginHarness()
    _boot(h)
    _command(h, "Take DF cut on the beacon")()
    text = _texts_for(h, KING_GID)[-1]
    assert "DF cut 1" in text and "another cut" in text
    assert _marks_for(h, KING_GID) == []
    _command(h, "Survivor status")()
    assert "no fix" in _texts_for(h, KING_GID)[-1]
    h.assert_no_lua_errors()


def test_two_cuts_far_enough_apart_make_a_fix_near_the_survivor() -> None:
    h = DcsPluginHarness()
    _boot(h)  # 20 nm south of the survivor
    _command(h, "Take DF cut on the beacon")()
    _move_king(h, SURVIVOR[0], 20 * NM)  # 20 nm east: a 90 degree cut
    _command(h, "Take DF cut on the beacon")()
    text = _texts_for(h, KING_GID)[-1]
    assert "DF cut 2" in text and "Fix on Ivan Doe" in text and "+/-" in text
    marks = _live_marks_for(h, KING_GID)
    assert len(marks) == 1 and marks[0]["text"].startswith("SURVIVOR Ivan Doe (est.")
    # The mark is the noisy intersection, not the pilot: within the DF error
    # budget of the true position, and not sitting exactly on it.
    assert _distance(marks[0], SURVIVOR) < 4000
    assert "exact" not in marks[0]["text"]
    h.assert_no_lua_errors()


def test_cuts_too_close_together_do_not_make_a_fix() -> None:
    h = DcsPluginHarness()
    _boot(h)
    _command(h, "Take DF cut on the beacon")()
    _move_king(h, 0, 1 * NM)  # barely moved: cuts a few degrees apart
    _command(h, "Take DF cut on the beacon")()
    assert "another cut" in _texts_for(h, KING_GID)[-1]
    assert _marks_for(h, KING_GID) == []
    h.assert_no_lua_errors()


def test_inside_pod_range_with_line_of_sight_the_fix_snaps_exact() -> None:
    h = DcsPluginHarness()
    _boot(h, king_at=(SURVIVOR[0] - 10 * NM, 0))
    _command(h, "Take DF cut on the beacon")()
    assert "Pod contact" in _texts_for(h, KING_GID)[-1]
    marks = _live_marks_for(h, KING_GID)
    assert len(marks) == 1 and "pod contact" in marks[0]["text"]
    assert _distance(marks[0], SURVIVOR) < 1
    h.assert_no_lua_errors()


def test_no_line_of_sight_means_a_df_cut_not_a_pod_contact() -> None:
    h = DcsPluginHarness()
    _boot(h, king_at=(SURVIVOR[0] - 10 * NM, 0))
    h.harness.losBlocked = True
    _command(h, "Take DF cut on the beacon")()
    text = _texts_for(h, KING_GID)[-1]
    assert "DF cut 1" in text and "Pod contact" not in text
    h.assert_no_lua_errors()


def test_beyond_beacon_range_there_is_nothing_to_cut() -> None:
    h = DcsPluginHarness()
    _boot(h, king_at=(-100 * NM, 0))
    _command(h, "Take DF cut on the beacon")()
    assert "Beacon not received" in _texts_for(h, KING_GID)[-1]
    h.assert_no_lua_errors()


# ---------------------------------------------------------------------------
# The threat sweep
# ---------------------------------------------------------------------------


def _snapped(h: DcsPluginHarness) -> None:
    _move_king(h, SURVIVOR[0] - 10 * NM, 0)
    _command(h, "Take DF cut on the beacon")()
    assert "Pod contact" in _texts_for(h, KING_GID)[-1]


def test_the_sweep_needs_a_fix_first() -> None:
    h = DcsPluginHarness()
    _boot(h)
    h.add_group(_ground("SAM", 3000, 0, "SAM TR"))
    _command(h, "Threat sweep around the fix")()
    assert "No fix yet" in _texts_for(h, KING_GID)[-1]
    assert not any("T1" in m["text"] for m in _marks_for(h, KING_GID))
    h.assert_no_lua_errors()


def test_the_sweep_reports_class_and_rough_position_closest_first() -> None:
    h = DcsPluginHarness()
    _boot(h)
    h.add_group(_ground("Armour", 1000, 1000, "Tanks"))
    h.add_group(_ground("SAM", 3000, 0, "SAM TR"))
    h.add_group(_ground("AAA", 0, 6000, "AAA"))
    h.add_group(_ground("Far", 30000, 0, "SAM TR"))  # outside the 8 nm sweep
    h.add_group(_ground("Friendly", 500, 0, "Tanks", side=BLUE))  # our own
    _snapped(h)
    _command(h, "Threat sweep around the fix")()
    text = _texts_for(h, KING_GID)[-1]
    lines = [ln for ln in text.split("\n") if ln.startswith("T")]
    assert [ln.split()[0:2] for ln in lines] == [
        ["T1", "ARMOUR"],
        ["T2", "SAM"],
        ["T3", "AAA"],
    ]
    # Never a unit type, and never an exact point: each mark sits within the
    # jitter of the unit it stands for, not on it.
    assert "T-72" not in text and "SNR" not in text
    threat_marks = [
        m for m in _live_marks_for(h, KING_GID) if m["text"].startswith("T")
    ]
    assert len(threat_marks) == 3
    sam = next(m for m in threat_marks if "SAM" in m["text"])
    assert 0 < _distance(sam, (SURVIVOR[0] + 3000, SURVIVOR[1])) <= 460
    h.assert_no_lua_errors()


def test_the_sweep_is_capped_at_the_closest_five() -> None:
    h = DcsPluginHarness()
    _boot(h)
    for i in range(7):
        h.add_group(_ground(f"AAA{i}", 1000 * (i + 1), 0, "AAA"))
    _snapped(h)
    _command(h, "Threat sweep around the fix")()
    text = _texts_for(h, KING_GID)[-1]
    assert text.count("\nT") == 5 and "2 more" in text
    h.assert_no_lua_errors()


# ---------------------------------------------------------------------------
# Passing the picture
# ---------------------------------------------------------------------------


def test_the_picture_goes_to_player_rescue_flights_only() -> None:
    h = DcsPluginHarness()
    _boot(
        h,
        extra_flights=[
            _rescue("Sandy 1", "sandy"),
            _rescue("Jolly 1", "jolly"),
            _rescue("Sandy 2", "sandy"),  # AI-crewed at runtime
            _rescue("Enemy Sandy", "sandy", side="red"),
        ],
    )
    h.add_group(_aircraft("Sandy 1", SANDY_GID, 0, 0, "Wingman"))
    h.add_group(_aircraft("Jolly 1", JOLLY_GID, 0, 0, "Hoist"))
    h.add_group(_aircraft("Sandy 2", 45, 0, 0, None))
    h.add_group(_aircraft("Enemy Sandy", 46, 0, 0, "Ivan", side=RED))
    h.add_group(_ground("SAM", 3000, 0, "SAM TR"))
    h.advance_to(60)  # a tick rebuilds the pass menu with the live groups
    paths = {r["path"] for r in _menu_records(h) if r.get("gid") == KING_GID}
    assert {"SANDY Sandy 1", "JOLLY Jolly 1", "All rescue flights"} <= paths
    assert "SANDY Sandy 2" not in paths and "SANDY Enemy Sandy" not in paths

    _snapped(h)
    _command(h, "Threat sweep around the fix")()
    _command(h, "SANDY Sandy 1")()
    brief = _texts_for(h, SANDY_GID)[-1]
    assert "KING picture for Ivan Doe" in brief and "T1 SAM" in brief
    sandy_marks = _live_marks_for(h, SANDY_GID)
    assert any(m["text"].startswith("SURVIVOR") for m in sandy_marks)
    assert any(m["text"].startswith("T1 SAM") for m in sandy_marks)
    assert _texts_for(h, JOLLY_GID) == []  # only the flight that was picked

    _command(h, "All rescue flights")()
    assert _texts_for(h, JOLLY_GID)
    # Cueing only: nothing was pushed onto any flight's controller.
    assert h.records("controllerTasks") == []
    h.assert_no_lua_errors()
