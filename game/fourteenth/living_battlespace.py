"""Living battlespace P1: seat player packages later in the ATO cycle (§89).

The turn's ATO already launches across ~90 minutes; the player just launches at
the front of it. Delaying only the player's startup by a phase-aware pre-roll,
then marching the existing mission simulation to that startup before
generation, puts the rest of the war mid-cycle at spawn -- flights outbound, on
station, and recovering -- with no new spawn machinery.
Design: docs/dev/design/414th-living-battlespace-notes.md (P1).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from game.ato.flighttype import FlightType
from game.data.weapons import WeaponType

if TYPE_CHECKING:
    from game import Game
    from game.ato.airtaaskingorder import AirTaskingOrder
    from game.ato.flight import Flight
    from game.coalition import Coalition
    from game.data.weapons import Weapon
    from game.settings import Settings
    from game.theater import ControlPoint

#: Phase curve: minutes of war before the player's startup, by turn number. The
#: first flyable turn keeps its H-hour launch; every turn past the table runs
#: at the settings cap. Strawman values -- open call 1 in the design note.
_EARLY_TURN_PREROLL_MINUTES = {0: 0, 1: 15, 2: 15}


def preroll_minutes(settings: Settings, turn: int) -> int:
    """Minutes of pre-roll this turn, honoring the gate and the cap."""
    if not settings.living_battlespace_preroll:
        return 0
    cap: int = settings.living_battlespace_preroll_cap
    return min(cap, _EARLY_TURN_PREROLL_MINUTES.get(turn, cap))


def pin_player_packages(coalition: Coalition, now: datetime) -> None:
    """Delay each player package so its earliest startup is the pre-roll offset.

    Runs inside ``MissionScheduler.schedule_missions`` after the base TOT pass
    and BEFORE the §69 SEAD windows and the carrier-recovery stagger, so both
    see the pinned player TOTs (a player SEAD's window moves with it; the
    stagger treats player packages as fixed and spaces AI recoveries around
    the new slot). Only ever delays: a package already starting later than the
    offset keeps its schedule, and hand-planned packages are untouched because
    this only runs during auto-planning.
    """
    settings = coalition.game.settings
    # Same duck-typed gate shape as the §69 pass beside this one: the scheduler
    # tests drive schedule_missions with fake games, so the gate must decline
    # before reading anything past the settings object.
    if not getattr(settings, "living_battlespace_preroll", False):
        return
    minutes = preroll_minutes(settings, coalition.game.turn)
    if minutes <= 0:
        return
    desired = now + timedelta(minutes=minutes)
    for package in coalition.ato.packages:
        if not package.has_players:
            continue
        starts = [f.flight_plan.startup_time() for f in package.flights]
        if not starts:
            continue
        delta = desired - min(starts)
        if delta > timedelta():
            package.time_over_target += delta


#: Task families whose ordnance is spent at the target waypoint. Loiter-shaped
#: air-to-ground (CAS, Armed Recon, SEAD Sweep) is deliberately absent -- their
#: "target" waypoint is a patrol anchor, so passing it says nothing about racks.
_EXPENDED_TASKS = frozenset(
    {
        FlightType.STRIKE,
        FlightType.BAI,
        FlightType.SEAD,
        FlightType.DEAD,
        FlightType.OCA_RUNWAY,
        FlightType.OCA_AIRCRAFT,
        FlightType.ANTISHIP,
    }
)

#: Pod-class weapon types that survive the expended strip: sensors and jammers
#: come home. AAMs and tanks also strip in v1 -- the tree has no A2A/tank
#: weapon taxonomy to keep them by (WeaponType is ARM/LGB/pods/UNKNOWN), so a
#: returning striker flies a clean wing. Enriching resources/weapons `type:`
#: with AAM/TANK is the refinement path (design note, P2 status).
_KEPT_WEAPON_TYPES = frozenset(
    {
        WeaponType.TGP,
        WeaponType.JAMMER,
        WeaponType.OFFENSIVE_JAMMER,
        WeaponType.DECOY,
    }
)


def stores_expended(flight: Flight) -> bool:
    """Whether this flight spawns with its A2G ordnance already delivered.

    True only mid-cycle: gate on, a strike-family task, an in-flight state
    past the flight plan's target waypoint. Duck-typed on the state (the
    fake-flight tests and non-InFlight states decline via the attributes).
    """
    settings = flight.coalition.game.settings
    if not getattr(settings, "living_battlespace_preroll", False):
        return False
    if flight.flight_type not in _EXPENDED_TASKS:
        return False
    state = flight.state
    if not getattr(state, "in_flight", False):
        return False
    has_passed = getattr(state, "has_passed_waypoint", None)
    if has_passed is None:
        return False
    try:
        tot_waypoint = flight.flight_plan.tot_waypoint
    except (AttributeError, NotImplementedError):
        return False
    return bool(has_passed(tot_waypoint))


def weapon_survives_expenditure(weapon: Weapon) -> bool:
    return weapon.weapon_group.type in _KEPT_WEAPON_TYPES


def use_estimated_fuel_for_ai(flight: Flight) -> bool:
    """AI units spawned in flight carry burned-down fuel (§89 P2).

    Upstream writes the state's fuel estimate only for player units; a
    mid-cycle world spawns whole AI packages en route, and full tanks on an
    egressing flight read wrong. Gate off keeps upstream behavior.
    """
    settings = flight.coalition.game.settings
    if not getattr(settings, "living_battlespace_preroll", False):
        return False
    return bool(getattr(flight.state, "in_flight", False))


def recovery_residue_enabled(settings: Settings) -> bool:
    """Whether Completed flights leave parked jets at their arrival (§89 P2)."""
    return bool(getattr(settings, "living_battlespace_preroll", False))


# §89 P2 residue ledger: the sim removes a Completed flight from the ATO at the
# tick boundary (aircraftsimulation's removal loop), so generation's ATO walk
# only ever saw final-tick completions -- solo-flight packages (most CAPs)
# never rendered (row B57). The removal site records here; generation reads the
# ledger in addition to the walk. Transient process state on the fogofwar.py
# pattern: cleared at begin_simulation, never pickled.
_completed_residue: list[tuple[Flight, ControlPoint]] = []


def clear_completed_residue() -> None:
    """Reset the ledger. Called unconditionally at sim start so a new march,
    game, or gate flip never inherits another cycle's flights."""
    _completed_residue.clear()


