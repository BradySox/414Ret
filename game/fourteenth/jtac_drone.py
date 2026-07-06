"""Auto-field a JTAC drone squadron so every JTAC-capable side actually has one.

The 414th ripped out the old FLOT auto-JTAC (a ``jtac_unit`` MQ-9 spawned glued to the
front line). Its replacement is the **packaged** drone-as-JTAC (see
``AircraftGenerator._maybe_configure_jtac``): a drone flown in an air-to-ground package
lazes for the shooters. But that only fires if a drone squadron actually *exists* and gets
fragged -- and squadrons are created only from a campaign's ``squadrons:`` block. So on the
55+ campaigns that never list a drone, no JTAC would ever appear.

This restores the "every JTAC-capable side has a JTAC" behaviour the FLOT drone had, as a
real packaged squadron: at New Game, for each blue side whose faction declares a drone JTAC
platform, auto-field **one small TARPS-tasked drone squadron at the rear-most airfield**. The
auto-recon hook (``_maybe_plan_tarps_recon``) then frags it forward into A/G packages, where
it becomes a JTAC (drone-JTAC), and -- being a drone -- it films the whole time (a drone is
always a sensor). No FLOT unit, no invisible/immortal drone: a real, killable asset that
rides the fight.

Deliberately conservative: it **skips** a side that already fields any drone squadron (a
campaign that hand-placed its drones -- e.g. Operation Inherent Resolve -- is untouched),
runs blue-only, and only for a drone that can actually fly TARPS (so it can self-frag). Gated
by ``auto_jtac_drone`` (default ON) as a kill switch for balance-sensitive campaigns.
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


def ensure_jtac_drone_squadron(coalition: "Coalition") -> None:
    """Auto-field a JTAC drone squadron for *coalition* if it should have one.

    Call once per coalition at New Game, right after the campaign's own squadrons are
    assigned (``configure_default_air_wing``). No-op unless the side is blue, the
    ``auto_jtac_drone`` setting is on, the faction declares a TARPS-capable drone JTAC,
    and it does not already field a drone squadron.
    """
    game = coalition.game
    if not coalition.player.is_blue:
        return  # the JTAC feeds the human's lasing/BDA; the AI opponent needs none
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
