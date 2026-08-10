"""The strike-escort reserve *trim* (Doctrine.strike_escort_reserve, half 1).

The HTN plans BARCAP before any strike, so on fighter-poor eras every airframe is
committed by the time ``always_escort_strikes`` requests escorts. This trims
BARCAP demand so ~reserve airframes stay untasked for those escorts. The fence
half (which stops non-STRIKE packages spending the freed jets) is covered by
tests/commander/test_escort_reserve_fence.py.

Only Vietnam sets a non-zero reserve, so every assertion here is a no-op for
other doctrines -- see test_zero_reserve_is_stock.
"""

from __future__ import annotations

from game.commander.theaterstate import trim_rounds_for_escort_reserve


def test_thins_rounds_until_the_reserve_fits() -> None:
    rounds = {"a": 4, "b": 3, "c": 3}
    # Demand = 2*10 = 20 jets; pool 20 < 20 + 4 -> shortage. Affordable rounds =
    # (20 - 4) // 2 = 8, so 2 rounds have to go.
    trimmed = trim_rounds_for_escort_reserve(rounds, 20, 4)
    assert sum(trimmed.values()) == 8
    assert trimmed == {"a": 4, "b": 3, "c": 1}


def test_abandons_whole_locations_but_never_the_first() -> None:
    rounds = {"a": 1, "b": 1, "c": 1}
    # Even the one-round floors are unaffordable: coverage is abandoned entirely
    # (MiGCAP where it matters), but one location always keeps a round so the
    # trim can never zero out BARCAP across the theater.
    trimmed = trim_rounds_for_escort_reserve(rounds, 0, 8)
    assert trimmed == {"a": 1, "b": 0, "c": 0}


def test_noop_when_fighters_are_plentiful() -> None:
    rounds = {"a": 3, "b": 3}
    # Demand 12 + reserve 4 = 16 <= 40: fighter-rich, keep full volume.
    assert trim_rounds_for_escort_reserve(rounds, 40, 4) == rounds


def test_zero_reserve_is_stock() -> None:
    # Every doctrine except Vietnam sets no reserve, so the trim never runs and
    # BARCAP volume is upstream's flat allocation untouched.
    rounds = {"a": 3}
    assert trim_rounds_for_escort_reserve(rounds, 0, 0) == rounds


def test_empty_rounds_are_returned_unchanged() -> None:
    assert trim_rounds_for_escort_reserve({}, 0, 4) == {}


def test_jets_per_round_scales_the_demand_estimate() -> None:
    rounds = {"a": 2, "b": 2}
    # At 2 jets/round demand is 8 and a pool of 19 covers 8 + 4 comfortably...
    assert trim_rounds_for_escort_reserve(rounds, 19, 4, jets_per_round=2) == rounds
    # ...but the planner budgets pessimistically at 4 jets/round: demand 16, and
    # 19 < 16 + 4, so the trim engages.
    trimmed = trim_rounds_for_escort_reserve(rounds, 19, 4, jets_per_round=4)
    assert sum(trimmed.values()) < sum(rounds.values())
