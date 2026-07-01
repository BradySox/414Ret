"""Vietnam campaign layer W2b: the static (bounded-oscillation) front.

Spec: docs/dev/design/414th-vietnam-political-will-roe-notes.md (static-front section).
Vietnam's ground war was static attrition -- Khe Sanh was besieged for 77 days without
the line *going* anywhere -- but Retribution's front position is a pure function of the
two bases' strength ratio (``FrontLine._blue_route_progress``), so a sustained strength
edge sweeps the front onto a base and captures it. That maneuver-war outcome is wrong
for the era: attrition should pay out in **political will** (the W1 feeds), and the war
should end at the negotiating table (W2), not with the front strolling into Hanoi.

This module arms a per-front clamp: each front's position may oscillate only inside a
band of +/-:data:`STATIC_FRONT_BAND` of the route length around its **anchor** (the
front's position when first seen with the setting on -- turn 0 for a new campaign; the
current position when enabled mid-campaign, which is documented as acceptable). The
strength battle underneath is fully alive -- pushes still move the line inside the band
and still feed the will economy -- but the front can never reach a base, so the
automatic sweep-capture path is dead. **Air Assault captures stay**: deliberate
heliborne ops remain the one territorial lever (user decision, 2026-07-01).

``apply_static_front`` runs from ``Game.initialize_turn`` (idempotent -- initialize_turn
can run several times per turn) and cleanly disarms every front when the setting is
off, so non-Vietnam campaigns and toggled-off saves get stock behaviour. ``FrontLine``
has no ``__setstate__`` and a pickle-sensitive identity ``__hash__``, so the clamp
lives as an optional attribute read with ``getattr(..., None)`` -- never a required
field, never touched during unpickling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game

#: Fraction of the route length the front may move to EACH side of its anchor. The
#: user-approved band is +/-10% -- wide enough that a hard push visibly bends the
#: line (pressure reads on the map), narrow enough that no push ever reaches a base.
STATIC_FRONT_BAND = 0.10


def clamp_bounds(
    anchor_fraction: float, band: float, route_length: float
) -> tuple[float, float]:
    """The (low, high) distance-from-blue clamp for an anchored front.

    ``anchor_fraction`` is the anchor as a fraction of ``route_length``; ``band`` is
    the excursion allowed each side, also a fraction. Both bounds are clamped into
    [0, route_length] so an anchor near an end never produces an out-of-route bound.
    """
    low = max(0.0, (anchor_fraction - band) * route_length)
    high = min(route_length, (anchor_fraction + band) * route_length)
    return low, high


def apply_static_front(game: "Game") -> None:
    """Arm (or disarm) the static-front clamp on every front. Idempotent and cheap.

    Setting off -> every front's clamp is cleared (clean disarm; anchors are kept so
    re-enabling mid-campaign restores the same band). Setting on -> each front gets an
    anchor captured from its **raw, unclamped** position on first sight -- a front that
    appears mid-campaign (an Air Assault capture creating a new pairing) is anchored
    where it first forms -- and the clamp derived from it.
    """
    enabled = getattr(game.settings, "vietnam_static_front", False)
    for front in game.theater.conflicts():
        if not enabled:
            front.static_front_clamp = None
            continue
        anchor = getattr(front, "static_front_anchor", None)
        if anchor is None:
            # Capture the anchor BEFORE any clamp exists: with the clamp attr unset
            # (or None), _blue_route_progress returns the raw strength-mapped
            # position (plus the min-CP-distance adjustment, which is fine -- the
            # anchor should respect it too).
            front.static_front_clamp = None
            anchor = front._blue_route_progress / front.route_length
            front.static_front_anchor = anchor
        front.static_front_clamp = clamp_bounds(
            anchor, STATIC_FRONT_BAND, front.route_length
        )
