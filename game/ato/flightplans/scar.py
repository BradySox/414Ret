from __future__ import annotations

from typing import Type

from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from .uizonedisplay import UiZone, UiZoneDisplay
from ..flightwaypointtype import FlightWaypointType
from ...utils import nautical_miles

# SCAR (Strike Coordination and Reconnaissance): a flight works a defined box
# (~10x10 mi) hunting one moving HVT among clutter and light threats. v1 reuses
# the Armed Recon ingress/area machinery with a wider engagement zone so the
# task is selectable with sane waypoints; the scenario itself (HVT/decoy/clutter
# spawn, movement, fail-on-arrival, scoring) lives in the SCAR Lua plugin.
#
# Deferred to later increments (see docs/dev/design/414th-scar-task-spec.md):
# airframe-scaled on-station loiter (15 min fast jet / 30 min A-10) and a
# dedicated INGRESS_SCAR waypoint type/builder. Until then SCAR borrows
# Armed Recon's INGRESS_ARMED_RECON ingress.
SCAR_AREA_RADIUS_NM = 5.0


class ScarFlightPlan(FormationAttackFlightPlan, UiZoneDisplay):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    def ui_zone(self) -> UiZone:
        return UiZone(
            [self.tot_waypoint.position],
            nautical_miles(SCAR_AREA_RADIUS_NM),
        )


class Builder(FormationAttackBuilder[ScarFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        return self._build(FlightWaypointType.INGRESS_ARMED_RECON)

    def build(self, dump_debug_info: bool = False) -> ScarFlightPlan:
        return ScarFlightPlan(self.flight, self.layout())
