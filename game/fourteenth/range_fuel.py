"""Route-aware external-fuel-tank top-up (414th feature §46).

Long-AO campaigns strand flights that the auto-planner frags with too little
fuel for the leg -- most visibly the COIN Enduring Resolve carrier, which sits
~800 km off the Helmand AO, so a Hornet on internal fuel (plus its two stock wing
tanks) still can't make the round trip. This adds drop tanks to a flight at
**mission-generation time** when, and only when, its planned route needs the range.

**Deliberately conservative -- it never removes a store.** Weapon *type* data can't
tell a self-defense Sidewinder from a primary JDAM (both resolve to
``WeaponType.UNKNOWN``), so a "swap low-value ordnance for a tank" step can't be
made safe by default -- it would risk stripping a TGP, ECM pod, or bomb. So this
only fills **empty, tank-capable** stations. That already gives the COIN Hornet
Strike its third bag (the reset upstream loadout leaves the centerline empty),
and by construction it can never degrade a loadout.

Generation-time only: it returns a new :class:`Loadout` for the ``.miz`` and never
mutates the persisted ATO loadout, so it is re-evaluated each turn as routes move
and leaves saves untouched. Gated by ``Settings.auto_range_fuel_tanks`` (default
ON -- it is inert on short-range routes, where internal + stock tanks already
cover the leg).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

import dcs.weapons_data as weapons_data

from game.data.weapons import Pylon, Weapon
from game.utils import KG_TO_LBS, meters

if TYPE_CHECKING:
    from game.ato.flight import Flight
    from game.ato.flightwaypoint import FlightWaypoint
    from game.ato.loadouts import Loadout
    from game.dcs.aircrafttype import AircraftType
    from game.settings import Settings

# Fuel-mass conversions for external tanks, whose capacity is only spelled out in
# the DCS display name (gallons / liters / kg). Jet fuel ~6.7 lb/US gal, ~1.75 lb/L.
_LBS_PER_US_GAL = 6.7
_LBS_PER_LITER = 1.75
_DEFAULT_TANK_LBS = 2000.0  # a sane mid-size tank when the name gives no number

# Identify a fuel tank from its DCS display name. There is no fuel-tank WeaponType
# in the Retribution model (tanks are UNKNOWN), and the pydcs weapon record carries
# no category flag, so we match the name -- but narrowly, so a "Color Oil Tank" or a
# fuel-air bomb is never mistaken for a drop tank.
_TANK_NAME_RE = re.compile(
    r"(fuel[ -]tank|drop ?tank|external[ -]tank|x-tank|conformal fuel|\bcft\b"
    r"|\bgallons?\b|\bgal\b|\bliters? fuel\b|\bkg fuel\b|\bptb-)",
    re.IGNORECASE,
)
_TANK_CAPACITY_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:u\.?s\.?\s*)?(gallons?|gal|liters?|litres?|lt|kg)\b",
    re.IGNORECASE,
)


def _weapon_name(clsid: str) -> str:
    record = weapons_data.weapon_ids.get(clsid)
    if not isinstance(record, dict):
        return ""
    return str(record.get("name", ""))


def is_fuel_tank(clsid: str) -> bool:
    """True if ``clsid`` is an external fuel tank (not an empty/ferry-shell tank)."""
    name = _weapon_name(clsid)
    if not name:
        return False
    if "empty" in name.lower():
        return False
    return bool(_TANK_NAME_RE.search(name))


def tank_capacity_lbs(clsid: str) -> float:
    """Best-effort fuel capacity of a tank, in pounds, parsed from its name."""
    name = _weapon_name(clsid)
    match = _TANK_CAPACITY_RE.search(name)
    if match is None:
        return _DEFAULT_TANK_LBS
    value = float(match.group(1))
    unit = match.group(2).lower()
    if unit.startswith("gal"):
        return value * _LBS_PER_US_GAL
    if unit == "kg":
        return value * KG_TO_LBS
    # liter / litre / lt
    return value * _LBS_PER_LITER


def route_length_nm(waypoints: list[FlightWaypoint]) -> float:
    """Total planned ground-track length (sum of legs) in nautical miles."""
    total = 0.0
    previous = None
    for waypoint in waypoints:
        if previous is not None:
            total += meters(
                previous.distance_to_point(waypoint.position)
            ).nautical_miles
        previous = waypoint.position
    return total


def _available_fuel_lbs(unit_type: AircraftType, loadout: Loadout) -> float:
    """Internal fuel plus the fuel already carried in external tanks, in pounds."""
    total = unit_type.max_fuel * KG_TO_LBS
    for weapon in loadout.pylons.values():
        if weapon is not None and is_fuel_tank(weapon.clsid):
            total += tank_capacity_lbs(weapon.clsid)
    return total


def _required_fuel_lbs(unit_type: AircraftType, route_nm: float) -> Optional[float]:
    """Rough cruise fuel to fly ``route_nm`` and land on the reserve, in pounds.

    Uses the airframe's measured fuel block, or the synthesised estimate that every
    airframe has, so this works fleet-wide. Tankers on the route are intentionally
    ignored: we would rather over-fuel (an unused tank) than under-fuel.
    """
    fuel = unit_type.fuel_consumption or unit_type.estimated_fuel_consumption
    if fuel is None:
        return None
    return fuel.taxi + fuel.cruise * route_nm + fuel.min_safe


def _best_tank_for_station(
    pylon: Pylon, existing_tank_clsids: list[str]
) -> Optional[Weapon]:
    """Pick a tank for ``pylon``: match one already on the jet, else the largest."""
    candidates = [w for w in pylon.allowed if is_fuel_tank(w.clsid)]
    if not candidates:
        return None
    # Prefer a tank the loadout already uses, so all bags match.
    for weapon in candidates:
        if weapon.clsid in existing_tank_clsids:
            return weapon
    return max(candidates, key=lambda w: tank_capacity_lbs(w.clsid))


def _empty_tank_stations(
    unit_type: AircraftType, loadout: Loadout
) -> dict[int, tuple[Weapon, float]]:
    """Empty, tank-capable stations mapped to (chosen tank, its capacity in lbs)."""
    existing_tank_clsids = [
        weapon.clsid
        for weapon in loadout.pylons.values()
        if weapon is not None and is_fuel_tank(weapon.clsid)
    ]
    stations: dict[int, tuple[Weapon, float]] = {}
    for number in unit_type.dcs_unit_type.pylons:
        if loadout.pylons.get(number) is not None:
            continue  # occupied -- never touched
        pylon = Pylon.for_aircraft(unit_type, number)
        tank = _best_tank_for_station(pylon, existing_tank_clsids)
        if tank is not None:
            stations[number] = (tank, tank_capacity_lbs(tank.clsid))
    return stations


def top_up_for_route(
    unit_type: AircraftType, route_nm: float, loadout: Loadout
) -> Loadout:
    """Return ``loadout`` with tanks added to empty stations if the route needs it.

    Only fills empty, tank-capable stations, and only enough to cover the route --
    never removes or replaces an existing store.
    """
    from game.ato.loadouts import Loadout as LoadoutCls

    if route_nm <= 0 or not loadout.pylons:
        return loadout
    required = _required_fuel_lbs(unit_type, route_nm)
    if required is None:
        return loadout
    available = _available_fuel_lbs(unit_type, loadout)
    if available >= required:
        return loadout
    stations = _empty_tank_stations(unit_type, loadout)
    if not stations:
        return loadout

    new_pylons = dict(loadout.pylons)
    added = False
    for number in sorted(stations):
        if available >= required:
            break
        tank, capacity = stations[number]
        new_pylons[number] = tank
        available += capacity
        added = True
    if not added:
        return loadout
    return LoadoutCls(
        loadout.name,
        new_pylons,
        loadout.date,
        loadout.is_custom,
        pylon_settings=dict(loadout.pylon_settings),
    )


def add_range_fuel_tanks(
    flight: Flight, loadout: Loadout, settings: Settings
) -> Loadout:
    """Generation-time hook: top up a flight's tanks for its route when enabled.

    No-op unless the setting is on, and always a no-op for a player-customised
    loadout (respect explicit edits) or an empty/clean one.
    """
    if not settings.auto_range_fuel_tanks:
        return loadout
    if loadout.is_custom or not loadout.pylons:
        return loadout
    flight_plan = getattr(flight, "flight_plan", None)
    if flight_plan is None:
        return loadout
    route_nm = route_length_nm(flight_plan.waypoints)
    return top_up_for_route(flight.unit_type, route_nm, loadout)
