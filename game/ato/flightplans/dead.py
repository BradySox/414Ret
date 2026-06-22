from __future__ import annotations

import logging
from typing import Type

from game.theater.theatergroundobject import (
    EwrGroundObject,
    SamGroundObject,
)
from .formationattack import (
    FormationAttackBuilder,
    FormationAttackFlightPlan,
    FormationAttackLayout,
)
from .invalidobjectivelocation import InvalidObjectiveLocation
from .tacticaloverlay import TacticalOverlay, TacticalOverlayDisplay, attack_run_overlay
from ..flightwaypointtype import FlightWaypointType
from ...settings.settings import TargetIntelPrecision


class DeadFlightPlan(FormationAttackFlightPlan, TacticalOverlayDisplay):
    @staticmethod
    def builder_type() -> Type[Builder]:
        return Builder

    def tactical_overlay(self) -> TacticalOverlay:
        return attack_run_overlay(
            self.layout.ingress.position,
            self.package.target.position,
            self.layout.split.position,
        )


class Builder(FormationAttackBuilder[DeadFlightPlan, FormationAttackLayout]):
    def layout(self) -> FormationAttackLayout:
        location = self.package.target

        if not isinstance(location, (EwrGroundObject, SamGroundObject)):
            logging.exception(
                f"Invalid Objective Location for DEAD flight {self.flight=} at "
                f"{location=}"
            )
            raise InvalidObjectiveLocation(self.flight.flight_type, location)

        # Mobile SAMs relocate between intel updates, so under Approximate intel
        # the player gets a single fuzzed target-area waypoint to visually acquire
        # rather than exact per-emitter points. Exact intel keeps the per-unit
        # points for trivial TOO designation.
        targets = (
            self.strike_targets_for(location)
            if self.settings.target_intel_precision is TargetIntelPrecision.EXACT
            else None
        )
        return self._build(FlightWaypointType.INGRESS_DEAD, targets)

    def build(self, dump_debug_info: bool = False) -> DeadFlightPlan:
        return DeadFlightPlan(self.flight, self.layout())
