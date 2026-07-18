"""Pilot recovery surge -- the "drop everything and get them home" op (§21 extension).

The standing rescue paths are slow-movers: the on-demand AI helo (auto_combat_sar)
starts cold at a rear field when the pilot goes down, and the 2026-07-17 flown test
had it *still in transit 1.4 h later*. The campaign answer is not a faster helo --
it is that the **next turn opens with the recovery op already airborne**: when a
pilot went MIA last mission (the §21 persistent-evader ledger, ``game.downed_pilots``),
BLUE frags one coordinated recovery package **at the evader's position** before the
commander plans anything else:

* rescue helo(s) ("Jolly", one flight per evader up to a cap) -- the pickup,
* a C-130 "King" on-scene commander (TACAN beacon + LARS), when the wing has one,
* a 2-ship "Sandy" SCAR escort, when the wing has one,
* a 2-ship A2A escort (pruned by the normal escort logic when no air threat).

The package targets a ``PilotRecoveryZone`` at the evaders' position, so
``CombatSarFlightPlan`` holds its racetrack a short distance friendly-side of the
*survivor* instead of the front centre; it is planned ASAP and the AI COMBAT_SAR
flights **air-start** (the existing ``PackageBuilder`` rule), so the op is on
station when the mission begins -- the runtime combatsar ledger then dispatches the
helo onto the re-spawned evader (``persistentSurvivors``) within minutes, and the
package helo suppresses the on-demand clone (``autoSpawn``) as usual.

**The gate** (squadron call 2026-07-17: "so it's not every mission"): the surge
fires **once per downed pilot** -- each ledger entry is stamped ``surge_turn`` when
its op is planned, and a stamped evader never draws another surge (the normal
paths -- player package, auto-CSAR, the walk-home/capture rolls -- continue). No
evader without a stamp, no surge, no package: quiet missions stay quiet.

BLUE only (red flies no CSAR -- the §21 rejected-symmetry call). Runs from
``Coalition.plan_missions`` before ``TheaterCommander`` so the surge claims its
helos/Sandys/escorts first -- that is what "drop everything" means. Gated by
``combat_sar_surge`` (default ON), which depends on ``combat_sar_persistent_pilots``
(no ledger, no evaders, nothing to surge for).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from game.ato.flighttype import FlightType
from game.commander.missionproposals import EscortType, ProposedFlight, ProposedMission

if TYPE_CHECKING:
    from datetime import datetime

    from game.coalition import Coalition
    from game.fourteenth.downed_pilots import DownedPilot
    from game.game import Game
    from game.profiling import MultiEventTracer
    from game.squadrons.squadron import Squadron
    from game.theater import PilotRecoveryZone

#: At most this many rescue-helo flights per surge (one 1-ship flight per evader --
#: the runtime dispatches each helo group to one survivor, so multiple survivors
#: need multiple groups). The first flight is required; extras drop silently when
#: the wing is thin.
SURGE_MAX_HELO_FLIGHTS = 2
#: "Sandy" SCAR rescue-escort section size (the §15 package shape).
SANDY_FLIGHT_SIZE = 2
#: A2A escort section size. Proposed optional + escort-typed, so the normal escort
#: logic prunes it with no air threat and a fighter-poor wing just drops it.
ESCORT_FLIGHT_SIZE = 2


def plan_pilot_recovery_surge(
    coalition: "Coalition", now: "datetime", tracer: "MultiEventTracer"
) -> None:
    """Frag the next-turn coordinated recovery package for newly-MIA pilots.

    No-op unless this is BLUE, ``combat_sar_surge`` is on, an un-surged evader
    exists, and the wing fields a rescue-capable helo squadron.
    """
    game = coalition.game
    if not coalition.player.is_blue:
        return
    if not getattr(game.settings, "combat_sar_surge", False):
        return
    evaders = _surge_eligible_evaders(game)
    if not evaders:
        return
    if _rescue_already_planned(coalition):
        return

    helo_sqn = _rescue_squadron(coalition, helicopter=True)
    if helo_sqn is None:
        # A surge that cannot pick anyone up is noise; the capture race and the
        # normal paths carry on. Not stamped, so a helo bought later still surges.
        logging.info("Pilot recovery surge: no rescue-helo squadron available")
        return

    zone = _recovery_zone(coalition, evaders)
    flights = [
        ProposedFlight(FlightType.COMBAT_SAR, 1, preferred_type=helo_sqn.aircraft)
    ]
    for _ in range(min(len(evaders), SURGE_MAX_HELO_FLIGHTS) - 1):
        flights.append(
            ProposedFlight(
                FlightType.COMBAT_SAR,
                1,
                preferred_type=helo_sqn.aircraft,
                optional=True,
            )
        )
    king_sqn = _rescue_squadron(coalition, helicopter=False)
    if king_sqn is not None:
        flights.append(
            ProposedFlight(
                FlightType.COMBAT_SAR,
                1,
                preferred_type=king_sqn.aircraft,
                optional=True,
            )
        )
    if _squadron_for(coalition, FlightType.SCAR) is not None:
        flights.append(
            ProposedFlight(FlightType.SCAR, SANDY_FLIGHT_SIZE, optional=True)
        )
    flights.append(
        ProposedFlight(
            FlightType.ESCORT,
            ESCORT_FLIGHT_SIZE,
            escort_type=EscortType.AirToAir,
            optional=True,
        )
    )

    from game.commander.packagefulfiller import PackageFulfiller

    fulfiller = PackageFulfiller(
        coalition, game.theater, game.db.flights, game.settings
    )
    with tracer.trace("Blue pilot recovery surge"):
        package = fulfiller.plan_mission(
            ProposedMission(zone, flights, asap=True),
            0,  # purchase_multiplier: never buy airframes for the surge
            now,
            tracer,
            # A rescue is flown regardless of the range tables: the AI COMBAT_SAR
            # flights air-start (PackageBuilder), so transit is not the limiter.
            ignore_range=True,
        )
    if package is None:
        logging.info("Pilot recovery surge: package could not be planned")
        return
    coalition.ato.add_package(package)
    for dp in evaders:
        dp.surge_turn = game.turn
    names = ", ".join(_label(dp) for dp in evaders)
    logging.info(
        "Pilot recovery surge fragged (%d flights) for: %s", len(package.flights), names
    )
    game.message(
        "Pilot recovery surge",
        f"A coordinated recovery package has been fragged for {names}. "
        "The rescue force opens the mission on station -- protect the pickup.",
    )


def _surge_eligible_evaders(game: "Game") -> list["DownedPilot"]:
    """Evaders who have never had their surge (``surge_turn`` unset), plus any
    stamped THIS turn (a re-plan pass re-plans the same op after an ATO reset)."""
    eligible: list["DownedPilot"] = []
    for dp in getattr(game, "downed_pilots", None) or []:
        stamped = getattr(dp, "surge_turn", 0)
        if stamped == 0 or stamped == game.turn:
            eligible.append(dp)
    return eligible


def _rescue_already_planned(coalition: "Coalition") -> bool:
    """One recovery op per plan pass: skip if the ATO already carries a Combat SAR
    flight (this surge on a re-entrant call, or any other CSAR source)."""
    for package in coalition.ato.packages:
        for flight in package.flights:
            if flight.flight_type is FlightType.COMBAT_SAR:
                return True
    return False


def _recovery_zone(
    coalition: "Coalition", evaders: list["DownedPilot"]
) -> "PilotRecoveryZone":
    from game.theater import PilotRecoveryZone

    game = coalition.game
    x = sum(dp.x for dp in evaders) / len(evaders)
    y = sum(dp.y for dp in evaders) / len(evaders)
    position = game.point_in_world(x, y)
    if len(evaders) == 1:
        name = f"Recovery: {_label(evaders[0])}"
    else:
        name = f"Recovery: {len(evaders)} downed pilots"
    return PilotRecoveryZone(name, position, coalition)


def _label(dp: "DownedPilot") -> str:
    if dp.pilot is not None:
        return dp.pilot.name
    if dp.aircraft:
        return f"the {dp.aircraft} pilot"
    return "a downed pilot"


def _rescue_squadron(coalition: "Coalition", helicopter: bool) -> Optional["Squadron"]:
    """The biggest stocked COMBAT_SAR-capable squadron of the given airframe kind
    (helo = the "Jolly" pickup, fixed-wing = the "King" C-130), or None."""
    best: Optional["Squadron"] = None
    for squadron in coalition.air_wing.iter_squadrons():
        if squadron.owned_aircraft <= 0:
            continue
        if not squadron.capable_of(FlightType.COMBAT_SAR):
            continue
        if bool(squadron.aircraft.helicopter) is not helicopter:
            continue
        if best is None or squadron.owned_aircraft > best.owned_aircraft:
            best = squadron
    return best


def _squadron_for(coalition: "Coalition", task: FlightType) -> Optional["Squadron"]:
    for squadron in coalition.air_wing.iter_squadrons():
        if squadron.owned_aircraft > 0 and squadron.capable_of(task):
            return squadron
    return None
