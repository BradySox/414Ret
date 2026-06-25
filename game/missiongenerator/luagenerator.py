from __future__ import annotations

import logging
import os
import textwrap
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from dcs import Mission
from dcs.action import DoScript, DoScriptFile
from dcs.task import Modulation
from dcs.translation import String
from dcs.triggers import TriggerStart

from game.ato import FlightType
from game.data.units import UnitClass
from game.dcs.aircrafttype import AircraftType
from game.plugins import LuaPluginManager
from game.theater import TheaterGroundObject
from game.theater.iadsnetwork.iadsrole import IadsRole
from game.utils import escape_string_for_lua
from .interceptluadata import populate_intercept_lua
from .missiondata import MissionData
from .scarluadata import build_scar_taskings, populate_scar_lua

if TYPE_CHECKING:
    from game import Game


# Civilian background-traffic routing knobs (consumed by civilian_traffic.lua).
# Kept here as named constants so they are easy to retune after an in-game pass.
# KEEPOUT is the radius of the no-fly bubble dropped around each active front so
# civilians never spawn in the fight; the MAXDIST caps turn RAT into short
# regional hops (a field with no neighbour within the cap simply gets no traffic)
# so straight-line routes stay clear of the contested band between the two sides.
# Units: KEEPOUT in metres (matches DCS world coords / Point.x|y); the MAXDIST
# caps in km (RAT:SetMaxDistance multiplies by 1000 internally).
CIVILIAN_TRAFFIC_KEEPOUT_M = 75_000  # ~40 NM
CIVILIAN_TRAFFIC_MAXDIST_FW_KM = 280  # fixed-wing regional hop cap (~150 NM)
CIVILIAN_TRAFFIC_MAXDIST_HELO_KM = 130  # rotary city-hop cap (~70 NM)
# The keep-out is intentionally SOFT: each neutral field inside the bubble is
# usually dropped, but kept with this small probability, so once in a while a
# civilian routes near/through the fight and the player has to watch for it. Low
# by design -- the front stays mostly clear. 0 = hard keep-out, 1 = no keep-out.
CIVILIAN_TRAFFIC_STRAY_CHANCE = 0.08