def record_completed_residue(flight: Flight) -> None:
    """Record a flight the sim is about to remove from the ATO (§89 P2).

    Call from the removal site only -- that keeps the ledger and the ATO walk
    disjoint (recorded means removed), and keeps the generation-time synthetic
    Completed flights (idle ramp, QRA and red-scramble templates) out by
    construction. The arrival is frozen now because ``Squadron.arrival``
    follows a live relocation order: an order placed while the sim is paused
    must not retroactively move jets that already landed.
    """
    settings = flight.coalition.game.settings
    if not getattr(settings, "living_battlespace_preroll", False):
        return
    _completed_residue.append((flight, flight.arrival))


def idle_spawn_count(untasked_aircraft: int, residue_parked: int) -> int:
    """Idle ramp filler left to spawn after this squadron's residue (§89 P2).

    Removing a completed flight returns its airframes to the untasked pool,
    so residue jets are ALSO counted as untasked -- spawning the full pool
    would render the same airframes twice (row B57 fail signature 2).
    """
    return max(0, untasked_aircraft - residue_parked)


def residue_flights_for(
    ato: AirTaskingOrder, settings: Settings
) -> list[tuple[Flight, ControlPoint]]:
    """Ledger entries that should park at this ATO's coalition side."""
    if not recovery_residue_enabled(settings):
        return []
    return [
        (flight, arrival)
        for flight, arrival in _completed_residue
        if flight.squadron.coalition.ato is ato and flight.alive
    ]


def followon_window_minutes(coalition: Coalition) -> int:
    """Minutes the AI TOT spread extends past the desired mission length (§89 P3).

    Symmetric with the pre-roll: the same phase-aware minutes the player is
    seated INTO the cycle are appended to its tail, so follow-on packages
    launch as/after the player recovers. Duck-typed gate first -- the
    scheduler tests drive this with fake games.
    """
    settings = coalition.game.settings
    if not getattr(settings, "living_battlespace_preroll", False):
        return 0
    return preroll_minutes(settings, coalition.game.turn)


