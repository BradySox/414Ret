"""One entry point for the air-war planner's threat-field + FLOT-standoff geometry.

The 414th air-defence rework grew a set of placement helpers that all answer the
same shape of question -- *where does this orbit/screen sit, given the front line
and the threat the aircraft must stand off from?* They already share
``supportorbit``'s ``_relevant_front`` math, but each caller re-threads the same
``(theater, player, threat_zones)`` trio by hand.

``AirspaceGeometry`` owns that trio once and exposes the placement primitives as
methods, so support orbits (AEW&C / tanker) and the forward-middle BARCAP screen
derive their geometry from one object instead of re-wiring the helpers at every
call site. The instance methods are a behaviour-preserving facade: each delegates
to the existing, tested ``supportorbit`` function unchanged. The threat-field ->
volume half lives here too as the ``barcap_rounds`` staticmethod (moved from
``theaterstate``, unchanged).

``threat_zones`` is always **the opponent's threat zone relative to** ``player`` --
i.e. the threats the planned aircraft must avoid. Every current caller already
passes exactly that (``IBuilder.threat_zones`` is ``coalition.opponent.threat_zone``;
the forward-BARCAP caller passes ``coalition.opponent.threat_zone`` directly), so
the meaning is now documented in one place rather than implied at each site.

Design rationale -- including why the DEAD reachability gate and theatre-tanker
demand were examined and deliberately *not* folded in (already-standalone /
too-coupled) -- is in
``docs/dev/design/414th-airwar-planner-consolidation-notes.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from game.ato.flightplans.supportorbit import (
    forward_cap_front_anchor,
    support_orbit_anchor,
)

if TYPE_CHECKING:
    from dcs.mapping import Point
    from game.coalition import Coalition
    from game.theater import ConflictTheater, MissionTarget, Player
    from game.threatzones import ThreatZones
    from game.utils import Distance, Heading


# Threat-weighted BARCAP volume ceiling: the hottest sector in the theater gets up
# to BARCAP_THREAT_CEILING x the baseline (legacy) wave count. The scaling is purely
# *additive* on top of the baseline, so a defended CP never gets fewer waves than the
# legacy flat allocation.
BARCAP_THREAT_CEILING = 2


@dataclass(frozen=True)
class AirspaceGeometry:
    """Front-relative placement geometry for one coalition, one turn.

    Holds the ``(theater, player, threat_zones)`` trio the placement helpers need
    and exposes them as methods. ``threat_zones`` is the *opponent's* threat zone
    relative to ``player`` -- the threats the planned aircraft must stand off from.
    """

    theater: ConflictTheater
    player: Player
    threat_zones: ThreatZones

    @classmethod
    def for_coalition(cls, coalition: Coalition) -> AirspaceGeometry:
        """Build the geometry for ``coalition`` planning against its opponent."""
        return cls(
            coalition.game.theater,
            coalition.player,
            coalition.opponent.threat_zone,
        )

    def standoff_anchor(
        self, target: MissionTarget, threat_buffer: Distance
    ) -> tuple[Point, Heading]:
        """Center + enemy-facing heading for a support racetrack (AEW&C / tanker).

        Delegates to :func:`supportorbit.support_orbit_anchor`; see it for the
        front-anchoring and player-forward / AI-deep standoff rules.
        """
        return support_orbit_anchor(
            self.theater, self.player, self.threat_zones, target, threat_buffer
        )

    def forward_middle_anchor(
        self, location: MissionTarget, standoff: Distance
    ) -> Optional[tuple[Point, Heading]]:
        """Center + heading for an added forward-middle BARCAP screen, or ``None``.

        Returns ``None`` unless ``location`` is the player's own control point on an
        active front. Delegates to :func:`supportorbit.forward_cap_front_anchor`.
        """
        return forward_cap_front_anchor(
            self.theater, self.player, self.threat_zones, location, standoff
        )

    @staticmethod
    def barcap_rounds(
        baseline_rounds: int,
        threat_score: float,
        max_threat_score: float,
        is_fleet: bool,
    ) -> int:
        """Threat-weighted BARCAP wave count; never below ``baseline_rounds``.

        A defended CP at the theater's peak air threat gets ``BARCAP_THREAT_CEILING
        * baseline_rounds`` waves; a CP with no threat gets exactly ``baseline_rounds``
        (the legacy count). Fleet CPs keep their legacy 2x multiplier on top.

        With no measurable threat anywhere (``max_threat_score <= 0``) every defended
        CP gets ``baseline_rounds``, reproducing the legacy flat allocation exactly.

        Pure (scalar in, scalar out); a staticmethod so callers don't need a built
        instance. This is the threat-field -> volume half of the air-war geometry.
        """
        if max_threat_score <= 0:
            rounds = baseline_rounds
        else:
            factor = threat_score / max_threat_score
            bonus = baseline_rounds * (BARCAP_THREAT_CEILING - 1)
            rounds = baseline_rounds + round(factor * bonus)
        return 2 * rounds if is_fleet else rounds
