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
from game.scar_rescue import PendingSofRescue, sof_rescue_pickup_name
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


# --- SOF-team recovery via Combat SAR -------------------------------------------------


def test_sof_rescue_pickup_name_is_stable_and_prefixed() -> None:
    # The generator and the debrief must compute the same name from the same
    # rescue: SOFRESCUE prefix (the Lua routes on it) + rounded strand metres.
    rescue = PendingSofRescue(x=12345.4, y=-6789.6)
    assert sof_rescue_pickup_name(rescue) == "SOFRESCUE_12345_-6790"
    # Stable across the float round-trip the point match tolerates.
    assert sof_rescue_pickup_name(
        PendingSofRescue(x=12345.0, y=-6790.0)
    ) == sof_rescue_pickup_name(PendingSofRescue(x=12345.49, y=-6789.51))


def test_parse_sof_recoveries_tolerates_malformed() -> None:
    assert (
        StateData.from_json({}, _no_flight_unit_map()).combat_sar_sof_recoveries == []
    )
    state = StateData.from_json(
        {"combat_sar_sof_recoveries": ["SOFRESCUE_1_2", "", 5, None]},
        _no_flight_unit_map(),
    )
    assert state.combat_sar_sof_recoveries == ["SOFRESCUE_1_2"]


def _sof_game(blue_pending: list[Any], red_pending: list[Any]) -> Any:
    blue = SimpleNamespace(
        player=SimpleNamespace(is_blue=True),
        ato=SimpleNamespace(packages=[]),
        pending_csars=blue_pending,
    )
    red = SimpleNamespace(
        player=SimpleNamespace(is_blue=False),
        ato=SimpleNamespace(packages=[]),
        pending_csars=red_pending,
    )
    return SimpleNamespace(
        blue=blue,
        red=red,
        settings=SimpleNamespace(scar_command_post_intel=True),
    )


def test_commit_sof_recoveries_credits_combat_sar_delivery() -> None:
    rescue = PendingSofRescue(x=12345.0, y=-6789.0)
    other = PendingSofRescue(x=99999.0, y=11111.0)
    game = _sof_game(blue_pending=[rescue, other], red_pending=[])
    processor = MissionResultsProcessor(cast(Any, game))
    refunds: list[tuple[Any, int]] = []
    processor._refund_sof_teams_to = (  # type: ignore[method-assign]
        lambda player, unit_name, count: refunds.append((player, count))
    )
    debriefing = cast(
        Any,
        SimpleNamespace(
            state_data=SimpleNamespace(
                combat_sar_sof_recoveries=[sof_rescue_pickup_name(rescue)]
            )
        ),
    )

    processor.commit_sof_recoveries(debriefing)

    # The delivered team is cleared + refunded; the un-rescued one stays pending.
    assert game.blue.pending_csars == [other]
    assert refunds == [(game.blue.player, 1)]


def test_commit_sof_recoveries_combat_sar_is_blue_only() -> None:
    red_rescue = PendingSofRescue(x=7.0, y=8.0)
    game = _sof_game(blue_pending=[], red_pending=[red_rescue])
    processor = MissionResultsProcessor(cast(Any, game))
    refunds: list[tuple[Any, int]] = []
    processor._refund_sof_teams_to = (  # type: ignore[method-assign]
        lambda player, unit_name, count: refunds.append((player, count))
    )
    # A blue-channel delivery name must never recover a RED stranded team.
    debriefing = cast(
        Any,
        SimpleNamespace(
            state_data=SimpleNamespace(
                combat_sar_sof_recoveries=[sof_rescue_pickup_name(red_rescue)]
            )
        ),
    )

    processor.commit_sof_recoveries(debriefing)

    assert game.red.pending_csars == [red_rescue]
    assert refunds == []
