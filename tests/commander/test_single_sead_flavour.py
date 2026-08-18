"""One suppression flight per package (Settings.single_sead_escort_flavour).

SEAD_ESCORT, SEAD_SWEEP and PlanDead's SEAD all carry EscortType.Sead, and
check_needed_escorts sets that flag once for the whole package, so upstream can
plan all three off a single radar-SAM trigger. Gated OFF by default under the
2026-08-09 re-convergence contract; the 414th planner suite turns it on.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from game.ato.flighttype import FlightType
from game.commander.missionproposals import EscortType, ProposedFlight
from game.commander.packagefulfiller import PackageFulfiller

SEAD_ESCORT = ProposedFlight(FlightType.SEAD_ESCORT, 2, EscortType.Sead)
SEAD_SWEEP = ProposedFlight(FlightType.SEAD_SWEEP, 2, EscortType.Sead)
A2A_ESCORT = ProposedFlight(FlightType.ESCORT, 2, EscortType.AirToAir)
JAMMER = ProposedFlight(FlightType.ESCORT_JAMMER, 2, EscortType.Jammer)


def _fulfiller(enabled: bool) -> PackageFulfiller:
    fulfiller = object.__new__(PackageFulfiller)
    fulfiller.coalition = MagicMock()
    fulfiller.single_sead_escort_flavour = enabled
    return fulfiller


@pytest.mark.parametrize("escort", [SEAD_ESCORT, SEAD_SWEEP])
def test_second_sead_flavour_is_dropped(escort: ProposedFlight) -> None:
    fulfiller = _fulfiller(enabled=True)
    assert not fulfiller.sead_flavour_satisfied(escort, sead_planned=False)
    assert fulfiller.sead_flavour_satisfied(escort, sead_planned=True)


@pytest.mark.parametrize("escort", [A2A_ESCORT, JAMMER])
def test_other_flavours_are_untouched(escort: ProposedFlight) -> None:
    # An anti-ship package doubles its fighter escort on purpose, and the jammer
    # has its own max_escort_jammers cap.
    fulfiller = _fulfiller(enabled=True)
    assert not fulfiller.sead_flavour_satisfied(escort, sead_planned=True)


@pytest.mark.parametrize("escort", [SEAD_ESCORT, SEAD_SWEEP])
def test_gate_off_keeps_upstream_stacking(escort: ProposedFlight) -> None:
    fulfiller = _fulfiller(enabled=False)
    assert not fulfiller.sead_flavour_satisfied(escort, sead_planned=True)
