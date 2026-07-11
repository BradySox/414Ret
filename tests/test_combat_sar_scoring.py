"""Combat SAR rescue scoring + King-beacon (TACAN-only) regression tests.

The ``combatsar`` Lua bridge appends the ejected aircraft's original unit name to
the state-file global ``combat_sar_rescues`` when a downed pilot is delivered
home. ``StateData`` parses that list and ``MissionResultsProcessor`` spares the
matching pilot in ``commit_air_losses`` -- the airframe is still attrited, but the
aviator returns to the squadron. These cover both halves without a running DCS
mission, plus the guard that the King beacon is TACAN-only (no ADF freq).
"""

from __future__ import annotations

import dataclasses
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

from game.debriefing import StateData
from game.missiongenerator.aircraft.flightdata import CombatSarKingBeacon
from game.sim.missionresultsprocessor import MissionResultsProcessor


def _no_flight_unit_map() -> Any:
    # StateData.from_json only touches unit_map.flight() while classifying killed
    # units; rescue parsing does not need it.
    return cast(Any, SimpleNamespace(flight=lambda _: None))


def test_parse_rescues_keeps_unit_name_strings() -> None:
    state = StateData.from_json(
        {"combat_sar_rescues": ["Enfield 1-1 | F-14B", "Pontiac 2-2 | F-16C"]},
        _no_flight_unit_map(),
    )
    assert state.combat_sar_rescues == ["Enfield 1-1 | F-14B", "Pontiac 2-2 | F-16C"]


def test_parse_rescues_tolerates_empty_and_malformed() -> None:
    # Lua serializes an empty table as []; missing key, [], and non-string junk
    # all collapse to an empty list rather than crashing debrief parsing.
    assert StateData.from_json({}, _no_flight_unit_map()).combat_sar_rescues == []
    assert (
        StateData.from_json(
            {"combat_sar_rescues": []}, _no_flight_unit_map()
        ).combat_sar_rescues
        == []
    )
    state = StateData.from_json(
        {"combat_sar_rescues": ["Pilot A", "", 7, {"unit": "x"}, None]},
        _no_flight_unit_map(),
    )
    assert state.combat_sar_rescues == ["Pilot A"]


def _loss(player: bool) -> Any:
    squadron = SimpleNamespace(owned_aircraft=4, destroyed_aircraft=0)
    return SimpleNamespace(
        pilot=MagicMock(player=player),
        flight=SimpleNamespace(squadron=squadron, unit_type="A/C"),
    )


def _debriefing(
    losses: list[Any], rescues: list[str], flight_map: dict[str, Any]
) -> Any:
    return cast(
        Any,
        SimpleNamespace(
            air_losses=SimpleNamespace(losses=losses),
            state_data=SimpleNamespace(combat_sar_rescues=rescues),
            unit_map=SimpleNamespace(flight=lambda name: flight_map.get(name)),
        ),
    )


def test_rescued_pilot_is_spared_but_airframe_still_lost() -> None:
    rescued = _loss(player=True)
    killed = _loss(player=False)
    debriefing = _debriefing(
        losses=[rescued, killed],
        rescues=["rescued_unit"],
        # The original unit name resolves through the unit map to the very loss
        # object in air_losses, so identity matching spares exactly that pilot.
        flight_map={"rescued_unit": rescued},
    )
    game = SimpleNamespace(settings=SimpleNamespace(invulnerable_player_pilots=False))
    processor = MissionResultsProcessor(cast(Any, game))

    processor.commit_air_losses(debriefing)

    # The rescued aviator is spared; the un-rescued one dies.
    rescued.pilot.kill.assert_not_called()
    killed.pilot.kill.assert_called_once()
    # Both airframes are still attrited -- a rescue saves the pilot, not the jet.
    assert rescued.flight.squadron.owned_aircraft == 3
    assert killed.flight.squadron.owned_aircraft == 3
    assert rescued.flight.squadron.destroyed_aircraft == 1


