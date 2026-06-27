import logging
from typing import Any, Optional

from dcs.point import MovingPoint
from dcs.task import (
    ActivateBeaconCommand,
    ControlledTask,
    EngageTargets,
    OrbitAction,
    Tanker,
    Targets,
    SetUnlimitedFuelCommand,
)

from game.ato import FlightType
from game.ato.flightplans.patrolling import PatrollingFlightPlan
from ._helper import create_stop_orbit_trigger
from .pydcswaypointbuilder import PydcsWaypointBuilder


class RaceTrackBuilder(PydcsWaypointBuilder):
    def add_tasks(self, waypoint: MovingPoint) -> None:
        flight_plan = self.flight.flight_plan

        # Unlimited fuel option : disable at racetrack start. Must be first option to work.
        if self.flight.squadron.coalition.game.settings.ai_unlimited_fuel:
            if waypoint.tasks and isinstance(
                waypoint.tasks[0], SetUnlimitedFuelCommand
            ):
                waypoint.tasks[0] = SetUnlimitedFuelCommand(False)
            else:
                waypoint.tasks.insert(0, SetUnlimitedFuelCommand(False))

        if not isinstance(flight_plan, PatrollingFlightPlan):
            flight_plan_type = flight_plan.__class__.__name__
            logging.error(
                f"Cannot create race track for {self.flight} because "
                f"{flight_plan_type} does not define a patrol."
            )
            return

        # NB: It's important that the engage task comes before the orbit task.
        # Though they're on the same waypoint, if the orbit task comes first it
        # is their first priority and they will not engage any targets because
        # they're fully focused on orbiting. If the STE task is first, they will
        # engage targets if available and orbit if they find nothing to shoot.
        if self.flight.flight_type is FlightType.REFUELING:
            self.configure_refueling_actions(waypoint)

        # The engage task must precede the orbit task (see note above), so an AI
        # that finds targets shoots and only orbits when there's nothing to hit.
        engage = self._engage_targets_task(flight_plan)
        if engage is not None:
            waypoint.tasks.append(engage)

        orbit = OrbitAction(
            altitude=waypoint.alt,
            pattern=OrbitAction.OrbitPattern.RaceTrack,
            speed=int(flight_plan.patrol_speed.kph),
        )

        racetrack = ControlledTask(orbit)
        self.set_waypoint_tot(waypoint, flight_plan.patrol_start_time)
        elapsed = int((flight_plan.patrol_end_time - self.now).total_seconds())
        racetrack.stop_after_time(elapsed)
        # What follows is some code to cope with the broken 'stop after time' condition
        create_stop_orbit_trigger(racetrack, self.package, self.mission, elapsed)
        # end of hotfix
        waypoint.add_task(racetrack)

    def _engage_targets_task(
        self, flight_plan: PatrollingFlightPlan[Any]
    ) -> Optional[EngageTargets]:
        """The patrol's engage task by flight type, or None for a pure orbit.

        CAP (BARCAP/TARCAP) engages air. The 414th Sandy RESCAP escort (SCAR)
        engages GROUND threats near the FLOT / a downed pilot instead of just
        orbiting -- an AI SCAR patrol otherwise got no engage task and sat idle
        in-game (2026-06-27). Both use the flight plan's engagement_distance as the
        bubble; rescue craft (Combat SAR helo/King), AEW&C and tankers keep a pure
        orbit (return None).
        """
        distance = int(flight_plan.engagement_distance.meters)
        if self.flight.flight_type in {FlightType.BARCAP, FlightType.TARCAP}:
            return EngageTargets(
                max_distance=distance,
                targets=[
                    Targets.All.Air,
                    Targets.All.Missile.AntishipMissiles,
                    Targets.All.Missile.CruiseMissiles,
                ],
            )
        if self.flight.flight_type is FlightType.SCAR:
            return EngageTargets(
                max_distance=distance,
                targets=[
                    Targets.All.GroundUnits.GroundVehicles,
                    Targets.All.GroundUnits.AirDefence.AAA,
                    Targets.All.GroundUnits.Infantry,
                ],
            )
        return None

    def configure_refueling_actions(self, waypoint: MovingPoint) -> None:
        waypoint.add_task(Tanker())

        tanker_info = self.mission_data.tankers[-1]
        tacan = tanker_info.tacan
        if self.flight.unit_type.dcs_unit_type.tacan and tacan:
            if self.flight.tcn_name is None:
                cs = tanker_info.callsign[:-2]
                csn = tanker_info.callsign[-1]
                tacan_callsign = {
                    "Texaco": "TX",
                    "Arco": "AC",
                    "Shell": "SH",
                }.get(cs)
                if tacan_callsign:
                    tacan_callsign = tacan_callsign + csn
                else:
                    tacan_callsign = cs[0:2] + csn
            else:
                tacan_callsign = self.flight.tcn_name

            waypoint.add_task(
                ActivateBeaconCommand(
                    tacan.number,
                    tacan.band.value,
                    tacan_callsign.upper(),
                    bearing=True,
                    unit_id=self.group.units[0].id,
                    aa=True,
                    tanker=True,
                )
            )
