from dataclasses import field, dataclass
from enum import Enum, auto
from typing import Optional

from game.ato.flighttype import FlightType
from game.dcs.aircrafttype import AircraftType, AirRefuelType
from game.theater import MissionTarget


class EscortType(Enum):
    AirToAir = auto()
    Sead = auto()
    Refuel = auto()
    # Growler escort jamming (ESCORT_JAMMER). Appended last so the existing
    # members keep their auto() values.
    Jammer = auto()


@dataclass(frozen=True)
class ProposedFlight:
    """A flight outline proposed by the mission planner.

    Proposed flights haven't been assigned specific aircraft yet. They have only
    a task, a required number of aircraft, and a maximum distance allowed
    between the objective and the departure airfield.
    """

    #: The flight's role.
    task: FlightType

    #: The number of aircraft required.
    num_aircraft: int

    #: The type of threat this flight defends against if it is an escort. Escort
    #: flights will be pruned if the rest of the package is not threatened by
    #: the threat they defend against. If this flight is not an escort, this
    #: field is None.
    escort_type: Optional[EscortType] = field(default=None)

    preferred_type: Optional[AircraftType] = field(default=None)

    #: For a REFUELING flight, the boom/probe method the tanker must provide. Lets the
    #: planner frag one theater tanker per receiver method (so a mixed boom+probe fleet
    #: gets a tanker for each). None leaves tanker selection unconstrained.
    refuel_method: Optional[AirRefuelType] = field(default=None)

    #: A surge flight: planned when a squadron has the jets, dropped silently when
    #: not -- it never scrubs the package and never places a purchase order. Used by
    #: the Alpha Strike fan (PlanStrike) so the extra sections mass onto the target
    #: only as deep as the live inventory allows.
    optional: bool = field(default=False)

    def __str__(self) -> str:
        return f"{self.task} {self.num_aircraft} ship"


@dataclass(frozen=True)
class ProposedMission:
    """A mission outline proposed by the mission planner.

    Proposed missions haven't been assigned aircraft yet. They have only an
    objective location and a list of proposed flights that are required for the
    mission.
    """

    #: The mission objective.
    location: MissionTarget

    #: The proposed flights that are required for the mission.
    flights: list[ProposedFlight]

    asap: bool = field(default=False)

    def __str__(self) -> str:
        flights = ", ".join([str(f) for f in self.flights])
        return f"{self.location.name}: {flights}"