def test_no_rescues_kills_every_pilot() -> None:
    a = _loss(player=False)
    b = _loss(player=False)
    debriefing = _debriefing(losses=[a, b], rescues=[], flight_map={})
    game = SimpleNamespace(settings=SimpleNamespace(invulnerable_player_pilots=False))

    MissionResultsProcessor(cast(Any, game)).commit_air_losses(debriefing)

    a.pilot.kill.assert_called_once()
    b.pilot.kill.assert_called_once()


# --- Enemy capture -> POW, routed to the survivor's coalition (ledger rework) --------


def test_parse_captures_threads_coalition_and_defaults_blue() -> None:
    # The ledger appends {unit, x, y, coalition}; parsing yields 4-tuples and a
    # record that omits coalition (pre-rework) defaults to "blue" (old behaviour).
    state = StateData.from_json(
        {
            "combat_sar_captures": [
                {"unit": "Red 1-1 | MiG-21", "x": 1.0, "y": 2.0, "coalition": "red"},
                {"unit": "Enfield 1-1 | F-14B", "x": 3.0, "y": 4.0},
                {"unit": "bad-no-coords"},
                {"unit": "junk-coalition", "x": 5.0, "y": 6.0, "coalition": "purple"},
            ]
        },
        _no_flight_unit_map(),
    )
    assert state.combat_sar_captures == [
        ("Red 1-1 | MiG-21", 1.0, 2.0, "red"),
        ("Enfield 1-1 | F-14B", 3.0, 4.0, "blue"),
        ("junk-coalition", 5.0, 6.0, "blue"),
    ]


def _capture_debriefing(captures: list[Any], rescues: list[str]) -> Any:
    return cast(
        Any,
        SimpleNamespace(
            state_data=SimpleNamespace(
                combat_sar_captures=captures, combat_sar_rescues=rescues
            ),
            unit_map=SimpleNamespace(flight=lambda _name: None),
        ),
    )


def test_record_pow_captures_routes_to_survivors_coalition() -> None:
    # A captured BLUE pilot -> a blue POW recovery; a captured RED pilot -> a red one.
    # The holding-airfield resolve runs at record time; with no control points it
    # degrades to an unresolved holding (the POW just runs the hold clock).
    game = SimpleNamespace(
        blue=SimpleNamespace(pending_pow_recoveries=[]),
        red=SimpleNamespace(pending_pow_recoveries=[]),
        theater=SimpleNamespace(controlpoints=[]),
        point_in_world=lambda x, y: SimpleNamespace(x=x, y=y),
        turn=1,  # stamped onto each PendingPowRecovery.captured_turn
    )
    processor = MissionResultsProcessor(cast(Any, game))
    debriefing = _capture_debriefing(
        captures=[
            ("Blue 1-1 | F-16C", 10.0, 20.0, "blue"),
            ("Red 2-2 | MiG-21", 30.0, 40.0, "red"),
        ],
        rescues=[],
    )

    processor.record_pow_captures(debriefing)

    assert [p.airframe_unit_name for p in game.blue.pending_pow_recoveries] == [
        "Blue 1-1 | F-16C"
    ]
    assert [p.airframe_unit_name for p in game.red.pending_pow_recoveries] == [
        "Red 2-2 | MiG-21"
    ]


# --- Persistent evaders: unresolved survivors go MIA instead of dying (2026-07-10) --


def test_parse_survivors_pulls_unit_and_position() -> None:
    state = StateData.from_json(
        {
            "combat_sar_survivors": [
                {
                    "unit": "Enfield 1-1 | F-14B",
                    "x": 1.0,
                    "y": 2.0,
                    "coalition": "blue",
                },
                {"unit": "bad-no-coords"},
                {"x": 3.0, "y": 4.0},
                "junk",
            ]
        },
        _no_flight_unit_map(),
    )
    assert state.combat_sar_survivors == [("Enfield 1-1 | F-14B", 1.0, 2.0)]


def test_parse_survivors_tolerates_missing_key() -> None:
    # Pre-feature state files omit the key entirely.
    assert StateData.from_json({}, _no_flight_unit_map()).combat_sar_survivors == []


