from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING

from dcs import Mission, Point
from dcs.flyingunit import FlyingUnit
from dcs.unit import Skill
from dcs.unitgroup import FlyingGroup

from game.ato import Flight, FlightType
from game.ato.flightplans.shiprecoverytanker import RecoveryTankerFlightPlan
from game.callsigns import callsign_for_support_unit
from game.data.weapons import Pylon
from game.fourteenth.range_fuel import add_range_fuel_tanks
from game.lasercodes.lasercode import LaserCode
from game.missiongenerator.logisticsgenerator import LogisticsGenerator
from game.missiongenerator.missiondata import MissionData, AwacsInfo, TankerInfo
from game.radio.radios import RadioFrequency, RadioRegistry
from game.radio.tacan import (
    TacanBand,
    TacanRegistry,
    TacanUsage,
    OutOfTacanChannelsError,
)
from game.runways import RunwayData
from game.missiongenerator.missiondata import EscortInfo
from game.squadrons import Pilot
from .aircraftbehavior import AircraftBehavior
from .aircraftpainter import AircraftPainter
from .bingoestimator import BingoEstimator
from .flightdata import CombatSarKingBeacon, FlightData
from .waypoints import WaypointGenerator
from ...ato.flightmember import FlightMember
from ...ato.flightplans.aewc import AewcFlightPlan
from ...ato.flightplans.packagerefueling import PackageRefuelingFlightPlan
from ...ato.flightplans.theaterrefueling import TheaterRefuelingFlightPlan
from ...radio.datalink import (
    DataLinkRegistry,
    DataLinkKey,
    DataLinkIdentifier,
    VOICE_CALLSIGN_LABEL,
    VOICE_CALLSIGN_NUMBER,
    OWNSHIP_CALLSIGN,
)
from ...theater import Fob

if TYPE_CHECKING:
    from game import Game