class LuaGenerator:
    def __init__(
        self,
        game: Game,
        mission: Mission,
        mission_data: MissionData,
    ) -> None:
        self.game = game
        self.mission = mission
        self.mission_data = mission_data
        self.plugin_scripts: list[str] = []

    def generate(self) -> None:
        self.generate_plugin_data()
        self.inject_plugins()
        self._inject_tic_script()
        self._inject_tars_script()
        self._inject_scar_script()
        self._inject_flightcontrol_script()
        self._inject_civilian_traffic_script()

    def _inject_tic_script(self) -> None:
        """Inject TIC_v1.1.lua (Troops In Contact, by Grendel) as a core script.

        Fires only when the TIC plugin is enabled and the FLOT generator handed
        frontline groups over to TIC (mission_data.tic_groups non-empty). The
        preamble pre-seeds the GLSCO config table from the plugin options
        before the script's file-scope auto-initialization runs. MOOSE is
        already loaded by the base plugin at this point in the trigger order.
        """
        if not self.mission_data.tic_groups:
            return
        script_path = Path("./resources/plugins/tic/TIC_v1.1.lua")
        if not script_path.exists():
            logging.error(
                "TIC_v1.1.lua not found at %s — TIC-named frontline groups "
                "will stay late-activated and never spawn",
                script_path.resolve(),
            )
            return
        init_path = Path("./resources/plugins/tic/tic_414_init.lua")
        if not init_path.exists():
            logging.error(
                "tic_414_init.lua not found at %s — TIC battle would never "
                "initialize; skipping TIC entirely",
                init_path.resolve(),
            )
            return
        preamble = textwrap.dedent("""\
            -- Pre-seed TIC (GLSCO) configuration from Retribution plugin
            -- options. TIC respects values that exist before it loads.
            -- AutoInitialize/AutoStart are disabled because tic_414_init.lua
            -- (loaded right after the main script) installs the 414th's
            -- ambient-fire extension and then owns Initialize/Activate.
            GLSCO = GLSCO or {}
            GLSCO.AutoInitialize = false
            GLSCO.AutoStart = false
            if dcsRetribution and dcsRetribution.plugins
                    and dcsRetribution.plugins.tic then
                GLSCO.StormTrooperAI =
                    dcsRetribution.plugins.tic.stormtrooper == true
                GLSCO.CreateMenus =
                    dcsRetribution.plugins.tic.createMenus == true
            end
            """)
        trigger = TriggerStart(comment="Load TIC_v1.1 (frontline battle sim)")
        trigger.add_action(DoScript(String(preamble)))
        fileref = self.mission.map_resource.add_resource_file(script_path.resolve())
        trigger.add_action(DoScriptFile(fileref))
        init_fileref = self.mission.map_resource.add_resource_file(init_path.resolve())
        trigger.add_action(DoScriptFile(init_fileref))
        self.mission.triggerrules.triggers.append(trigger)

    def _inject_civilian_traffic_script(self) -> None:
        """Inject civilian_traffic.lua for RAT background air traffic.

        Bakes the list of every Retribution-controlled airbase into a DO SCRIPT
        preamble so the Lua can compute the civilian pool at runtime by subtracting
        those from world.getAirbases(). Works on any terrain without modification.
        MOOSE and the RAT_CIV_* template groups must already be present.
        """
        script_path = Path("./resources/plugins/civilian_traffic/civilian_traffic.lua")
        if not script_path.exists():
            logging.error(
                "civilian_traffic.lua not found at %s — skipping civilian RAT traffic",
                script_path.resolve(),
            )
            return

        preamble = self._civilian_traffic_preamble()
        trigger = TriggerStart(comment="Civilian background air traffic (RAT)")
        trigger.add_action(DoScript(String(preamble)))
        fileref = self.mission.map_resource.add_resource_file(script_path.resolve())
        trigger.add_action(DoScriptFile(fileref))
        self.mission.triggerrules.triggers.append(trigger)

    def _civilian_traffic_preamble(self) -> str:
        """Build the DO SCRIPT preamble the civilian_traffic.lua reads at runtime.

        Emits four globals: the combat-airbase exclusion list (endpoints to skip),
        the active-front contested points (a keep-out bubble so civilians never
        spawn in the fight), and the per-layer regional route caps. Positions use
        the pydcs convention (Point.x -> DCS x, Point.y -> DCS z); the Lua compares
        them against ab:getPoint() (.x/.z).
        """
        excl = sorted(
            cp.name
            for cp in self.game.theater.controlpoints
            if cp.dcs_airport is not None
        )
        excl_lua = "{" + ", ".join(f'"{b}"' for b in excl) + "}"

        fronts = [
            f"{{x={front.position.x}, y={front.position.y}}}"
            for front in self.game.theater.conflicts()
        ]
        fronts_lua = "{" + ", ".join(fronts) + "}"

        return (
            f"_CIVILIAN_TRAFFIC_EXCL = {excl_lua}\n"
            f"_CIVILIAN_TRAFFIC_FRONTS = {fronts_lua}\n"
            f"_CIVILIAN_TRAFFIC_KEEPOUT = {CIVILIAN_TRAFFIC_KEEPOUT_M}\n"
            f"_CIVILIAN_TRAFFIC_MAXDIST_FW = {CIVILIAN_TRAFFIC_MAXDIST_FW_KM}\n"
            f"_CIVILIAN_TRAFFIC_MAXDIST_HELO = {CIVILIAN_TRAFFIC_MAXDIST_HELO_KM}\n"
            f"_CIVILIAN_TRAFFIC_STRAY_CHANCE = {CIVILIAN_TRAFFIC_STRAY_CHANCE}\n"
        )

    @staticmethod
    def _plugin_enabled(identifier: str) -> bool:
        for plugin in LuaPluginManager.plugins():
            if plugin.definition.identifier == identifier:
                return plugin.enabled
        return False

    def _inject_tars_script(self) -> None:
        """Inject Ops.TARS (vendored) + the 414th config/bridge layer.

        Fires only when the TARS plugin is enabled. TARS.lua defines the class
        but does NOT self-instantiate; tars_414_init.lua calls TARS:New(),
        applies the 414th config (theater-correct target/loadout filters), and
        bridges captures into the tars_recon_captures global the base plugin
        serializes into state.json. Appended after inject_plugins() so
        dcsRetribution.plugins.tars already exists; MOOSE is loaded earlier by
        the base plugin.
        """
        if not self._plugin_enabled("tars"):
            return
        script_path = Path("./resources/plugins/tars/TARS.lua")
        init_path = Path("./resources/plugins/tars/tars_414_init.lua")
        for path in (script_path, init_path):
            if not path.exists():
                logging.error(
                    "TARS plugin file not found at %s — recon disabled",
                    path.resolve(),
                )
                return
        trigger = TriggerStart(comment="Load Ops.TARS (player recon / TARPS film)")
        fileref = self.mission.map_resource.add_resource_file(script_path.resolve())
        trigger.add_action(DoScriptFile(fileref))
        init_fileref = self.mission.map_resource.add_resource_file(init_path.resolve())
        trigger.add_action(DoScriptFile(init_fileref))
        self.mission.triggerrules.triggers.append(trigger)

    def _inject_scar_script(self) -> None:
        """Inject the SCAR scenario/results bridge.

        Fires only when the SCAR plugin is enabled and at least one SCAR flight
        was planned (mission_data.scar_taskings non-empty). The
        dcsRetribution.Scar config table is already emitted by
        generate_plugin_data(); scar_414_init.lua reads it, spawns the
        placeholder HVT per tasking, runs the pass/fail watcher, and appends to
        the scar_results global the base plugin serializes into state.json.
        MOOSE/mist are loaded earlier by the base plugin.
        """
        if not self._plugin_enabled("scar"):
            return
        if not self.mission_data.scar_taskings:
            return
        script_path = Path("./resources/plugins/scar/scar_414_init.lua")
        if not script_path.exists():
            logging.error(
                "scar_414_init.lua not found at %s — SCAR scenario disabled",
                script_path.resolve(),
            )
            return
        trigger = TriggerStart(comment="Load SCAR scenario bridge")
        fileref = self.mission.map_resource.add_resource_file(script_path.resolve())
        trigger.add_action(DoScriptFile(fileref))
        self.mission.triggerrules.triggers.append(trigger)

    def _inject_flightcontrol_script(self) -> None:
        """Inject players-only MOOSE FLIGHTCONTROL ATC at friendly land airbases.

        Fires only when the FlightControl plugin is enabled. Emits the friendly
        airdrome list (name + ATC frequency where known) into
        dcsRetribution.FlightControl, then loads flightcontrol_414_init.lua which
        spins up one FLIGHTCONTROL per base. MOOSE FLIGHTCONTROL itself rejects
        FARPs and ships, so we only need to pre-filter to blue airdromes.
        """
        if not self._plugin_enabled("flightcontrol"):
            return
        script_path = Path(
            "./resources/plugins/flightcontrol/flightcontrol_414_init.lua"
        )
        if not script_path.exists():
            logging.error(
                "flightcontrol_414_init.lua not found at %s — ATC disabled",
                script_path.resolve(),
            )
            return

        entries = self._flightcontrol_airbase_entries()
        if not entries:
            return

        preamble = (
            "dcsRetribution = dcsRetribution or {}\n"
            "dcsRetribution.FlightControl = { airbases = {\n"
            + ",\n".join(entries)
            + "\n} }\n"
        )
        trigger = TriggerStart(comment="Flight Control (players-only ATC tower)")
        trigger.add_action(DoScript(String(preamble)))
        fileref = self.mission.map_resource.add_resource_file(script_path.resolve())
        trigger.add_action(DoScriptFile(fileref))
        self.mission.triggerrules.triggers.append(trigger)

    def _flightcontrol_airbase_entries(self) -> list[str]:
        """Build the Lua table-literal entries for each friendly land airbase.

        One entry per blue-held airdrome: its name plus the ATC frequency and
        modulation when we have runway data for it (the Lua side falls back to a
        default frequency otherwise). Carriers/FARPs are excluded here, and
        FLIGHTCONTROL also rejects them at runtime.
        """
        atc_by_field = {
            runway.airfield_name: runway.atc
            for runway in self.mission_data.runways
            if runway.atc is not None
        }

        entries: list[str] = []
        for cp in self.game.theater.controlpoints:
            if cp.dcs_airport is None or not cp.captured.is_blue:
                continue
            name = escape_string_for_lua(cp.name)
            atc = atc_by_field.get(cp.name)
            if atc is not None:
                entries.append(
                    f'{{ name = "{name}", freq = {atc.mhz}, '
                    f"modulation = {atc.modulation.value} }}"
                )
            else:
                entries.append(f'{{ name = "{name}" }}')
        return entries

    def generate_plugin_data(self) -> None:
        lua_data = LuaData("dcsRetribution")

        install_path = lua_data.add_item("installPath")
        install_path.set_value(os.path.abspath("."))

        airbases_object = lua_data.add_item("Airbases")
        for runway in self.mission_data.runways:
            if runway.tacan is not None:
                airbase_item = airbases_object.add_item()
                airbase_item.add_key_value("name", runway.airfield_name)
                airbase_item.add_key_value("tacan", str(runway.tacan))
                airbase_item.add_key_value(
                    "tacan_callsign", runway.tacan_callsign or ""
                )

        carriers_object = lua_data.add_item("Carriers")

        for carrier in self.mission_data.carriers:
            carrier_item = carriers_object.add_item()
            carrier_item.add_key_value("dcsGroupName", carrier.group_name)
            carrier_item.add_key_value("unit_name", carrier.unit_name)
            carrier_item.add_key_value("callsign", carrier.callsign)
            carrier_item.add_key_value("radio", str(carrier.freq.mhz))
            carrier_item.add_key_value(
                "tacan", str(carrier.tacan.number) + carrier.tacan.band.name
            )
            carrier_item.add_key_value("tacan_channel", str(carrier.tacan.number))
            carrier_item.add_key_value("tacan_band", carrier.tacan.band.name)
            if carrier.icls_channel:
                carrier_item.add_key_value("icls", str(carrier.icls_channel))

        tankers_object = lua_data.add_item("Tankers")
        for tanker in self.mission_data.tankers:
            tanker_item = tankers_object.add_item()
            tanker_item.add_key_value("dcsGroupName", tanker.group_name)
            tanker_item.add_key_value("callsign", tanker.callsign)
            tanker_item.add_key_value("variant", tanker.variant)
            tanker_item.add_key_value("radio", str(tanker.freq.mhz))
            if tanker.tacan:
                tanker_item.add_key_value("tacan", str(tanker.tacan))

        awacs_object = lua_data.add_item("AWACs")
        for awacs in self.mission_data.awacs:
            awacs_item = awacs_object.add_item()
            awacs_item.add_key_value("dcsGroupName", awacs.group_name)
            awacs_item.add_key_value("callsign", awacs.callsign)
            awacs_item.add_key_value("radio", str(awacs.freq.mhz))

        jtacs_object = lua_data.add_item("JTACs")
        for jtac in self.mission_data.jtacs:
            jtac_item = jtacs_object.add_item()
            jtac_item.add_key_value("dcsGroupName", jtac.group_name)
            jtac_item.add_key_value("callsign", jtac.callsign)
            jtac_item.add_key_value("zone", jtac.region)
            jtac_item.add_key_value("dcsUnit", jtac.unit_name)
            jtac_item.add_key_value("laserCode", jtac.code)
            jtac_item.add_key_value("radio", str(jtac.freq.mhz))
            jtac_item.add_key_value("modulation", jtac.freq.modulation.name)

        logistics_object = lua_data.add_item("Logistics")
        logistics_flights = logistics_object.add_item("flights")
        crates_object = logistics_object.add_item("crates")
        spawnable_crates: dict[str, str] = {}
        transports: list[AircraftType] = []
        for logistic_info in self.mission_data.logistics:
            if logistic_info.transport not in transports:
                transports.append(logistic_info.transport)
            coalition_color = "blue" if logistic_info.blue.is_blue else "red"
            logistics_item = logistics_flights.add_item()
            logistics_item.add_data_array("pilot_names", logistic_info.pilot_names)
            logistics_item.add_key_value("pickup_zone", logistic_info.pickup_zone)
            logistics_item.add_key_value("drop_off_zone", logistic_info.drop_off_zone)
            logistics_item.add_key_value("target_zone", logistic_info.target_zone)
            logistics_item.add_key_value(
                "side", str(2 if logistic_info.blue.is_blue else 1)
            )
            logistics_item.add_key_value("logistic_unit", logistic_info.logistic_unit)
            logistics_item.add_key_value(
                "aircraft_type", logistic_info.transport.dcs_id
            )
            logistics_item.add_key_value(
                "preload", "true" if logistic_info.preload else "false"
            )
            for cargo in logistic_info.cargo:
                if cargo.unit_type not in spawnable_crates:
                    spawnable_crates[cargo.unit_type] = str(200 + len(spawnable_crates))
                crate_weight = spawnable_crates[cargo.unit_type]
                for i in range(cargo.amount):
                    cargo_item = crates_object.add_item()
                    cargo_item.add_key_value("weight", crate_weight)
                    cargo_item.add_key_value("coalition", coalition_color)
                    cargo_item.add_key_value("zone", cargo.spawn_zone)
        transport_object = logistics_object.add_item("transports")
        for transport in transports:
            transport_item = transport_object.add_item()
            transport_item.add_key_value("aircraft_type", transport.dcs_id)
            transport_item.add_key_value("cabin_size", str(transport.cabin_size))
            transport_item.add_key_value(
                "troops", "true" if transport.cabin_size > 0 else "false"
            )
            transport_item.add_key_value(
                "crates", "true" if transport.can_carry_crates else "false"
            )
        spawnable_crates_object = logistics_object.add_item("spawnable_crates")
        for unit, weight in spawnable_crates.items():
            crate_item = spawnable_crates_object.add_item()
            crate_item.add_key_value("unit", unit)
            crate_item.add_key_value("weight", weight)

        target_points = lua_data.add_item("TargetPoints")
        for flight in self.mission_data.flights:
            if flight.friendly.is_blue and flight.flight_type in [
                FlightType.ANTISHIP,
                FlightType.DEAD,
                FlightType.SEAD,
                FlightType.STRIKE,
            ]:
                flight_type = str(flight.flight_type)
                flight_target = flight.package.target
                if flight_target:
                    flight_target_name = None
                    flight_target_type = None
                    if isinstance(flight_target, TheaterGroundObject):
                        flight_target_name = flight_target.obj_name
                        flight_target_type = (
                            flight_type + f" TGT ({flight_target.category})"
                        )
                    elif hasattr(flight_target, "name"):
                        flight_target_name = flight_target.name
                        flight_target_type = flight_type + " TGT (Airbase)"
                    target_item = target_points.add_item()
                    if flight_target_name:
                        target_item.add_key_value("name", flight_target_name)
                    if flight_target_type:
                        target_item.add_key_value("type", flight_target_type)
                    target_item.add_key_value(
                        "positionX", str(flight_target.position.x)
                    )
                    target_item.add_key_value(
                        "positionY", str(flight_target.position.y)
                    )

        for cp in self.game.theater.controlpoints:
            coalition_object = (
                lua_data.get_or_create_item("BlueAA")
                if cp.captured.is_blue
                else lua_data.get_or_create_item("RedAA")
            )
            for ground_object in cp.ground_objects:
                for g in ground_object.groups:
                    threat_range = g.max_threat_range()

                    if not threat_range:
                        continue

                    aa_item = coalition_object.add_item()
                    aa_item.add_key_value("name", ground_object.name)
                    aa_item.add_key_value("range", str(threat_range.meters))
                    aa_item.add_key_value("positionX", str(ground_object.position.x))
                    aa_item.add_key_value("positionY", str(ground_object.position.y))

        # Generate IADS Lua Item. The IADS node/connection data is emitted the same
        # way regardless of engine; an `engine` marker tells the Lua config bridges
        # which one should act (skynetiads-config.lua vs mantis-config.lua) — the
        # non-selected bridge no-ops. Default is SKYNET; MANTIS is gated behind the
        # (not-yet-UI-exposed) iads_engine setting and needs an in-game pass before
        # the default flips (docs/dev/design/414th-mantis-migration-notes.md).
        iads_engine = self.game.settings.iads_engine
        iads_object = lua_data.add_item("IADS")
        # NB: emit the marker as a nested item, not add_key_value — LuaData.serialize
        # drops scalar key-values on an object that also has nested items.
        iads_object.add_item("engine").set_value(iads_engine.value)
        # These should always be created even if they are empty.
        iads_object.get_or_create_item("BLUE")
        iads_object.get_or_create_item("RED")
        # Should probably do the same with all the roles... but the script is already
        # tolerant of those being empty.
        for node in self.game.theater.iads_network.iads_nodes(self.game):
            coalition = iads_object.get_or_create_item(
                "BLUE" if node.player.is_blue else "RED"
            )
            iads_type = coalition.get_or_create_item(node.iads_role.skynet_value)
            iads_element = iads_type.add_item()
            iads_element.add_key_value("dcsGroupName", node.dcs_name)
            if node.iads_role in [IadsRole.SAM, IadsRole.SAM_AS_EWR]:
                # add additional SkynetProperties to SAM Sites
                for property, value in node.properties.items():
                    iads_element.add_key_value(property, value)
            for role, connections in node.connections.items():
                iads_element.add_data_array(role, connections)

        populate_intercept_lua(lua_data, self.mission_data.intercept_entries)

        # SCAR scenario bridge: collect one tasking per SCAR target and emit
        # dcsRetribution.Scar. scar_taskings also gates _inject_scar_script. The
        # mission start time anchors each scenario's fail clock to the flight TOT.
        self.mission_data.scar_taskings = build_scar_taskings(
            self.game, self.mission.start_time
        )
        populate_scar_lua(lua_data, self.mission_data.scar_taskings)

        # Add artillery and support units info
        artillery_object = lua_data.add_item("artilleryGroups")
        ground_artillery_group_collection = artillery_object.get_or_create_item(
            "groundArtillery"
        )
        ship_artillery_group_collection = artillery_object.get_or_create_item(
            "shipArtillery"
        )

        # First add all artillery units that are theater objects (mostly ships)
        for ground_object in self.game.theater.ground_objects:
            for group in ground_object.groups:
                # Check if first unit in group is ground-based or ship artillery
                group_first_unit = group.units[0]
                if group_first_unit.unit_type is None:
                    continue
                if group_first_unit.unit_type.unit_class == UnitClass.ARTILLERY:
                    ground_artillery_group = (
                        ground_artillery_group_collection.add_item()
                    )
                    ground_artillery_group.add_key_value("groupName", group.group_name)
                elif group_first_unit.unit_type.unit_class in (
                    UnitClass.CRUISER,
                    UnitClass.DESTROYER,
                    UnitClass.FRIGATE,
                ):
                    # TODO: we assume that these ship classes have guns... Which might not be the case.
                    ship_artillery_group = ship_artillery_group_collection.add_item()
                    ship_artillery_group.add_key_value("groupName", group.group_name)

        # Add artillery that are frontline groups
        for frontline_group in (
            self.mission_data.player_frontline_groups
            + self.mission_data.enemy_frontline_groups
        ):
            if frontline_group.unit_type.unit_class == UnitClass.ARTILLERY:
                ground_artillery_group = ground_artillery_group_collection.add_item()
                ground_artillery_group.add_key_value(
                    "groupName", frontline_group.group_name
                )

        # Add forward observer (FO) (TODO: maybe adding new flight type "Foward Observer"?)
        forward_observer_object = lua_data.add_item("forwardObserverUnits")
        for flight in self.mission_data.flights:
            if len(flight.client_units) == 0:
                continue
            if flight.flight_type != FlightType.ARMED_RECON:
                continue

            for client_unit in flight.client_units:
                forward_observer = forward_observer_object.add_item()
                forward_observer.add_key_value("unitName", client_unit.name)

        escorts_object = lua_data.add_item("Escorts")
        for escort in self.mission_data.escorts:
            escort_item = escorts_object.add_item()
            escort_item.add_key_value("escortGroupId", str(escort.escort_group_id))
            escort_item.add_key_value("escortedGroupId", str(escort.escorted_group_id))
            escort_item.add_key_value("escortGroupName", escort.escort_group_name)
            escort_item.add_key_value("escortedGroupName", escort.escorted_group_name)
            escort_item.add_key_value(
                "engagementRangeMeters", str(escort.engagement_range_meters)
            )

        self._generate_combat_sar(lua_data)

        trigger = TriggerStart(comment="Set DCS Retribution data")
        trigger.add_action(DoScript(String(lua_data.create_operations_lua())))
        self.mission.triggerrules.triggers.append(trigger)

        self._inject_atis_lua()

    def _generate_combat_sar(self, lua_data: LuaData) -> None:
        """Emit dcsRetribution.CombatSAR + the downed-pilot template group.

        Combat SAR (FlightType.COMBAT_SAR) is a player-flown pilot-rescue orbit
        executed at runtime by the MOOSE CSAR engine (resources/plugins/combatsar).
        Python's job is only to (1) tell the Lua bridge which generated groups are
        the CH-47 rescue helos (and which C-130s fly the "King" orbit), and (2) drop
        one late-activation infantry group that MOOSE CSAR clones at each crash site
        as the downed pilot. Blue-only for v1; AI standing alert is a later phase.
        """
        rescue_helos: list[str] = []
        kings: list[str] = []
        for flight in self.mission_data.flights:
            if flight.flight_type is not FlightType.COMBAT_SAR:
                continue
            if not flight.friendly.is_blue:
                continue
            if flight.aircraft_type.helicopter:
                rescue_helos.append(flight.group_name)
            else:
                kings.append(flight.group_name)

        # No rescue helo tasked -> the CSAR service is simply absent this mission.
        # Skip the template too so we never leave an orphan group in the .miz.
        if not rescue_helos:
            return

        template_name = self._generate_combat_sar_pilot_template()
        if template_name is None:
            logging.warning(
                "Combat SAR: could not build the downed-pilot template; "
                "skipping CSAR setup for this mission."
            )
            return

        combat_sar = lua_data.add_item("CombatSAR")
        combat_sar.add_key_value("pilotTemplate", template_name)
        combat_sar.add_data_array("rescueHelos", rescue_helos)
        combat_sar.add_data_array("kings", kings)

    def _generate_combat_sar_pilot_template(self) -> Optional[str]:
        """Add a hidden, late-activation infantry group for MOOSE CSAR to clone as
        the downed pilot. Returns its group name, or None if it can't be built."""
        faction = self.game.blue.faction
        infantry = next(faction.infantry_with_class(UnitClass.INFANTRY), None)
        if infantry is not None:
            dcs_unit_type = infantry.dcs_unit_type
        else:
            # Vanilla fallback so the template exists even for an infantry-less faction.
            from dcs.vehicles import Infantry

            dcs_unit_type = Infantry.Soldier_M4

        anchor = next(
            (cp for cp in self.game.theater.controlpoints if cp.captured.is_blue),
            None,
        )
        if anchor is None:
            return None

        country = self.mission.country(faction.country.name)
        group_name = "Combat SAR Downed Pilot"
        group = self.mission.vehicle_group(
            country,
            group_name,
            dcs_unit_type,
            position=anchor.position,
            group_size=1,
        )
        group.late_activation = True
        group.hidden_on_mfd = True
        return group_name

    def _serialize_atis_lua(self) -> str:
        """Return a Lua assignment for dcsRetribution.Atis, or '' when empty.

        freq/modulation are emitted as bare Lua numbers (MOOSE ATIS:New expects
        numeric args); only the airbase name is a quoted string.
        """
        if not self.mission_data.atis_frequencies:
            return ""
        rows = []
        for atis in self.mission_data.atis_frequencies:
            name = escape_string_for_lua(atis.airfield_name)
            modulation = 0 if atis.frequency.modulation == Modulation.AM else 1
            rows.append(
                '  { name = "%s", freq = %.3f, modulation = %d },'
                % (name, atis.frequency.mhz, modulation)
            )
        body = "\n".join(rows)
        return (
            "if dcsRetribution then\n"
            "  dcsRetribution.Atis = {\n" + body + "\n  }\nend\n"
        )

    def _inject_atis_lua(self) -> None:
        lua = self._serialize_atis_lua()
        if lua:
            self.inject_lua_trigger(lua, "dcsRetribution.Atis (MOOSE ATIS)")

    def inject_lua_trigger(self, contents: str, comment: str) -> None:
        trigger = TriggerStart(comment=comment)
        trigger.add_action(DoScript(String(contents)))
        self.mission.triggerrules.triggers.append(trigger)

    def bypass_plugin_script(self, mnemonic: str) -> None:
        self.plugin_scripts.append(mnemonic)

    def inject_plugin_script(
        self, plugin_mnemonic: str, script: str, script_mnemonic: str
    ) -> None:
        if script_mnemonic in self.plugin_scripts:
            logging.debug(f"Skipping already loaded {script} for {plugin_mnemonic}")
            return

        self.plugin_scripts.append(script_mnemonic)

        plugin_path = Path("./resources/plugins", plugin_mnemonic)

        script_path = Path(plugin_path, script)
        if not script_path.exists():
            logging.error(f"Cannot find {script_path} for plugin {plugin_mnemonic}")
            return

        trigger = TriggerStart(comment=f"Load {script_mnemonic}")
        filename = script_path.resolve()
        fileref = self.mission.map_resource.add_resource_file(filename)
        trigger.add_action(DoScriptFile(fileref))
        self.mission.triggerrules.triggers.append(trigger)

    def inject_other_plugin_resources(self, plugin_mnemonic: str, file: str) -> None:
        plugin_path = Path("./resources/plugins", plugin_mnemonic)

        resource_path = Path(plugin_path, file)
        if not resource_path.exists():
            logging.error(f"Cannot find {resource_path} for plugin {plugin_mnemonic}")
            return

        filename = resource_path.resolve()
        self.mission.map_resource.add_resource_file(filename)

    def _sof_c130_present(self) -> bool:
        """True if a SOF insert is flying the C-130J-30.

        The EW plugin (C-130J Mission Systems) attaches to every C-130J-30 by
        airframe alone (its eligibility check is purely ``getTypeName() ==
        "C-130J-30"``), so it would hijack a SOF insert's C-130 -- bolting the
        EW/ISR menu and behavior onto the airdrop aircraft. When a SOF C-130 is
        in the mission we suppress the EW plugin so the insert flies clean.
        """
        for coalition in (self.game.blue, self.game.red):
            for package in coalition.ato.packages:
                for flight in package.flights:
                    if flight.flight_type is FlightType.SOF and flight.is_c130j:
                        return True
        return False

    def inject_plugins(self) -> None:
        skip_ew = self._sof_c130_present()
        for plugin in LuaPluginManager.plugins():
            if skip_ew and plugin.definition.identifier == "c130j":
                logging.warning(
                    "SOF insert is flying the C-130J-30 the EW plugin claims by "
                    "airframe; skipping the C-130J Mission Systems (EW) plugin for "
                    "this mission so it doesn't hijack the SOF aircraft."
                )
                continue
            if plugin.enabled:
                plugin.inject_scripts(self)
                plugin.inject_configuration(self)
                plugin.inject_other_resource_files(self)


