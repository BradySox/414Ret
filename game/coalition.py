from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING

from faker import Faker

from game.armedforces.armedforces import ArmedForces
from game.ato.airtaaskingorder import AirTaskingOrder
from game.ato.codewords import MissionCodeWords
from game.campaignloader.defaultsquadronassigner import DefaultSquadronAssigner
from game.commander import TheaterCommander
from game.commander.missionscheduler import MissionScheduler
from game.income import Income
from game.navmesh import NavMesh
from game.orderedset import OrderedSet
from game.procurement import AircraftProcurementRequest, ProcurementAi
from game.profiling import MultiEventTracer, logged_duration
from game.pow_recovery import PendingPowRecovery, age_pending_pows
from game.scar_rescue import PendingSofRescue, surviving_rescues
from game.squadrons import AirWing
from game.theater.bullseye import Bullseye
from game.theater.player import Player
from game.theater.transitnetwork import TransitNetwork, TransitNetworkBuilder
from game.threatzones import ThreatZones
from game.transfers import PendingTransfers

if TYPE_CHECKING:
    from .campaignloader import CampaignAirWingConfig
    from .data.doctrine import Doctrine
    from .factions.faction import Faction
    from .game import Game
    from .lasercodes import LaserCodeRegistry
    from .sim import GameUpdateEvents


