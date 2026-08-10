from __future__ import annotations

from typing import Iterator, TYPE_CHECKING

from dcs.mapping import Point

if TYPE_CHECKING:
    from game.ato.flighttype import FlightType
    from game.theater import TheaterUnit, Coalition, Player
    from game.utils import Heading


class MissionTarget:
    def __init__(self, name: str, position: Point) -> None:
        """Initializes a mission target.

        Args:
            name: The name of the mission target.
            position: The location of the mission target.
        """
        self.name = name
        self.position = position

    def distance_to(self, other: MissionTarget) -> float:
        """Computes the distance to the given mission target."""
        return self.position.distance_to_point(other.position)

    def is_friendly(self, to_player: Player) -> bool:
        """Returns True if the objective is in friendly territory."""
        raise NotImplementedError

    def mission_types(self, for_player: Player) -> Iterator[FlightType]:
        from game.ato import FlightType

        if self.is_friendly(for_player):
            yield FlightType.BARCAP
        else:
            yield from [
                FlightType.ESCORT,
                FlightType.TARCAP,
                FlightType.SEAD_ESCORT,
                FlightType.ESCORT_JAMMER,
                FlightType.SEAD_SWEEP,
                FlightType.ARMED_RECON,
                FlightType.SWEEP,
                FlightType.JAMMING,
                # TODO: FlightType.ELINT,
                # TODO: FlightType.EWAR,
                # TODO: FlightType.RECON,
            ]

    @property
    def strike_targets(self) -> list[TheaterUnit]:
        return []

    @property
    def coalition(self) -> Coalition:
        raise NotImplementedError


class HomeBaseDefenseZone(MissionTarget):
    """A BARCAP orbit anchored *at* a friendly home airfield (base-defense CAP).

    Used as the package target for the player-manned QRA alert flight (§1, design
    note 414th-qra-player-manning-notes.md). Unlike a control-point BARCAP -- whose
    racetrack is pushed forward toward the nearest enemy airfield --
    ``CapBuilder.cap_racetrack_for_objective`` lays this orbit straddling the base
    position itself, so the alert flight sits over the field it defends rather than
    screening forward. ``mission_types`` is the friendly default (BARCAP).
    """

    def __init__(self, name: str, position: Point, coalition: Coalition) -> None:
        super().__init__(name, position)
        self._coalition = coalition

    def is_friendly(self, to_player: Player) -> bool:
        return self._coalition.player == to_player

    @property
    def coalition(self) -> Coalition:
        return self._coalition
