from __future__ import annotations

import logging
import os
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
from game.scar_rescue import sof_rescue_pickup_name
from game.theater import TheaterGroundObject
from game.theater.iadsnetwork.iadsrole import IadsRole
from game.utils import escape_string_for_lua
from .interceptluadata import populate_intercept_lua
from .missiondata import MissionData
from .vietnamopsluadata import populate_vietnam_ops_lua

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from .aircraft.flightdata import FlightData


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
            # Coalition is needed by the MANTIS IADS bridge, which folds each
            # AWACS into its own coalition's EWR set as an always-on wide-area
            # sensor. It must come from here, not from inspecting the live group:
            # a ground-starting AWACS (e.g. an A-50 that taxis out after mission
            # start) is not yet a spawned group when the bridge builds, so a
            # runtime coalition lookup silently dropped it. (mantis-config.lua)
            awacs_item.add_key_value(
                "coalition", "blue" if awacs.blue.is_blue else "red"
            )

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

        # Generate IADS Lua Item. The IADS node/connection data drives MANTIS
        # (resources/plugins/mantisiads), now the sole IADS engine (Skynet removed).
        # The `engine` marker is retained as "mantis" for the bridge's sanity log.
        iads_object = lua_data.add_item("IADS")
        # NB: emit the marker as a nested item, not add_key_value — LuaData.serialize
        # drops scalar key-values on an object that also has nested items.
        iads_object.add_item("engine").set_value("mantis")
        # These should always be created even if they are empty.
        iads_object.get_or_create_item("BLUE")
        iads_object.get_or_create_item("RED")
        # Should probably do the same with all the roles... but the script is already
        # tolerant of those being empty.
        # 414th: tally each coalition's radar SAM "shooters" (held dark until cued
        # by MANTIS) vs. its always-on detectors (dedicated EWR sites only). A
        # SAM-as-EWR is itself held dark and contributes no detection, so it counts
        # as a shooter, not a detector. AWACS are folded in below. A coalition with
        # shooters but no detector has a BLIND network whose SAMs never engage.
        iads_shooters = {"BLUE": 0, "RED": 0}
        iads_detectors = {"BLUE": 0, "RED": 0}
        for node in self.game.theater.iads_network.iads_nodes(self.game):
            coalition_key = "BLUE" if node.player.is_blue else "RED"
            coalition = iads_object.get_or_create_item(coalition_key)
            iads_type = coalition.get_or_create_item(node.iads_role.skynet_value)
            iads_element = iads_type.add_item()
            iads_element.add_key_value("dcsGroupName", node.dcs_name)
            if node.iads_role in [IadsRole.SAM, IadsRole.SAM_AS_EWR]:
                # add additional SkynetProperties to SAM Sites
                for property, value in node.properties.items():
                    iads_element.add_key_value(property, value)
                iads_shooters[coalition_key] += 1
            elif node.iads_role == IadsRole.EWR:
                iads_detectors[coalition_key] += 1
            for role, connections in node.connections.items():
                iads_element.add_data_array(role, connections)

        # An AWACS is the network's only other always-on wide-area sensor; fold it
        # into the detector tally (the MANTIS bridge folds it into the EWR set).
        for awacs in self.mission_data.awacs:
            iads_detectors["BLUE" if awacs.blue.is_blue else "RED"] += 1

        # Warn (at generation time, while it can still be fixed) about a coalition
        # that fields radar SAMs but has NO always-on detection feeding them. Under
        # MANTIS every SAM is held dark until cued, so detection rides solely on
        # dedicated EWR sites + AWACS; a coalition with neither is blind and its
        # SAMs never engage (they stay GREEN). Common cause: a campaign with no EWR
        # preset locations / a faction with no EWR ForceGroup, and no AWACS fragged.
        for side in ("BLUE", "RED"):
            if iads_shooters[side] > 0 and iads_detectors[side] == 0:
                logging.warning(
                    "IADS: %s fields %d radar SAM group(s) but has NO always-on "
                    "detection source (dedicated EWR or AWACS). Under MANTIS every SAM "
                    "is held dark until cued, so this network is BLIND -- its SAMs will "
                    "never engage. Add an EWR site or an AWACS for %s.",
                    side,
                    iads_shooters[side],
                    side,
                )

        populate_intercept_lua(
            lua_data,
            self.mission_data.intercept_entries,
            self.mission_data.player_alert_entries,
        )

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

        # C-130J EW de-confliction: hand the c130j plugin the group names of C-130J-30
        # flights in a non-EW role (SOF insert / Combat SAR King) so it skips just those,
        # instead of the whole mission losing EW when one is present (which also stripped a
        # co-present JAMMING C-130J-30). Always emitted; empty list = exclude nothing.
        lua_data.add_item("EwExcludedGroups").set_data_array(
            self._ew_excluded_c130j_groups()
        )

        # Vietnam Ops suite (Arc Light, etc.) -- emits dcsRetribution.VietnamOps only
        # when a suite feature is enabled; the vietnamops plugin gates on data presence.
        populate_vietnam_ops_lua(lua_data, self.game, self.mission_data)

        trigger = TriggerStart(comment="Set DCS Retribution data")
        trigger.add_action(DoScript(String(lua_data.create_operations_lua())))
        self.mission.triggerrules.triggers.append(trigger)

        self._inject_atis_lua()

    def _generate_combat_sar(self, lua_data: LuaData) -> None:
        """Emit dcsRetribution.CombatSAR + the downed-pilot template group(s).

        Combat SAR (FlightType.COMBAT_SAR) is executed at runtime by the survivor-
        ledger plugin (resources/plugins/combatsar). Python's job, per coalition, is
        to (1) tell the Lua bridge which generated groups are the rescue helos (and
        which C-130s fly the "King" orbit, with their nav beacons), and (2) drop one
        late-activation infantry group per side that the runtime clones at each crash
        site as the downed pilot. Blue rides the top-level keys (back-compat); red
        rides a nested ``red`` node, so a side with no Combat SAR flights isn't
        emitted at all. ``enableForAI`` carries the standing-alert setting
        (auto_combat_sar); the ledger runtime is coalition-generic.
        """
        blue_rescue: list[FlightData] = []
        blue_kings: list[FlightData] = []
        red_rescue: list[FlightData] = []
        red_kings: list[FlightData] = []
        for flight in self.mission_data.flights:
            if flight.flight_type is not FlightType.COMBAT_SAR:
                continue
            if flight.friendly.is_blue:
                bucket = blue_rescue if flight.aircraft_type.helicopter else blue_kings
            else:
                bucket = red_rescue if flight.aircraft_type.helicopter else red_kings
            bucket.append(flight)

        # No rescue helo on either side -> the CSAR service is simply absent this
        # mission. Skip the template(s) too so we never leave an orphan group.
        if not blue_rescue and not red_rescue:
            return

        enable_for_ai = self.game.settings.auto_combat_sar
        combat_sar: Optional[LuaItem] = None

        if blue_rescue:
            template = self._generate_combat_sar_pilot_template(self.game.blue)
            if template is not None:
                combat_sar = lua_data.add_item("CombatSAR")
                self._emit_combat_sar_side(
                    combat_sar,
                    template,
                    blue_rescue,
                    blue_kings,
                    self.game.blue,
                    enable_for_ai,
                )

        if red_rescue:
            template = self._generate_combat_sar_pilot_template(self.game.red)
            if template is not None:
                if combat_sar is None:
                    combat_sar = lua_data.add_item("CombatSAR")
                self._emit_combat_sar_side(
                    combat_sar.add_item("red"),
                    template,
                    red_rescue,
                    red_kings,
                    self.game.red,
                    enable_for_ai,
                )

    def _emit_combat_sar_side(
        self,
        node: LuaItem,
        template_name: str,
        rescue_flights: list["FlightData"],
        kings: list["FlightData"],
        coalition: "Coalition",
        enable_for_ai: bool,
    ) -> None:
        """Populate one coalition's Combat SAR node (the blue top-level node or the
        nested ``red`` node). Scalars are emitted as single-value child items so the
        LuaData serializer keeps them alongside the nested kings/sofTeams lists.
        """
        node.add_item("pilotTemplate").set_value(template_name)
        node.add_item("enableForAI").set_value("true" if enable_for_ai else "false")
        node.add_item("rescueHelos").set_data_array(
            [flight.group_name for flight in rescue_flights]
        )

        # AI auto-rescue needs a helo group to clone + a home airbase to launch from
        # and deliver to. Reuse the first rescue flight's group + its departure field.
        if enable_for_ai and rescue_flights:
            node.add_item("heloTemplate").set_value(rescue_flights[0].group_name)
            node.add_item("farp").set_value(rescue_flights[0].departure.airfield_name)

        # Each King (C-130) lights the TACAN the rescue helo homes on.
        kings_item = node.add_item("kings")
        for king in kings:
            item = kings_item.add_item()
            item.add_key_value("group", king.group_name)
            beacon = king.combat_sar_king
            if beacon is not None:
                item.add_key_value("callsign", beacon.callsign)
                # callsign + TACAN are the King beacon: air-tracking, so it follows
                # the orbit, and every rescue helo we use can home on it.
                if beacon.tacan is not None:
                    item.add_key_value("tacanChannel", str(beacon.tacan.number))
                    item.add_key_value("tacanBand", beacon.tacan.band.value)

        # Stranded SOF teams (SCAR commander-capture loop): offer each on-map team
        # as a CASEVAC pickup so the SAME rescue helo can extract it. Delivery clears
        # the rescue + refunds the team at debrief. Gated on the SCAR intel feature;
        # the anchor check keeps it to teams surfaced as an objective this turn.
        if self.game.settings.scar_command_post_intel:
            teams_item = node.add_item("sofTeams")
            for rescue in coalition.pending_csars:
                if rescue.anchor_cp_id is None:
                    continue
                item = teams_item.add_item()
                item.add_key_value("name", sof_rescue_pickup_name(rescue))
                item.add_key_value("x", str(rescue.x))
                item.add_key_value("y", str(rescue.y))

    def _generate_combat_sar_pilot_template(
        self, coalition: "Coalition"
    ) -> Optional[str]:
        """Add a hidden, late-activation infantry group the runtime clones as the
        downed pilot for this coalition. Returns its group name, or None if the side
        holds no base. Blue and red get distinct group names so both can coexist."""
        faction = coalition.faction
        infantry = next(faction.infantry_with_class(UnitClass.INFANTRY), None)
        if infantry is not None:
            dcs_unit_type = infantry.dcs_unit_type
        else:
            # Vanilla fallback so the template exists even for an infantry-less faction.
            from dcs.vehicles import Infantry

            dcs_unit_type = Infantry.Soldier_M4

        anchor = next(
            (
                cp
                for cp in self.game.theater.controlpoints
                if cp.captured is coalition.player
            ),
            None,
        )
        if anchor is None:
            return None

        country = self.mission.country(faction.country.name)
        group_name = (
            "Combat SAR Downed Pilot"
            if coalition.player.is_blue
            else "Combat SAR Downed Pilot RED"
        )
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

    def inject_late_plugin_scripts(
        self,
        plugin_mnemonic: str,
        files: list[str],
        comment: str,
        preamble: Optional[str] = None,
    ) -> None:
        """Load a plugin's late-init scripts in a single trigger, after config.

        Emits one TriggerStart containing an optional inline ``preamble``
        (DoScript) followed by a DoScriptFile for each file in order. This runs
        in inject_plugins()'s second pass, so every plugin's
        dcsRetribution.plugins.<id> table (and MOOSE) already exists. If any
        declared file is missing the whole pass is skipped with a loud error,
        instead of the feature silently never starting.
        """
        if not files:
            return
        plugin_path = Path("./resources/plugins", plugin_mnemonic)
        resolved: list[Path] = []
        for file in files:
            script_path = Path(plugin_path, file)
            if not script_path.exists():
                logging.error(
                    "Cannot find %s for plugin %s — late-init skipped, the "
                    "feature will not start this mission",
                    script_path,
                    plugin_mnemonic,
                )
                return
            resolved.append(script_path)

        trigger = TriggerStart(comment=comment)
        if preamble:
            trigger.add_action(DoScript(String(preamble)))
        for script_path in resolved:
            fileref = self.mission.map_resource.add_resource_file(script_path.resolve())
            trigger.add_action(DoScriptFile(fileref))
        self.mission.triggerrules.triggers.append(trigger)

    def _ew_excluded_c130j_groups(self) -> list[str]:
        """Group names of C-130J-30 flights flying a NON-EW role this mission.

        The EW plugin (C-130J Mission Systems) attaches to every C-130J-30 by airframe
        alone (its eligibility check is purely ``getTypeName() == "C-130J-30"``), so it
        would bolt the EW/ISR menu and behavior onto any other C-130J-30 role. Two roles
        must fly clean: the **SOF insert** airdrop and the **Combat SAR "King"** orbit
        (both are C-130J-30 now that the stock C-130 was retired). Rather than skip the
        whole EW plugin for the mission -- which also stripped EW from a legitimate
        **JAMMING** C-130J-30 flying alongside -- we hand the plugin a per-group deny-list
        (emitted as ``dcsRetribution.EwExcludedGroups``) so it skips only these aircraft
        and still claims the EW jet. Both coalitions; empty when none apply.
        """
        non_ew = (FlightType.SOF, FlightType.COMBAT_SAR)
        c130j = AircraftType.named("C-130J-30")
        return [
            flight.group_name
            for flight in self.mission_data.flights
            if flight.flight_type in non_ew and flight.aircraft_type == c130j
        ]

    def inject_plugins(self) -> None:
        for plugin in LuaPluginManager.plugins():
            if plugin.enabled:
                plugin.inject_scripts(self)
                plugin.inject_configuration(self)
                plugin.inject_other_resource_files(self)
        # Second pass: late-init scripts (TIC/TARS/SCAR) that must load AFTER
        # every plugin's config table exists. Ordering within this pass follows
        # plugins.json; the features share no Lua globals so relative order is
        # immaterial. Replaces the old hand-injected _inject_*_script tail.
        for plugin in LuaPluginManager.plugins():
            if plugin.should_late_init(self):
                plugin.inject_late_init(self)


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