class LuaValue:
    key: Optional[str]
    value: str | list[str]

    def __init__(self, key: Optional[str], value: str | list[str]):
        self.key = key
        self.value = value

    def serialize(self) -> str:
        serialized_value = self.key + " = " if self.key else ""
        if isinstance(self.value, str):
            serialized_value += f'"{escape_string_for_lua(self.value)}"'
        else:
            escaped_values = [f'"{escape_string_for_lua(v)}"' for v in self.value]
            serialized_value += "{" + ", ".join(escaped_values) + "}"
        return serialized_value


class LuaItem(ABC):
    value: LuaValue | list[LuaValue]
    name: Optional[str]

    def __init__(self, name: Optional[str]):
        self.value = []
        self.name = name

    def set_value(self, value: str) -> None:
        self.value = LuaValue(None, value)

    def set_data_array(self, values: list[str]) -> None:
        self.value = LuaValue(None, values)

    def add_data_array(self, key: str, values: list[str]) -> None:
        self._add_value(LuaValue(key, values))

    def add_key_value(self, key: str, value: str) -> None:
        self._add_value(LuaValue(key, value))

    def _add_value(self, value: LuaValue) -> None:
        if isinstance(self.value, list):
            self.value.append(value)
        else:
            self.value = value

    @abstractmethod
    def add_item(self, item_name: Optional[str] = None) -> LuaItem:
        """adds a new item to the LuaArray without checking the existence"""
        raise NotImplementedError

    @abstractmethod
    def get_item(self, item_name: str) -> Optional[LuaItem]:
        """gets item from LuaArray. Returns None if it does not exist"""
        raise NotImplementedError

    @abstractmethod
    def get_or_create_item(self, item_name: Optional[str] = None) -> LuaItem:
        """gets item from the LuaArray or creates one if it does not exist already"""
        raise NotImplementedError

    @abstractmethod
    def serialize(self) -> str:
        if isinstance(self.value, LuaValue):
            return self.value.serialize()
        else:
            serialized_data = [d.serialize() for d in self.value]
            return "{" + ", ".join(serialized_data) + "}"


