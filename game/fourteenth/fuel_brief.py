"""The in-app fuel-plan readout, for the Edit-flight Payload tab.

Nothing here decides anything. §46's fuel-first planner -- which fitted tanks and
tasked tankers from route fuel -- was REVERTED 2026-08-09; tanker tasking is
upstream's again and nothing fits tanks. Its external-fuel accounting helpers
survive, and this module uses them to *report* the sortie's fuel picture: what
the jet carries, what the plan burns, and whether it gets home.

One fuel model everywhere: the walk uses the flight plan's own
``fuel_consumption_between_points`` (real per-leg climb/combat/cruise rates, the
same call the kneeboard ladder makes) over the planned waypoints, topping back up
to a full load at each REFUEL waypoint, and stops at the landing point (the
trailing divert/bullseye reference waypoints are not flown legs). External fuel
counts the tanks on the loadout being shown, matching the tanker decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from game.ato.flightwaypointtype import FlightWaypointType
from game.fourteenth.range_fuel import external_fuel_lbs, is_fuel_tank
from game.utils import KG_TO_LBS

if TYPE_CHECKING:
    from game.ato.flight import Flight
    from game.ato.loadouts import Loadout


@dataclass(frozen=True)
class FuelBrief:
    """A flight's sortie fuel picture, in pounds."""

    #: Internal fuel at start (the flight's fuel slider value).
    internal_lbs: float
    #: Fuel in the external tanks on the loadout shown.
    external_lbs: float
    #: Number of external tanks on the loadout shown.
    tank_count: int
    #: Total planned burn, taxi through landing, with no tanker top-offs.
    burn_lbs: float
    #: Landing reserve to preserve (the airframe's min-safe figure).
    reserve_lbs: float
    #: REFUEL waypoints on the planned route (tanker passes).
    refuel_passes: int
    #: Fuel over (or short of) the reserve at landing, tanker top-offs applied.
    margin_lbs: float
    #: The same figure with NO tanker top-off -- what the jet gets home on if it
    #: never plugs in. This is the honest headline: a refuel waypoint means a
    #: tanker is planned, not that the gas was taken.
    dry_margin_lbs: float
    #: True when the numbers come from the synthesised fuel model rather than
    #: hand-measured data (the same fallback the kneeboard ladder uses).
    estimated: bool

    @property
    def carried_lbs(self) -> float:
        return self.internal_lbs + self.external_lbs

    @property
    def is_short(self) -> bool:
        return self.dry_margin_lbs < 0 and self.margin_lbs < 0

    @property
    def needs_the_tanker(self) -> bool:
        """True when the sortie only closes because of a planned top-off."""
        return self.dry_margin_lbs < 0 <= self.margin_lbs


def _loadout_for_brief(flight: Flight) -> Optional[Loadout]:
    """Default to the driest member's loadout -- what the tanker decision used."""
    loadouts = [m.loadout for m in flight.iter_members()]
    if not loadouts:
        return None
    return min(loadouts, key=external_fuel_lbs)


def fuel_brief_for(
    flight: Flight, loadout: Optional[Loadout] = None
) -> Optional[FuelBrief]:
    """The sortie fuel picture for ``flight``, or None without a usable model.

    ``loadout`` selects whose tanks to count (the payload tab passes the member
    being edited); it defaults to the driest member's, matching the tanker
    decision. Returns None when the airframe has no fuel data at all or the
    flight has no routed plan.
    """
    unit_type = flight.unit_type
    measured = unit_type.fuel_consumption
    consumption = measured or unit_type.estimated_fuel_consumption
    if consumption is None:
        return None
    flight_plan = getattr(flight, "flight_plan", None)
    if flight_plan is None:
        return None
    waypoints = list(flight_plan.waypoints)
    if len(waypoints) < 2:
        return None

    if loadout is None:
        loadout = _loadout_for_brief(flight)
    external = external_fuel_lbs(loadout) if loadout is not None else 0.0
    tanks = 0
    if loadout is not None:
        tanks = sum(
            1
            for weapon in loadout.pylons.values()
            if weapon is not None and is_fuel_tank(weapon.clsid)
        )

    internal_kg = getattr(flight, "fuel", None)
    if internal_kg is None:
        internal_kg = unit_type.max_fuel
    internal = internal_kg * KG_TO_LBS

    full = internal + external
    remaining = full - consumption.taxi
    # The same walk with no top-offs applied. Tracked alongside rather than
    # derived afterwards, because the burn up to each REFUEL waypoint is exactly
    # what a top-off hides.
    dry = remaining
    burn = consumption.taxi
    passes = 0
    previous = None
    for waypoint in waypoints:
        if previous is not None:
            leg = flight_plan.fuel_consumption_between_points(
                previous, waypoint, consumption
            )
            if leg is not None:
                remaining -= leg
                dry -= leg
                burn += leg
        if waypoint.waypoint_type is FlightWaypointType.REFUEL:
            passes += 1
            remaining = full
        previous = waypoint
        if waypoint.waypoint_type is FlightWaypointType.LANDING_POINT:
            break

    return FuelBrief(
        internal_lbs=internal,
        external_lbs=external,
        tank_count=tanks,
        burn_lbs=burn,
        reserve_lbs=consumption.min_safe,
        refuel_passes=passes,
        margin_lbs=remaining - consumption.min_safe,
        dry_margin_lbs=dry - consumption.min_safe,
        estimated=measured is None,
    )


def fuel_brief_text(brief: Optional[FuelBrief]) -> str:
    """A compact one/two-line plain-text rendering for the planning UI."""
    if brief is None:
        return "Fuel plan: no fuel model for this airframe."
    bags = (
        f" + {brief.tank_count} tank{'s' if brief.tank_count != 1 else ''} "
        f"{brief.external_lbs:,.0f} lb"
        if brief.tank_count
        else ""
    )
    # Lead with the unrefuelled margin. A refuel waypoint means a tanker is
    # planned, never that the gas was taken, so the with-tanker figure is only
    # worth printing when the sortie actually depends on it.
    sign = "+" if brief.dry_margin_lbs >= 0 else "-"
    estimated = " (estimated)" if brief.estimated else ""
    text = (
        f"Fuel plan{estimated}: burns ~{brief.burn_lbs:,.0f} lb · carries "
        f"{brief.carried_lbs:,.0f} lb ({brief.internal_lbs:,.0f} internal{bags}) · "
        f"RTB margin {sign}{abs(brief.dry_margin_lbs):,.0f} lb unrefuelled"
    )
    if brief.refuel_passes:
        text += (
            f" · {brief.refuel_passes} tanker pass"
            f"{'es' if brief.refuel_passes != 1 else ''} planned"
        )
    if brief.needs_the_tanker:
        text += (
            f" — this sortie does NOT get home without the tanker "
            f"(+{brief.margin_lbs:,.0f} lb with it)."
        )
    elif brief.is_short:
        text += " — short of getting home as planned; tank, divert, or lighten."
    return text
