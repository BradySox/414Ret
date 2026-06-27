"""Capability weighting for abstract (non-player-flown) combat resolution.

The simulation auto-resolves the engagements the player does not fly. Historically that
was a coin flip -- the side with more flights won outright, ties broke 50/50, and each
survivor then died on another 50/50 -- which let an obsolete jet beat a modern one and
ignored SEAD's entire reason for existing. These helpers weight the odds by the airframe
capability the planner already encodes (``AircraftType.task_priority``) and the flight's
role, so an auto-resolved outcome tracks the matchup the player would expect.

Deliberately coarse: this is a campaign abstraction, not a DCS dogfight. It only nudges
probabilities -- the missions the player actually flies are resolved by DCS, and the
``SKIP``/``PAUSE`` resolution methods are untouched. See ``aircombat.py`` /
``defendingsam.py`` for the callers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.ato.flighttype import FlightType

if TYPE_CHECKING:
    from game.ato import Flight

# A2A tasks whose per-airframe planner priority doubles as an air-to-air capability
# proxy: a better fighter carries a higher BARCAP/TARCAP/sweep rating in its unit YAML.
_A2A_TASKS = (
    FlightType.TARCAP,
    FlightType.BARCAP,
    FlightType.SWEEP,
    FlightType.ESCORT,
    FlightType.INTERCEPTION,
)

# Floor so an airframe with no A2A rating at all (a bomber jumped by fighters) is very
# weak but never zero -- it keeps strength ratios well-defined and leaves a sliver of a
# chance rather than a guaranteed massacre.
_A2A_CAPABILITY_FLOOR = 100.0

# SAM-defeating tasks: these flights carry the gear and training to survive air defenses.
_SEAD_TASKS = (
    FlightType.SEAD,
    FlightType.DEAD,
    FlightType.SEAD_ESCORT,
    FlightType.SEAD_SWEEP,
)


def air_to_air_capability(flight: Flight) -> float:
    """A single airframe's air-to-air capability proxy (its best A2A task priority)."""
    aircraft = flight.unit_type
    best = _A2A_CAPABILITY_FLOOR
    for task in _A2A_TASKS:
        if aircraft.capable_of(task):
            best = max(best, float(aircraft.task_priority(task)))
    return best


def air_to_air_strength(flight: Flight) -> float:
    """A flight's weight in an A2A engagement: capability x number of airframes."""
    return air_to_air_capability(flight) * max(flight.count, 1)


def air_combat_win_probability(
    friendly_strength: float, enemy_strength: float
) -> float:
    """Probability the friendly side wins, from the two aggregate strengths.

    A simple strength share, so both capability and numbers matter and neither is
    absolute: two cheap fighters can still overwhelm one good one, but the good one is
    no longer doomed by a coin flip. Falls back to even odds if both sides score zero.
    """
    total = friendly_strength + enemy_strength
    if total <= 0:
        return 0.5
    return friendly_strength / total


def air_combat_survivor_loss_chance(
    winner_strength: float, loser_strength: float
) -> float:
    """Per-survivor loss chance for the winning side, scaled by how close the fight was.

    A lopsided win bleeds few survivors; an even fight still costs roughly half (the old
    flat rate), so this never makes the winner *more* fragile than the legacy 50/50 --
    it only rewards dominance. Clamped to [0.05, 0.5].
    """
    total = winner_strength + loser_strength
    if total <= 0:
        return 0.5
    return min(max(loser_strength / total, 0.05), 0.5)


def sam_death_chance(flight: Flight, site_count: int) -> float:
    """Probability a flight is lost when an abstract SAM engagement auto-resolves.

    Anchored at the legacy 0.5 for a generic flight versus a single site, then:
      * SEAD-role or SEAD-capable flights are equipped to survive -> halved, and
      * each *additional* engaging site stacks the threat.
    Clamped to [0.05, 0.95] so nothing is a guaranteed (or impossible) loss.
    """
    chance = 0.5
    is_sead = flight.flight_type in _SEAD_TASKS or flight.unit_type.capable_of(
        FlightType.SEAD
    )
    if is_sead:
        chance *= 0.5
    chance *= 1.0 + 0.25 * max(site_count - 1, 0)
    return min(max(chance, 0.05), 0.95)