class LuaData(LuaItem):
    objects: list[LuaData]
    base_name: Optional[str]

    def __init__(self, name: Optional[str], is_base_name: bool = True):
        self.objects = []
        self.base_name = name if is_base_name else None
        super().__init__(name)

    def add_item(self, item_name: Optional[str] = None) -> LuaItem:
        item = LuaData(item_name, False)
        self.objects.append(item)
        return item

    def get_item(self, item_name: str) -> Optional[LuaItem]:
        for lua_object in self.objects:
            if lua_object.name == item_name:
                return lua_object
        return None

    def get_or_create_item(self, item_name: Optional[str] = None) -> LuaItem:
        if item_name:
            item = self.get_item(item_name)
            if item:
                return item
        return self.add_item(item_name)

    def serialize(self, level: int = 0) -> str:
        """serialize the LuaData to a string"""
        serialized_data: list[str] = []
        serialized_name = ""
        linebreak = "\n"
        tab = "\t"
        tab_end = ""
        for _ in range(level):
            tab += "\t"
            tab_end += "\t"
        if self.base_name:
            # Only used for initialization of the object in lua
            serialized_name += self.base_name + " = "
        if self.objects:
            # nested objects
            serialized_objects = [o.serialize(level + 1) for o in self.objects]
            if self.name:
                if self.name is not self.base_name:
                    serialized_name += self.name + " = "
            serialized_data.append(
                serialized_name
                + "{"
                + linebreak
                + tab
                + ("," + linebreak + tab).join(serialized_objects)
                + linebreak
                + tab_end
                + "}"
            )
        else:
            # key with value
            if self.name:
                serialized_data.append(self.name + " = " + super().serialize())
            # only value
            else:
                serialized_data.append(super().serialize())

        return "\n".join(serialized_data)

    def create_operations_lua(self) -> str:
        """crates the liberation lua script for the dcs mission"""
        lua_prefix = """
-- setting configuration table
env.info("DCSRetribution|: setting configuration table")
"""

        return lua_prefix + self.serialize()
