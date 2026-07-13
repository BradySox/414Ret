"""Route-aware external-fuel-tank planning (414th feature §46).

Long-AO campaigns strand flights that the auto-planner frags with too little
fuel for the leg -- most visibly the COIN Enduring Resolve carrier, which sits
~800 km off the Helmand AO, so a Hornet on internal fuel (plus its two stock wing
tanks) still can't make the round trip. Two halves, one module:

**Plan-time fuel-first pass** (:func:`plan_sortie_fuel`, called from the
formation-attack ``_refuel_tasking`` before the pre/post-vul tanker decision):
once the package is built and the sortie route is known, the flight is given the
gas for the sortie *before* the tanker passes are decided --

* **Tier 1** (``auto_range_fuel_tanks``): fill empty, tank-capable stations while
  the sortie is short of fuel (§46's original behavior, moved ahead of the tanker
  decision so the decision can see the tanks).
* **Tier 2** (``fuel_tanks_over_jammers``): trade a self-protection **jammer pod**
  (``WeaponType.JAMMER`` -- the one store type that is both typed and expendable
  for range; a TGP, ordnance, or anything UNKNOWN-typed is never touched) for a
  tank, but only when the extra bag strictly reduces the number of tanker passes
  the sortie needs (pre+post-vul -> one pass, or one pass -> none). With no
  tanker in theater the bags are the only gas there is, so the trade happens
  whenever the sortie is short. The motivating case: a SEAD Viper with two wing
  bags and a centerline ALQ-184 that was planned pre- AND post-vul refueling --
  three bags and a single pass beat the pod.

The plan-time pass **mutates the members' persisted loadouts in place** (shared
Loadout objects stay shared, custom loadouts are never touched), so the payload
editor, the kneeboard, the fuel ladder, the tanker decision, and the generated
``.miz`` all agree on what the jet carries. Idempotent across plan rebuilds.

**Generation-time top-up** (:func:`add_range_fuel_tanks`, the original §46 hook):
a safety net for everything planned outside the formation-attack family (ferries,
CAPs, pre-feature saves). Fill-empty-stations only, never removes a store, returns
a new :class:`Loadout` for the ``.miz`` and never mutates the persisted ATO
loadout. Gated by ``Settings.auto_range_fuel_tanks`` (default ON -- inert on
short-range routes, where internal + stock tanks already cover the leg).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

import dcs.weapons_data as weapons_data

from game.data.weapons import Pylon, Weapon, WeaponType
from game.utils import KG_TO_LBS, meters

if TYPE_CHECKING:
    from game.ato.flight import Flight
    from game.ato.flightwaypoint import FlightWaypoint
    from game.ato.loadouts import Loadout
    from game.dcs.aircrafttype import AircraftType, FuelConsumption
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


def external_fuel_lbs(loadout: Loadout) -> float:
    """Fuel carried in the loadout's external tanks, in pounds."""
    total = 0.0
    for weapon in loadout.pylons.values():
        if weapon is not None and is_fuel_tank(weapon.clsid):
            total += tank_capacity_lbs(weapon.clsid)
    return total


def flight_external_fuel_lbs(flight: Flight) -> float:
    """The external fuel the flight can count on: the driest member's tanks.

    Members usually share one loadout, but per-member (custom) loadouts can
    diverge; the tanker decision has to serve the driest jet in the flight.
    """
    external = [external_fuel_lbs(m.loadout) for m in flight.iter_members()]
    if not external:
        return 0.0
    return min(external)


def _available_fuel_lbs(unit_type: AircraftType, loadout: Loadout) -> float:
    """Internal fuel plus the fuel already carried in external tanks, in pounds."""
    return unit_type.max_fuel * KG_TO_LBS + external_fuel_lbs(loadout)


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


# --- The plan-time fuel-first pass -------------------------------------------------
#
# Called from FormationAttackBuilder._refuel_tasking once the sortie route exists but
# BEFORE the pre/post-vul tanker decision, so the decision sees the tanks. Mutates the
# members' persisted loadouts in place (see the module docstring for the contract).

#: Store types a fuel tank may displace. Deliberately just the self-protection
#: jammer pod: it is the one store that is both reliably *typed* (so the swap can
#: never hit ordnance, a TGP, or anything UNKNOWN) and worth trading for the gas
#: that decides whether the jet reaches the target at all. OFFENSIVE_JAMMER (an
#: EW mission store) and DECOY (SEAD tactics ordnance) stay protected.
_DISPLACEABLE_TYPES = frozenset({WeaponType.JAMMER})


