"""Growler escort-jamming emitter (dcsRetribution.growler).

The ESCORT_JAMMER planner role puts an EW-capable jet on the package's
join->split leg; this emits each such flight, the package group names it
protects, and its **graduated tier** (§77), and the ``growler`` plugin drives
the scripted jamming effects at runtime (the Timberwolf/Matador escort-geometry
family the C-130 §2 systems descend from). Escort jamming is a *role*, not one
airframe -- the effect scales to how real the jet's EW kit is:

- ``full`` (Growler / Prowler, ALQ-99): strong missile-spoof bubble over the
  package **plus** offensive ROE ``WEAPON_HOLD`` pulses on radar SAMs.
- ``ecm`` / ``self_protect`` / ``loose``: defensive bubble only, at descending
  strength -- no offensive suppression.

ROE only -- the plugin never touches ``enableEmission`` (the C-130 crash lesson)
and owns no kills. A player-crewed jammer is emitted with ``isPlayer`` so the
plugin offers the F10 jamming menu instead of the AI auto-policy. No
ESCORT_JAMMER flight -> no node -> the plugin no-ops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.ato import FlightType
from game.data.escort_jamming import EscortJammerTier, effect_for
from game.theater import Player

if TYPE_CHECKING:
    from game import Game

    from .aircraft.flightdata import FlightData
    from .luagenerator import LuaData
    from .missiondata import MissionData


def _tier_for(flight: "FlightData") -> EscortJammerTier:
    """The flight's escort-jamming tier, defaulting a stray untagged jammer to
    the defensive-only SELF_PROTECT tier (a planned jammer always does *something*
    defensive, but only a tagged dedicated jet ever suppresses SAMs)."""
    return flight.aircraft_type.escort_jammer_tier or EscortJammerTier.SELF_PROTECT


def populate_growler_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    jammers = [
        flight
        for flight in mission_data.flights
        if flight.flight_type is FlightType.ESCORT_JAMMER
    ]
    if not jammers:
        return

    growler = root.add_item("growler")
    entries = growler.add_item("jammers")
    for flight in jammers:
        tier = _tier_for(flight)
        effect = effect_for(tier)
        record = entries.add_item()
        # NB: scalars are emitted as child items (add_item().set_value()), not
        # add_key_value -- LuaData drops plain key-values from a node that also
        # carries nested objects (the `protected` list below).
        record.add_item("groupName").set_value(flight.group_name)
        record.add_item("side").set_value(
            "2" if flight.friendly is Player.BLUE else "1"
        )
        record.add_item("isPlayer").set_value("1" if flight.client_units else "0")
        record.add_item("tier").set_value(tier.value)
        # Effect knobs derived from the tier: the plugin scales its spoof bands by
        # defensivePower and only runs the SAM-suppression loop when offensive=1.
        record.add_item("defensivePower").set_value(str(effect.defensive_power))
        record.add_item("offensive").set_value("1" if effect.offensive else "0")
        protected = record.add_item("protected")
        for other in mission_data.flights:
            if other.package is flight.package and other is not flight:
                member = protected.add_item()
                member.add_key_value("groupName", other.group_name)
