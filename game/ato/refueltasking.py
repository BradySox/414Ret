"""Fuel-driven pre/post-vul tanker tasking.

Every flight launches normally. A flight whose planned fuel burn exceeds what it can
carry needs to take gas from a tanker, and *when* it should do so depends on where in
the sortie it runs short:

* **Pre-vul** -- it cannot complete the run in to the target and the vulnerability
  window (takeoff -> split) on internal fuel while keeping its landing reserve, so it
  tops off on the ingress leg before the vul.
* **Post-vul** -- it can fight through the vul on internal fuel but cannot make it home
  with reserve afterward, so it tanks on the egress leg.

This module holds only the (pure, unit-agnostic) decision; the flight plan supplies the
fuel numbers and inserts the matching refuel waypoint. All fuel quantities passed in
must share the same unit (pounds, matching ``FuelConsumption``).
"""

from __future__ import annotations

from enum import Enum, unique
from typing import TYPE_CHECKING, Sequence

from game.ato.flightwaypointtype import FlightWaypointType

if TYPE_CHECKING:
    from collections.abc import Container

    from game.ato.flightwaypoint import FlightWaypoint
    from game.dcs.aircrafttype import FuelConsumption

#: One nautical mile in meters, for converting leg lengths to the per-nm fuel rates.
_METERS_PER_NAUTICAL_MILE = 1852.0


@unique
class RefuelTasking(Enum):
    """Where, if anywhere, a flight should be sent to a tanker."""

    #: Internal fuel is sufficient for the whole sortie; no tanker needed.
    NONE = "none"
    #: Top off on the ingress leg, before the vulnerability window.
    PRE_VUL = "pre_vul"
    #: Tank on the egress leg, after the vulnerability window.
    POST_VUL = "post_vul"

    @property
    def needs_tanker(self) -> bool:
        return self is not RefuelTasking.NONE

    @property
    def refuels_pre_vul(self) -> bool:
        return self is RefuelTasking.PRE_VUL

    @property
    def refuels_post_vul(self) -> bool:
        return self is RefuelTasking.POST_VUL


def sortie_fuel_split(
    route: Sequence[FlightWaypoint],
    fuel: FuelConsumption,
    combat_speed_waypoints: Container[FlightWaypoint],
    split: FlightWaypoint,
) -> tuple[float, float]:
    """Fuel burned over a sortie route, split at the vul.

    Walks consecutive legs of ``route`` applying the same per-leg fuel rate as the
    flight plan itself: the climb rate off the takeoff waypoint, the combat rate into
    any combat-speed (formation) waypoint, and the cruise rate everywhere else.

    Args:
        route: The ordered sortie waypoints, takeoff first and landing last.
        fuel: The airframe's per-nautical-mile fuel rates (pounds).
        combat_speed_waypoints: Waypoints flown at combat power (join/targets/split).
        split: The waypoint that ends the vulnerability window.

    Returns:
        ``(fuel takeoff -> split inclusive, fuel split -> landing)``, both in pounds.
    """
    to_split = 0.0
    after_split = 0.0
    passed_split = False
    previous: FlightWaypoint | None = None
    for waypoint in route:
        if previous is not None:
            distance_nm = (
                previous.position.distance_to_point(waypoint.position)
                / _METERS_PER_NAUTICAL_MILE
            )
            if previous.waypoint_type is FlightWaypointType.TAKEOFF:
                rate = fuel.climb
            elif waypoint in combat_speed_waypoints:
                rate = fuel.combat
            else:
                rate = fuel.cruise
            leg = distance_nm * rate
            if passed_split:
                after_split += leg
            else:
                to_split += leg
        if waypoint is split:
            passed_split = True
        previous = waypoint
    return to_split, after_split


def decide_refuel_tasking(
    usable_fuel: float,
    fuel_to_end_of_vul: float,
    fuel_vul_to_home: float,
    reserve: float,
) -> RefuelTasking:
    """Decide whether and where a flight should tank.

    Args:
        usable_fuel: Internal fuel available at the start of the sortie (after taxi),
            in pounds.
        fuel_to_end_of_vul: Fuel burned from takeoff through the end of the
            vulnerability window (split), in pounds.
        fuel_vul_to_home: Fuel burned from the split back to landing, in pounds.
        reserve: Landing fuel reserve to preserve, in pounds.

    Returns:
        ``NONE`` if internal fuel covers the whole sortie plus reserve, ``PRE_VUL`` if
        the flight cannot reach the end of the vul with reserve to spare, otherwise
        ``POST_VUL``.
    """
    total_required = fuel_to_end_of_vul + fuel_vul_to_home + reserve
    if usable_fuel >= total_required:
        return RefuelTasking.NONE
    # The flight is short. If it can't even fight through the vul while holding its
    # reserve it has to top off on the way in; otherwise it can wait until egress.
    if usable_fuel < fuel_to_end_of_vul + reserve:
        return RefuelTasking.PRE_VUL
    return RefuelTasking.POST_VUL