def _mia_debriefing(
    losses: list[Any], survivors: list[Any], flight_map: dict[str, Any]
) -> Any:
    return cast(
        Any,
        SimpleNamespace(
            air_losses=SimpleNamespace(losses=losses),
            state_data=SimpleNamespace(
                combat_sar_rescues=[],
                combat_sar_captures=[],
                combat_sar_survivors=survivors,
                minefields_state=[],
            ),
            unit_map=SimpleNamespace(flight=lambda name: flight_map.get(name)),
        ),
    )


def test_evading_pilot_is_spared_when_persistence_is_on() -> None:
    evading = _loss(player=False)
    killed = _loss(player=False)
    debriefing = _mia_debriefing(
        losses=[evading, killed],
        survivors=[("evading_unit", 1.0, 2.0)],
        flight_map={"evading_unit": evading},
    )
    game = SimpleNamespace(
        settings=SimpleNamespace(
            invulnerable_player_pilots=False, combat_sar_persistent_pilots=True
        )
    )

    MissionResultsProcessor(cast(Any, game)).commit_air_losses(debriefing)

    # The evader is spared the kill (record_downed_pilots marks them MIA after);
    # the airframe is still attrited. The un-listed pilot dies as normal.
    evading.pilot.kill.assert_not_called()
    killed.pilot.kill.assert_called_once()
    assert evading.flight.squadron.owned_aircraft == 3


def test_evading_pilot_dies_when_persistence_is_off() -> None:
    # The pre-feature behaviour is the toggle-off contract: an un-rescued,
    # un-captured pilot is lost at debrief.
    evading = _loss(player=False)
    debriefing = _mia_debriefing(
        losses=[evading],
        survivors=[("evading_unit", 1.0, 2.0)],
        flight_map={"evading_unit": evading},
    )
    game = SimpleNamespace(
        settings=SimpleNamespace(
            invulnerable_player_pilots=False, combat_sar_persistent_pilots=False
        )
    )

    MissionResultsProcessor(cast(Any, game)).commit_air_losses(debriefing)

    evading.pilot.kill.assert_called_once()


def test_captured_evader_pilot_resolves_from_the_downed_ledger() -> None:
    # A persistent evader captured on a LATER mission: the airframe died turns ago,
    # so the unit map knows nothing -- record_pow_captures falls back to the
    # downed-pilot ledger for the aviator (who then flips MIA -> POW).
    from game.fourteenth.downed_pilots import DownedPilot
    from game.squadrons.pilot import Pilot, PilotStatus

    pilot = Pilot("Capt Mitchell")
    pilot.go_missing()
    game = SimpleNamespace(
        blue=SimpleNamespace(pending_pow_recoveries=[]),
        red=SimpleNamespace(pending_pow_recoveries=[]),
        theater=SimpleNamespace(controlpoints=[]),
        point_in_world=lambda x, y: SimpleNamespace(x=x, y=y),
        turn=3,
        downed_pilots=[
            DownedPilot("Enfield 1-1 | F-14B", 1.0, 2.0, pilot=pilot, turn_downed=1)
        ],
    )
    debriefing = _capture_debriefing(
        captures=[("Enfield 1-1 | F-14B", 1.0, 2.0, "blue")], rescues=[]
    )

    MissionResultsProcessor(cast(Any, game)).record_pow_captures(debriefing)

    assert len(game.blue.pending_pow_recoveries) == 1
    assert game.blue.pending_pow_recoveries[0].pilot is pilot
    assert pilot.status is PilotStatus.POW


def test_king_beacon_is_tacan_only_no_adf_freq() -> None:
    # The ADF radio beacon was dropped: the King homes the rescue helo on TACAN
    # alone, so the beacon dataclass carries no reserved frequency field.
    fields = {f.name for f in dataclasses.fields(CombatSarKingBeacon)}
    assert fields == {"callsign", "tacan"}
    beacon = CombatSarKingBeacon(callsign="KING", tacan=None)
    assert beacon.callsign == "KING"