def preroll_brief_lines(game: Game) -> list[str]:
    """Briefing lines for the air war's state at generation time (§89 P3).

    Empty with the gate off, and empty when nothing has moved yet (an H-hour
    launch), which suppresses the briefing section entirely. State matching is
    by class name so briefing generation never imports the state classes and
    the fake-flight tests stay cheap. Recovered flights mostly left the ATO at
    the tick boundary (the removal loop), so that count reads the residue
    ledger too -- the walk alone reported 0 forever (row B57).
    """
    if not getattr(game.settings, "living_battlespace_preroll", False):
        return []
    lines: list[str] = []
    for coalition, label in ((game.blue, "Friendly"), (game.red, "Enemy")):
        airborne = recovered = lost = 0
        for package in coalition.ato.packages:
            for flight in package.flights:
                state = flight.state
                if getattr(state, "in_flight", False):
                    airborne += 1
                elif type(state).__name__ == "Completed":
                    recovered += 1
                elif type(state).__name__ == "Killed":
                    lost += 1
        recovered += sum(
            1 for f, _ in _completed_residue if f.squadron.coalition is coalition
        )
        if airborne or recovered or lost:
            suffix = "" if label == "Friendly" else " (assessed)"
            lines.append(
                f"{label}: airborne {airborne}, recovered {recovered}, "
                f"lost {lost}{suffix}."
            )
    return lines


#: §89 P5: the reaction-alert package name prefix -- the emitter finds the
#: generated reaction groups by it, so the two sides never carry a shared id.
REACTION_PACKAGE_PREFIX = "Reaction Alert"

#: How many red reaction flights are fragged per turn. The pool is the cap:
#: the plugin can only ever launch what the planner really claimed.
REACTION_FLIGHTS_CAP = 2


def plan_red_reactions(coalition: Coalition, now: datetime) -> None:
    """Frag the red reaction-alert flights into the red ATO (§89 P5).

    Real flights from real inventory (normal claiming, normal debrief): each
    is a 2-ship home-defense BARCAP whose TOT is parked hours past the mission,
    so it only ever flies when the ``reactivered`` plugin activates it early
    over a struck objective. Runs AFTER MissionScheduler so the spread never
    touches them, and only for the red coalition -- the reaction stays inside
    red's settled defensive fighter posture (a defensive CAP over its own
    struck objective, never an offensive tasking).
    """
    from game.ato.flight import Flight
    from game.ato.package import Package
    from game.ato.starttype import StartType
    from game.theater import Airfield, HomeBaseDefenseZone

    settings = coalition.game.settings
    if not getattr(settings, "living_battlespace_preroll", False):
        return
    if not getattr(settings, "living_battlespace_reactive_red", False):
        return
    if not coalition.player.is_red:
        return
    made = 0
    for squadron in coalition.air_wing.iter_squadrons():
        if made >= REACTION_FLIGHTS_CAP:
            break
        if not isinstance(squadron.location, Airfield):
            continue
        if not squadron.capable_of(FlightType.BARCAP):
            continue
        if squadron.untasked_aircraft < 2:
            continue
        base = squadron.location
        target = HomeBaseDefenseZone(
            f"{REACTION_PACKAGE_PREFIX} {base.name}", base.position, coalition
        )
        package = Package(
            target,
            coalition.game.db.flights,
            auto_asap=False,
            custom_name=f"{REACTION_PACKAGE_PREFIX} ({squadron})",
        )
        try:
            flight = Flight(
                package,
                squadron,
                2,
                FlightType.BARCAP,
                StartType.COLD,
                divert=None,
            )
        except Exception:
            logging.info(
                "BSNET reactions: could not claim a reaction flight from %s", squadron
            )
            continue
        package.add_flight(flight)
        flight.recreate_flight_plan()
        # Parked far past the mission: WaitingForStart with an hours-long delay
        # generates a late-activation group whose own trigger never matters --
        # the plugin's early activate() is the only way it flies.
        package.time_over_target = now + timedelta(hours=8)
        coalition.ato.add_package(package)
        made += 1
    if made:
        logging.info("BSNET reactions: fragged %d red reaction alert flights", made)


def auto_preroll_stop_needed(game: Game) -> bool:
    """Whether the launch flow should force a PLAYER_STARTUP fast-forward.

    True when this turn has a pre-roll and a player flight exists to stop on.
    The launch path runs the existing sim fast-forward under a temporary
    PLAYER_STARTUP stop condition when the user's own stop condition
    (DISABLED/MANUAL) would otherwise skip the march and spawn the whole
    pre-roll's worth of war on the ramp.
    """
    if preroll_minutes(game.settings, game.turn) <= 0:
        return False
    return game.ato_has_clients()
