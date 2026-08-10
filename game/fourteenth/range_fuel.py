"""External-fuel-tank accounting.

Reports the fuel a flight carries in its drop tanks. Consumers are display-side:
the kneeboard fuel ladder and bingo estimate
(:mod:`game.missiongenerator.aircraft.waypoints.waypointgenerator`) and the
Edit-flight Payload tab readout (:mod:`game.fourteenth.fuel_brief`), both of which
need to know that a jet's usable fuel is more than its internal capacity.

Nothing here fits, removes, or otherwise plans stores -- a flight carries exactly
the tanks its loadout preset (or the player) gave it. The route-aware tank-fitting
that used to live here was feature §46, reverted 2026-08-09 with the rest of the
auto-planner re-convergence to upstream; see
``docs/dev/design/414th-autoplanner-upstream-divergence-audit.md``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import dcs.weapons_data as weapons_data

from game.utils import KG_TO_LBS

if TYPE_CHECKING:
    from game.ato.flight import Flight
    from game.ato.loadouts import Loadout

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
    diverge; the readout has to describe the driest jet in the flight.
    """
    external = [external_fuel_lbs(m.loadout) for m in flight.iter_members()]
    if not external:
        return 0.0
    return min(external)
