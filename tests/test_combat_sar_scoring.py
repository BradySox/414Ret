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


def test_king_beacon_is_tacan_only_no_adf_freq() -> None:
    # The ADF radio beacon was dropped: the King homes the rescue helo on TACAN
    # alone, so the beacon dataclass carries no reserved frequency field.
    fields = {f.name for f in dataclasses.fields(CombatSarKingBeacon)}
    assert fields == {"callsign", "tacan"}
    beacon = CombatSarKingBeacon(callsign="KING", tacan=None)
    assert beacon.callsign == "KING"
