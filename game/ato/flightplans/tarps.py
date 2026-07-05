from __future__ import annotations

from datetime import timedelta
from typing import Type

from game.theater import ControlPoint, TheaterGroundObject
from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from .invalidobjectivelocation import InvalidObjectiveLocation
from ..flightwaypointtype import FlightWaypointType


class TarpsFlightPlan(FormationAttackFlightPlan):
    """Tactical photo-recon overflight (F-14B TARPS).

    Routes a strike-style ingress / target overflight / egress, but carries a
    positive TOT offset so the recon bird passes over the target a couple of
    minutes behind the strikers — i.e. a post-strike BDA / discovery pass rather
    than an attack. The flight itself drops nothing; the recon value (imagery) is
    handled out-of-band and is intentionally not modeled here (fog of war stays
    intact).
    """

    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    def default_tot_offset(self) -> timedelta:
        # Overfly the target shortly after the strikers have hit it (post-strike
        # BDA). Kept tight (2 min) on purpose: the unarmed recon bird ingresses
        # the threatened corridor WITH the package so it shares the escort window,
        # instead of trailing in alone minutes later where MiGs pick it off (the
        # AI escort splits at the strikers' egress and turns back short of the
        # target, so a lone late straggler is uncovered). See checklist G19.
        return timedelta(minutes=2)


class Builder(FormationAttackBuilder[TarpsFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        location = self.package.target

        # A TGO target is the strike/DEAD BDA case; a ControlPoint target is the
        # Armed Recon overwatch case (a recon drone fragged into the sweep package
        # overflies the same area). Both are MissionTargets with a position, so the
        # base recon-area overflight below handles either -- only the explicit type
        # gate had to widen.
        if not isinstance(location, (TheaterGroundObject, ControlPoint)):
            raise InvalidObjectiveLocation(self.flight.flight_type, location)

        # A photo-recon pass is a single overflight of the target area, not an
        # attack run weaving over every individual unit. Passing no per-unit
        # targets makes the builder emit one TARGET-area waypoint at the target
        # center instead of one waypoint per strike target. INGRESS_RECON (rather
        # than INGRESS_STRIKE) keeps the ingress point free of Bombing tasks the
        # weaponless recon bird could never fulfil, and the target-area waypoint is
        # a flyover (recon_area) so the AI actually crosses the target.
        return self._build(FlightWaypointType.INGRESS_RECON, None)

    def build(self, dump_debug_info: bool = False) -> TarpsFlightPlan:
        return TarpsFlightPlan(self.flight, self.layout())
