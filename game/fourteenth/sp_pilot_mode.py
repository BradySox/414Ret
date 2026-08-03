"""SP Pilot Mode -- the aircraft-first sortie board.

Single-player campaigns die after turn 1, and the asymmetry against the 414th's
multiplayer campaigns is stark: **in MP you play a pilot; in SP you play the DM
*and* the pilot, and the DM job has no fun in it.** In an MP event the host
processes the turn, builds the ATO and generates the mission once for eight
sorties; in SP one person pays that cost for one sortie, before any reward. The
stop point is reproducible -- the player accepts the results and quits at
"now plan turn 2".

This module is the data layer for the express lane that removes it. It answers
two questions and nothing else:

1. **What can I fly?** -- every airframe the wing can actually put up, listed
   whether or not the commander happened to frag it. The airframe is the
   *primary* axis by DM specification ("I like to fly a lot of different
   aircraft"); a flat list of sorties would keep offering the same three Hornet
   missions because that is what the planner chose.
2. **Which sortie, in that jet?** -- resolved through a strict ladder, because
   picking the jet first makes an offer-only board dead-end the moment you
   choose an airframe the commander ignored:

   * **Rung 1 -- take a seat in an existing planned flight** of that type. Pure
     ``FlightMembers.set_pilot``; zero planner involvement. Always preferred.
   * **Rung 2 -- join an existing package** in the role that package still
     needs. The package already owns the target, the TOT and the coordination,
     so this stays inside the commander's plan rather than inventing a private
     war. This is the headline rung, and it is cheap: adding a flight to an
     existing package is exactly what the ATO UI does on *Add Flight*
     (``Flight(package, squadron, ...)`` + ``Package.add_flight``), not a
     commander re-entry.

The **role comes from the air war, not the player** -- second DM specification:
"I would like to be put into existing packages, should still be escort, strike,
jamming, whatever the planner decides." Two independent variety axes, only one
of which the player drives.

**One seat, AI wingmen, exactly as in MP.** The player takes a single slot; the
rest of the flight, the package and the ATO stay AI-crewed, so ``client_count``
stays 1 and generation runs the path MP already exercises nightly.

This module owns no UI and mutates nothing until ``take_seat`` is called.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from game.ato.flight import Flight
    from game.dcs.aircrafttype import AircraftType
    from game.game import Game
    from game.squadrons.pilot import Pilot
    from game.squadrons.squadron import Squadron


@dataclass(frozen=True)
class AirframeOption:
    """One airframe the player could fly this turn (board step 1)."""

    aircraft: "AircraftType"
    squadrons: List["Squadron"] = field(default_factory=list)

    @property
    def name(self) -> str:
        return str(self.aircraft)

    @property
    def bases(self) -> List[str]:
        seen: List[str] = []
        for squadron in self.squadrons:
            base = str(squadron.location)
            if base not in seen:
                seen.append(base)
        return seen

    @property
    def ready_airframes(self) -> int:
        return sum(int(getattr(s, "untasked_aircraft", 0)) for s in self.squadrons)

    @property
    def has_spare_airframes(self) -> bool:
        """Whether the wing has an untasked jet of this type.

        Note this is **not** the same as "can I fly it": a type whose airframes
        are all tasked can still be flown by taking a seat in one of those very
        flights (rung 1). Whether a sortie exists is answered by
        :func:`sortie_options`, which is what the board should gate on -- this
        property only explains *why* a type has no join available.
        """
        return self.ready_airframes > 0


@dataclass(frozen=True)
class SortieOption:
    """One flyable sortie in the chosen airframe (board step 2).

    ``rung`` records how it would be produced -- 1 to seat an existing flight,
    2 to join an existing package -- so the UI can label a join honestly rather
    than implying the commander planned it for you.
    """

    rung: int
    task: str
    target: str
    squadron: "Squadron"
    flight: Optional["Flight"] = None
    package_summary: str = ""
    tot: Optional[str] = None

    @property
    def description(self) -> str:
        """Role and package lead the line, never the target -- the role is the
        variety axis the player does not control, so it is the news."""
        where = f" on {self.target}" if self.target else ""
        joining = " (joining)" if self.rung == 2 else ""
        when = f" — TOT {self.tot}" if self.tot else ""
        return f"{self.task}{where}{joining}{when}"


def enabled(game: "Game") -> bool:
    return bool(getattr(game.settings, "sp_pilot_mode", False))


# ------------------------------------------------------------------- step 1


def airframe_options(game: "Game") -> List[AirframeOption]:
    """Every airframe the player's wing can put up this turn.

    Deliberately **not** filtered by what the commander planned: the whole
    point of choosing the jet first is that the choice is the player's, and an
    airframe with no sortie available is still worth showing (it is either an
    arrival to look forward to or a base that needs retaking).
    """
    by_aircraft: Dict["AircraftType", List["Squadron"]] = {}
    for squadron in game.blue.air_wing.iter_squadrons():
        by_aircraft.setdefault(squadron.aircraft, []).append(squadron)

    options = [
        AirframeOption(aircraft=aircraft, squadrons=squadrons)
        for aircraft, squadrons in by_aircraft.items()
    ]
    options.sort(key=lambda o: o.name)
    return options


# ------------------------------------------------------------------- step 2


def sortie_options(game: "Game", aircraft: "AircraftType") -> List[SortieOption]:
    """The sorties available in one airframe, resolved through the ladder.

    Rung 1 first (a seat costs nothing), then rung 2. Both are read-only; the
    ATO is untouched until :func:`take_seat`.
    """
    options: List[SortieOption] = []
    squadrons = [
        squadron
        for squadron in game.blue.air_wing.iter_squadrons()
        if squadron.aircraft == aircraft
    ]
    if not squadrons:
        return options

    squadron_set = {id(squadron) for squadron in squadrons}

    for package in game.blue.ato.packages:
        for flight in package.flights:
            if id(flight.squadron) not in squadron_set:
                continue
            if not _has_open_seat(flight):
                continue
            options.append(
                SortieOption(
                    rung=1,
                    task=str(flight.flight_type),
                    target=str(package.target),
                    squadron=flight.squadron,
                    flight=flight,
                    package_summary=_package_summary(package),
                    tot=_tot_text(package),
                )
            )

    options.extend(_join_options(game, squadrons))
    return options


def _has_open_seat(flight: "Flight") -> bool:
    """A flight the player can slot into without displacing a human.

    One seat only: a flight that already carries a client is somebody else's
    (or already yours), so it is not offered again.
    """
    try:
        if flight.client_count:
            return False
        roster = flight.roster
        return roster is not None and roster.max_size > 0
    except Exception:
        return False


def _join_options(game: "Game", squadrons: List["Squadron"]) -> List[SortieOption]:
    """Rung 2 -- packages that could use another flight of this airframe.

    The role offered is what the package is missing, so the air war picks the
    job. Reading which roles are *present* needs no engine change; the
    threat-derived "should it have one" judgement is a refinement, not a
    requirement.
    """
    options: List[SortieOption] = []
    ready = [s for s in squadrons if int(getattr(s, "untasked_aircraft", 0)) > 0]
    if not ready:
        return options

    for package in game.blue.ato.packages:
        if not package.flights:
            continue
        present = {str(flight.flight_type) for flight in package.flights}
        for role in _roles_a_package_could_use(package, present):
            options.append(
                SortieOption(
                    rung=2,
                    task=role,
                    target=str(package.target),
                    squadron=ready[0],
                    package_summary=_package_summary(package),
                    tot=_tot_text(package),
                )
            )
    return options


#: Escort roles a strike-class package plausibly wants. Deliberately a small,
#: legible set: the board is offering the player a job, not re-deriving doctrine.
_ESCORT_ROLES = ("Escort", "SEAD Escort", "Escort Jammer")


def _roles_a_package_could_use(package: object, present: set[str]) -> List[str]:
    """Roles this package does not already field."""
    return [role for role in _ESCORT_ROLES if role not in present]


def _package_summary(package: object) -> str:
    flights = getattr(package, "flights", [])
    if not flights:
        return ""
    primary = getattr(package, "primary_flight", None)
    lead = str(primary.flight_type) if primary is not None else ""
    return f"{lead} package, {len(flights)} flight{'s' if len(flights) != 1 else ''}"


def _tot_text(package: object) -> Optional[str]:
    tot = getattr(package, "time_over_target", None)
    if tot is None:
        return None
    try:
        return str(tot)
    except Exception:
        return None


# -------------------------------------------------------------- taking a seat


def take_seat(game: "Game", option: SortieOption) -> Optional["Flight"]:
    """Put the player in the chosen sortie. Returns the seated flight.

    Rung 1 seats an existing flight. Rung 2 is deliberately **not** implemented
    here as a silent package mutation: the caller (the UI) owns building the
    flight through the same path the ATO's *Add Flight* uses, then seats it with
    :func:`seat_player_in`. Keeping the mutation in one place means the board
    can be rendered, re-rendered and abandoned without ever touching the ATO.
    """
    if option.flight is None:
        return None
    return seat_player_in(game, option.flight)


def seat_player_in(game: "Game", flight: "Flight") -> Optional["Flight"]:
    """Claim one seat in ``flight`` for a player pilot.

    One seat, AI wingmen -- exactly as in MP. Returns the flight when a seat was
    taken, None when no player pilot was available (which is not an error: the
    squadron simply has none free, and the caller should offer another sortie).
    """
    squadron = flight.squadron
    pilot = _available_player_pilot(squadron)
    if pilot is None:
        logging.info("SP Pilot Mode: no player pilot free in %s", squadron.name)
        return None
    try:
        flight.roster.set_pilot(0, pilot)
    except Exception:
        logging.exception("SP Pilot Mode: could not seat %s in %s", pilot, flight)
        return None
    return flight


def _available_player_pilot(squadron: "Squadron") -> Optional["Pilot"]:
    """A free *player* pilot in this squadron, if one exists.

    Player pilots are the ones a campaign (or the Air Wing dialog) named, so
    seating one is what makes the flight a client flight rather than an AI one.
    """
    for pilot in list(getattr(squadron, "available_pilots", []) or []):
        if getattr(pilot, "player", False):
            return pilot
    return None