class FlightGroupConfigurator:
    def __init__(
        self,
        flight: Flight,
        group: FlyingGroup[Any],
        game: Game,
        mission: Mission,
        time: datetime,
        radio_registry: RadioRegistry,
        tacan_registry: TacanRegistry,
        datalink_registry: DataLinkRegistry,
        mission_data: MissionData,
        dynamic_runways: dict[str, RunwayData],
        use_client: bool,
    ) -> None:
        self.flight = flight
        self.group = group
        self.game = game
        self.mission = mission
        self.time = time
        self.radio_registry = radio_registry
        self.tacan_registry = tacan_registry
        self.datalink_registry = datalink_registry
        self.mission_data = mission_data
        self.dynamic_runways = dynamic_runways
        self.use_client = use_client

    def register_combat_sar_king(self) -> Optional[CombatSarKingBeacon]:
        """Allocate the homing beacon for a C-130 "King" Combat SAR flight.

        Only the fixed-wing King carries a beacon; the CH-47 is the rescuer and
        homes on it. TACAN is the King beacon (air-tracking, follows the orbit, and
        every rescue helo we use has a receiver) and is best-effort (None if the
        channel pool is dry). Returns None for any other flight.
        """
        if self.flight.flight_type is not FlightType.COMBAT_SAR:
            return None
        if self.flight.unit_type.helicopter:
            return None

        tacan = None
        try:
            tacan = self.tacan_registry.alloc_for_band(TacanBand.Y, TacanUsage.AirToAir)
        except OutOfTacanChannelsError:
            tacan = None

        return CombatSarKingBeacon(
            callsign=callsign_for_support_unit(self.group),
            tacan=tacan,
        )

    def configure(self) -> FlightData:
        flight_channel = self.setup_radios()
        combat_sar_king = self.register_combat_sar_king()
        AircraftBehavior(self.flight.flight_type, self.mission_data).apply_to(
            self.flight, self.group
        )
        AircraftPainter(self.flight, self.group).apply_livery()
        self.setup_props()
        self.setup_payloads()
        self.setup_fuel()

        laser_codes: list[Optional[int]] = []
        for unit, member in zip(self.group.units, self.flight.iter_members()):
            self.configure_flight_member(unit, member, laser_codes)

        divert = None
        if self.flight.divert is not None:
            divert = self.flight.divert.active_runway(
                self.game.theater, self.game.conditions, self.dynamic_runways
            )

        if self.flight.flight_type in [
            FlightType.TRANSPORT,
            FlightType.AIR_ASSAULT,
        ] and self.game.settings.plugin_option("ctld"):
            transfer = None
            if self.flight.flight_type == FlightType.TRANSPORT:
                coalition = self.game.coalition_for(player=self.flight.blue)
                transfer = coalition.transfers.transfer_for_flight(self.flight)
            self.mission_data.logistics.append(
                LogisticsGenerator(
                    self.flight, self.group, self.mission, self.game.settings, transfer
                ).generate_logistics()
            )

        mission_start_time, waypoints = WaypointGenerator(
            self.flight,
            self.group,
            self.mission,
            self.time,
            self.game.settings,
            self.mission_data,
            self.use_client,
        ).create_waypoints()

        # Special handling for landing waypoints when:
        # 1. It's an AI-only flight
        # 2. Aircraft are not helicopters/VTOL
        # 3. Landing waypoint does not point to an airfield
        if (
            self.flight.client_count < 1
            and not self.flight.unit_type.helicopter
            and not self.flight.unit_type.lha_capable
            and isinstance(self.flight.squadron.location, Fob)
        ):
            # Need to set uncontrolled to false, otherwise the AI will skip the mission and just land
            self.group.uncontrolled = False

        divert_position: Point | None = None
        if self.flight.divert is not None:
            divert_position = self.flight.divert.position
        bingo_estimator = BingoEstimator(
            self.flight.unit_type.fuel_consumption,
            self.flight.arrival.position,
            divert_position,
            self.flight.flight_plan.waypoints,
        )

        # Racetrack plans carry their on-station speed to the kneeboard: the
        # racetrack row's schedule time is dwell, not transit, so the flight
        # plan table shows the planned patrol speed there instead of dist/time.
        flight_plan = self.flight.flight_plan
        patrol_speed = (
            flight_plan.patrol_speed if flight_plan.is_patrol(flight_plan) else None
        )

        flight_data = FlightData(
            package=self.flight.package,
            aircraft_type=self.flight.unit_type,
            squadron=self.flight.squadron,
            flight_type=self.flight.flight_type,
            group_name=self.group.name,
            combat_sar_king=combat_sar_king,
            units=self.group.units,
            size=len(self.group.units),
            friendly=self.flight.departure.captured,
            departure_delay=mission_start_time,
            departure=self.flight.departure.active_runway(
                self.game.theater, self.game.conditions, self.dynamic_runways
            ),
            arrival=self.flight.arrival.active_runway(
                self.game.theater, self.game.conditions, self.dynamic_runways
            ),
            divert=divert,
            waypoints=waypoints,
            intra_flight_channel=flight_channel,
            bingo_fuel=bingo_estimator.estimate_bingo(),
            joker_fuel=bingo_estimator.estimate_joker(),
            custom_name=self.flight.custom_name,
            laser_codes=laser_codes,
            start_type=self.flight.start_type,
            patrol_speed=patrol_speed,
        )

        self.register_escort_leash()

        return flight_data

    def register_escort_leash(self) -> None:
        if self.flight.flight_type not in [
            FlightType.ESCORT,
            FlightType.SEAD_ESCORT,
        ]:
            return

        if self.flight.package.primary_flight is None:
            return

        escort_group_id = self.flight.group_id
        escorted_group_id = self.flight.package.primary_flight.group_id
        if escort_group_id <= 0 or escorted_group_id <= 0:
            return

        engagement_range = (
            self.flight.coalition.doctrine.sead_escort_engagement_range
            if self.flight.flight_type == FlightType.SEAD_ESCORT
            else self.flight.coalition.doctrine.escort_engagement_range
        ).meters

        if self.flight.is_helo:
            engagement_range *= 0.25

        escorted_group = self.mission.find_group_by_id(escorted_group_id)
        escorted_group_name = str(escorted_group.name) if escorted_group else ""

        self.mission_data.escorts.append(
            EscortInfo(
                escort_group_id=escort_group_id,
                escorted_group_id=escorted_group_id,
                engagement_range_meters=int(engagement_range),
                escort_group_name=str(self.group.name),
                escorted_group_name=escorted_group_name,
            )
        )

    def configure_flight_member(
        self, unit: FlyingUnit, member: FlightMember, laser_codes: list[Optional[int]]
    ) -> None:
        self.set_skill(unit, member)

        # Only surface the laser code on the kneeboard when this member's loadout can
        # actually use it (LGB or targeting pod). An escort F/A-18 still gets a code
        # allocated (member.tgp_laser_code, applied to the unit for the .miz), but
        # printing a Laser Code page for an aircraft carrying neither is just noise.
        if (
            code := member.tgp_laser_code
        ) is not None and member.loadout.uses_laser_code():
            laser_codes.append(code.code)
        else:
            laser_codes.append(None)

    def setup_radios(self) -> RadioFrequency:
        freq = self.flight.frequency
        if freq is None and (freq := self.flight.package.frequency) is None:
            freq = self.radio_registry.alloc_uhf()
            self.flight.package.frequency = freq
        if freq not in self.radio_registry.allocated_channels:
            self.radio_registry.reserve(freq)

        if self.flight.flight_type in {
            FlightType.AEWC,
            FlightType.REFUELING,
            FlightType.RECOVERY,
        }:
            self.register_air_support(freq)
        elif self.flight.client_count and self.flight.squadron.radio_presets:
            freq = self.flight.squadron.radio_presets["intra_flight"][0]
        elif self.flight.frequency is None and self.flight.client_count:
            freq = self.flight.unit_type.alloc_flight_radio(self.radio_registry)

        self.group.set_frequency(freq.mhz)
        return freq

    def register_air_support(self, channel: RadioFrequency) -> None:
        callsign = callsign_for_support_unit(self.group)
        if isinstance(self.flight.flight_plan, AewcFlightPlan):
            self.mission_data.awacs.append(
                AwacsInfo(
                    group_name=str(self.group.name),
                    callsign=callsign,
                    freq=channel,
                    depature_location=self.flight.departure.name,
                    start_time=self.flight.flight_plan.patrol_start_time,
                    end_time=self.flight.flight_plan.patrol_end_time,
                    blue=self.flight.departure.captured,
                    unit=self.group.units[0],
                )
            )
        elif (
            isinstance(self.flight.flight_plan, TheaterRefuelingFlightPlan)
            or isinstance(self.flight.flight_plan, PackageRefuelingFlightPlan)
            or isinstance(self.flight.flight_plan, RecoveryTankerFlightPlan)
        ):
            tacan = self.flight.tacan
            if tacan is None and self.flight.squadron.aircraft.dcs_unit_type.tacan:
                try:
                    tacan = self.tacan_registry.alloc_for_band(
                        TacanBand.Y, TacanUsage.AirToAir
                    )
                except OutOfTacanChannelsError:
                    tacan = random.choice(list(self.tacan_registry.allocated_channels))
            else:
                tacan = self.flight.tacan
            self.mission_data.tankers.append(
                TankerInfo(
                    group_name=str(self.group.name),
                    callsign=callsign,
                    variant=self.flight.unit_type.display_name,
                    freq=channel,
                    tacan=tacan,
                    start_time=self.flight.flight_plan.patrol_start_time,
                    end_time=self.flight.flight_plan.patrol_end_time,
                    blue=self.flight.departure.captured,
                    aircraft_type=self.flight.unit_type,
                )
            )

    def set_skill(self, unit: FlyingUnit, member: FlightMember) -> None:
        if not member.is_player:
            unit.skill = self.skill_level_for(unit, member.pilot)
            return

        if self.use_client or "Pilot #1" not in unit.name:
            unit.set_client()
        else:
            unit.set_player()

    def skill_level_for(self, unit: FlyingUnit, pilot: Optional[Pilot]) -> Skill:
        squadron = self.flight.squadron
        if pilot is None:
            logging.error(f"Cannot determine skill level: {unit.name} has not pilot")
            return squadron.base_skill
        return squadron.pilot_skill(pilot)

    def setup_props(self) -> None:
        unit: FlyingUnit
        member: FlightMember
        for unit, member in zip(self.group.units, self.flight.iter_members()):
            props = dict(member.properties)
            if (code := member.weapon_laser_code) is not None:
                for laser_code_config in self.flight.unit_type.laser_code_configs:
                    props.update(laser_code_config.property_dict_for_code(code.code))
            if unit.unit_type.datalink_networkable() and self.no_datalink_set(props):
                self.set_datalink(props, unit.callsign_as_str())
            if self.game.settings.restrict_props_by_date:
                self.degrade_props_for_date(props)
            for prop_id, value in props.items():
                unit.set_property(prop_id, value)

    def degrade_props_for_date(
        self, props: dict[str, bool | float | int | str]
    ) -> None:
        """Clamp date-gated aircraft properties (e.g. JHMCS) to a period-correct value.

        Mirrors weapon date-gating. We resolve each gated property against the unit
        type's default and force-set the fallback when needed, because an unset helmet
        device still defaults to JHMCS in the .miz — so only inspecting ``props`` would
        miss the (common) defaulted case.
        """
        date = self.game.date
        unit_type = self.flight.unit_type
        gate = unit_type.property_date_gate
        for prop in gate.gated_props(unit_type.dcs_unit_type.properties):
            if prop.values is None or prop.default is None:
                continue
            current = props.get(prop.identifier, prop.default)
            clamped = gate.period_correct_value(prop, current, date)
            if clamped is not None and clamped != current:
                props[prop.identifier] = clamped

    @staticmethod
    def no_datalink_set(props: dict[str, bool | float | int | str]) -> bool:
        for type in DataLinkKey:
            if type.value in props:
                return False
        return True

    def set_datalink(
        self, props: dict[str, bool | float | int | str], callsign: str
    ) -> None:
        vcl = callsign[:-2][0] + callsign[:-2][-1]
        vcn = callsign[-2:]
        identifier = self.datalink_registry.alloc_for_aircraft(self.flight.unit_type)
        self.set_datalink_props(props, vcl.upper(), vcn, identifier)

    @staticmethod
    def set_datalink_props(
        props: dict[str, bool | float | int | str],
        label: str,
        number: str,
        identifier: DataLinkIdentifier,
    ) -> None:
        if identifier.type in [DataLinkKey.LINK16, DataLinkKey.SADL]:
            if not props.get(VOICE_CALLSIGN_LABEL):
                props[VOICE_CALLSIGN_LABEL] = label
            if not props.get(VOICE_CALLSIGN_NUMBER):
                props[VOICE_CALLSIGN_NUMBER] = number
        elif identifier.type in [DataLinkKey.IDM]:
            if not props.get(OWNSHIP_CALLSIGN):
                props[OWNSHIP_CALLSIGN] = f"G-{identifier.id}"
        props[identifier.type.value] = identifier.id

    def setup_payloads(self) -> None:
        for unit, member in zip(self.group.units, self.flight.iter_members()):
            self.setup_payload(unit, member)

    def setup_payload(self, unit: FlyingUnit, member: FlightMember) -> None:
        unit.pylons.clear()

        loadout = member.loadout
        if self.game.settings.restrict_weapons_by_date:
            # Always apply target overrides for AI, only for players if setting is enabled
            should_apply_overrides = (
                not member.is_player
                or self.game.settings.apply_target_overrides_to_loadouts
            )
            target = self.flight.package.target if should_apply_overrides else None
            loadout = loadout.degrade_for_date(
                self.flight.unit_type,
                self.game.date,
                self.flight.squadron.coalition.faction,
                target,
            )

        # §54 M2: enforce airfield munitions stock -- swap scarce stores the base is
        # out of down to a stocked fallback (dumb bombs), or clear the pylon. Only once
        # the stocks are seeded (so pre-seed turns aren't falsely starved).
        if self.game.settings.restrict_weapons_by_stock and getattr(
            self.game, "munitions_seeded", False
        ):
            loadout = loadout.degrade_for_stock(
                self.flight.departure.base.munitions,
                self.flight.unit_type,
                self.game.date,
                self.flight.squadron.coalition.faction,
            )

        loadout = add_range_fuel_tanks(self.flight, loadout, self.game.settings)

        for pylon_number, weapon in loadout.pylons.items():
            if weapon is None:
                continue
            pylon = Pylon.for_aircraft(self.flight.unit_type, pylon_number)
            settings = self._merge_laser_code(
                loadout.pylon_settings.get(pylon_number),
                weapon.accepts_laser_code(),
                member.weapon_laser_code,
            )
            pylon.equip(unit, weapon, settings)

    @staticmethod
    def _merge_laser_code(
        base: Optional[dict[str, Any]],
        accepts_laser_code: bool,
        laser_code: Optional[LaserCode],
    ) -> Optional[dict[str, Any]]:
        if laser_code is None or not accepts_laser_code:
            return base
        settings = dict(base or {})
        settings["laser_code"] = laser_code.code
        return settings

    def setup_fuel(self) -> None:
        fuel = self.flight.state.estimate_fuel()
        if fuel < 0:
            logging.warning(
                f"Flight {self.flight} is estimated to have no fuel at mission start. "
                "This estimate does not account for external fuel tanks. Setting "
                "starting fuel to 100kg."
            )
            fuel = 100
        for unit, pilot in zip(self.group.units, self.flight.roster.iter_pilots()):
            if pilot is not None and pilot.player:
                unit.fuel = fuel
            else:
                unit.fuel = self.flight.fuel
