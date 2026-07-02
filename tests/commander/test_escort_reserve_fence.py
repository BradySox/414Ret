"""The strike-escort reserve *fence* (Doctrine.strike_escort_reserve, half 2).

The BARCAP trim (tests/test_barcap_threat_weighting.py) frees ~reserve fighters
from BARCAP volume; this fence stops every non-STRIKE package planned before the
strikes from spending them on its own A2A escort. Only a STRIKE-led package may
dip the live untasked-fighter pool below the reserve.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from game.ato.flighttype import FlightType
from game.commander.missionproposals import EscortType, ProposedFlight
from game.commander.packagefulfiller import PackageFulfiller
from game.squadrons.airwing import AirWing


def _fulfiller(reserve: int, untasked_fighters: int) -> PackageFulfiller:
    fulfiller = object.__new__(PackageFulfiller)
    coalition = MagicMock()
    coalition.doctrine.strike_escort_reserve = reserve
    coalition.air_wing.untasked_fighters.return_value = untasked_fighters
    fulfiller.coalition = coalition
    return fulfiller


def _builder(primary: FlightType | None) -> MagicMock:
    builder = MagicMock()
    if primary is None:
        builder.package.primary_flight = None
    else:
        builder.package.primary_flight.flight_type = primary
    return builder


A2A_ESCORT = ProposedFlight(FlightType.ESCORT, 2, EscortType.AirToAir)


def test_no_reserve_is_a_noop() -> None:
    fulfiller = _fulfiller(reserve=0, untasked_fighters=1)
    assert not fulfiller.escort_reserve_withholds(_builder(FlightType.BAI), A2A_ESCORT)


def test_only_a2a_escorts_are_fenced() -> None:
    fulfiller = _fulfiller(reserve=4, untasked_fighters=2)
    sead = ProposedFlight(FlightType.SEAD_ESCORT, 2, EscortType.Sead)
    assert not fulfiller.escort_reserve_withholds(_builder(FlightType.BAI), sead)


def test_strike_packages_may_spend_the_reserve() -> None:
    # The reserve is held FOR the bombers: a STRIKE-led package plans its escort
    # even when doing so empties the pool entirely.
    fulfiller = _fulfiller(reserve=4, untasked_fighters=2)
    assert not fulfiller.escort_reserve_withholds(
        _builder(FlightType.STRIKE), A2A_ESCORT
    )


def test_non_strike_escort_allowed_while_pool_stays_above_reserve() -> None:
    # 6 untasked - 2 for this escort = 4 left, exactly the reserve: allowed.
    fulfiller = _fulfiller(reserve=4, untasked_fighters=6)
    assert not fulfiller.escort_reserve_withholds(_builder(FlightType.BAI), A2A_ESCORT)


def test_non_strike_escort_withheld_when_it_would_dip_the_reserve() -> None:
    # 5 untasked - 2 for this escort = 3 < 4: withheld, the BAI flies unescorted.
    fulfiller = _fulfiller(reserve=4, untasked_fighters=5)
    assert fulfiller.escort_reserve_withholds(_builder(FlightType.BAI), A2A_ESCORT)


def test_package_without_a_primary_flight_counts_as_non_strike() -> None:
    fulfiller = _fulfiller(reserve=4, untasked_fighters=5)
    assert fulfiller.escort_reserve_withholds(_builder(None), A2A_ESCORT)


def test_untasked_fighters_counts_only_fighter_primary_squadrons() -> None:
    wing = object.__new__(AirWing)
    barcap = MagicMock(untasked_aircraft=4, primary_task=FlightType.BARCAP)
    cas = MagicMock(untasked_aircraft=6, primary_task=FlightType.CAS)
    sweep = MagicMock(untasked_aircraft=2, primary_task=FlightType.SWEEP)
    wing.squadrons = {MagicMock(): [barcap, cas], MagicMock(): [sweep]}
    assert wing.untasked_fighters() == 6