def _displaceable_stations(
    unit_type: AircraftType, loadout: Loadout
) -> dict[int, tuple[Weapon, float]]:
    """Stations carrying a displaceable pod that could hold a tank instead."""
    existing_tank_clsids = [
        weapon.clsid
        for weapon in loadout.pylons.values()
        if weapon is not None and is_fuel_tank(weapon.clsid)
    ]
    stations: dict[int, tuple[Weapon, float]] = {}
    for number, weapon in loadout.pylons.items():
        if weapon is None or weapon.weapon_group.type not in _DISPLACEABLE_TYPES:
            continue
        pylon = Pylon.for_aircraft(unit_type, number)
        tank = _best_tank_for_station(pylon, existing_tank_clsids)
        if tank is not None:
            stations[number] = (tank, tank_capacity_lbs(tank.clsid))
    return stations


def _refuel_passes(
    internal: float,
    external: float,
    taxi: float,
    fuel_to_end_of_vul: float,
    fuel_vul_to_home: float,
    reserve: float,
) -> int:
    """How many tanker passes the sortie needs with this fuel load (0, 1, or 2)."""
    from game.ato.refueltasking import RefuelTasking, decide_refuel_tasking

    full = internal + external
    tasking = decide_refuel_tasking(
        full - taxi, fuel_to_end_of_vul, fuel_vul_to_home, reserve, full
    )
    return {
        RefuelTasking.NONE: 0,
        RefuelTasking.PRE_VUL: 1,
        RefuelTasking.POST_VUL: 1,
        RefuelTasking.BOTH: 2,
    }[tasking]


def _equip_tank(loadout: Loadout, station: int, tank: Weapon) -> None:
    loadout.pylons[station] = tank
    loadout.pylon_settings.pop(station, None)


def _plan_loadout_fuel(
    unit_type: AircraftType,
    loadout: Loadout,
    *,
    internal: float,
    taxi: float,
    reserve: float,
    fuel_to_end_of_vul: float,
    fuel_vul_to_home: float,
    tanker_available: bool,
    allow_displacement: bool,
) -> bool:
    """Tank one loadout for the sortie, in place. Returns True if it changed.

    Tier 1 fills empty tank-capable stations while the sortie is short; tier 2
    (``allow_displacement``) trades jammer pods for tanks when the extra bag
    strictly reduces the tanker-pass count -- or, with no tanker in theater,
    whenever the sortie is still short (the bags are the only gas there is).
    """
    external = external_fuel_lbs(loadout)
    required_usable = fuel_to_end_of_vul + fuel_vul_to_home + reserve

    def short(ext: float) -> bool:
        return internal + ext - taxi < required_usable

    changed = False
    if short(external):
        empty = _empty_tank_stations(unit_type, loadout)
        for number in sorted(empty):
            if not short(external):
                break
            tank, capacity = empty[number]
            _equip_tank(loadout, number, tank)
            external += capacity
            changed = True

    if not allow_displacement:
        return changed
    candidates = _displaceable_stations(unit_type, loadout)
    if not candidates:
        return changed

    if not tanker_available:
        for number in sorted(candidates):
            if not short(external):
                break
            tank, capacity = candidates[number]
            _equip_tank(loadout, number, tank)
            external += capacity
            changed = True
        return changed

    def passes(ext: float) -> int:
        return _refuel_passes(
            internal, ext, taxi, fuel_to_end_of_vul, fuel_vul_to_home, reserve
        )

    current = passes(external)
    if current == 0:
        return changed
    best = passes(external + sum(capacity for _, capacity in candidates.values()))
    if best >= current:
        # Even every pod traded for a bag saves no pass: keep the pods.
        return changed
    for number in sorted(candidates):
        tank, capacity = candidates[number]
        _equip_tank(loadout, number, tank)
        external += capacity
        changed = True
        if passes(external) <= best:
            break
    return changed


def plan_sortie_fuel(
    flight: Flight,
    fuel: FuelConsumption,
    fuel_to_end_of_vul: float,
    fuel_vul_to_home: float,
    tanker_available: bool,
    settings: Settings,
) -> None:
    """Fuel-first pass: tank the flight for the sortie before tanker tasking.

    Mutates the members' persisted loadouts in place so every consumer (payload
    editor, kneeboard, fuel ladder, tanker decision, generation) agrees on what
    the jet carries. Shared Loadout objects are mutated once and stay shared;
    custom (player-edited) loadouts are never touched. Idempotent: a rebuilt
    flight plan finds the tanks already fitted and changes nothing.
    """
    if not settings.auto_range_fuel_tanks:
        return
    internal = flight.unit_type.max_fuel * KG_TO_LBS
    seen: set[int] = set()
    for member in flight.iter_members():
        loadout = member.loadout
        if loadout.is_custom or not loadout.pylons or id(loadout) in seen:
            continue
        seen.add(id(loadout))
        _plan_loadout_fuel(
            flight.unit_type,
            loadout,
            internal=internal,
            taxi=fuel.taxi,
            reserve=fuel.min_safe,
            fuel_to_end_of_vul=fuel_to_end_of_vul,
            fuel_vul_to_home=fuel_vul_to_home,
            tanker_available=tanker_available,
            allow_displacement=settings.fuel_tanks_over_jammers,
        )
