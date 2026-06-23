from abc import ABC
from datetime import timedelta

from game.utils import Speed, Distance, meters
from .patrolling import PatrollingFlightPlan, PatrollingLayout


class RefuelingFlightPlan(PatrollingFlightPlan[PatrollingLayout], ABC):
    @property
    def patrol_duration(self) -> timedelta:
        return self.flight.coalition.game.settings.desired_tanker_on_station_time

    @property
    def patrol_speed(self) -> Speed:
        unit_type = self.flight.unit_type
        if unit_type.patrol_speed is not None:
            return unit_type.patrol_speed
        # No explicit racetrack speed for this airframe: estimate from its performance
        # at the altitude the racetrack is actually planned at. WaypointBuilder.
        # get_patrol_altitude bases the orbit on preferred_patrol_altitude, so taking
        # the speed estimate there keeps the two consistent. This replaces a flat
        # 400 kt fallback that ignored both the airframe and its planned orbit altitude.
        return unit_type.preferred_patrol_speed(unit_type.preferred_patrol_altitude)

    @property
    def engagement_distance(self) -> Distance:
        # TODO: Factor out a common base of the combat and non-combat race-tracks.
        # No harm in setting this, but we ought to clean up a bit.
        return meters(0)
