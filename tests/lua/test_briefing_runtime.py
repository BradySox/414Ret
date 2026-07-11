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
    # it from double-showing the same slotting. t=5 is before the taxi card (which
    # flashes at t=DURATION=12), so only the briefing card is up.
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


def test_taxi_card_flashes_after_the_briefing_card() -> None:
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    # Short duration so the taxi card (scheduled at t=DURATION) fires quickly.
    h.lua.globals().dcsRetribution = h.to_lua(
        _briefing_config(durationS=3, startGraceS=99)
    )
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    h.advance_to(2)  # only the briefing card so far
    assert len(h.records("texts")) == 1
    h.advance_to(4)  # past DURATION=3 -> the taxi card has flashed

    texts = h.records("texts")
    assert len(texts) == 2
    briefing, taxi = texts[0], texts[1]
    assert "Callsign:" in briefing["text"]  # first card is the briefing
    # The second card: addressed to the callsign, the taxi instruction + the freq.
    assert taxi["groupId"] == 42
    assert taxi["duration"] == 3
    assert "Enfield11" in taxi["text"]
    assert "Contact ground @ 249.50 when ready to taxi" in taxi["text"]
    assert "Callsign:" not in taxi["text"]  # it's the taxi card, not the briefing
    h.assert_no_lua_errors()


def test_beep_plays_with_each_card() -> None:
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    h.lua.globals().dcsRetribution = h.to_lua(
        _briefing_config(durationS=3, startGraceS=99)
    )
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    h.advance_to(1)  # briefing card + its beep
    assert len(h.records("sounds")) == 1
    h.advance_to(4)  # taxi card + its beep

    sounds = h.records("sounds")
    assert len(sounds) == 2  # one beep per card
    assert all(s["groupId"] == 42 for s in sounds)
    assert all(s["file"] == "briefing-beep.wav" for s in sounds)
    h.assert_no_lua_errors()


def test_beep_can_be_disabled() -> None:
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    h.lua.globals().dcsRetribution = h.to_lua(
        _briefing_config(durationS=3, startGraceS=99, playSound=False)
    )
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    h.advance_to(4)
    assert len(h.records("texts")) == 2  # both cards still show
    assert h.records("sounds") == []  # but no beep
    h.assert_no_lua_errors()


def test_ground_freq_option_overrides_the_taxi_freq() -> None:
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    h.lua.globals().dcsRetribution = h.to_lua(
        _briefing_config(durationS=3, startGraceS=99, groundFreq="305.00")
    )
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    h.advance_to(4)
    taxi = h.records("texts")[1]
    assert "Contact ground @ 305.00 when ready to taxi" in taxi["text"]
    assert "249.50" not in taxi["text"]
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
