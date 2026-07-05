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
from ...utils import nautical_miles


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
        return self._build(FlightWaypointType.INGRESS_ARMED_RECON)

    def build(self, dump_debug_info: bool = False) -> ArmedReconFlightPlan:
        return ArmedReconFlightPlan(self.flight, self.layout())
