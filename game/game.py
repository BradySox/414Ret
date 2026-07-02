from __future__ import annotations

import itertools
import logging
import math
from collections.abc import Iterator
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Any, List, Optional, TYPE_CHECKING, Union, cast
from uuid import UUID

from dcs.countries import Switzerland, USAFAggressors, UnitedNationsPeacekeepers
from dcs.country import Country
from dcs.mapping import Point
from dcs.task import CAP, CAS, PinpointStrike
from dcs.vehicles import AirDefence
from faker import Faker

from game.ato.closestairfields import ObjectiveDistanceCache
from game.customkneeboard import CustomKneeboard
from game.ground_forces.ai_ground_planner import GroundPlanner
from game.models.game_stats import GameStats
from game.plugins import LuaPluginManager
from game.sitrep import Sitrep
from game.utils import Distance
from . import naming, persistency
from .ato import Flight
from .ato.flighttype import FlightType
from .campaignloader import CampaignAirWingConfig
from .coalition import Coalition
from .db.gamedb import GameDb
from .dcs.countries import country_with_name
from .infos.information import Information
from .lasercodes.lasercoderegistry import LaserCodeRegistry
from .profiling import logged_duration
from .settings import Settings
from .data.groups import GroupTask
from .theater import ConflictTheater, Player
from .theater.bullseye import Bullseye
from .theater.theatergroundobject import (
    EwrGroundObject,
    SamGroundObject,
    TheaterGroundObject,
)
from .theater.transitnetwork import TransitNetwork, TransitNetworkBuilder
from .timeofday import TimeOfDay
from .weather.conditions import Conditions

if TYPE_CHECKING:
    from .ato.airtaaskingorder import AirTaskingOrder
    from .factions.faction import Faction
    from .fourteenth.phases import PhaseBaseline
    from .fourteenth.super_gaggle import SuperGaggleCommitment
    from .navmesh import NavMesh
    from .sim import GameUpdateEvents
    from .squadrons import AirWing
    from .threatzones import ThreatZones

COMMISION_UNIT_VARIETY = 4
COMMISION_LIMITS_SCALE = 1.5
COMMISION_LIMITS_FACTORS = {
    PinpointStrike: 10,
    CAS: 5,
    CAP: 8,
    AirDefence: 8,
}

COMMISION_AMOUNTS_SCALE = 1.5
COMMISION_AMOUNTS_FACTORS = {
    PinpointStrike: 3,
    CAS: 1,
    CAP: 2,
    AirDefence: 0.8,
}

PLAYER_INTERCEPT_GLOBAL_PROBABILITY_BASE = 30
PLAYER_INTERCEPT_GLOBAL_PROBABILITY_LOG = 2
PLAYER_BASEATTACK_THRESHOLD = 0.4

# amount of strength player bases recover for the turn
PLAYER_BASE_STRENGTH_RECOVERY = 0.2

# amount of strength enemy bases recover for the turn
ENEMY_BASE_STRENGTH_RECOVERY = 0.05

# cost of AWACS for single operation
AWACS_BUDGET_COST = 4

# Bonus multiplier logarithm base
PLAYER_BUDGET_IMPORTANCE_LOG = 2


class TurnState(Enum):
    WIN = 0
    LOSS = 1
    CONTINUE = 2


