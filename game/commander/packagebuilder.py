from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from game.ato.flightmember import apply_default_player_laser_code
from game.theater import ControlPoint, MissionTarget, OffMapSpawn
from game.utils import nautical_miles
from ..ato import FlightType
from ..ato.flight import Flight
from ..ato.package import Package
from ..ato.starttype import StartType
from ..db.database import Database

if TYPE_CHECKING:
    from game.ato.closestairfields import ClosestAirfields
    from game.dcs.aircrafttype import AircraftType, AirRefuelType
    from game.lasercodes import LaserCodeRegistry
    from game.squadrons.airwing import AirWing
    from .missionproposals import ProposedFlight


def assault_flight_size(task: FlightType, aircraft: AircraftType, proposed: int) -> int:
    """Fixed-wing air assault flies single-ship.

    One transport paradrops the whole stick, so a second only doubles the troops
    delivered. Helicopters keep the proposed size -- their lift is per airframe.
    Applied after the squadron is picked, because the airframe is not known when
    the flight is proposed.
    """
    if task is FlightType.AIR_ASSAULT and not aircraft.helicopter:
        return 1
    return proposed


class PackageBuilder:
    """Builds a Package for the flights it receives."""

    def __init__(
        self,
        location: MissionTarget,
        closest_airfields: ClosestAirfields,
        air_wing: AirWing,
        laser_code_registry: LaserCodeRegistry,
        flight_db: Database[Flight],
        is_player: bool,
        start_type: StartType,
        asap: bool,
    ) -> None:
        self.closest_airfields = closest_airfields
        self.is_player = is_player
        self.package = Package(location, flight_db, auto_asap=asap)
        self.air_wing = air_wing
        self.laser_code_registry = laser_code_registry
        self.start_type = start_type

    def plan_flight(self, plan: ProposedFlight, ignore_range: bool) -> bool:
        """Allocates aircraft for the given flight and adds them to the package.

        If no suitable aircraft are available, False is returned. If the failed
        flight was critical and the rest of the mission will be scrubbed, the
        caller should return any previously planned flights to the inventory
        using release_planned_aircraft.
        """
        target = self.package.target
        heli = False
        pf = self.package.primary_flight
        if pf:
            target = (
                pf.departure
                if pf.flight_type
                in [FlightType.AEWC, FlightType.REFUELING, FlightType.RECOVERY]
                else target
            )
            heli = pf.is_helo
        squadron = self.air_wing.best_squadron_for(
            target,
            plan.task,
            plan.num_aircraft,
            heli,
            this_turn=True,
            preferred_type=plan.preferred_type,
            ignore_range=ignore_range,
            refuel_methods=self._required_refuel_methods(plan),
        )
        if squadron is None:
            return False
        start_type = squadron.location.required_aircraft_start_type
        if start_type is None:
            start_type = self.start_type

        num_aircraft = assault_flight_size(
            plan.task, squadron.aircraft, plan.num_aircraft
        )

        flight = Flight(
            self.package,
            squadron,
            num_aircraft,
            plan.task,
            start_type,
            divert=self.find_divert_field(squadron.aircraft, squadron.location),
        )
        for member in flight.iter_members():
            apply_default_player_laser_code(
                member,
                squadron.coalition.game.settings,
                self.laser_code_registry,
            )
        # Now the roster exists, re-derive the start type: a client flight follows
        # the player default, and some tasks (CSAR) have one of their own.
        # https://github.com/dcs-liberation/dcs_liberation/issues/1567
        # A base that dictates its own start type (carriers, off-map spawns) wins.
        if squadron.location.required_aircraft_start_type is None:
            settings = squadron.coalition.game.settings
            has_players = flight.roster is not None and flight.roster.player_count > 0
            flight.start_type = settings.start_type_for(
                plan.task, has_players=has_players
            )
            # The 414th air-start overrides sit UNDER that call, not beside it.
            # Before upstream #929 they were `elif` arms behind the client-flight
            # branch, so they only ever applied to AI flights and a player-crewed
            # flight always kept its configured start type. Keeping them as sibling
            # elifs after #929 made both unreachable (their guard re-tested the `if`
            # above), silently killing two shipped features.
            #
            # CSAR is excluded deliberately: #929 gives it a dedicated
            # `csar_start_type` that is documented to override the AI and player
            # defaults, so a blanket air-start must not stomp it.
            if (
                not has_players
                and plan.task is not FlightType.CSAR
                and settings.opfor_air_start
                and squadron.coalition.player.is_red
            ):
                # OPFOR-air-start: the enemy holds the air from t=0 instead of being
                # caught spooling up on the ramp. Applies to every AI red flight.
                flight.start_type = StartType.IN_FLIGHT
            elif (
                not has_players
                and settings.support_air_start
                and flight.flight_type
                in (FlightType.AEWC, FlightType.REFUELING, FlightType.RECOVERY)
            ):
                # Air-start AWACS/tankers so they hold station from mission start
                # rather than burning the first minutes taxiing and climbing out.
                flight.start_type = StartType.IN_FLIGHT
        self.package.add_flight(flight)
        return True

    def _required_refuel_methods(
        self, plan: ProposedFlight
    ) -> Optional[frozenset[AirRefuelType]]:
        """Refueling methods a tanker must provide for this package.

        Only relevant when planning a tanker (REFUELING). Returns None for every other
        task. For a same-package buddy tanker the methods are inferred from the
        package's already-planned receivers; untagged receivers leave selection
        unconstrained.
        """
        if plan.task is not FlightType.REFUELING:
            return None
        methods: set[AirRefuelType] = set()
        for flight in self.package.flights:
            if flight.flight_type is FlightType.REFUELING:
                continue
            method = flight.unit_type.air_refuel_type
            if method is not None:
                methods.add(method)
        return frozenset(methods) if methods else None

    def find_divert_field(
        self, aircraft: AircraftType, arrival: ControlPoint
    ) -> Optional[ControlPoint]:
        divert_limit = nautical_miles(150)
        for airfield in self.closest_airfields.operational_airfields_within(
            divert_limit
        ):
            if airfield.captured != self.is_player:
                continue
            if airfield == arrival:
                continue
            if not airfield.can_operate(aircraft):
                continue
            if isinstance(airfield, OffMapSpawn):
                continue
            return airfield
        return None

    def build(self) -> Package:
        """Returns the built package."""
        return self.package

    def release_planned_aircraft(self) -> None:
        """Returns any planned flights to the inventory."""
        flights = list(self.package.flights)
        for flight in flights:
            self.package.remove_flight(flight)
