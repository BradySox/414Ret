from __future__ import annotations

from datetime import timedelta
from typing import Type

from game.ato.flighttype import FlightType
from game.theater import ControlPoint, TheaterGroundObject
from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from .invalidobjectivelocation import InvalidObjectiveLocation
from ..flightwaypointtype import FlightWaypointType

#: TARPS serves two different jobs depending on the package it rides, and the two
#: want opposite timing (this is the de-jumble of the 2026-07 recon rework):
#:  * a **post-strike BDA** pass on a Strike/DEAD package overflies a couple of
#:    minutes AFTER the shooters, to photograph the damage they did; and
#:  * a **find / overwatch** pass on an Armed Recon package (or a standalone recon
#:    mission) has no strike moment to trail -- the recon bird works the area WITH
#:    the package to scout/localize, so it takes no positive offset.
#: The BDA offset is kept tight (2 min, not more) so the unarmed bird still
#: ingresses the threatened corridor under the package's escort window rather than
#: trailing in alone where MiGs pick it off (checklist G19).
_BDA_TRAIL_OFFSET = timedelta(minutes=2)


class TarpsFlightPlan(FormationAttackFlightPlan):
    """Tactical photo-recon overflight (F-14 TARPS / recon drone).

    Routes a strike-style ingress / target overflight / egress. The TOT offset is
    role-aware (see :data:`_BDA_TRAIL_OFFSET`): a post-strike BDA pass on a
    Strike/DEAD package trails the shooters by two minutes, while a find/overwatch
    pass on an Armed Recon (or standalone) package arrives with the package. The
    flight itself drops nothing; the recon value (imagery/BDA) is handled out-of-band
    and is intentionally not modeled here (fog of war stays intact).
    """

    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    def default_tot_offset(self) -> timedelta:
        primary = self.package.primary_flight
        # Only a strike-style primary gives the recon bird a *post-strike* moment to
        # trail for BDA. On an Armed Recon package (or when the recon flight is the
        # package's own primary), it is a find/overwatch pass -- on station with the
        # shooters, not two minutes behind an event that never happens.
        if primary is not None and primary.flight_type in (
            FlightType.STRIKE,
            FlightType.DEAD,
        ):
            return _BDA_TRAIL_OFFSET
        return timedelta()


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