class Game:
    scenery_clear_zones: List[Point]

    def __init__(
        self,
        player_faction: Faction,
        enemy_faction: Faction,
        theater: ConflictTheater,
        air_wing_config: CampaignAirWingConfig,
        start_date: datetime,
        start_time: time | None,
        settings: Settings,
        player_budget: float,
        enemy_budget: float,
        campaign_name: Optional[str] = None,
    ) -> None:
        self.settings = settings
        self.theater = theater
        self.campaign_name = campaign_name
        self.turn = 0
        # One-turn campaign summary (§29) captured at mission-results commit and
        # shown on the next turn's kneeboard cover band. None until the first
        # mission is flown; persisted.
        self.last_sitrep: Optional[Sitrep] = None
        # Vietnam Ops Super Gaggle (§37): the turn's planned resupply run, drawn from real
        # BLUE squadrons; None when the feature is off or no gaggle is plannable. Losses are
        # charged back to the squadrons at debrief. Replanned each turn in finish_turn.
        self.super_gaggle_commitment: Optional["SuperGaggleCommitment"] = None
        # Campaign phases (W3, docs/dev/design/414th-campaign-phases-notes.md §5):
        # only the *pointer* + the turn-0 baseline persist; phase definitions are
        # code (Tier 0) and re-derived, never pickled. Resolved each turn in
        # initialize_turn by game.fourteenth.phases.update_campaign_phase.
        self.current_phase_key: Optional[str] = None
        self.phase_entered_on_turn: Optional[int] = None
        self.phase_status_line: Optional[str] = None
        self.phase_baseline: Optional["PhaseBaseline"] = None
        # Transient: True while this is an all-neutral blank-canvas setup game the
        # player is painting ownership onto (campaign maker). Never persisted.
        self.blank_canvas_setup = False
        # True if this game was built from a blank canvas (set at finalize). Gates the
        # "Save as Campaign" action (campaign maker Increment D) — a hand-built theater
        # can be bottled as a reusable .miz-less campaign; a normal .miz campaign can't.
        self.from_blank_canvas = False
        # NB: This is the *start* date. It is never updated.
        self.date = date(start_date.year, start_date.month, start_date.day)
        self.game_stats = GameStats()
        self.notes = ""
        # Player-imported kneeboard images injected into client flights at mission
        # generation (managed in the UI; see game/customkneeboard.py).
        self.custom_kneeboards: list[CustomKneeboard] = []
        # Opaque JSON blob with the web client's map-layer panel state (which layers
        # are visible, base map, which groups are open). The client owns the
        # (de)serialization; the game just stores it so the choices travel with the
        # save instead of being lost on reload.
        self.client_map_layers: Optional[str] = None
        self.ground_planners: dict[UUID, GroundPlanner] = {}
        self.informations: list[Information] = []
        self.message("Game Start", "-" * 40)
        # Culling Zones are for areas around points of interest that contain things we may not wish to cull.
        self.__culling_zones: List[Point] = []
        self.__destroyed_units: list[dict[str, Union[float, str]]] = []
        self.savepath = ""
        self.current_unit_id = 0
        self.current_group_id = 0
        self.name_generator = naming.namegen
        self.laser_code_registry = LaserCodeRegistry()
        # Drop-spawn: TGOs queued for next-turn materialisation.
        self.pending_unit_placements: list[Any] = []

        self.db = GameDb()

        if start_time is None:
            self.time_of_day_offset_for_start_time = list(TimeOfDay).index(
                TimeOfDay.Day
            )
        else:
            self.time_of_day_offset_for_start_time = list(TimeOfDay).index(
                self.theater.daytime_map.best_guess_time_of_day_at(start_time)
            )
        self.conditions = self.generate_conditions(forced_time=start_time)

        self.sanitize_sides(player_faction, enemy_faction)
        self.blue = Coalition(self, player_faction, player_budget, player=Player.BLUE)
        self.red = Coalition(self, enemy_faction, enemy_budget, player=Player.RED)
        neutral_faction = deepcopy(player_faction)
        neutral_faction.country = self.neutral_country
        self.neutral = Coalition(self, neutral_faction, 0, player=Player.NEUTRAL)
        self.blue.set_opponent(self.red)
        self.red.set_opponent(self.blue)

        for control_point in self.theater.controlpoints:
            control_point.finish_init(self)

        self.blue.configure_default_air_wing(air_wing_config)
        self.red.configure_default_air_wing(air_wing_config)

        self.on_load(game_still_initializing=True)

    def __setstate__(self, state: dict[str, Any]) -> None:
        state.setdefault("pending_unit_placements", [])
        state.setdefault("blank_canvas_setup", False)
        state.setdefault("from_blank_canvas", False)
        state.setdefault("custom_kneeboards", [])
        state.setdefault("last_sitrep", None)
        state.setdefault("client_map_layers", None)
        state.setdefault("super_gaggle_commitment", None)
        # Campaign phases (W3): pre-feature saves compute a phase on their next
        # initialize_turn; the baseline re-snapshots then (spec §5 migration).
        state.setdefault("current_phase_key", None)
        state.setdefault("phase_entered_on_turn", None)
        state.setdefault("phase_status_line", None)
        state.setdefault("phase_baseline", None)
        # will_history (a briefly-shipped bespoke per-turn series) was folded into
        # game_stats' FactionTurnMetadata.political_will; drop it from any save
        # written in the interim so it doesn't linger as dead state.
        state.pop("will_history", None)
        self.__dict__.update(state)
        if not hasattr(self, "laser_code_registry"):
            self.laser_code_registry = LaserCodeRegistry()
            for front_line in self.theater.conflicts():
                front_line.laser_code = self.laser_code_registry.alloc_laser_code()
        # Regenerate any state that was not persisted.
        self.on_load()

    @property
    def coalitions(self) -> Iterator[Coalition]:
        yield self.blue
        yield self.red

    def point_in_world(self, x: float, y: float) -> Point:
        return Point(x, y, self.theater.terrain)

    def ato_for(self, player: Player) -> AirTaskingOrder:
        return self.coalition_for(player).ato

    def transit_network_for(self, player: Player) -> TransitNetwork:
        return self.coalition_for(player).transit_network

    def generate_conditions(self, forced_time: time | None = None) -> Conditions:
        return Conditions.generate(
            self.theater,
            self.current_day,
            self.current_turn_time_of_day,
            self.settings,
            forced_time=forced_time,
        )

    @staticmethod
    def sanitize_sides(player_faction: Faction, enemy_faction: Faction) -> None:
        """
        Make sure the opposing factions are using different countries
        :return:
        """
        # TODO: This should just be rejected and sent back to the user to fix.
        # This isn't always something that the original faction can support.
        if player_faction.country == enemy_faction.country:
            if player_faction.country.name == "USA":
                enemy_faction.country = country_with_name("USAF Aggressors")
            elif player_faction.country.name == "Russia":
                enemy_faction.country = country_with_name("USSR")
            else:
                enemy_faction.country = country_with_name("Russia")

    def faction_for(self, player: Player) -> Faction:
        return self.coalition_for(player).faction

    def faker_for(self, player: Player) -> Faker:
        return self.coalition_for(player).faker

    def air_wing_for(self, player: Player) -> AirWing:
        return self.coalition_for(player).air_wing

    def repropagate_qra_reserves(self, old_ownfor: int, old_opfor: int) -> None:
        """Re-apply changed QRA-reserve defaults to existing squadrons."""
        self.blue.air_wing.repropagate_qra_reserve(
            old_ownfor, self.settings.ownfor_default_qra_reserve
        )
        self.red.air_wing.repropagate_qra_reserve(
            old_opfor, self.settings.opfor_default_qra_reserve
        )

    @property
    def neutral_country(self) -> Country:
        """Return the best fitting country that can be used as neutral faction in the generated mission"""
        countries_in_use = {self.red.faction.country, self.blue.faction.country}
        if UnitedNationsPeacekeepers() not in countries_in_use:
            return UnitedNationsPeacekeepers()
        elif Switzerland() not in countries_in_use:
            return Switzerland()
        else:
            return USAFAggressors()

    def coalition_for(self, player: Player) -> Coalition:
        if player.is_neutral:
            return self.neutral
        elif player.is_blue:
            return self.blue
        else:
            return self.red

    def adjust_budget(self, amount: float, player: Player) -> None:
        self.coalition_for(player).adjust_budget(amount)

    def on_load(self, game_still_initializing: bool = False) -> None:
        from .sim import GameUpdateEvents

        if not hasattr(self, "name_generator"):
            self.name_generator = naming.namegen
        # Hack: Replace the global name generator state with the state from the save
        # game.
        #
        # We need to persist this state so that names generated after game load don't
        # conflict with those generated before exit.
        naming.namegen = self.name_generator
        LuaPluginManager.load_settings(self.settings)
        ObjectiveDistanceCache.set_theater(self.theater)
        self.compute_unculled_zones(GameUpdateEvents())
        # Apply mod settings again so mod properties get injected again,
        # in case mods like CJS F/A-18E/F/G or IDF F-16I are selected by the player
        self.blue.faction.apply_mod_settings()
        self.red.faction.apply_mod_settings()
        if not game_still_initializing:
            # We don't need to push events that happen during load. The UI will fully
            # reset when we're done.
            self.compute_threat_zones(GameUpdateEvents())

    def finish_turn(self, events: GameUpdateEvents, skipped: bool = False) -> None:
        """Finalizes the current turn and advances to the next turn.

        This handles the turn-end portion of passing a turn. Initialization of the next
        turn is handled by `initialize_turn`. These are separate processes because while
        turns may be initialized more than once under some circumstances (see the
        documentation for `initialize_turn`), `finish_turn` performs the work that
        should be guaranteed to happen only once per turn:

        * Turn counter increment.
        * Delivering units ordered the previous turn.
        * Transfer progress.
        * Squadron replenishment.
        * Income distribution.
        * Base strength (front line position) adjustment.
        * Weather/time-of-day generation.

        Some actions (like transit network assembly) will happen both here and in
        `initialize_turn`. We need the network to be up to date so we can account for
        base captures when processing the transfers that occurred last turn, but we also
        need it to be up to date in the case of a re-initialization in `initialize_turn`
        (such as to account for a cheat base capture) so that orders are only placed
        where a supply route exists to the destination. This is a relatively cheap
        operation so duplicating the effort is not a problem.

        Args:
            skipped: True if the turn was skipped.
        """
        self.message("End of turn #" + str(self.turn), "-" * 40)
        self.turn += 1

        # The coalition-specific turn finalization *must* happen before unit deliveries,
        # since the coalition-specific finalization handles transit network updates and
        # transfer processing. If in the other order, units may be delivered to captured
        # bases, and freshly delivered units will spawn one leg through their journey.
        self.blue.end_turn()
        self.red.end_turn()

        for control_point in self.theater.controlpoints:
            control_point.process_turn(self)

        # Vietnam Ops convoy interdiction (§35): ensure the opfor has a *real*, tracked
        # convoy flowing on the trail corridor to interdict (replacing the old phantom
        # runtime spawn). Once per turn, after transfers are processed and the network is
        # current; a no-op unless the setting is on and a real corridor + spare rear units
        # exist. See game/fourteenth/vietnam_convoy.py.
        from game.fourteenth.vietnam_convoy import ensure_enemy_trail_convoy

        ensure_enemy_trail_convoy(self)

        # Vietnam Ops Super Gaggle (§37): (re)plan the turn's resupply run from real BLUE
        # squadrons (drawing the helos + suppressors from actual airframes, whose losses are
        # charged back at debrief), or clear it. No-op unless the setting is on and a besieged
        # outpost + launch field + a helo squadron with airframes all exist.
        from game.fourteenth.super_gaggle import plan_super_gaggle

        plan_super_gaggle(self)

        # Movable ship TGOs snap to their destination and re-parent to the
        # nearest friendly CP. Runs after captures are committed (process_results
        # precedes pass_turn -> finish_turn), so re-parenting sees post-capture
        # ownership.
        from game.theater.shipmovement import move_and_reparent_ships

        move_and_reparent_ships(self.theater.controlpoints)

        if not skipped:
            for cp in self.theater.player_points():
                for front_line in cp.front_lines.values():
                    front_line.update_position()
                    events.update_front_line(front_line)
                cp.base.affect_strength(+PLAYER_BASE_STRENGTH_RECOVERY)

        # After the first mission, reveal surviving MERAD groups. They start hidden
        # so players don't know enemy SA-6/11/17 positions before flying; the first
        # mission acts as intel gathering and they become visible from turn 2 onward.
        if self.turn == 1:
            self._reveal_merad_groups()

        # We don't actually advance time or change the conditions between turn 0 and
        # turn 1.
        if self.turn > 1:
            self.conditions = self.generate_conditions()

    def _reveal_merad_groups(self) -> None:
        for tgo in self.theater.ground_objects:
            if tgo.task == GroupTask.MERAD and tgo.hide_on_mfd:
                tgo.hide_on_mfd = False

    def begin_turn_0(self, squadrons_start_full: bool) -> None:
        """Initialization for the first turn of the game."""
        from .sim import GameUpdateEvents

        # Build the IADS Network
        with logged_duration("Generate IADS Network"):
            self.theater.iads_network.initialize_network(self.theater.ground_objects)

        for control_point in self.theater.controlpoints:
            control_point.initialize_turn_0(self.laser_code_registry)
            for tgo in control_point.connected_objectives:
                self.db.tgos.add(tgo.id, tgo)

        # Correct the heading of specifc TGOs, can only be done after init turn 0
        for tgo in self.theater.ground_objects:
            # If heading is 0 then we change the orientation to head towards the
            # closest conflict. Heading of 0 means that the campaign designer wants
            # to determine the heading automatically by liberation. Values other
            # than 0 mean it is custom defined.
            if tgo.should_head_to_conflict and tgo.heading.degrees == 0:
                # Calculate the heading to conflict
                heading = self.theater.heading_to_conflict_from(tgo.position)
                # Rotate the whole TGO with the new heading
                tgo.rotate(heading or tgo.heading)

        self.blue.preinit_turn_0(squadrons_start_full)
        self.red.preinit_turn_0(squadrons_start_full)

        if self.blank_canvas_setup:
            # In a blank-canvas setup game every base is still neutral until the
            # player paints ownership and hits Finalize, so neither coalition owns
            # any points. initialize_turn would read that as an instant loss
            # (check_win_loss) and return early -- before computing the threat
            # zones / navmesh the map render path asserts on, and before
            # game_stats.update -- and would also post a bogus "Game Over"
            # message. Compute just the threat zones (empty, but non-None) so the
            # setup theater renders for painting. The real turn is initialized
            # later from the finalized game (see finalize_blank_canvas).
            self.compute_threat_zones(GameUpdateEvents())
            return

        # TODO: Check for overfull bases.
        # We don't need to actually stream events for turn zero because we haven't given
        # *any* state to the UI yet, so it will need to do a full draw once we do.
        self.initialize_turn(
            GameUpdateEvents(), squadrons_start_full=squadrons_start_full
        )

    def pass_turn(self, no_action: bool = False) -> None:
        """Ends the current turn and initializes the new turn.

        Called both when skipping a turn or by ending the turn as the result of combat.

        Args:
            no_action: True if the turn was skipped.
        """
        from .server import EventStream
        from .sim import GameUpdateEvents

        events = GameUpdateEvents()

        logging.info("Pass turn")
        with logged_duration("Turn finalization"):
            self.finish_turn(events, no_action)

        with logged_duration("Turn initialization"):
            self.initialize_turn(events)

        EventStream.put_nowait(events)

        # Autosave progress
        persistency.autosave(self)

    def check_win_loss(self) -> TurnState:
        # A blank-canvas setup game is mid-construction: the player is painting
        # base ownership and at any moment may have only blue bases (or only red,
        # or none) before the opponent's side is painted in. That is not a win or
        # a loss -- evaluating it pops a bogus "Victory!"/"Defeat!" dialog while
        # the player is still laying out the map. Win/loss only applies once the
        # campaign is finalized into a normal game.
        if self.blank_canvas_setup:
            return TurnState.CONTINUE

        # Vietnam campaign layer (W2): the negotiation ending, ahead of the territory
        # checks -- break Hanoi's resolve before Washington's patience breaks. Gated on
        # vietnam_political_will (returns None when off); territory victory stays.
        from game.fourteenth.political_will import negotiation_verdict

        verdict = negotiation_verdict(self)
        if verdict == "loss":
            return TurnState.LOSS
        if verdict == "win":
            return TurnState.WIN

        if not self.theater.player_points(state_check=True):
            return TurnState.LOSS

        if not self.theater.enemy_points(state_check=True):
            return TurnState.WIN

        return TurnState.CONTINUE

    def set_bullseye(self) -> None:
        player_cp, enemy_cp = self.theater.closest_opposing_control_points()
        self.blue.bullseye = Bullseye(enemy_cp.position)
        self.red.bullseye = Bullseye(player_cp.position)

    def initialize_turn(
        self,
        events: GameUpdateEvents,
        for_red: bool = True,
        for_blue: bool = True,
        squadrons_start_full: bool = False,
    ) -> None:
        """Performs turn initialization for the specified players.

        Turn initialization performs all of the beginning-of-turn actions. *End-of-turn*
        processing happens in `pass_turn` (despite the name, it's called both for
        skipping the turn and ending the turn after combat).

        Special care needs to be taken here because initialization can occur more than
        once per turn. A number of events can require re-initializing a turn:

        * Cheat capture. Bases changing hands invalidates many missions in both ATOs,
          purchase orders, threat zones, transit networks, etc. Practically speaking,
          after a base capture the turn needs to be treated as fully new. The game might
          even be over after a capture.
        * Cheat front line position. CAS missions are no longer in the correct location,
          and the ground planner may also need changes.
        * Selling/buying units at TGOs. Selling a TGO might leave missions in the ATO
          with invalid targets. Buying a new SAM (or even replacing some units in a SAM)
          potentially changes the threat zone and may alter mission priorities and
          flight planning.

        Most of the work is delegated to initialize_turn_for, which handles the
        coalition-specific turn initialization. In some cases only one coalition will be
        (re-) initialized. This is the case when buying or selling TGO units, since we
        don't want to force the player to redo all their planning just because they
        repaired a SAM, but should replan opfor when that happens. On the other hand,
        base captures are significant enough (and likely enough to be the first thing
        the player does in a turn) that we replan blue as well. Front lines are less
        impactful but also likely to be early, so they also cause a blue replan.

        Args:
            events: Game update event container for turn initialization.
            for_red: True if opfor should be re-initialized.
            for_blue: True if the player coalition should be re-initialized.
            squadrons_start_full: True if generator setting was checked.
        """
        # A blank-canvas setup game has no playable turn to initialize: bases are
        # neutral and being painted, so bullseye/planning have no opposing points
        # to work from (closest_opposing_control_points would assert). The setup
        # game is started via finalize_blank_canvas, not by advancing turns.
        if self.blank_canvas_setup:
            return

        # Check for win or loss condition FIRST!
        turn_state = self.check_win_loss()
        if turn_state in (TurnState.LOSS, TurnState.WIN):
            return self.process_win_loss(turn_state)

        # Update bullseye positions for blue & red
        self.set_bullseye()

        # Update statistics
        self.game_stats.update(self)

        # Plan flights & combat for next turn
        with logged_duration("Threat zone computation"):
            self.compute_threat_zones(events)

        # Resolve this turn's campaign phase (W3) BEFORE the coalitions plan, so the
        # commander's soft emphasis reads the fresh phase. Idempotent under the
        # multiple-init-per-turn cases above; lazily snapshots the turn-0 baseline.
        from game.fourteenth.phases import update_campaign_phase

        update_campaign_phase(self)

        # Plan Coalition specific turn
        if for_blue:
            self.blue.initialize_turn(self.turn == 0 and squadrons_start_full)
        if for_red:
            self.red.initialize_turn(self.turn == 0 and squadrons_start_full)

        # Surface stranded-SOF teams as "downed SOF team" recovery objectives
        # (SCAR 2c-3). Rebuilt from each coalition's pending_csars; idempotent, so
        # safe under the multiple-init-per-turn cases documented above.
        from game.scar_objectives import sync_downed_sof_objectives

        sync_downed_sof_objectives(self)

        # Surface captured-pilot POWs as recovery objectives held at enemy
        # airfields (SCAR rescue rework, Phase 3). Rebuilt from each coalition's
        # pending_pow_recoveries; idempotent like the SOF sync above.
        from game.pow_objectives import sync_pow_objectives

        sync_pow_objectives(self)

        # Materialise any TGOs queued for this turn via drop-spawn.
        from game.theater.unitplacement import (
            process_pending_placements,
            process_respawns,
        )

        for coalition in self.coalitions:
            process_pending_placements(self, coalition)
            process_respawns(self, coalition)

        # Arm (or disarm) the Vietnam static-front clamp before the ground war is
        # planned, so this turn's front positions already respect the band.
        # Idempotent, so safe under the multiple-init-per-turn cases above; a front
        # that first appears after an Air Assault capture is anchored on first sight.
        from game.fourteenth.static_front import apply_static_front

        apply_static_front(self)

        # Plan GroundWar
        self.ground_planners = {}
        for cp in self.theater.controlpoints:
            if cp.has_frontline:
                gplanner = GroundPlanner(cp, self)
                gplanner.plan_groundwar()
                self.ground_planners[cp.id] = gplanner

        # Update cull zones
        with logged_duration("Computing culling positions"):
            self.compute_unculled_zones(events)

        events.begin_new_turn()

    def message(self, title: str, text: str = "") -> None:
        self.informations.append(Information(title, text, turn=self.turn))

    @property
    def current_turn_time_of_day(self) -> TimeOfDay:
        tod_turn = max(0, self.turn - 1) + self.time_of_day_offset_for_start_time
        return list(TimeOfDay)[tod_turn % 4]

    @property
    def current_day(self) -> date:
        return self.date + timedelta(days=self.turn // 4)

    def next_unit_id(self) -> int:
        """
        Next unit id for pre-generated units
        """
        self.current_unit_id += 1
        return self.current_unit_id

    def next_group_id(self) -> int:
        """
        Next unit id for pre-generated units
        """
        self.current_group_id += 1
        return self.current_group_id

    def compute_transit_network_for(self, player: Player) -> TransitNetwork:
        return TransitNetworkBuilder(self.theater, player).build()

    def compute_threat_zones(self, events: GameUpdateEvents) -> None:
        self.blue.compute_threat_zones(events)
        self.red.compute_threat_zones(events)
        self.blue.compute_nav_meshes(events)
        self.red.compute_nav_meshes(events)

    def threat_zone_for(self, player: Player) -> ThreatZones:
        return self.coalition_for(player).threat_zone

    def navmesh_for(self, player: Player) -> NavMesh:
        return self.coalition_for(player).nav_mesh

    def compute_unculled_zones(self, events: GameUpdateEvents) -> None:
        """
        Compute the current conflict position(s) used for culling calculation
        """
        from game.missiongenerator.frontlineconflictdescription import (
            FrontLineConflictDescription,
        )

        zones = []

        # By default, use the existing frontline conflict position
        for front_line in self.theater.conflicts():
            position = FrontLineConflictDescription.frontline_position(
                front_line, self.theater, self.settings
            )
            zones.append(position[0])
            zones.append(front_line.blue_cp.position)
            zones.append(front_line.red_cp.position)

        for cp in self.theater.controlpoints:
            # If do_not_cull_carrier is enabled, add carriers as culling point
            if self.settings.perf_do_not_cull_carrier:
                if cp.is_carrier or cp.is_lha:
                    zones.append(cp.position)

        # If there is no conflict take the center point between the two nearest opposing bases
        if len(zones) == 0:
            cpoint = None
            min_distance = math.inf
            for cp in self.theater.player_points():
                for cp2 in self.theater.enemy_points():
                    d = cp.position.distance_to_point(cp2.position)
                    if d < min_distance:
                        min_distance = d
                        cpoint = cp.position.midpoint(cp2.position)
                        zones.append(cp.position)
                        zones.append(cp2.position)
                        break
                if cpoint is not None:
                    break
            if cpoint is not None:
                zones.append(cpoint)

        packages = itertools.chain(self.blue.ato.packages, self.red.ato.packages)
        for package in packages:
            if package.primary_task in [
                FlightType.BARCAP,
                FlightType.TRANSPORT,
                FlightType.AEWC,
                FlightType.REFUELING,
                FlightType.RECOVERY,
            ]:
                # BARCAPs will be planned at most locations on smaller theaters,
                # rendering culling fairly useless. BARCAP packages don't really
                # need the ground detail since they're defensive. SAMs nearby
                # are only interesting if there are enemies in the area, and if
                # there are they won't be culled because of the enemy's mission.

                # Don't create culling exclusion zones around FlightType.TRANSPORT,
                # FlightType.AEWC & FlightType.REFUELING mission targets.
                continue
            zones.append(package.target.position)

        self.__culling_zones = zones
        events.update_unculled_zones(zones)

    def add_destroyed_units(self, data: dict[str, Union[float, str]]) -> None:
        pos = Point(
            cast(float, data["x"]), cast(float, data["z"]), self.theater.terrain
        )
        if self.theater.is_on_land(pos):
            self.__destroyed_units.append(data)

    def get_destroyed_units(self) -> list[dict[str, Union[float, str]]]:
        return self.__destroyed_units

    def position_culled(self, pos: Point) -> bool:
        """
        Check if unit can be generated at given position depending on culling performance settings
        :param pos: Position you are tryng to spawn stuff at
        :return: True if units can not be added at given position
        """
        if not self.settings.perf_culling:
            return False
        for z in self.__culling_zones:
            if z.distance_to_point(pos) < self.settings.perf_culling_distance * 1000:
                return False
        return True

    def iads_considerate_culling(self, tgo: TheaterGroundObject) -> bool:
        if not self.settings.perf_do_not_cull_threatening_iads:
            return self.position_culled(tgo.position)
        else:
            if self.settings.perf_culling:
                if isinstance(tgo, EwrGroundObject):
                    max_detection_range = tgo.max_detection_range().meters
                    for z in self.__culling_zones:
                        seperation = z.distance_to_point(tgo.position)
                        # Don't cull EWR if in detection range.
                        if seperation < max_detection_range:
                            return False
                if isinstance(tgo, SamGroundObject):
                    max_threat_range = tgo.max_threat_range().meters
                    for z in self.__culling_zones:
                        seperation = z.distance_to_point(tgo.position)
                        # Create a 12nm buffer around nearby SAMs.
                        respect_bubble = (
                            max_threat_range + Distance.from_nautical_miles(12).meters
                        )
                        if seperation < respect_bubble:
                            return False
            return self.position_culled(tgo.position)

    def get_culling_zones(self) -> list[Point]:
        """
        Check culling points
        :return: List of culling zones
        """
        return self.__culling_zones

    def process_win_loss(self, turn_state: TurnState) -> None:
        if turn_state is TurnState.WIN:
            self.message(
                "Congratulations, you are victorious! Start a new campaign to continue."
            )
        elif turn_state is TurnState.LOSS:
            self.message("Game Over, you lose. Start a new campaign to continue.")

    def ato_has_clients(self) -> bool:
        for package in self.blue.ato.packages:
            for flight in package.flights:
                if flight.client_count > 0:
                    return True
        return False
