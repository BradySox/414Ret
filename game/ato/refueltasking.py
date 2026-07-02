"""Fuel-driven pre/post-vul tanker tasking.

Every flight launches normally. A flight whose planned fuel burn exceeds what it can
carry needs to take gas from a tanker, and *when* it should do so depends on where in
the sortie it runs short:

* **Pre-vul** -- it cannot complete the run in to the target and the vulnerability
  window (takeoff -> split) on internal fuel while keeping its landing reserve, so it
  tops off on the ingress leg before the vul.
* **Post-vul** -- it can fight through the vul on internal fuel but cannot make it home
  with reserve afterward, so it tanks on the egress leg.
* **Both** -- the sortie is so long that even a full top-off cannot cover it on a single
  refuel, so it tanks before *and* after the vul.

This module holds only the (pure, unit-agnostic) decision; the flight plan supplies the
fuel numbers and inserts the matching refuel waypoint. All fuel quantities passed in
must share the same unit (pounds, matching ``FuelConsumption``).
"""

from __future__ import annotations

from datetime import timedelta
from enum import Enum, unique
from typing import TYPE_CHECKING, Sequence

from game.ato.flightwaypointtype import FlightWaypointType

if TYPE_CHECKING:
    from collections.abc import Container

    from game.ato.flightwaypoint import FlightWaypoint
    from game.dcs.aircrafttype import FuelConsumption

#: One nautical mile in meters, for converting leg lengths to the per-nm fuel rates.
_METERS_PER_NAUTICAL_MILE = 1852.0


def refuel_service_time(flight_size: int) -> timedelta:
    """Time budgeted for one flight to cycle a tanker (every jet topping off).

    Shared by both sides of the rendezvous: the receiver's flight plan spends this
    at its refuel waypoint, and the package tanker budgets the same amount of
    on-station time per receiving flight, so neither out-schedules the other.
    """
    return timedelta(minutes=4 * flight_size + 1)


@unique
class RefuelTasking(Enum):
    """Where, if anywhere, a flight should be sent to a tanker."""

    #: Internal fuel is sufficient for the whole sortie; no tanker needed.
    NONE = "none"
    #: Top off on the ingress leg, before the vulnerability window.
    PRE_VUL = "pre_vul"
    #: Tank on the egress leg, after the vulnerability window.
    POST_VUL = "post_vul"
    #: Tank both before and after the vul -- the sortie is too long for a single
    #: top-off to full internal fuel to cover.
    BOTH = "both"

    @property
    def needs_tanker(self) -> bool:
        return self is not RefuelTasking.NONE

    @property
    def refuels_pre_vul(self) -> bool:
        return self in (RefuelTasking.PRE_VUL, RefuelTasking.BOTH)

    @property
    def refuels_post_vul(self) -> bool:
        return self in (RefuelTasking.POST_VUL, RefuelTasking.BOTH)


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
    full_fuel: float,
) -> RefuelTasking:
    """Decide whether and where a flight should tank.

    Args:
        usable_fuel: Internal fuel available at the start of the sortie (after taxi),
            in pounds.
        fuel_to_end_of_vul: Fuel burned from takeoff through the end of the
            vulnerability window (split), in pounds.
        fuel_vul_to_home: Fuel burned from the split back to landing, in pounds.
        reserve: Landing fuel reserve to preserve, in pounds.
        full_fuel: Internal fuel after topping off at a tanker (no taxi burn), in
            pounds -- i.e. how far a single refuel gets the flight.

    Returns:
        ``NONE`` if internal fuel covers the whole sortie plus reserve; ``POST_VUL`` if
        the flight can reach the end of the vul and a single top-off then covers the
        trip home; ``PRE_VUL`` if it must top off on the way in and one tank still gets
        it home; ``BOTH`` when even a full top-off can't cover the remaining sortie, so
        it needs to tank before *and* after the vul.
    """
    total_required = fuel_to_end_of_vul + fuel_vul_to_home + reserve
    if usable_fuel >= total_required:
        return RefuelTasking.NONE

    # The flight is short. Prefer tanking on egress when it can both reach the end of
    # the vul on internal fuel and make it home on a single post-vul top-off.
    reaches_end_of_vul = usable_fuel >= fuel_to_end_of_vul + reserve
    one_tank_covers_egress = full_fuel >= fuel_vul_to_home + reserve
    if reaches_end_of_vul and one_tank_covers_egress:
        return RefuelTasking.POST_VUL

    # Otherwise it must top off on the way in. A pre-vul top-off refills to full early,
    # so it only helps if a full load then covers the whole remaining sortie; if not,
    # the flight is too long for one tank and needs both a pre- and post-vul tanker.
    if full_fuel >= total_required:
        return RefuelTasking.PRE_VUL
    return RefuelTasking.BOTH
