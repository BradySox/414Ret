"""Auto-planned convoy mining (§57 Phase 3) — frag an air-drop mining sortie at a convoy.

With ``auto_plan_minefields`` on, the BLUE auto-planner frags one mining sortie a turn against an
enemy supply convoy: a mining-capable aircraft (one that carries the CBU-99 **"Aerial Minefield"**
loadout — the A-7E / Hornet / Harrier) flies BAI at the convoy and drops the dispenser, and the
runtime plugin lays the proximity field there (§57 P1). This honors the premise that the **only**
way a minefield is laid is an air-drop — it just gets the AI (or the player, if they fly the
fragged sortie) to fly one. The field and any convoy kill belong to the plugin + the turn-boundary
force model (no phantom spawns).

Hooked in ``Coalition.plan_missions`` (the §44 carrier-ops pattern), **before** the commander so
the mining jet is claimed for this package first. Gated ``auto_plan_minefields`` (default OFF) +
``air_droppable_minefields`` — a no-op for red, a wing with no CBU-99 aircraft, or a turn with no
enemy convoy.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.commander.missionproposals import ProposedFlight, ProposedMission

if TYPE_CHECKING:
    from datetime import datetime

    from game.ato.package import Package
    from game.coalition import Coalition
    from game.dcs.aircrafttype import AircraftType
    from game.game import Game
    from game.profiling import MultiEventTracer
    from game.squadrons.squadron import Squadron
    from game.transfers import Convoy

#: The customized-payload preset carrying the CBU-99 dispenser (§57 P1). Outside the
#: ``Retribution <task>`` namespace on purpose — there is no Minefield FlightType; we force it
#: here by name onto a BAI sortie.
MINE_LOADOUT_NAME = "Aerial Minefield"
#: Bombers per mining sortie (a section). One sustainable package a turn, not a surge.
MINE_FLIGHT_SIZE = 2


def plan_convoy_mining(
    coalition: "Coalition", now: "datetime", tracer: "MultiEventTracer"
) -> None:
    """Add one auto-planned convoy-mining package to the ATO.

    No-op unless ``auto_plan_minefields`` (and its ``air_droppable_minefields`` parent) are on and
    this is BLUE. Idempotent per plan pass via the already-planned guard.
    """
    game = coalition.game
    if not coalition.player.is_blue:
        return
    if not getattr(game.settings, "auto_plan_minefields", False):
        return
    if not getattr(game.settings, "air_droppable_minefields", False):
        return
    if _already_planned(coalition):
        return

    squadron = _mining_squadron(coalition)
    if squadron is None:
        return
    convoy = _enemy_convoy(game)
    if convoy is None:
        return

    from game.commander.packagefulfiller import PackageFulfiller

    flights = [
        ProposedFlight(
            FlightType.BAI, MINE_FLIGHT_SIZE, preferred_type=squadron.aircraft
        )
    ]
    fulfiller = PackageFulfiller(
        coalition, game.theater, game.db.flights, game.settings
    )
    with tracer.trace("Blue convoy mining"):
        package = fulfiller.plan_mission(
            ProposedMission(convoy, flights, asap=False), 0, now, tracer
        )
    if package is None:
        logging.debug("Convoy mining: PackageFulfiller could not build the package")
        return
    if not _arm_dispensers(package, squadron.aircraft):
        # Could not load the CBU-99 dispenser -> the sortie would fly BAI with bombs and lay no
        # mine, which defeats the purpose. Drop it rather than frag a pointless package.
        logging.debug(
            "Convoy mining: no %r loadout for %s; dropping the package",
            MINE_LOADOUT_NAME,
            squadron.aircraft,
        )
        return
    coalition.ato.add_package(package)
    logging.info(
        "Convoy mining: %s (%d) fragged to mine convoy %s",
        squadron.aircraft.display_name,
        len(package.flights),
        convoy.name,
    )


def _mine_loadout(aircraft: "AircraftType") -> Optional[Loadout]:
    """The aircraft's ``"Aerial Minefield"`` payload preset (with the CBU-99 dispenser), or None
    if it carries no such preset."""
    for loadout in Loadout.iter_for_aircraft(aircraft):
        if loadout.name == MINE_LOADOUT_NAME:
            return loadout
    return None


def _has_mine_loadout(aircraft: "AircraftType") -> bool:
    return _mine_loadout(aircraft) is not None


def _mining_squadron(coalition: "Coalition") -> Optional["Squadron"]:
    """The biggest BLUE squadron that can fly BAI, has airframes, and carries the dispenser
    loadout, or None (a wing with no CBU-99 aircraft can't mine)."""
    best: Optional["Squadron"] = None
    for squadron in coalition.air_wing.iter_squadrons():
        if squadron.owned_aircraft <= 0:
            continue
        if not squadron.capable_of(FlightType.BAI):
            continue
        if not _has_mine_loadout(squadron.aircraft):
            continue
        if best is None or squadron.owned_aircraft > best.owned_aircraft:
            best = squadron
    return best


def _enemy_convoy(game: "Game") -> Optional["Convoy"]:
    """An enemy (RED) supply convoy with live units to mine, or None."""
    for convoy in getattr(game.red.transfers, "convoys", []):
        if getattr(convoy, "size", 0) > 0:
            return convoy
    return None


def _arm_dispensers(package: "Package", aircraft: "AircraftType") -> bool:
    """Force the ``"Aerial Minefield"`` loadout onto every mining-aircraft flight in the package
    (a fresh Loadout per member so a later date-degrade can't be shared). Returns True if at least
    one flight was armed."""
    armed = False
    for flight in package.flights:
        if flight.unit_type != aircraft:
            continue
        for member in flight.iter_members():
            loadout = _mine_loadout(aircraft)
            if loadout is None:
                return False
            member.loadout = loadout
            member.use_custom_loadout = True
        armed = True
    return armed


def _already_planned(coalition: "Coalition") -> bool:
    """True if the ATO already carries a mining sortie this pass (one per turn)."""
    for package in coalition.ato.packages:
        for flight in package.flights:
            for member in flight.iter_members():
                loadout = getattr(member, "loadout", None)
                if loadout is not None and loadout.name == MINE_LOADOUT_NAME:
                    return True
    return False
