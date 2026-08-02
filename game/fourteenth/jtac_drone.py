"""Auto-field a JTAC drone squadron for a COIN campaign flying the packaged drone JTAC.

COIN campaigns replace the stock front-line JTAC (an invisible, immortal FAC orbiting the
FLOT) with the **packaged** drone-as-JTAC (see ``AircraftGenerator._maybe_configure_jtac``):
a real, killable drone flown in an air-to-ground package that lazes for the shooters from
inside the fight, because a COIN war has no front line worth orbiting. But that only fires
if a drone squadron actually *exists* and gets fragged -- and squadrons are created only
from a campaign's ``squadrons:`` block, so a COIN campaign that never lists a drone would
have no JTAC at all.

So, when the packaged drone JTAC is on: at New Game, for each blue side whose faction
declares a drone JTAC platform, auto-field **one small TARPS-tasked drone squadron at the
rear-most airfield**. The auto-recon hook (``_maybe_plan_tarps_recon``) then frags it forward
into A/G packages, where it becomes the JTAC, and -- being a drone -- it films the whole time
(a drone is always a sensor).

Deliberately conservative: it **skips** a side that already fields any drone squadron (a
campaign that hand-placed its drones -- e.g. Operation Inherent Resolve -- is untouched),
runs blue-only, and only for a drone that can actually fly TARPS (so it can self-frag).
Gated by ``coin_packaged_jtac_drone`` (the COIN JTAC model itself) and then by
``auto_jtac_drone`` as a kill switch for campaigns that want their air wing left exactly
as authored.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from game.ato.flighttype import FlightType
from game.data.units import UAV_DCS_IDS
from game.squadrons.squadron import Squadron

if TYPE_CHECKING:
    from game.coalition import Coalition
    from game.dcs.aircrafttype import AircraftType
    from game.theater import ControlPoint

#: A rear-based ISR detachment, not a strike wing -- kept small on purpose so the
#: auto-field never distorts a campaign's air balance.
JTAC_DRONE_SQUADRON_SIZE = 2

#: Real-world in-service year of each drone. Many factions carry a lazy default
#: ``jtac_unit: MQ-9 Reaper`` even in the 1980s/90s, so the auto-field is era-gated:
#: it never drops a drone that didn't exist yet onto a period campaign (Red Tide is
#: 1988 -- no Reaper). This is only a *floor* for the AUTO-field; a campaign that
#: deliberately fields a drone is its own author's call and is never removed here.
_UAV_SERVICE_YEAR = {
    "RQ-1A Predator": 1995,
    "MQ-9 Reaper": 2007,
    "WingLoong-I": 2014,
}


def ensure_jtac_drone_squadron(coalition: "Coalition") -> None:
    """Auto-field a JTAC drone squadron for *coalition* if it should have one.

    Call once per coalition at New Game, right after the campaign's own squadrons are
    assigned (``configure_default_air_wing``). No-op unless the side is blue, the campaign
    flies the COIN packaged drone JTAC, the ``auto_jtac_drone`` kill switch is on, the
    faction declares a TARPS-capable drone JTAC, and it does not already field a drone
    squadron.
    """
    game = coalition.game
    if not coalition.player.is_blue:
        return  # the JTAC feeds the human's lasing/BDA; the AI opponent needs none
    if not getattr(game.settings, "coin_packaged_jtac_drone", False):
        return  # a front-line-JTAC campaign needs no drone squadron fielded for this
    if not getattr(game.settings, "auto_jtac_drone", False):
        return
    faction = coalition.faction
    if not faction.has_jtac:
        return
    drone = faction.jtac_unit
    if drone is None or drone.dcs_unit_type.id not in UAV_DCS_IDS:
        return  # a crewed FAC (OV-10, Yak-52, ...) is not auto-fielded here
    if not drone.capable_of(FlightType.TARPS):
        return  # can't self-frag into A/G packages as a recon/JTAC overwatch
    if game.date.year < _UAV_SERVICE_YEAR.get(drone.dcs_unit_type.id, 0):
        return  # era gate: the drone didn't exist yet (a 1980s campaign's lazy MQ-9)

    air_wing = coalition.air_wing
    for squadron in air_wing.iter_squadrons():
        if squadron.aircraft.dcs_unit_type.id in UAV_DCS_IDS:
            return  # the campaign already fields drones -- don't double up

    base = _rearmost_operable_airfield(coalition, drone)
    if base is None:
        return  # no blue airfield can operate the drone

    squadron_def = air_wing.squadron_def_generator.generate_for_aircraft(drone)
    squadron = Squadron.create_from(
        squadron_def,
        FlightType.TARPS,
        JTAC_DRONE_SQUADRON_SIZE,
        base,
        coalition,
        game,
    )
    air_wing.add_squadron(squadron)
    logging.info(
        "Auto-fielded a %s JTAC drone squadron at %s (%s)",
        drone.variant_id,
        base.name,
        faction.name,
    )


def _rearmost_operable_airfield(
    coalition: "Coalition", drone: "AircraftType"
) -> Optional["ControlPoint"]:
    """The blue airfield deepest in the rear (farthest from the nearest enemy base)
    that can operate *drone* -- so the ISR detachment launches from safety and transits
    forward, rather than sitting under the guns at the front."""
    theater = coalition.game.theater
    friendly = coalition.player
    enemy = coalition.opponent.player
    operable = [
        cp
        for cp in theater.controlpoints
        if cp.captured == friendly and not cp.is_fleet and cp.can_operate(drone)
    ]
    if not operable:
        return None
    enemy_bases = [cp for cp in theater.controlpoints if cp.captured == enemy]
    if not enemy_bases:
        return operable[0]

    def rear_depth(cp: "ControlPoint") -> float:
        return min(cp.position.distance_to_point(e.position) for e in enemy_bases)

    return max(operable, key=rear_depth)
