from dcs.point import MovingPoint
from dcs.task import (
    OptECMUsing,
    ControlledTask,
    Targets,
    EngageTargetsInZone,
)

from game.utils import nautical_miles
from .pydcswaypointbuilder import PydcsWaypointBuilder


class ArmedReconIngressBuilder(PydcsWaypointBuilder):
    def add_tasks(self, waypoint: MovingPoint) -> None:
        self.register_special_ingress_points()
        # Preemptively use ECM to better avoid getting swatted.
        ecm_option = OptECMUsing(value=OptECMUsing.Values.UseIfDetectedLockByRadar)
        waypoint.tasks.append(ecm_option)

        # One engage zone per search point. Armed recon plans a single target-area
        # point, so this is one big "look in the area and find them" hunt zone out to
        # the engagement range; the loop stays general in case a future plan ever
        # supplies several search points.
        flight_plan = self.flight.flight_plan
        positions = [
            target.position
            for target in getattr(flight_plan.layout, "targets", []) or []
        ] or [flight_plan.tot_waypoint.position]
        radius = int(
            nautical_miles(
                self.flight.coalition.game.settings.armed_recon_engagement_range_distance
            ).meters
        )
        for position in positions:
            waypoint.add_task(
                ControlledTask(
                    EngageTargetsInZone(
                        position=position,
                        radius=radius,
                        targets=[
                            Targets.All.GroundUnits,
                            Targets.All.Air.Helicopters,
                        ],
                    )
                )
            )
