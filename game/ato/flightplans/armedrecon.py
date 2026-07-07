from __future__ import annotations

from typing import Type

from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from .tacticaloverlay import TacticalOverlay, TacticalOverlayDisplay, attack_run_overlay
from .uizonedisplay import UiZone, UiZoneDisplay
from ..flightwaypointtype import FlightWaypointType
from ...theater import ControlPoint, TheaterGroundObject
from ...utils import Distance, meters, nautical_miles

#: The search fly-over point stands off from the target area itself. The armed-recon
#: anchor is usually an enemy control point -- a defended FOB or airfield -- and a
#: steerpoint on the CP centre parks the flight (and the player flying it) directly
#: over the garrison's SHORAD/AAA. The point is pushed back along the ingress bearing
#: at least this far even when the target area shows no threat rings.
MIN_SEARCH_STANDOFF = nautical_miles(5)

#: Extra margin past the target area's longest ground-based threat ring.
SEARCH_STANDOFF_BUFFER = nautical_miles(2)


class ArmedReconFlightPlan(
    FormationAttackFlightPlan, UiZoneDisplay, TacticalOverlayDisplay
):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    def ui_zone(self) -> UiZone:
        # One engagement ring over the search area: armed recon hunts targets of
        # opportunity anywhere within the engagement range of the target area, not
        # down a single road.
        return UiZone(
            [waypoint.position for waypoint in self.layout.targets],
            nautical_miles(
                self.flight.coalition.game.settings.armed_recon_engagement_range_distance
            ),
        )

    def tactical_overlay(self) -> TacticalOverlay:
        return attack_run_overlay(
            self.layout.ingress.position,
            self.package.target.position,
            self.layout.split.position,
        )


class Builder(FormationAttackBuilder[ArmedReconFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        # Look in the AREA and find them: a single armed-recon overflight of the
        # target area, which the ArmedReconIngressBuilder turns into an
        # EngageTargetsInZone hunt out to the engagement range (~10 NM / ~18.5 km by
        # default). NOT a road-polyline sweep -- that was the fork's #406 change,
        # reverted 2026-07-05: marching SEARCH START/MID/END down one road wasn't a
        # "look in the area" search, and a single engage zone already blankets the
        # corridor. Convoy / supply-route interdiction still frags armed recon on the
        # enemy end (§35); the flight now area-searches that end instead of the road.
        layout = self._build(FlightWaypointType.INGRESS_ARMED_RECON)
        self._stand_off_search_point(layout)
        return layout

    def _stand_off_search_point(self, layout: FormationAttackLayout) -> None:
        """Pull the ARMED RECON fly-over point off the target area's defenses.

        The hunt zone (EngageTargetsInZone, centred on this waypoint by the
        ingress builder) is capped below by the standoff so the target area
        itself stays inside the search zone; the corridor toward the ingress
        point -- where the convoys actually drive -- gains coverage.
        """
        target = self.package.target
        ingress = layout.ingress.position
        standoff = max(
            MIN_SEARCH_STANDOFF,
            self._target_area_threat_range() + SEARCH_STANDOFF_BUFFER,
        )
        zone_radius = nautical_miles(
            self.settings.armed_recon_engagement_range_distance
        )
        distance_to_ingress = meters(target.position.distance_to_point(ingress))
        standoff = min(standoff, zone_radius, distance_to_ingress)
        if standoff <= meters(0):
            return
        heading = target.position.heading_between_point(ingress)
        for waypoint in layout.targets:
            waypoint.position = target.position.point_from_heading(
                heading, standoff.meters
            )

    def _target_area_threat_range(self) -> Distance:
        """The longest ground-based threat ring of the target area itself."""
        target = self.package.target
        if isinstance(target, ControlPoint):
            return max(
                (tgo.max_threat_range() for tgo in target.ground_objects),
                default=meters(0),
            )
        if isinstance(target, TheaterGroundObject):
            return target.max_threat_range()
        return meters(0)

    def build(self, dump_debug_info: bool = False) -> ArmedReconFlightPlan:
        return ArmedReconFlightPlan(self.flight, self.layout())
