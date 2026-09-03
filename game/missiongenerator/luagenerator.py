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
from game.missiongenerator.aircraft.waypoints.csarpickup import (
    briefed_hover_altitude,
    HOVER_DURATION_SECONDS,
)
from game.missiongenerator.csargenerator import EMBARK_ZONE_RADIUS
from game.plugins import LuaPluginManager
from game.theater import TheaterGroundObject
from game.theater.theatergroup import SceneryUnit
from game.theater.iadsnetwork.iadsrole import IadsRole
from game.utils import escape_string_for_lua, nautical_miles
from .csarbeacon import sar_beacon_hz
from .aisleepluadata import populate_ai_sleep_lua
from .briefingluadata import populate_briefing_lua
from .coinluadata import populate_coin_lua
from .commsjamluadata import populate_comms_jam_lua
from .reactiveredluadata import populate_reactive_red_lua
from .rednetluadata import populate_red_net_lua
from .minefieldluadata import populate_minefields_lua
from .interceptluadata import (
    DefensePolygonEntry,
    DefenseZoneEntry,
    aligned_defense_polygons,
    defense_zone_entries,
    populate_intercept_lua,
)
from .cruisemissileluadata import populate_cruise_missiles_lua
from .missiondata import MissionData
from .gpsjammingluadata import populate_gps_jamming_lua
from .growlerluadata import populate_growler_lua
from .navalmagazineluadata import populate_naval_magazines_lua
from .neutralborderluadata import populate_neutral_border_lua
from .redscrambleluadata import populate_red_scramble_lua
from .vietnamopsluadata import populate_vietnam_ops_lua

