"""Vietnam campaign layer W2b: the static (bounded-oscillation) front.

Locks the user-approved design: the front oscillates inside a +/-10% band around its
campaign-start anchor instead of sweeping onto a base (only the automatic sweep-capture
path dies; Air Assault stays the territorial lever). Arm/disarm is idempotent and the
anchor is captured exactly once, from the raw unclamped position.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from game.fourteenth.static_front import (
    STATIC_FRONT_BAND,
    apply_static_front,
    clamp_bounds,
)
from game.theater.frontline import FRONTLINE_MIN_CP_DISTANCE, FrontLine


def _real_front(
    blue_strength: float, red_strength: float, route_length: float = 100_000.0
) -> FrontLine:
    """A real FrontLine (the fork's __new__ trick) so the actual clamp path runs.

    __init__ needs control points and a convoy route; the position math only needs
    the two bases' strengths and the segment list, so build just those.
    """
    fl = FrontLine.__new__(FrontLine)
    fl.blue_cp = SimpleNamespace(  # type: ignore[assignment]
        base=SimpleNamespace(strength=blue_strength)
    )
    fl.red_cp = SimpleNamespace(  # type: ignore[assignment]
        base=SimpleNamespace(strength=red_strength)
    )
    fl.segments = [SimpleNamespace(length=route_length)]  # type: ignore[list-item]
    return fl


def _game(fronts: list[FrontLine], on: bool = True) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(vietnam_static_front=on),
        theater=SimpleNamespace(conflicts=lambda: list(fronts)),
    )


def test_clamp_bounds_basic() -> None:
    low, high = clamp_bounds(0.5, 0.1, 100_000.0)
    assert low == 40_000.0
    assert high == 60_000.0


def test_clamp_bounds_clamps_to_route_ends() -> None:
    # An anchor near an end never yields an out-of-route bound.
    low, high = clamp_bounds(0.05, 0.1, 100_000.0)
    assert low == 0.0
    assert high == pytest.approx(15_000.0)
    low, high = clamp_bounds(0.97, 0.1, 100_000.0)
    assert low == pytest.approx(87_000.0)
    assert high == 100_000.0


def test_arm_sets_anchor_and_clamp() -> None:
    fl = _real_front(blue_strength=1.0, red_strength=1.0)
    apply_static_front(_game([fl]))
    # Even strengths anchor mid-route.
    assert fl.static_front_anchor == 0.5
    assert fl.static_front_clamp == clamp_bounds(0.5, STATIC_FRONT_BAND, 100_000.0)


def test_anchor_is_captured_once() -> None:
    fl = _real_front(blue_strength=1.0, red_strength=1.0)
    game = _game([fl])
    apply_static_front(game)
    assert fl.static_front_anchor == 0.5
    # The strength battle swings hard; re-arming (initialize_turn runs multiple
    # times per turn) must NOT re-anchor on the new position.
    fl.blue_cp.base.strength = 3.0
    apply_static_front(game)
    assert fl.static_front_anchor == 0.5
    assert fl.static_front_clamp == clamp_bounds(0.5, STATIC_FRONT_BAND, 100_000.0)


def _clamp_of(fl: FrontLine) -> Any:
    # Read through a helper so mypy's is-not-None narrowing on the attribute does not
    # mark the post-disarm assertion unreachable (apply_static_front mutates fl).
    return fl.static_front_clamp


def test_disarm_clears_clamp_keeps_anchor() -> None:
    fl = _real_front(blue_strength=1.0, red_strength=1.0)
    apply_static_front(_game([fl], on=True))
    assert _clamp_of(fl) is not None
    apply_static_front(_game([fl], on=False))
    assert _clamp_of(fl) is None
    # The anchor survives so re-enabling restores the same band.
    assert fl.static_front_anchor == 0.5
    apply_static_front(_game([fl], on=True))
    assert fl.static_front_clamp == clamp_bounds(0.5, STATIC_FRONT_BAND, 100_000.0)


def test_clamped_front_stays_in_band_at_strength_extremes() -> None:
    route = 100_000.0
    fl = _real_front(blue_strength=1.0, red_strength=1.0, route_length=route)
    apply_static_front(_game([fl]))
    low, high = 40_000.0, 60_000.0

    # Blue collapses entirely: raw position would be the blue base's doorstep.
    fl.blue_cp.base.strength = 0.0
    assert fl._blue_route_progress == low

    # Red collapses entirely: raw position would be the red base's doorstep.
    fl.blue_cp.base.strength = 1.0
    fl.red_cp.base.strength = 0.0
    assert fl._blue_route_progress == high

    # A big-but-not-total edge is also held inside the band.
    fl.red_cp.base.strength = 9.0
    assert fl._blue_route_progress == low
    # And inside the band the strength battle still moves the line.
    fl.red_cp.base.strength = 1.2
    assert low < fl._blue_route_progress < high


def test_unclamped_front_keeps_stock_behaviour() -> None:
    route = 100_000.0
    fl = _real_front(blue_strength=1.0, red_strength=0.0, route_length=route)
    # No clamp armed: the stock sweep (min-CP-distance adjusted) is untouched.
    assert fl.static_front_clamp is None
    assert fl._blue_route_progress == route - FRONTLINE_MIN_CP_DISTANCE
    fl.blue_cp.base.strength = 0.0
    fl.red_cp.base.strength = 1.0
    assert fl._blue_route_progress == FRONTLINE_MIN_CP_DISTANCE


def test_min_cp_distance_applies_after_clamp() -> None:
    # A short route where the band's low bound is inside the min-CP standoff: the
    # min-dist adjustment (applied AFTER the clamp) still wins.
    route = 12_000.0
    fl = _real_front(blue_strength=1.0, red_strength=1.0, route_length=route)
    apply_static_front(_game([fl]))
    fl.blue_cp.base.strength = 0.0
    # Band low = (0.5 - 0.1) * 12000 = 4800, inside the 5000 m standoff.
    assert fl._blue_route_progress == FRONTLINE_MIN_CP_DISTANCE
