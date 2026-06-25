"""One entry point for the air-war planner's threat-field + FLOT-standoff geometry.

The 414th air-defence rework grew a set of placement helpers that all answer the
same shape of question -- *where does this orbit/screen sit, given the front line
and the threat the aircraft must stand off from?* They already share
``supportorbit``'s ``_relevant_front`` math, but each caller re-threads the same
``(theater, player, threat_zones)`` trio by hand.

``AirspaceGeometry`` owns that trio once and exposes the placement primitives as
methods, so support orbits (AEW&C / tanker) and the forward-middle BARCAP screen
derive their geometry from one object instead of re-wiring the helpers at every
call site. It is a behaviour-preserving facade: each method delegates to the
existing, tested ``supportorbit`` function unchanged.

``threat_zones`` is always **the opponent's threat zone relative to** ``player`` --
i.e. the threats the planned aircraft must avoid. Every current caller already
passes exactly that (``IBuilder.threat_zones`` is ``coalition.opponent.threat_zone``;
the forward-BARCAP caller passes ``coalition.opponent.threat_zone`` directly), so
the meaning is now documented in one place rather than implied at each site.

Design rationale and the planned follow-on consumers (threat-weighted BARCAP
volume, the DEAD reachability gate, theatre-tanker demand) are in
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