if TYPE_CHECKING:
    from game import Game


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
        # Plugin CONFIG-script loads are collected here and emitted together in
        # one bundled TriggerStart (flush_deferred_plugin_scripts). DCS silently
        # drops some mission-start DoScriptFile triggers when a heavy mission
        # fields many separate ones -- observed on Red Tide, where the
        # vietnamops/commsjam config loads never executed while
        # adjacent, byte-identically-wired plugin loads did. Bundling into a
        # single trigger (the same shape the reliable late-init pass uses) keeps
        # any one config from being dropped.
        self._deferred_plugin_loads: list[DoScriptFile] = []

    def generate(self) -> None:
        self.generate_plugin_data()
        self.inject_plugins()
        self._seed_scenery_objectives()

    def _seed_scenery_objectives(self) -> None:
        """Hand the base script the position of every building objective.

        DCS reports a scenery death with the object's numeric id rather than a
        name, so the base script cannot tell which objective just lost a
        building. It resolves that by position instead, which needs the list of
        objectives and where they stand -- this is that list.

        Objectives already destroyed are seeded too, marked dead. They are not
        there to be scored again -- the base script pre-counts them so they never
        are -- but to own the deaths around them: the destruction zone that
        replays their rubble at mission start kills their scenery, and without
        them in the list those deaths would be credited to whichever live
        objective happened to be nearest.
        """
        rows = []
        for tgo in self.game.theater.ground_objects:
            for unit in tgo.units:
                if not isinstance(unit, SceneryUnit):
                    continue
                name = escape_string_for_lua(unit.name)
                dead = "false" if unit.alive else "true"
                rows.append(
                    f'  {{ name = "{name}", x = {unit.position.x}, '
                    f"y = {unit.position.y}, dead = {dead} }},"
                )
        if not rows:
            return

        preamble = "RETRIBUTION_SCENERY_ZONES = {\n" + "\n".join(rows) + "\n}\n"
        trigger = TriggerStart(comment="Building objectives (positions)")
        trigger.add_action(DoScript(String(preamble)))
        self.mission.triggerrules.triggers.append(trigger)
        logging.info("Seeded %d building objectives for scenery matching", len(rows))

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
            # A fixed-wing troop transport cannot land at the assault zone, so
            # the CTLD runtime delivers its troops by paradrop instead (player:
            # airborne unload jumps the stick; AI: auto-drop over the target
            # zone). Helos keep the stock land/fast-rope behavior.
            transport_item.add_key_value(
                "paradrop",
                (
                    "true"
                    if transport.cabin_size > 0 and not transport.helicopter
                    else "false"
                ),
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

        # C2 nodes killed on an earlier turn. The runtime's own death test only sees
        # this mission (a dead-spawned static, or a name in dead_events), and many C2
        # nodes are scenery it cannot look up at all, so the campaign names them here.
        for player, dead_names in self.game.theater.iads_network.dead_c2_names(
            self.game
        ).items():
            iads_object.get_or_create_item(
                "BLUE" if player.is_blue else "RED"
            ).add_data_array("DeadC2", dead_names)

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

        # 414th QRA forward defense: bound each dispatcher to the airspace over its own
        # bases + its own side of the front, so a widened scramble radius lets rear
        # fields answer raids at the front without anyone chasing deep into enemy
        # territory. Emitted only when a dispatcher exists; an empty list means the Lua
        # skips SetBorderZone and behaves exactly as it did before the feature.
        defense_zones: list[DefenseZoneEntry] = []
        if (
            self.game.settings.qra_forward_defense
            and self.mission_data.intercept_entries
        ):
            defense_zones = defense_zone_entries(
                self.game.theater,
                nautical_miles(self.game.settings.qra_defense_depth_nm),
            )

        # §96: a country hosting a side's airfields is that side's territory, so
        # its border joins that side's QRA accept zones. Independent of
        # qra_forward_defense -- this is about who owns the airspace, not about
        # the forward-defense geometry -- but still only useful with a dispatcher.
        defense_polygons: list[DefensePolygonEntry] = []
        if self.mission_data.intercept_entries and getattr(
            self.game.settings, "neutral_border_defense", False
        ):
            defense_polygons = aligned_defense_polygons(self.game.theater)

        populate_intercept_lua(
            lua_data,
            self.mission_data.intercept_entries,
            self.mission_data.player_alert_entries,
            defense_zones,
            defense_polygons,
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

        # C-130J EW de-confliction: hand the c130j plugin the group names of C-130J-30
        # flights in a non-EW role (airlift / paradrop) so it skips just those,
        # instead of the whole mission losing EW when one is present (which also stripped a
        # co-present JAMMING C-130J-30). Always emitted; empty list = exclude nothing.
        lua_data.add_item("EwExcludedGroups").set_data_array(
            self._ew_excluded_c130j_groups()
        )

        # Vietnam Ops suite (Arc Light, etc.) -- emits dcsRetribution.VietnamOps only
        # when a suite feature is enabled; the vietnamops plugin gates on data presence.
        populate_vietnam_ops_lua(lua_data, self.game, self.mission_data)

        # COIN in-mission movement -- emits dcsRetribution.coin only when a live HVT
        # convoy and/or mobile VBIED exists; the coin plugin drives them at runtime
        # (the kill/fuse consequence stays in the turn-boundary force model).
        populate_coin_lua(lua_data, self.game, self.mission_data)

        # Growler escort jamming -- emits dcsRetribution.growler only when an
        # ESCORT_JAMMER flight exists; the growler plugin drives the scripted
        # jamming effects (missile-spoof bubble + ROE-hold pulses, never
        # enableEmission) over the package it escorts.
        populate_growler_lua(lua_data, self.game, self.mission_data)

        # GPS jamming (§85) -- emits dcsRetribution.gpsJamming only when the
        # setting is on and a live GPS-jamming ground site exists; the gpsjamming
        # plugin tracks each satellite-guided weapon released into a jammer's
        # bubble and puts it down off the aimpoint. Real ordnance from a real
        # jet: no spawns, and killing the jammer restores accuracy at once.
        populate_gps_jamming_lua(lua_data, self.game, self.mission_data)

        # Ground AI sleep (§59) -- emits dcsRetribution.aiSleep only when
        # perf_ground_ai_sleep is on and an eligible garrison group exists; the
        # aisleep plugin sleeps each group's controller until an aircraft closes
        # inside the wake radius (performance only -- no gameplay-model change).
        populate_ai_sleep_lua(lua_data, self.game, self.mission_data)

        # Air-dropped minefields (§57 Phase 2) -- emits dcsRetribution.minefields only when
        # air_droppable_minefields is on and a live persisted field exists, so the plugin
        # re-arms fields left undisturbed last turn. Fresh drops are the plugin's own
        # S_EVENT_SHOT detection; kills stay in the turn-boundary force model.
        populate_minefields_lua(lua_data, self.game, self.mission_data)

        # Ship cruise missile strikes (§63) -- emits dcsRetribution.cruiseMissiles only
        # when cruise_missile_strikes is on and a live land-attack-capable ship group
        # has missiles left; the cruisemissiles plugin fires the auto raids + the F10
        # call-for-fire and mirrors expenditure back for the turn-boundary magazine
        # debit. The missiles are real weapons from a tracked ship -- kills record
        # natively.
        populate_cruise_missiles_lua(lua_data, self.game, self.mission_data)

        # Cross-turn naval magazines (§81) -- emits dcsRetribution.navalMagazines only
        # when the stagger or the magazine is on and a live naval group exists; the
        # navalmagazines plugin releases ships to weapons-free across a window (they
        # generate on ReturnFire) and counts real anti-ship shots against the campaign
        # stock, mirroring expenditure back for the turn-boundary debit. Its weapon set
        # is disjoint from §63's above, so a shot is never charged to both magazines.
        populate_naval_magazines_lua(lua_data, self.game, self.mission_data)

        # Enemy comms jamming (§51) -- emits dcsRetribution.commsJam only when the
        # plan computed before this pass exists (setting on + alive enemy C2 node +
        # briefed blue channels); the commsjam plugin transmits the barrage noise
        # (audio pressure only, kills record natively on the ordinary C2 TGO).
        populate_comms_jam_lua(lua_data, self.game, self.mission_data)

        # Red comms net (§70 C1) -- emits dcsRetribution.redNet only when the plan
        # computed before this pass exists (red_comms_net on + an alive enemy C2
        # node); the rednet plugin transmits the periodic CW traffic (audio + DF
        # geometry only, kills record natively on the ordinary C2 TGO).
        populate_red_net_lua(lua_data, self.mission_data)

        # Reactive red (§89 P5) -- emits dcsRetribution.reactiveRed only when the
        # plan exists (both gates + a watched objective + a fragged reaction
        # flight); the reactivered plugin may only activate the listed groups
        # over the listed objectives. No spawns, no kills owned by Lua.
        populate_reactive_red_lua(lua_data, self.mission_data)

        # Mission-start briefing popup (§58) -- emits dcsRetribution.briefing only when
        # mission_briefing_popup is on and the mission has a player-crewed flight; the
        # briefing plugin shows each pilot a short campaign/mission/callsign/field card
        # when they slot in. Display only, no gameplay-model change.
        populate_briefing_lua(lua_data, self.game, self.mission_data)

        # Host red-interceptor scramble (§61) -- emits dcsRetribution.redScramble only
        # when host_red_scramble is on and red fighter templates + red airfields exist;
        # the redscramble plugin builds the host's F10 menu and force-vectors the
        # cloned bandits onto blue fighters (a GM event tool -- untracked by design).
        populate_red_scramble_lua(lua_data, self.game, self.mission_data)

        # Neutral-faction border defense (§96) -- emits dcsRetribution.neutralBorder
        # only when neutral_border_defense is on and the generator could build
        # templates for the map's zones; the neutralborder plugin runs the
        # border watch, the shadow launches and the escalation ladder.
        populate_neutral_border_lua(lua_data, self.game, self.mission_data)

        # Combat SAR -- emits dcsRetribution.CSAR (the downed-pilot list, the
        # rescue-capable type whitelist and the Ops.CSAR flags) for the opscsar
        # plugin. Always emitted; the plugin gates on the per-side enable flags.
        self.generate_csar_data(lua_data)

        trigger = TriggerStart(comment="Set DCS Retribution data")
        trigger.add_action(DoScript(String(lua_data.create_operations_lua())))
        self.mission.triggerrules.triggers.append(trigger)

        self._inject_atis_lua()

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

    def generate_csar_data(self, lua_data: LuaData) -> None:
        """Injects Ops.CSAR data into the dcsRetribution table.

        Exposes downed pilots (so the OpsCSAR.lua plugin can spawn them for pickup)
        and the CSAR-capable aircraft whitelist (so MOOSE will accept transport
        types it doesn't ship a default capacity for, like the Hercules).
        """
        settings = self.game.settings
        csar_object = lua_data.add_item("CSAR")
        # NB: LuaData serializes a node as *either* scalar key/values or nested
        # items, never both, and always quotes string values. So the flags are
        # emitted as individual leaf items (string "true"/"false", compared as
        # strings in OpsCSAR.lua) alongside the downedPilots/rescueTypes arrays.
        templates = self.mission_data.csar_pilot_templates
        flags = {
            "blueEnabled": "true" if settings.csar_enabled else "false",
            "redEnabled": "true" if settings.csar_enabled_red else "false",
            "rescueAI": "true" if settings.csar_rescue_ai_pilots else "false",
            # Ops.CSAR's pilotmustopendoors. Player pickups only -- the AI paths
            # don't model doors at all.
            "requireOpenDoors": (
                "true" if settings.csar_require_open_doors else "false"
            ),
            # Ops.CSAR's rescuehoverheight/rescuehoverdistance, for player hoists.
            "playerHoverHeight": str(settings.csar_player_hover_height),
            "playerHoverDistance": str(settings.csar_player_hover_distance),
            # Survivors this close together come out on the same lift.
            "clusterRadius": str(settings.csar_cluster_radius),
            # Landing mode leaves the pickup to DCS's native embark; hover mode
            # needs OpsCSAR.lua to extract the pilot by script.
            "hoverExtraction": ("true" if settings.csar_hover_extraction else "false"),
            # How the scripted hoist is flown. Both come from csarpickup.py so the
            # waypoint and the script that holds the flight over it agree.
            "hoverDurationSeconds": str(HOVER_DURATION_SECONDS),
            "hoverAltitudeMeters": str(round(briefed_hover_altitude(settings).meters)),
            # Shared with the pilot's EmbarkToTransport task so the smoke the
            # survivor pops matches the zone they can actually be picked up in.
            "embarkZoneRadius": str(round(EMBARK_ZONE_RADIUS.meters)),
            "blueTemplate": templates.get("blue", ""),
            "redTemplate": templates.get("red", ""),
            # MOOSE defaults its CSAR countries to USA/Russia and applies them
            # via InitCountry() when spawning the pilot. DCS derives coalition
            # membership from country, so a faction that doesn't field those
            # countries would get its downed pilots on the wrong side.
            "blueCountry": str(self.game.blue.faction.country.id),
            "redCountry": str(self.game.red.faction.country.id),
            # 414th: the ONE briefed survivor beacon channel for the mission, in Hz.
            # Stock Ops.CSAR draws a random channel per survivor, which cannot be
            # briefed -- the kneeboard renders before the mission runs. Pinning it
            # here is what lets the kneeboard SAR line carry a real frequency the
            # crew can dial into their ADF before they launch. See csarbeacon.py.
            "beaconHz": str(sar_beacon_hz()),
        }
        for key, value in flags.items():
            csar_object.add_item(key).set_value(value)

        downed_object = csar_object.get_or_create_item("downedPilots")
        for coalition in (self.game.blue, self.game.red):
            enabled = (
                settings.csar_enabled
                if coalition.player.is_blue
                else settings.csar_enabled_red
            )
            if not enabled:
                continue
            side = "blue" if coalition.player.is_blue else "red"
            for downed in coalition.downed_pilots:
                pilot_group = self.mission_data.csar_pilot_groups.get(str(downed.id))
                if pilot_group is None:
                    # CsarGenerator skipped it (CSAR disabled for this side).
                    continue
                item = downed_object.add_item()
                item.add_key_value("id", str(downed.id))
                item.add_key_value("x", str(downed.position.x))
                item.add_key_value("z", str(downed.position.y))
                item.add_key_value("coalition", side)
                item.add_key_value("description", downed.pilot.name)
                item.add_key_value("aircraft", downed.aircraft_name)
                # The pilot is already placed in the mission (with an
                # EmbarkToTransport task for the native AI pickup). OpsCSAR.lua
                # hands this same group to Ops.CSAR so players can rescue it too.
                item.add_key_value("groupName", pilot_group.group_name)
                # How OpsCSAR.lua tells whether the survivor is still standing
                # there: Unit.getByName is a live registry lookup, where a group's
                # unit handles can outlive the units and never report the pickup.
                item.add_key_value("unitName", pilot_group.unit_name)
                # Per pilot, not per mission: a survivor in the water is hoisted
                # out whatever the setting says, because nothing can land there.
                item.add_key_value(
                    "hoverExtraction",
                    "true" if downed.needs_hover_extraction(settings) else "false",
                )

        rescue_types = csar_object.get_or_create_item("rescueTypes")
        seen: set[str] = set()
        for aircraft in AircraftType.priority_list_for_task(FlightType.CSAR):
            if aircraft.dcs_id in seen:
                continue
            seen.add(aircraft.dcs_id)
            type_item = rescue_types.add_item()
            type_item.add_key_value("dcs_id", aircraft.dcs_id)
            type_item.add_key_value("capacity", str(max(1, aircraft.cabin_size)))

    def inject_lua_trigger(self, contents: str, comment: str) -> None:
        trigger = TriggerStart(comment=comment)
        trigger.add_action(DoScript(String(contents)))
        self.mission.triggerrules.triggers.append(trigger)

    def bypass_plugin_script(self, mnemonic: str) -> None:
        self.plugin_scripts.append(mnemonic)

    def inject_plugin_script(
        self,
        plugin_mnemonic: str,
        script: str,
        script_mnemonic: str,
        defer: bool = False,
    ) -> None:
        """Load a plugin script at mission start via a DoScriptFile trigger.

        When ``defer`` is set the load is not emitted as its own trigger but
        queued for ``flush_deferred_plugin_scripts`` to bundle into one trigger
        (used for plugin *config* scripts -- see ``_deferred_plugin_loads``).
        The resource is still registered here so map-resource ordering is stable.
        """
        if script_mnemonic in self.plugin_scripts:
            logging.debug(f"Skipping already loaded {script} for {plugin_mnemonic}")
            return

        self.plugin_scripts.append(script_mnemonic)

        plugin_path = Path("./resources/plugins", plugin_mnemonic)

        script_path = Path(plugin_path, script)
        if not script_path.exists():
            logging.error(f"Cannot find {script_path} for plugin {plugin_mnemonic}")
            return

        filename = script_path.resolve()
        fileref = self.mission.map_resource.add_resource_file(filename)
        action = DoScriptFile(fileref)
        if defer:
            self._deferred_plugin_loads.append(action)
            return

        trigger = TriggerStart(comment=f"Load {script_mnemonic}")
        trigger.add_action(action)
        self.mission.triggerrules.triggers.append(trigger)

    def flush_deferred_plugin_scripts(self) -> None:
        """Emit every deferred plugin-config load in a single TriggerStart.

        Collapsing the per-plugin config loads into one trigger -- the shape the
        reliable late-init pass already uses -- stops DCS from silently dropping
        any one of them at a heavy mission start (see ``_deferred_plugin_loads``).
        Order is preserved: actions run in the order they were queued, which is
        the plugins' registration order.
        """
        if not self._deferred_plugin_loads:
            return
        trigger = TriggerStart(comment="Load plugin configurations")
        for action in self._deferred_plugin_loads:
            trigger.add_action(action)
        self.mission.triggerrules.triggers.append(trigger)
        self._deferred_plugin_loads = []

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
        would bolt the EW/ISR menu and behavior onto any other C-130J-30 role. A
        **TRANSPORT** airlifter and an **AIR_ASSAULT** paradrop bird must fly clean
        (both fly the CTLD troop/cargo menus, not the EW station). Rather than skip
        the whole EW plugin for the mission -- which also stripped EW from a
        legitimate **JAMMING** C-130J-30 flying alongside -- we hand the plugin a
        per-group deny-list (emitted as ``dcsRetribution.EwExcludedGroups``) so it
        skips only these aircraft and still claims the EW jet. Both coalitions;
        empty when none apply.
        """
        non_ew = (
            FlightType.TRANSPORT,
            FlightType.AIR_ASSAULT,
        )
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
        # Emit every plugin's config-script load in one bundled trigger (their
        # options are already set inline above, so this preserves the load
        # invariant) -- guards against DCS dropping individual mission-start
        # DoScriptFile triggers. Runs before the late-init pass.
        self.flush_deferred_plugin_scripts()
        # Second pass: late-init scripts (TIC/TARS) that must load AFTER
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

    def _serialized_scalars(self) -> list[str]:
        """This item's own key/values, as table entries."""
        if isinstance(self.value, LuaValue):
            return [self.value.serialize()]
        return [v.serialize() for v in self.value]

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
            # Nested objects AND this item's own scalars. Emitting only the
            # nested half silently dropped every add_key_value/add_data_array on
            # a mixed item -- flown 2026-08-16: a record that carried both kept
            # its nested list and lost every scalar beside it, so the plugin read
            # empty names and took its "nothing to do" exit. Hid the reactive-red
            # group pool the same way. Locked by
            # tests/missiongenerator/test_luadata.py.
            entries = self._serialized_scalars()
            entries += [o.serialize(level + 1) for o in self.objects]
            if self.name:
                if self.name is not self.base_name:
                    serialized_name += self.name + " = "
            serialized_data.append(
                serialized_name
                + "{"
                + linebreak
                + tab
                + ("," + linebreak + tab).join(entries)
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
