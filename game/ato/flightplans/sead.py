from __future__ import annotations

from datetime import timedelta
from typing import Type

from game.theater import TheaterGroundObject
from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from .tacticaloverlay import (
    TacticalOverlay,
    TacticalOverlayDisplay,
    loiter_overlay,
    orbit_radius,
)
from .uizonedisplay import UiZone, UiZoneDisplay
from ..flightwaypoint import FlightWaypoint
from ..flightwaypointtype import FlightWaypointType
from ...settings.settings import TargetIntelPrecision
from ...utils import nautical_miles

# Plain SEAD reactively fires HARMs from its loiter anchor. The planner overlay shows a
# fixed HARM-reach bubble rather than the user-tunable SEAD-sweep engagement range, so
# the orbit is always drawn against a realistic engagement envelope.
SEAD_ENGAGEMENT_RANGE = nautical_miles(20)


class SeadFlightPlan(FormationAttackFlightPlan, UiZoneDisplay, TacticalOverlayDisplay):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    def default_tot_offset(self) -> timedelta:
        return -timedelta(minutes=1)

    def ui_zone(self) -> UiZone:
        # Centre the HARM-reach bubble on the loiter anchor (where the flight orbits and
        # engages), falling back to the target if no anchor was planned.
        anchor = self.layout.initial or self.tot_waypoint
        return UiZone([anchor.position], SEAD_ENGAGEMENT_RANGE)

    @property
    def _loiter_anchor(self) -> FlightWaypoint:
        # Standoff loiter point (the "SEAD Search" anchor); fall back to the
        # target if the layout has no standoff anchor.
        return self.layout.initial or self.tot_waypoint

    def tactical_overlay(self) -> TacticalOverlay:
        # SEAD loiters at standoff and reacts to radars near its own position, so
        # both the orbit and the engagement bubble sit on the loiter anchor. The
        # engagement bubble uses the fixed HARM-reach SEAD_ENGAGEMENT_RANGE (see
        # the module comment) rather than the tunable sead-sweep range, matching
        # the fork's ui_zone.
        anchor = self._loiter_anchor
        return loiter_overlay(
            orbit_center=anchor.position,
            loiter_radius=orbit_radius(
                self.flight.unit_type.preferred_patrol_speed(anchor.alt)
            ),
            engagement_center=anchor.position,
            engagement_range=SEAD_ENGAGEMENT_RANGE,
            target_position=self.tot_waypoint.position,
        )


class Builder(FormationAttackBuilder[SeadFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        location = self.package.target
        # Only ground objectives expose individual units with coordinates (the
        # same list the SEAD kneeboard page renders). Against those, give each
        # listed target its own waypoint; against e.g. naval groups the kneeboard
        # lists no per-unit coordinates, so fall back to the single target area.
        # Mobile SAMs relocate, so under Approximate intel we also fall back to a
        # single fuzzed target-area waypoint instead of exact per-emitter points.
        targets = (
            self.strike_targets_for(location)
            if (
                isinstance(location, TheaterGroundObject)
                and self.settings.target_intel_precision is TargetIntelPrecision.EXACT
            )
            else None
        )
        return self._build(FlightWaypointType.INGRESS_SEAD, targets)

    def build(self, dump_debug_info: bool = False) -> SeadFlightPlan:
        return SeadFlightPlan(self.flight, self.layout())
