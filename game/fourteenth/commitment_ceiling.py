"""Commitment ceiling -- the will-coupled war budget (CLAUDE.md feature).

The political-will economy (``political_will.py``) decides the war at the negotiating
table, but until a side actually breaks, a flagging war has no *material* cost -- you
keep the same income whether the home front is behind you or not. Historically it was
the opposite: in the canonical political wargame *Vietnam 1965-1975* (Victory Games),
**US commitment can never exceed morale** -- as morale falls, forces are drawn down and
the war is quite literally taken out of your hands.

This is that coupling, in economic terms: as BLUE **Political Will** falls below a
threshold, the coalition's per-turn income is scaled down toward a floor (Congress trims
the war budget), so a losing war is starved of replacements. It is a deliberate,
gentle-by-design pressure -- full funding while will stays high, and even at rock bottom
the floor keeps *some* budget flowing so it pressures rather than hard-locks. The BLUE
side only (Washington's war budget); RED is not coupled (the insurgent-style regime
absorbs loss without a congressional appropriation, matching the VG asymmetry).

Gated by ``vietnam_commitment_ceiling`` (default OFF, campaign-preseeded) **and**
``vietnam_political_will`` (no will economy ⇒ nothing to couple to). Off ⇒ income is
returned untouched, so non-Vietnam campaigns and pre-feature saves are unaffected.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.fourteenth.political_will import WILL_MAX, WILL_MIN

if TYPE_CHECKING:
    from game import Game
    from game.theater import Player

#: At or above this BLUE will, the war is fully funded (multiplier 1.0). Below it the
#: budget ramps down -- the cut only bites once patience is already low, so a healthy
#: war never feels it.
CEILING_FULL_WILL = 60.0

#: The floor multiplier at zero will: even a collapsing home front still appropriates
#: half the war budget (the ceiling pressures, it never zeroes procurement).
CEILING_FLOOR_MULT = 0.5


def will_budget_multiplier(game: "Game") -> float:
    """The BLUE income multiplier for this turn from Washington's patience.

    1.0 while will >= :data:`CEILING_FULL_WILL`, ramping linearly down to
    :data:`CEILING_FLOOR_MULT` at will 0. Reads ``game.blue.political_will``;
    getattr-guarded so a duck-typed test game or a pre-will save reads as full will.
    """
    will = getattr(game.blue, "political_will", WILL_MAX)
    if will >= CEILING_FULL_WILL:
        return 1.0
    if will <= WILL_MIN:
        return CEILING_FLOOR_MULT
    frac = will / CEILING_FULL_WILL  # 0..1 across the ramp
    return CEILING_FLOOR_MULT + (1.0 - CEILING_FLOOR_MULT) * frac


def apply_commitment_ceiling(game: "Game", player: "Player", income: float) -> float:
    """Scale a turn's income by the commitment ceiling, or return it unchanged.

    No-op unless the feature and the will economy are both on and this is the BLUE
    coalition. Messages the player when the budget is actually cut (multiplier < 1)
    so the draw-down is legible, not silent bookkeeping.
    """
    if not getattr(game.settings, "vietnam_commitment_ceiling", False):
        return income
    if not getattr(game.settings, "vietnam_political_will", False):
        return income
    if not player.is_blue:
        return income
    multiplier = will_budget_multiplier(game)
    if multiplier >= 1.0:
        return income
    cut = income * (1.0 - multiplier)
    game.message(
        "War budget cut",
        f"Washington's patience is low -- Congress trims the war budget by "
        f"{(1.0 - multiplier) * 100:.0f}% (−{cut:.0f}) this turn. Break the "
        f"enemy's resolve before the funding dries up.",
    )
    return income * multiplier
