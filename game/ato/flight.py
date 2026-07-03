from __future__ import annotations

import random
import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import Any, List, Optional, TYPE_CHECKING

from dcs import Point
from dcs.planes import C_101CC, C_101EB, Su_33, FA_18C_hornet, C_130J_30

from game.dcs.aircrafttype import AircraftType
from game.theater import ControlPoint, MissionTarget
from .flightmembers import FlightMembers
from .flightroster import FlightRoster
from .flightstate import FlightState, Navigating, Uninitialized
from .flightstate.killed import Killed
from .flighttype import FlightType
from .loadouts import Weapon
from ..radio.CallsignContainer import Callsign, CallsignContainer
from ..radio.RadioFrequencyContainer import RadioFrequencyContainer
from ..radio.TacanContainer import TacanContainer
from ..radio.radios import RadioFrequency
from ..radio.tacan import TacanChannel
from ..sidc import (
    Entity,
    SidcDescribable,
    StandardIdentity,
    Status,
    SymbolSet,
)

if TYPE_CHECKING:
    from game.sim.gameupdateevents import GameUpdateEvents
    from game.sim.simulationresults import SimulationResults
    from game.squadrons import Squadron, Pilot
    from game.theater.player import Player
    from game.transfers import TransferOrder
    from game.data.weapons import WeaponType
    from .flightmember import FlightMember
    from .flightplans.flightplan import FlightPlan
    from .flightwaypoint import FlightWaypoint
    from .package import Package
    from .starttype import StartType

F18_TGP_PYLON: int = 4


def roll_plane_altitude_offset(low: int, high: int) -> int:
    """Roll a per-flight altitude offset (in feet) from a [min, max] band.

    ``low`` and ``high`` are in thousands of feet (the doctrine settings units).
    Bounds are tolerant of being supplied in either order; equal bounds disable
    randomization and return a fixed offset.
    """
    if low > high:
        low, high = high, low
    return 1000 * random.randint(low, high)


# 414th: fixed "role" callsigns for the rescue/EW package. They are surfaced in the
# per-flight callsign picker (available_callsigns) and used to default a fresh
# flight's callsign, but stay player-editable (a soft lock). They are NOT stock DCS
# callsigns, so FlightGroupSpawner registers the chosen one into the spawn country's
# callsign pool before spawning (pydcs ValueErrors on an unknown callsign). The AI
# cannot voice them (no audio for unknown names), but every display reads the role.
_ROLE_CALLSIGN_BY_TYPE: dict[FlightType, str] = {
    FlightType.SCAR: "Sandy",  # RESCAP escort (A-10 / Apache)
    FlightType.JAMMING: "Toxic",  # EC-130H/RC-130H EW C-130
}

#: Every fixed role callsign, for the spawner's "is this a custom callsign?" guard.
ROLE_CALLSIGNS: frozenset[str] = frozenset({"King", "Jolly", "Sandy", "Toxic"})


def role_callsign(flight_type: FlightType, is_helicopter: bool) -> Optional[str]:
    """The fixed role callsign for a 414th rescue/EW role, or None if there isn't one.

    Combat SAR splits by airframe: the C-130 on-scene commander is "King", the
    rescue helo is "Jolly".
    """
    if flight_type is FlightType.COMBAT_SAR:
        return "Jolly" if is_helicopter else "King"
    return _ROLE_CALLSIGN_BY_TYPE.get(flight_type)


