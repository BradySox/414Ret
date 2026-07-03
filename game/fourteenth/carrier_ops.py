"""Long-range carrier strike planning (414th) — a deterministic carrier package the
stock auto-planner won't build.

The COIN campaign parks the carrier ~800 km off the Helmand AO (the real OEF
Arabian-Sea cycle). The stock planner never anticipated that standoff: its plane
range gate (``Squadron.capable_of`` vs ``max_mission_range_planes``) rejects every
carrier squadron because the targets sit 400-500 NM away, so the Hornets, the A-6
tankers, and the E-2 all sit on the deck while the land-based air does the whole war.
Raising ``max_mission_range_planes`` gets the Hornets *assignable*, but the theater
support planner still won't crew the carrier's own tanker/AEWC out there (its tanker
orbit sits at the closest land field, the probe A-6 can't reach it, and the AEWC/
tanker support packages prune when the fighter-poor COIN wing can't spare their
escorts).

So we build the package the user actually wants, deterministically, from the carrier's
own squadrons: **N F/A-18 on a strike target + one A-6E tanker + one E-2 on AEWC**. The
tanker and the E-2 ride as PRIMARY package flights (not escorts -- the ``EscortType.Refuel``
path is a dead end that always prunes; see ``plan_carrier_strike``), so the A-6 gets a
tanker orbit off the boat (launch + recovery gas) and the E-2 an AEWC orbit. It reuses the
engine's own ``PackageFulfiller`` (proper flight plans, waypoints, fuel, TOT), pinning
the carrier airframes via ``ProposedFlight.preferred_type`` and bypassing the range gate
with ``ignore_range=True``. Runs once per plan pass from ``Coalition.plan_missions``,
*before* the commander's ATO so the boat's Hornets are claimed for this package first
(the commander then flies any spares), and ``MissionScheduler`` still times it in.

Everything is behind ``long_range_carrier_ops`` (default OFF, campaign-preseeded).
BLUE only, guarded at every step -- no carrier, no Hornets, no legal target ⇒ no-op.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from game.ato.flighttype import FlightType
from game.commander.missionproposals import ProposedFlight, ProposedMission

if TYPE_CHECKING:
    from datetime import datetime

    from game.coalition import Coalition
    from game.dcs.aircrafttype import AircraftType
    from game.game import Game
    from game.profiling import MultiEventTracer
    from game.squadrons.squadron import Squadron
    from game.theater import ControlPoint, MissionTarget

#: F/A-18 shooters per carrier strike (a section). Small on purpose -- one sustainable
#: coordinated package a turn, not the whole air wing surged off the deck.
STRIKE_SECTION_SIZE = 2


def plan_carrier_strike(
    coalition: "Coalition", now: "datetime", tracer: "MultiEventTracer"
) -> None:
    """Add one deterministic long-range carrier strike package to the ATO.

    No-op unless ``long_range_carrier_ops`` is on and this is the BLUE coalition.
    Idempotent per plan pass by the ``has`` guard below (one carrier package a turn).
    """
    game = coalition.game
    if not coalition.player.is_blue:
        return
    if not getattr(game.settings, "long_range_carrier_ops", False):
        return

    carrier = _friendly_carrier(coalition)
    if carrier is None:
        return
    if _already_planned_from(coalition, carrier):
        return

    strike_sqn = _carrier_squadron(coalition, carrier, FlightType.STRIKE)
    if strike_sqn is None:
        return
    target = _nearest_legal_strike_target(game, carrier)
    if target is None:
        return

    flights = [
        ProposedFlight(
            FlightType.STRIKE,
            STRIKE_SECTION_SIZE,
            preferred_type=strike_sqn.aircraft,
        )
    ]
    # The tanker and the E-2 ride as PRIMARY package flights, not escorts: the
    # EscortType.Refuel path is a dead end (check_needed_escorts never marks refuel
    # "needed", so an escort tanker always prunes), and an AEWC escort would prune the
    # same way. As primaries they always plan -- the A-6 gets a tanker orbit off the
    # carrier (launch + recovery tanking, the boat's own gas) and the E-2 an AEWC orbit.
    tanker_type = _carrier_aircraft(coalition, carrier, FlightType.REFUELING)
    if tanker_type is not None:
        flights.append(
            ProposedFlight(FlightType.REFUELING, 1, preferred_type=tanker_type)
        )
    aewc_type = _carrier_aircraft(coalition, carrier, FlightType.AEWC)
    if aewc_type is not None:
        flights.append(ProposedFlight(FlightType.AEWC, 1, preferred_type=aewc_type))

    from game.commander.packagefulfiller import PackageFulfiller

    fulfiller = PackageFulfiller(
        coalition, game.theater, game.db.flights, game.settings
    )
    with tracer.trace("Blue long-range carrier strike"):
        package = fulfiller.plan_mission(
            ProposedMission(target, flights, asap=False),
            0,  # purchase_multiplier: never buy jets for this, use what's aboard
            now,
            tracer,
            ignore_range=True,
        )
    if package is None:
        logging.debug("Carrier strike: PackageFulfiller could not build the package")
        return
    coalition.ato.add_package(package)
    logging.info(
        "Carrier strike: %s (%d flights) fragged from %s onto %s",
        strike_sqn.aircraft.display_name,
        len(package.flights),
        carrier.name,
        target.name,
    )


def _friendly_carrier(coalition: "Coalition") -> Optional["ControlPoint"]:
    for cp in coalition.game.theater.controlpoints:
        if getattr(cp, "is_carrier", False) and cp.captured == coalition.player:
            return cp
    return None


def _already_planned_from(coalition: "Coalition", carrier: "ControlPoint") -> bool:
    """True if the ATO already has a strike package flying off this carrier -- keeps
    this to one carrier package per plan pass (and never doubles a commander package
    that happened to use the boat)."""
    for package in coalition.ato.packages:
        for flight in package.flights:
            if flight.departure == carrier and flight.flight_type is FlightType.STRIKE:
                return True
    return False


def _carrier_squadron(
    coalition: "Coalition", carrier: "ControlPoint", task: FlightType
) -> Optional["Squadron"]:
    """A carrier-based squadron that can fly *task* and has airframes, or None."""
    best: Optional["Squadron"] = None
    for squadron in coalition.air_wing.iter_squadrons():
        if squadron.location != carrier:
            continue
        if squadron.owned_aircraft <= 0:
            continue
        if not squadron.capable_of(task):
            continue
        if best is None or squadron.owned_aircraft > best.owned_aircraft:
            best = squadron
    return best


def _carrier_aircraft(
    coalition: "Coalition", carrier: "ControlPoint", task: FlightType
) -> Optional["AircraftType"]:
    squadron = _carrier_squadron(coalition, carrier, task)
    return squadron.aircraft if squadron is not None else None


def _nearest_legal_strike_target(
    game: "Game", carrier: "ControlPoint"
) -> Optional["MissionTarget"]:
    """The nearest enemy strike-worthy ground object to the carrier that the ROE
    doesn't lock (so the carrier package never gets fragged into a population ring --
    the same restraint the rest of the BLUE planner honors).

    Prefers ammo caches (the COIN throttle -- thematically the carrier's job) but
    falls back to any strikeable enemy TGO.
    """
    from game.fourteenth.phases import roe_blocks_target

    caches: list[tuple[float, "MissionTarget"]] = []
    others: list[tuple[float, "MissionTarget"]] = []
    for cp in game.theater.controlpoints:
        if not cp.captured.is_red:
            continue
        for tgo in cp.ground_objects:
            if not any(unit.alive for unit in tgo.units):
                continue
            if getattr(tgo, "is_control_point", False):
                continue
            if roe_blocks_target(game, tgo):
                continue
            dist = carrier.position.distance_to_point(tgo.position)
            if getattr(tgo, "category", None) == "ammo":
                caches.append((dist, tgo))
            else:
                others.append((dist, tgo))
    pool = caches or others
    if not pool:
        return None
    return min(pool, key=lambda item: item[0])[1]