class Coalition:
    def __init__(
        self, game: Game, faction: Faction, budget: float, player: Player
    ) -> None:
        self.game = game
        self.player = player
        self.faction = faction
        self.budget = budget
        self.ato = AirTaskingOrder()
        self.transit_network = TransitNetwork()
        self.procurement_requests: OrderedSet[AircraftProcurementRequest] = OrderedSet()
        self.bullseye = Bullseye(self.game.point_in_world(0, 0))
        self.faker = Faker(self.faction.locales)
        self.air_wing = AirWing(player, game, self.faction)
        self.armed_forces = ArmedForces(self.faction)
        self.transfers = PendingTransfers(game, player)
        # SCAR campaign engine: set once this coalition captures an enemy
        # commander, which reveals the enemy's command posts (gated by the
        # scar_command_post_intel setting). Persisted campaign state.
        self.captured_commander = False
        # SOF teams stranded by a botched SCAR capture, awaiting a CSAR pickup
        # next turn(s). Persisted; surfaced as map objectives and aged each turn.
        self.pending_csars: list[PendingSofRescue] = []
        # Pilots captured by the Combat SAR enemy snatch party (the rescue rework's
        # capture race), held as POWs at an enemy field and recoverable for a few
        # turns. Persisted; surfaced as map objectives and aged each turn.
        self.pending_pow_recoveries: list[PendingPowRecovery] = []
        # Money the automated HQ spent per category last turn (front_line,
        # runways, buildings, ground_objects, aircraft). Surfaced in the
        # Finances dialog so the player sees where their income went.
        self.last_turn_expenses: dict[str, float] = {}

        # Mission-wide SRS code words (per-task push table + events), regenerated each
        # turn and stored so planners and kneeboards share one stable table. See the
        # ``code_words`` property below.
        self._code_words: Optional[MissionCodeWords] = None
        self._code_words_turn: Optional[int] = None

        # Late initialized because the two coalitions in the game are mutually
        # dependent, so must be both constructed before this property can be set.
        self._opponent: Optional[Coalition] = None

        # Volatile properties that are not persisted to the save file since they can be
        # recomputed on load. Keeping this data out of the save file makes save compat
        # breaks less frequent. Each of these properties has a non-underscore-prefixed
        # @property that should be used for non-Optional access.
        #
        # All of these are late-initialized (whether via on_load or called later), but
        # will be non-None after the game has finished loading.
        self._threat_zone: Optional[ThreatZones] = None
        self._navmesh: Optional[NavMesh] = None
        self.on_load()

    @property
    def doctrine(self) -> Doctrine:
        return self.faction.doctrine

    @property
    def code_words(self) -> MissionCodeWords:
        """Mission-wide SRS code-word table for this side, refreshed each turn.

        Generated once per turn and stored, so it stays stable while a planner builds
        a briefing and regenerates the mission, and persists in the save; a new turn
        draws a fresh themed set. ``getattr`` migrates saves from before the field
        existed. See ``game/ato/codewords.py``.
        """
        turn = self.game.turn
        current = getattr(self, "_code_words", None)
        if current is None or getattr(self, "_code_words_turn", None) != turn:
            current = MissionCodeWords.generate()
            self._code_words = current
            self._code_words_turn = turn
        return current

    @property
    def coalition_id(self) -> int:
        if self.player.is_blue:
            return 2
        elif self.player.is_red:
            return 1
        return 0

    @property
    def opponent(self) -> Coalition:
        assert self._opponent is not None
        return self._opponent

    @property
    def threat_zone(self) -> ThreatZones:
        assert self._threat_zone is not None
        return self._threat_zone

    @property
    def nav_mesh(self) -> NavMesh:
        assert self._navmesh is not None
        return self._navmesh

    @property
    def laser_code_registry(self) -> LaserCodeRegistry:
        return self.game.laser_code_registry

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        # Avoid persisting any volatile types that can be deterministically
        # recomputed on load for the sake of save compatibility.
        del state["faker"]
        # TODO: Figure out why this is needed after adding neutral point support
        if state["player"] != Player.NEUTRAL:
            del state["_threat_zone"]
            del state["_navmesh"]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        # Migration: Convert old boolean player values to Player enum
        if "player" in state and isinstance(state["player"], bool):
            from game.theater.player import Player

            if state["player"]:
                state["player"] = Player.BLUE
            else:
                state["player"] = Player.RED

        # Migration: older saves predate the SCAR commander-capture flag.
        state.setdefault("captured_commander", False)
        # Migration: older saves predate the SOF CSAR pending-rescue list.
        state.setdefault("pending_csars", [])
        # Migration: older saves predate the captured-pilot POW recovery list.
        state.setdefault("pending_pow_recoveries", [])
        # Migration: older saves predate the per-turn HQ expense breakdown.
        state.setdefault("last_turn_expenses", {})

        self.__dict__.update(state)
        # Regenerate any state that was not persisted.
        self.on_load()

    def on_load(self) -> None:
        self.faker = Faker(self.faction.locales)

    def set_opponent(self, opponent: Coalition) -> None:
        if self._opponent is not None:
            raise RuntimeError("Double-initialization of Coalition.opponent")
        self._opponent = opponent

    def configure_default_air_wing(
        self, air_wing_config: CampaignAirWingConfig
    ) -> None:
        DefaultSquadronAssigner(air_wing_config, self.game, self).assign()

    def adjust_budget(self, amount: float) -> None:
        self.budget += amount

    def compute_threat_zones(self, events: GameUpdateEvents) -> None:
        self._threat_zone = ThreatZones.for_faction(self.game, self.player)
        events.update_threat_zones(self.player, self._threat_zone)

    def compute_nav_meshes(self, events: GameUpdateEvents) -> None:
        self._navmesh = NavMesh.from_threat_zones(
            self.opponent.threat_zone, self.game.theater
        )
        events.update_navmesh(self.player, self._navmesh)

    def update_transit_network(self) -> None:
        self.transit_network = TransitNetworkBuilder(
            self.game.theater, self.player
        ).build()

    def set_bullseye(self, bullseye: Bullseye) -> None:
        self.bullseye = bullseye

    def end_turn(self) -> None:
        """Processes coalition-specific turn finalization.

        For more information on turn finalization in general, see the documentation for
        `Game.finish_turn`.
        """
        self.air_wing.end_turn()
        self.budget += Income(self.game, self.player).total

        # Need to recompute before transfers and deliveries to account for captures.
        # This happens in in initialize_turn as well, because cheating doesn't advance a
        # turn but can capture bases so we need to recompute there as well.
        self.update_transit_network()

        # Must happen *before* unit deliveries are handled, or else new units will spawn
        # one hop ahead. ControlPoint.process_turn handles unit deliveries. The
        # coalition-specific turn-end happens before the theater-wide turn-end, so this
        # is handled correctly.
        self.transfers.perform_transfers()

        # Age stranded-SOF CSAR pickups and drop any lost to the turn cap or to the
        # enemy overrunning their anchor base. end_turn runs exactly once per turn,
        # unlike initialize_turn, so it's the correct place to do this. Gated with
        # the rest of the SCAR SOF feature.
        if self.game.settings.scar_command_post_intel:
            self.pending_csars = surviving_rescues(
                self.game, self.player, self.pending_csars
            )

        # Age captured-pilot POWs and drop any held past the recovery window.
        # Ungated: the list is only ever non-empty when the Combat SAR capture
        # race produced a capture, so this is a no-op otherwise.
        self.pending_pow_recoveries = age_pending_pows(self.pending_pow_recoveries)

    def preinit_turn_0(self, squadrons_start_full: bool) -> None:
        """Runs final Coalition initialization.

        Final initialization occurs before Game.initialize_turn runs for turn 0.
        """
        self.air_wing.populate_for_turn_0(squadrons_start_full)

    def initialize_turn(self, is_turn_0: bool) -> None:
        """Processes coalition-specific turn initialization.

        For more information on turn initialization in general, see the documentation
        for `Game.initialize_turn`.
        """
        # Needs to happen *before* planning transfers so we don't cancel them.
        self.ato.clear()
        self.air_wing.reset()
        self.refund_outstanding_orders()
        self.procurement_requests.clear()

        with logged_duration("Transit network identification"):
            self.update_transit_network()
        with logged_duration("Procurement of airlift assets"):
            self.transfers.order_airlift_assets()
        with logged_duration("Transport planning"):
            self.transfers.plan_transports(self.game.conditions.start_time)

        if not is_turn_0:
            self.plan_missions(self.game.conditions.start_time)
        self.plan_procurement()

    def refund_outstanding_orders(self) -> None:
        # TODO: Split orders between air and ground units.
        # This isn't quite right. If the player has ground purchases automated we should
        # be refunding the ground units, and if they have air automated but not ground
        # we should be refunding air units.
        if self.player and not self.game.settings.automate_aircraft_reinforcements:
            return

        for cp in self.game.theater.control_points_for(self.player):
            cp.ground_unit_orders.refund_all(self)
        for squadron in self.air_wing.iter_squadrons():
            squadron.refund_orders()

    def plan_missions(self, now: datetime) -> None:
        color = "Blue" if self.player.is_blue else "Red"
        with MultiEventTracer() as tracer:
            with tracer.trace(f"{color} mission planning"):
                with tracer.trace(f"{color} mission identification"):
                    TheaterCommander(self.game, self.player).plan_missions(now, tracer)
                with tracer.trace(f"{color} mission scheduling"):
                    MissionScheduler(
                        self, self.game.settings.desired_player_mission_duration
                    ).schedule_missions(now)

    def plan_procurement(self) -> None:
        # The first turn needs to buy a *lot* of aircraft to fill CAPs, so it gets much
        # more of the budget that turn. Otherwise budget (after repairs) is split evenly
        # between air and ground. For the default starting budget of 2000 this gives 600
        # to ground forces and 1400 to aircraft. After that the budget will be spent
        # proportionally based on how much is already invested.

        if self.player.is_blue:
            manage_runways = self.game.settings.automate_runway_repair
            manage_front_line = self.game.settings.automate_front_line_reinforcements
            manage_aircraft = self.game.settings.automate_aircraft_reinforcements
        else:
            manage_runways = True
            manage_front_line = True
            manage_aircraft = True

        procurement = ProcurementAi(
            self.game,
            self.player,
            self.faction,
            manage_runways,
            manage_front_line,
            manage_aircraft,
        )
        self.budget = procurement.spend_budget(self.budget)
        self.last_turn_expenses = procurement.last_expenses

    def add_procurement_request(self, request: AircraftProcurementRequest) -> None:
        self.procurement_requests.add(request)