class Flight(
    SidcDescribable, RadioFrequencyContainer, TacanContainer, CallsignContainer
):
    def __init__(
        self,
        package: Package,
        squadron: Squadron,
        count: int,
        flight_type: FlightType,
        start_type: StartType,
        divert: Optional[ControlPoint],
        custom_name: Optional[str] = None,
        cargo: Optional[TransferOrder] = None,
        roster: Optional[FlightRoster] = None,
        frequency: Optional[RadioFrequency] = None,
        channel: Optional[TacanChannel] = None,
        callsign_tcn: Optional[str] = None,
        claim_inv: bool = True,
    ) -> None:
        self.id = uuid.uuid4()
        self.package = package
        self.coalition = squadron.coalition
        self.squadron = squadron
        self.flight_type = flight_type
        # 414th: default a fresh flight's callsign to its fixed role callsign
        # (King / Jolly / Sandy / Toxic) when one applies, numbered after any
        # same-role flights already fragged. Soft -- editable in the picker.
        # Defensive airframe lookup so a lightweight Flight (tests) never crashes.
        if self.callsign is None:
            is_heli = bool(
                getattr(getattr(squadron, "aircraft", None), "helicopter", False)
            )
            role = role_callsign(flight_type, is_heli)
            if role is not None:
                self.callsign = Callsign(role, self._next_role_callsign_nr(role))
        if claim_inv:
            self.squadron.claim_inventory(count)
        if roster is None:
            self.roster = FlightMembers(self, initial_size=count)
        else:
            self.roster = FlightMembers.from_roster(self, roster)
        self.divert = divert

        self.start_type = start_type
        self.custom_name = custom_name
        self.group_id: int = 0

        self.frequency = frequency
        if self.unit_type.dcs_unit_type.tacan:
            self.tacan = channel
            self.tcn_name = callsign_tcn

        self.initialize_fuel()
        # 414th (§43): seed a genuinely fresh player-side flight's fuel + cockpit
        # properties (condition/wear/spawn/...) from the per-aircraft "save as
        # default" store. Only when roster is None -- a brand-new flight, never a
        # clone that already carries member edits -- and BLUE only, so it never
        # touches enemy AI. Fully defensive: a no-op when nothing is saved or
        # persistency isn't set up (headless tests). Runs after initialize_fuel so
        # it wins over the engine's full-tank default.
        if roster is None:
            from game.fourteenth.flight_defaults import apply_flight_defaults

            apply_flight_defaults(self)
        self.use_same_loadout_for_all_members = True
        self.use_same_livery_for_all_members = True
        # 414th: a demand-based service point set by the post-planning theater-tanker
        # reposition pass (game/commander/tankerdemand.py); only meaningful for a
        # shared REFUELING flight, where TheaterRefuelingFlightPlan centers the orbit
        # here instead of on the front. None for everything else. Old saves predating
        # this attribute fall back via getattr in the tanker builder.
        self.refueling_service_point: Optional[Point] = None

        # 414th: an override for this flight's REFUEL waypoint position, set by the
        # long-range carrier post-planning pass (game/fourteenth/carrier_ops.py). A
        # carrier flight whose package has no tanker of its own would otherwise route
        # its refuel point to the far end of the package (no tanker there); this pins
        # it onto the carrier's held buddy-tanker orbit instead. None for everything
        # else; the refuel waypoint builders fall back to the package point via
        # refuel_waypoint_position(). Old saves predating this attribute use getattr.
        self.refuel_point_override: Optional[Point] = None

        # Only used by transport missions.
        self.cargo = cargo

        # Flight properties that can be set in the mission editor. This is used for
        # things like HMD selection, ripple quantity, etc. Any values set here will take
        # the place of the defaults defined by DCS.
        #
        # This is a part of the Flight rather than the Loadout because DCS does not
        # associate these choices with the loadout, and we don't want to reset these
        # options when players switch loadouts.
        self.props: dict[str, Any] = {}

        # Manual-timing state for player flights. When manually_timed is True the flight's
        # waypoint times are user-owned: they form a forward chain from manual_takeoff_time
        # plus each waypoint's manual_tot_offset, fully decoupled from the package TOT.
        self.manually_timed: bool = False
        self.manual_takeoff_time: datetime | None = None

        # Used for simulating the travel to first contact.
        self.state: FlightState = Uninitialized(self, squadron.settings)

        # Will be replaced with a more appropriate FlightPlan later, but start with a
        # cheaply constructed one since adding more flights to the package may affect
        # the optimal layout.
        from .flightplans.flightplanbuildertypes import FlightPlanBuilderTypes

        self._flight_plan_builder = FlightPlanBuilderTypes.for_flight(self)(self)

        is_f18 = self.squadron.aircraft.dcs_unit_type.id == FA_18C_hornet.id
        on_land = not self.squadron.location.is_fleet
        if on_land and is_f18 and self.coalition.game.settings.atflir_autoswap:
            for fm in self.roster.members:
                fm.loadout.pylons[F18_TGP_PYLON] = Weapon.with_clsid(
                    str(
                        FA_18C_hornet.Pylon4.AN_AAQ_28_LITENING___Targeting_Pod[1][
                            "clsid"
                        ]
                    )
                )

        # altitude offset for planes: roll a per-flight offset somewhere in the
        # [min, max] band (x1000 ft). Equal bounds disable randomization.
        settings = self.coalition.game.settings
        self.plane_altitude_offset = roll_plane_altitude_offset(
            settings.min_plane_altitude_offset, settings.max_plane_altitude_offset
        )

    @property
    def available_callsigns(self) -> List[str]:
        callsigns = set()
        dcs_unit = self.squadron.aircraft.dcs_unit_type
        category = dcs_unit.category
        category = "Air" if category == "Interceptor" else category
        for name in self.squadron.coalition.faction.country.callsign[category]:
            callsigns.add(name)
        if hasattr(dcs_unit, "callnames"):
            country_name = self.squadron.coalition.faction.country.name
            for c in dcs_unit.callnames:
                if "Combined Joint Task Forces" in country_name or c == country_name:
                    for name in dcs_unit.callnames[c]:
                        callsigns.add(name)
        # 414th: offer the flight's fixed role callsign (King/Jolly/Sandy/Toxic) in
        # the picker too, so the rescue/EW roles can keep their callsign.
        role = role_callsign(self.flight_type, self.squadron.aircraft.helicopter)
        if role is not None:
            callsigns.add(role)
        return sorted(callsigns)

    def _next_role_callsign_nr(self, role: str) -> int:
        # Number a defaulted role callsign after any same-role flights already
        # fragged (Sandy 1, Sandy 2, ...). Best-effort + guarded for lightweight
        # Flights built without a full ATO (tests); falls back to 1.
        try:
            used = sum(
                1
                for package in self.coalition.ato.packages
                for flight in package.flights
                if flight.callsign is not None and flight.callsign.name == role
            )
        except (AttributeError, TypeError):
            used = 0
        return used + 1

    @property
    def flight_plan(self) -> FlightPlan[Any]:
        return self._flight_plan_builder.get_or_build()

    def degrade_to_custom_flight_plan(self) -> None:
        from .flightplans.custom import Builder as CustomBuilder

        self.manually_timed = False
        self.manual_takeoff_time = None
        self._flight_plan_builder = CustomBuilder(self, self.flight_plan.waypoints[1:])
        self.recreate_flight_plan()

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        # Avoid persisting the flight state since that's not (currently) used outside
        # mission generation. This is a bit of a hack for the moment and in the future
        # we will need to persist the flight state, but for now keep it out of save
        # compat (it also contains a generator that cannot be pickled).
        del state["state"]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        state["state"] = Uninitialized(self, state["squadron"].settings)
        if "use_same_loadout_for_all_members" not in state:
            state["use_same_loadout_for_all_members"] = True
        if "manually_timed" not in state:
            state["manually_timed"] = False
        if "manual_takeoff_time" not in state:
            state["manual_takeoff_time"] = None
        self.__dict__.update(state)
        if isinstance(self.roster, FlightRoster):
            self.roster = FlightMembers.from_roster(self, self.roster)

    @property
    def blue(self) -> Player:
        return self.squadron.player

    @property
    def standard_identity(self) -> StandardIdentity:
        if self.blue.is_blue:
            return StandardIdentity.FRIEND
        elif self.blue.is_red:
            return StandardIdentity.HOSTILE_FAKER
        else:
            return StandardIdentity.UNKNOWN

    @property
    def sidc_status(self) -> Status:
        return Status.PRESENT if self.alive else Status.PRESENT_DESTROYED

    @property
    def symbol_set_and_entity(self) -> tuple[SymbolSet, Entity]:
        return SymbolSet.AIR, self.flight_type.entity_type

    @property
    def departure(self) -> ControlPoint:
        return self.squadron.location

    @property
    def arrival(self) -> ControlPoint:
        return self.squadron.arrival

    @property
    def count(self) -> int:
        return self.roster.max_size

    @property
    def client_count(self) -> int:
        return self.roster.player_count

    @property
    def unit_type(self) -> AircraftType:
        return self.squadron.aircraft

    @property
    def task_display_name(self) -> str:
        """The flight's tasking label under its coalition's doctrine -- the Vietnam
        rename layer (e.g. STRIKE -> "Alpha Strike"). Falls back to the canonical
        ``FlightType.value`` when the doctrine supplies no override. A STRIKE flight
        only reads the era "Alpha Strike" label when its package actually masses
        (>= 2 sections on one target); a lone section is a plain Strike. Display
        only: the persisted enum value is untouched."""
        if self.flight_type is FlightType.STRIKE and not self.package.is_massed_strike:
            return FlightType.STRIKE.value
        return self.coalition.doctrine.display_name_for(self.flight_type)

    @property
    def is_lha(self) -> bool:
        return self.unit_type.lha_capable

    @property
    def is_helo(self) -> bool:
        return self.unit_type.helicopter

    @property
    def is_c130j(self) -> bool:
        return self.unit_type == AircraftType.named("C-130J-30")

    @property
    def points(self) -> List[FlightWaypoint]:
        return self.flight_plan.waypoints[1:]

    @property
    def custom_targets(self) -> List[MissionTarget]:
        return [
            MissionTarget(wpt.name, wpt.position)
            for wpt in self.flight_plan.layout.custom_waypoints
        ]

    def position(self) -> Point:
        return self.state.estimate_position()

    def resize(self, new_size: int) -> None:
        self.squadron.claim_inventory(new_size - self.count)
        self.roster.resize(new_size)

    def set_pilot(self, index: int, pilot: Optional[Pilot]) -> None:
        self.roster.set_pilot(index, pilot)

    @property
    def missing_pilots(self) -> int:
        return self.roster.missing_pilots

    def iter_members(self) -> Iterator[FlightMember]:
        yield from self.roster.members

    def set_flight_type(self, var: FlightType) -> None:
        self.flight_type = var

        # Update _flight_plan_builder so that the builder class remains relevant
        # to the flight type
        from .flightplans.flightplanbuildertypes import FlightPlanBuilderTypes

        self._flight_plan_builder = FlightPlanBuilderTypes.for_flight(self)(self)

    def return_pilots_and_aircraft(self) -> None:
        self.roster.clear()
        self.squadron.claim_inventory(-self.count)

    def initialize_fuel(self) -> None:
        unit_type = self.unit_type.dcs_unit_type
        self.fuel = unit_type.fuel_max
        # Special cases where we want less fuel for takeoff
        if unit_type == Su_33:
            if self.flight_type.is_air_to_air:
                self.fuel = Su_33.fuel_max / 2.2
            else:
                self.fuel = Su_33.fuel_max * 0.8
        elif unit_type in {C_101EB, C_101CC}:
            self.fuel = unit_type.fuel_max * 0.5
        elif unit_type == C_130J_30:
            self.fuel = unit_type.fuel_max * 0.75

    def any_member_has_weapon_of_type(self, weapon_type: WeaponType) -> bool:
        return any(
            m.loadout.has_weapon_of_type(weapon_type) for m in self.iter_members()
        )

    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self) -> str:
        # Prefer the doctrine display label (era renames, e.g. STRIKE -> "Alpha
        # Strike"); identical to the canonical task for every non-Vietnam doctrine.
        # __str__ must never raise, so fall back to the raw task if the coalition /
        # doctrine isn't reachable (e.g. a partially-restored flight in a log line).
        try:
            task: object = self.task_display_name
        except Exception:
            task = self.flight_type
        string = f"[{task}] {self.count} x {self.unit_type} - {self.start_type.value}"
        if self.custom_name:
            return f"{self.custom_name} - {string}"
        return string

    def abort(self) -> None:
        from .flightplans.rtb import RtbFlightPlan

        self._flight_plan_builder = RtbFlightPlan.builder_type()(self)
        plan = self._flight_plan_builder.get_or_build()

        self.set_state(
            Navigating(
                self,
                self.squadron.settings,
                plan.abort_index,
                has_aborted=True,
            )
        )

    def set_state(self, state: FlightState) -> None:
        self.state = state

    def on_game_tick(
        self, events: GameUpdateEvents, time: datetime, duration: timedelta
    ) -> None:
        self.state.on_game_tick(events, time, duration)

    def should_halt_sim(self) -> bool:
        return self.state.should_halt_sim()

    @property
    def alive(self) -> bool:
        return self.state.alive

    def kill(self, results: SimulationResults, events: GameUpdateEvents) -> None:
        # This is a bit messy while we're in transition from turn-based to turnless
        # because we want the simulation to have minimal impact on the save game while
        # turns exist so that loading a game is essentially a way to reset the
        # simulation to the start of the turn. As such, we don't actually want to mark
        # pilots killed or reduce squadron aircraft availability, but we do still need
        # the UI to reflect that aircraft were lost and avoid generating those flights
        # when the mission is generated.
        #
        # For now we do this by logging the kill in the SimulationResults, which is
        # similar to the Debriefing. We also set the flight's state to Killed, which
        # will prevent it from being spawned in the mission and updates the SIDC.
        # This does leave an opportunity for players to cheat since the UI won't stop
        # them from cancelling a dead flight, returning the aircraft to the pool. Not a
        # big deal for now.
        # TODO: Support partial kills.
        self.set_state(
            Killed(self.state.estimate_position(), self, self.squadron.settings)
        )
        events.update_flight(self)
        for pilot in self.roster.iter_pilots():
            if pilot is not None:
                results.kill_pilot(self, pilot)

    def recreate_flight_plan(self, dump_debug_info: bool = False) -> None:
        self.manually_timed = False
        self.manual_takeoff_time = None
        self._flight_plan_builder.regenerate(dump_debug_info)

    def refuel_waypoint_position(self, default: Point) -> Point:
        """The position to build this flight's REFUEL waypoint at: the 414th
        carrier buddy-tanker override when set, else the shared package refuel
        point (the stock behavior). See ``refuel_point_override``."""
        override = getattr(self, "refuel_point_override", None)
        return override if override is not None else default

    @staticmethod
    def clone_flight(flight: Flight) -> Flight:
        return Flight(
            flight.package,
            flight.squadron,
            flight.count,
            flight.flight_type,
            flight.start_type,
            flight.divert,
        )
