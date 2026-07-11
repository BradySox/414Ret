"""Headless runtime check for the briefing plugin (briefing-config.lua).

Pins the "script errors and the feature silently never starts" invariant plus the
behaviour contract: a pilot who slots in gets exactly one card (birth handler and
the mission-start sweep dedupe), the card carries the shared header + that flight's
own details and the group's id/duration, an AI birth or an unknown group is
ignored, and a mission with no briefing node is a clean no-op.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/briefing/briefing-config.lua"

_HEADER = {
    "campaign": "Red Tide",
    "mission": "1",
    "date": "Tuesday 12 June 1968",
    "time": "14:30L",
}
_FLIGHT = {
    "group": "Enfield 1-1",
    "callsign": "Enfield11",
    "aircraft": "F/A-18C",
    "task": "BARCAP",
    "airfield": "Kutaisi",
}


def _player_group(name: str, gid: int, player: bool = True) -> dict[str, Any]:
    return {
        "name": name,
        "id": gid,
        "side": 2,  # BLUE
        "category": 0,  # AIRPLANE
        "units": [
            {
                "name": name + "-1",
                "type": "FA-18C_hornet",
                "playerName": "Maverick" if player else None,
            }
        ],
    }


def _briefing_config(**plugin_opts: Any) -> dict[str, Any]:
    return {
        "plugins": {"briefing": plugin_opts or {"durationS": 12, "startGraceS": 2}},
        "briefing": {"header": _HEADER, "flights": [_FLIGHT]},
    }


def test_birth_shows_one_card_with_all_fields() -> None:
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    h.lua.globals().dcsRetribution = h.to_lua(_briefing_config())
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    # Run past the grace so the mission-start sweep also runs; the debounce must keep
    # it from double-showing the same slotting.
    h.advance_to(5)

    texts = h.records("texts")
    assert len(texts) == 1
    card = texts[0]
    assert card["groupId"] == 42
    assert card["duration"] == 12
    for expected in (
        "Red Tide",
        "Mission 1",
        "Enfield11",
        "F/A-18C",
        "BARCAP",
        "Kutaisi",
    ):
        assert expected in card["text"], (expected, card["text"])
    h.assert_no_lua_errors()


def test_mission_start_sweep_catches_seated_player_without_a_birth() -> None:
    # Models single-player: the pilot's birth fired before the handler registered, so
    # only the post-grace sweep can catch them.
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    h.lua.globals().dcsRetribution = h.to_lua(_briefing_config())
    h.load_plugin_script(PLUGIN)

    h.advance_to(1)
    assert h.records("texts") == []  # nothing during the grace
    h.advance_to(5)
    assert len(h.records("texts")) == 1
    h.assert_no_lua_errors()


def test_ai_birth_shows_nothing() -> None:
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42, player=False))
    h.lua.globals().dcsRetribution = h.to_lua(_briefing_config())
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    h.advance_to(5)
    assert h.records("texts") == []
    h.assert_no_lua_errors()


def test_unknown_group_shows_nothing() -> None:
    h = DcsPluginHarness()
    # A player group the briefing knows nothing about.
    h.add_group(_player_group("Ghost 1-1", 7))
    h.lua.globals().dcsRetribution = h.to_lua(_briefing_config())
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Ghost 1-1")
    h.advance_to(5)
    assert h.records("texts") == []
    h.assert_no_lua_errors()


def test_no_node_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}})
    h.load_plugin_script(PLUGIN)
    h.fire_birth("Enfield 1-1")
    h.advance_to(5)
    assert h.records("texts") == []
    h.assert_no_lua_errors()
