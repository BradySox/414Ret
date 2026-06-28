"""Regression tests for ``cap_orbit_distance_band``.

This is the BARCAP/TARCAP orbit-distance clamp. The bug it guards against:
when a defended base sits *inside* the enemy threat zone, ``distance_to_no_fly``
goes below the doctrine minimum (often negative), and the old
``min(cap_*, distance_to_no_fly)`` collapsed both bounds onto that value -- which
placed the racetrack behind the base (pointing away from the threat) with zero
jitter and a dead forward-bias. The band must stay forward (>= cap_min) and keep
a real min..max spread.
"""

from __future__ import annotations

from game.ato.flightplans.capbuilder import cap_orbit_distance_band
from game.utils import nautical_miles

CAP_MIN = nautical_miles(8)
CAP_MAX = nautical_miles(25)


def test_quiet_flank_uses_full_doctrine_band() -> None:
    # Far from any threat: the no-fly limit doesn't bind, so the band is the full
    # doctrine spread.
    lo, hi = cap_orbit_distance_band(CAP_MIN, CAP_MAX, nautical_miles(200))
    assert lo == CAP_MIN
    assert hi == CAP_MAX


def test_moderate_threat_pulls_in_outer_bound_only() -> None:
    # The no-fly limit sits between cap_min and cap_max: inner bound stays at
    # cap_min, outer bound pulls in to the no-fly limit (unchanged behaviour).
    no_fly = nautical_miles(15)
    lo, hi = cap_orbit_distance_band(CAP_MIN, CAP_MAX, no_fly)
    assert lo == CAP_MIN
    assert hi == no_fly


def test_base_at_threat_edge_keeps_forward_spread() -> None:
    # no_fly below cap_min (but positive): must NOT collapse to a single
    # sub-minimum value -- fall back to the full forward band.
    lo, hi = cap_orbit_distance_band(CAP_MIN, CAP_MAX, nautical_miles(3))
    assert lo == CAP_MIN
    assert hi == CAP_MAX


def test_base_inside_threat_zone_negative_no_fly_stays_forward() -> None:
    # The reported bug: a base inside the enemy threat ring yields a deeply
    # negative no-fly distance. The orbit must stay FORWARD (lower bound >= cap_min,
    # strictly positive) rather than landing behind the base.
    lo, hi = cap_orbit_distance_band(CAP_MIN, CAP_MAX, nautical_miles(-40))
    assert lo == CAP_MIN
    assert hi == CAP_MAX
    assert lo.meters > 0


def test_threatened_band_preserves_jitter_and_bias_precondition() -> None:
    # The forward-bias / placement-jitter both require max > min. The old collapse
    # made them equal (dead feature); the fix must keep a real spread.
    lo, hi = cap_orbit_distance_band(CAP_MIN, CAP_MAX, nautical_miles(-40))
    assert hi > lo
