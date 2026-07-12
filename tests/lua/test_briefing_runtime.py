"""Headless runtime check for the briefing plugin (briefing-config.lua).

Pins the "script errors and the feature silently never starts" invariant plus the
behaviour contract: a pilot who slots in gets a briefing card after the slot-in
delay, then a taxi card DURATION s later, each with a beep (mutable), keyed to the
group id; the birth handler and the mission-start sweep dedupe to one sequence; an
AI birth or an unknown group is ignored; and a mission with no briefing node is a
clean no-op.
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


def test_briefing_card_shows_after_the_slot_in_delay() -> None:
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    # startGraceS high so only the birth path fires; startDelayS=5 is the delay under test.
    h.lua.globals().dcsRetribution = h.to_lua(
        _briefing_config(durationS=12, startGraceS=99, startDelayS=5)
    )
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    h.advance_to(4)  # still inside the 5 s slot-in delay -> nothing yet
    assert h.records("texts") == []
    h.advance_to(6)  # past the delay -> the briefing card is up

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


def test_birth_and_sweep_do_not_double_show() -> None:
    # Birth (t=0) and the mission-start sweep (t=grace) both target the same slotting;
    # the debounce must keep it to a single card sequence, not two.
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    h.lua.globals().dcsRetribution = h.to_lua(
        _briefing_config(durationS=12, startGraceS=2, startDelayS=1)
    )
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    h.advance_to(5)  # birth's card at t=1; the sweep at t=2 is debounced
    assert len(h.records("texts")) == 1  # exactly one briefing card
    h.assert_no_lua_errors()


def test_taxi_card_flashes_after_the_briefing_card() -> None:
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    # Short delay + duration so the sequence (card at t=1, taxi at t=1+3=4) runs quickly.
    h.lua.globals().dcsRetribution = h.to_lua(
        _briefing_config(durationS=3, startGraceS=99, startDelayS=1)
    )
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    h.advance_to(2)  # only the briefing card so far (t=1)
    assert len(h.records("texts")) == 1
    h.advance_to(5)  # taxi card (t=4) has flashed

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
        _briefing_config(durationS=3, startGraceS=99, startDelayS=1)
    )
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    h.advance_to(2)  # briefing card + its beep (t=1)
    assert len(h.records("sounds")) == 1
    h.advance_to(5)  # taxi card + its beep (t=4)

    sounds = h.records("sounds")
    assert len(sounds) == 2  # one beep per card
    assert all(s["groupId"] == 42 for s in sounds)
    # The archive path matters: DCS resolves an in-miz sound ONLY via its l10n/DEFAULT/
    # path -- the bare basename fails silently (the flown Red Tide M1 dead-beep bug).
    assert all(s["file"] == "l10n/DEFAULT/briefing-beep.wav" for s in sounds)
    h.assert_no_lua_errors()


def test_beep_can_be_disabled() -> None:
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    h.lua.globals().dcsRetribution = h.to_lua(
        _briefing_config(durationS=3, startGraceS=99, startDelayS=1, playSound=False)
    )
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    h.advance_to(5)
    assert len(h.records("texts")) == 2  # both cards still show
    assert h.records("sounds") == []  # but no beep
    h.assert_no_lua_errors()


def test_ground_freq_option_overrides_the_taxi_freq() -> None:
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    h.lua.globals().dcsRetribution = h.to_lua(
        _briefing_config(
            durationS=3, startGraceS=99, startDelayS=1, groundFreq="305.00"
        )
    )
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    h.advance_to(5)
    taxi = h.records("texts")[1]
    assert "Contact ground @ 305.00 when ready to taxi" in taxi["text"]
    assert "249.50" not in taxi["text"]
    h.assert_no_lua_errors()


def test_mission_start_sweep_catches_seated_player_without_a_birth() -> None:
    # Models single-player: the pilot's birth fired before the handler registered, so
    # only the post-grace sweep can catch them. The card = grace (t=2) + slot-in delay (1).
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    h.lua.globals().dcsRetribution = h.to_lua(
        _briefing_config(durationS=12, startGraceS=2, startDelayS=1)
    )
    h.load_plugin_script(PLUGIN)

    h.advance_to(1)  # before the sweep grace (t=2)
    assert h.records("texts") == []
    h.advance_to(4)  # sweep at t=2 -> card at t=3
    assert len(h.records("texts")) == 1
    h.assert_no_lua_errors()


def test_ai_birth_shows_nothing() -> None:
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42, player=False))
    h.lua.globals().dcsRetribution = h.to_lua(_briefing_config())
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    h.advance_to(15)  # past the nil-player re-check (+2 s) and any card delay
    assert h.records("texts") == []
    h.assert_no_lua_errors()


def test_card_and_taxi_fires_are_logged() -> None:
    # The M1 no-show hunt found zero per-card logging -- dcs.log could not tell "card
    # sent but unseen" from "card never sent". Each fire must now leave a log line.
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    h.lua.globals().dcsRetribution = h.to_lua(
        _briefing_config(durationS=3, startGraceS=99, startDelayS=1)
    )
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    h.advance_to(5)  # card at t=1, taxi at t=4
    infos = h.records("infos")
    assert any("BRIEFING|: card -> Enfield 1-1 gid=42" in i for i in infos), infos
    assert any("BRIEFING|: taxi -> Enfield 1-1 gid=42" in i for i in infos), infos
    h.assert_no_lua_errors()


def test_skipped_fire_clears_the_debounce() -> None:
    # A pilot who leaves the seat before the card fires never saw it: the skipped fire
    # must clear the debounce stamp so their next slot-in still gets the card.
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42))
    h.lua.globals().dcsRetribution = h.to_lua(
        _briefing_config(durationS=12, startGraceS=99, startDelayS=1)
    )
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")  # card scheduled for t=1
    h.lua.execute('DcsHarness.groupsByName["Enfield 1-1"] = nil')  # pilot leaves
    h.advance_to(2)  # fire skipped (group gone), stamp cleared
    assert h.records("texts") == []

    h.add_group(_player_group("Enfield 1-1", 42))  # re-slot, well inside DEBOUNCE
    h.fire_birth("Enfield 1-1")
    h.advance_to(4)  # the re-slot's card (t=3) must not be debounced away
    assert len(h.records("texts")) == 1
    h.assert_no_lua_errors()


def test_nil_player_at_birth_is_rechecked() -> None:
    # Documented DCS event-timing race (MOOSE #806): getPlayerName can be nil at the
    # BIRTH instant for a genuine human slot-in. A nil in a briefing-listed group gets
    # one +2 s re-check instead of being written off as AI.
    h = DcsPluginHarness()
    h.add_group(_player_group("Enfield 1-1", 42, player=False))  # name not yet bound
    h.lua.globals().dcsRetribution = h.to_lua(
        _briefing_config(durationS=12, startGraceS=99, startDelayS=1)
    )
    h.load_plugin_script(PLUGIN)

    h.fire_birth("Enfield 1-1")
    # The player name binds moments after the event (the race resolving).
    h.lua.execute(
        'DcsHarness.groupsByName["Enfield 1-1"]:getUnit(1).playerName = "Maverick"'
    )
    h.advance_to(1.5)  # before the +2 s re-check -> nothing yet
    assert h.records("texts") == []
    h.advance_to(4)  # re-check at t=2 -> card at t=3
    assert len(h.records("texts")) == 1
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
