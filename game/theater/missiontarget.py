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
                # SCAR is no longer a broad anti-armor task: it is the "Sandy"
                # rescue-escort, scoped to the FLOT (see FrontLine.mission_types)
                # so the King + Jolly + Sandy rescue package frags against the
                # front. Rescue rework: 414th-scar-rescue-rework-notes.md.
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


class ForwardBarcapZone(MissionTarget):
    """An *added* forward-middle BARCAP screen location on the friendly side of an
    active front (414th red forward-BARCAP layer).

    Used as a package target so ``CapBuilder.cap_racetrack_for_objective`` lays the
    racetrack here -- parallel to the FLOT, in the forward-middle of the sector --
    instead of at a rear control point. The rear/base BARCAP (CP-targeted) is
    unchanged; this is a separate, additional layer planned only for large maps.
    Placement geometry lives in ``game/ato/flightplans/supportorbit.py``
    (``forward_cap_front_anchor``); the trigger lives in ``TheaterState.from_game``.
    """

    def __init__(
        self, name: str, position: Point, coalition: Coalition, heading: Heading
    ) -> None:
        super().__init__(name, position)
        self._coalition = coalition
        # Enemy-facing heading across the FLOT; CapBuilder lays the racetrack
        # perpendicular to it so the orbit runs parallel to the front.
        self.heading = heading

    def is_friendly(self, to_player: Player) -> bool:
        return self._coalition.player == to_player

    @property
    def coalition(self) -> Coalition:
        return self._coalition


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


class PilotRecoveryZone(MissionTarget):
    """The recovery objective of a pilot-recovery surge package (§21 extension,
    game/fourteenth/csar_surge.py): the last known position of one or more MIA
    evaders. Targeting the package here makes ``CombatSarFlightPlan`` hold its
    racetrack a short distance friendly-side of the *survivor* -- not the front
    centre -- so the rescue package stages where the pickup actually is.

    Friendly-owned (it is our aviator); ``mission_types`` offers the rescue
    package's own roles so the player can reinforce the fragged package from the
    ATO dialog.
    """

    def __init__(self, name: str, position: Point, coalition: Coalition) -> None:
        super().__init__(name, position)
        self._coalition = coalition

    def is_friendly(self, to_player: Player) -> bool:
        return self._coalition.player == to_player

    def mission_types(self, for_player: Player) -> Iterator[FlightType]:
        from game.ato import FlightType

        if self.is_friendly(for_player):
            yield from [
                FlightType.COMBAT_SAR,
                FlightType.SCAR,
                FlightType.ESCORT,
                FlightType.TARCAP,
            ]

    @property
    def coalition(self) -> Coalition:
        return self._coalition
