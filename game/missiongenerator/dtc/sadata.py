"""Coalition SA data for the F/A-18C DTC cartridge, extracted from the game state.

Scope is intentionally narrow: the only thing the cartridge carries is the Hornet SA-page
**CAP/tanker tracks**, so all this collects is friendly racetracks (player/AI CAP plus
tankers) as centreline + width. Threat rings draw themselves from DCS intel and COMM /
waypoints load from the mission, so neither is gathered here.

Positions are DCS world coordinates in metres (``x`` north, ``y`` east) -- the same
projection pydcs uses, so no conversion is needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from game.ato.flightplans.aewc import AewcFlightPlan
from game.ato.flightplans.patrolling import PatrollingFlightPlan

if TYPE_CHECKING:
    from game import Game

# Default racetrack width when we only know the centreline (metres ~= 5 NM).
DEFAULT_TRACK_WIDTH_M = 9260.0


@dataclass(frozen=True)
class OrbitTrack:
    """A friendly racetrack (CAP or tanker), as a centreline + width."""

    x: float  # centre
    y: float
    course_deg: int
    length_m: int
    width_m: float
    name: str


@dataclass
class SaData:
    orbits: list[OrbitTrack] = field(default_factory=list)


def _collect_orbits(game: Game) -> list[OrbitTrack]:
    # The Hornet SA page wants CAP stations and tanker tracks so players know where
    # friendly CAP is holding and where to refuel. Both are PatrollingFlightPlan
    # racetracks. We deliberately include AI flights (tankers are always AI; the player
    # still needs the track) and exclude AEW&C orbits, which are not a track the strikers
    # work against.
    orbits: list[OrbitTrack] = []
    for package in game.blue.ato.packages:
        for flight in package.flights:
            flight_plan = flight.flight_plan
            if not isinstance(flight_plan, PatrollingFlightPlan):
                continue
            if isinstance(flight_plan, AewcFlightPlan):
                continue
            start = flight_plan.layout.patrol_start.position
            end = flight_plan.layout.patrol_end.position
            center = (start + end) / 2
            orbits.append(
                OrbitTrack(
                    x=center.x,
                    y=center.y,
                    course_deg=int(start.heading_between_point(end)),
                    length_m=int(start.distance_to_point(end)),
                    width_m=DEFAULT_TRACK_WIDTH_M,
                    name=str(flight),
                )
            )
    return orbits


def collect_sa_data(game: Game) -> SaData:
    """Build the blue-coalition CAP/tanker tracks shared by the DTC cartridge."""
    return SaData(orbits=_collect_orbits(game))
