from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING

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
from game.pow_recovery import PendingPowRecovery, surviving_pows
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
        self.air_wing = AirWing(player, game, self.faction)
        self.armed_forces = ArmedForces(self.faction)
        self.transfers = PendingTransfers(game, player)
        # SCAR campaign engine: True once this coalition captured an enemy
        # commander, which permanently reveals the enemy's command posts (gated by
        # the scar_command_post_intel setting). The capture economy that SET this
        # was removed 2026-07-01; the flag is kept (persisted) so old saves keep
        # their reveal, and the command-post fog still reads it.
        self.captured_commander = False
        # Pilots captured by the Combat SAR enemy snatch party (the capture
        # race), held as POWs at an enemy field for a few turns: freed if the
        # field falls, killed when the clock expires, draining will meanwhile.
        # Persisted; aged each turn.
        self.pending_pow_recoveries: list[PendingPowRecovery] = []
        # Vietnam campaign layer (W1): this side's political capital for the war --
        # BLUE reads it as Political Will (Washington's patience), RED as Regime
        # Resolve (Hanoi's capacity to absorb punishment). 0-100; fed each turn from
        # the debriefing when vietnam_political_will is on (observe-only until the
        # W2 negotiation win/loss lands). Persisted campaign state.
        # See docs/dev/design/414th-vietnam-political-will-roe-notes.md.
        self.political_will: float = 100.0
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
        # All of these are late-initialized, but will be non-None after the game has
        # finished loading.
        self._threat_zone: Optional[ThreatZones] = None
        self._navmesh: Optional[NavMesh] = None

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
        # Migration: the SOF capture economy was removed 2026-07-01. Old saves may
        # carry a pending-rescue list (of tombstone PendingSofRescue objects, kept
        # unpicklable-safe in game.scar_rescue); drop it -- nothing reads it.
        state.pop("pending_csars", None)
        # Migration: older saves predate the captured-pilot POW recovery list.
        state.setdefault("pending_pow_recoveries", [])
        # Migration: older saves predate the per-turn HQ expense breakdown.
        state.setdefault("last_turn_expenses", {})
        # Migration: older saves predate the Vietnam political-will layer (W1).
        state.setdefault("political_will", 100.0)

        self.__dict__.update(state)

    def set_opponent(self, opponent: Coalition) -> None:
        if self._opponent is not None:
            raise RuntimeError("Double-initialization of Coalition.opponent")
        self._opponent = opponent

    def configure_default_air_wing(
        self, air_wing_config: CampaignAirWingConfig
    ) -> None:
        DefaultSquadronAssigner(air_wing_config, self.game, self).assign()
        # 414th: auto-field a rear ISR/JTAC drone squadron (the packaged replacement
        # for the retired FLOT auto-JTAC) for any blue side that declares a drone JTAC
        # and doesn't already field one. No-op unless applicable; gated by the setting.
        from game.fourteenth.jtac_drone import ensure_jtac_drone_squadron

        ensure_jtac_drone_squadron(self)

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
        # Commitment ceiling: as BLUE Political Will falls, Congress trims the war
        # budget (a no-op unless vietnam_commitment_ceiling + the will economy are on
        # and this is BLUE). The war is taken away as the home front turns.
        from game.fourteenth.commitment_ceiling import apply_commitment_ceiling

        income = Income(self.game, self.player).total
        self.budget += apply_commitment_ceiling(self.game, self.player, income)

        # Need to recompute before transfers and deliveries to account for captures.
        # This happens in in initialize_turn as well, because cheating doesn't advance a
        # turn but can capture bases so we need to recompute there as well.
        self.update_transit_network()

        # Must happen *before* unit deliveries are handled, or else new units will spawn
        # one hop ahead. ControlPoint.process_turn handles unit deliveries. The
        # coalition-specific turn-end happens before the theater-wide turn-end, so this
        # is handled correctly.
        self.transfers.perform_transfers()

        # Advance the captured-pilot POW clock: free those whose holding airfield
        # we recaptured, kill those held past the hold window, keep the rest.
        # Ungated: the list is only ever non-empty when the Combat SAR capture
        # race produced a capture, so this is a no-op otherwise.
        self.pending_pow_recoveries = surviving_pows(
            self.game, self.player, self.pending_pow_recoveries
        )

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
        # NB: self.player is a Player enum (always truthy), so the old bare
        # `if self.player` skipped the refund for RED/neutral too whenever the
        # (BLUE-intent) setting was off. Only the human-managed BLUE coalition
        # should keep its manual orders; the AI always refunds and re-plans.
        if (
            self.player.is_blue
            and not self.game.settings.automate_aircraft_reinforcements
        ):
            return

        for cp in self.game.theater.control_points_for(self.player):
            cp.ground_unit_orders.refund_all(self)
        for squadron in self.air_wing.iter_squadrons():
            squadron.refund_orders()

    def plan_missions(self, now: datetime) -> None:
        color = "Blue" if self.player.is_blue else "Red"
        with MultiEventTracer() as tracer:
            with tracer.trace(f"{color} mission planning"):
                # 414th long-range carrier ops: the stock range gate leaves an
                # 800-km-standoff carrier idle, so frag one deterministic carrier
                # package (Hornet strike + A-6 tanker + E-2) from the boat's own
                # squadrons. Runs BEFORE the commander so it claims its carrier air
                # first (else the commander spends the Hornets on nearer SEAD/BAI and
                # leaves none for the package). No-op unless the setting is on.
                with tracer.trace(f"{color} long-range carrier strike"):
                    from game.fourteenth.carrier_ops import plan_carrier_strike

                    plan_carrier_strike(self, now, tracer)
                # 414th auto-planned convoy mining (§57 P3): frag one air-drop mining
                # sortie a turn at an enemy convoy, before the commander so the mining
                # jet is claimed first. No-op unless auto_plan_minefields is on (BLUE only,
                # a wing with a CBU-99 aircraft, an enemy convoy to mine).
                with tracer.trace(f"{color} convoy mining"):
                    from game.fourteenth.convoy_mining import plan_convoy_mining

                    plan_convoy_mining(self, now, tracer)
                # 414th pilot recovery surge (§21): when a pilot went MIA last
                # mission, frag ONE coordinated recovery package (Jolly + King +
                # Sandy + escort) at the evader's position -- before the commander,
                # so the surge claims its aircraft first ("drop everything").
                # Once per downed pilot; no-op with no un-surged evader.
                with tracer.trace(f"{color} pilot recovery surge"):
                    from game.fourteenth.csar_surge import plan_pilot_recovery_surge

                    plan_pilot_recovery_surge(self, now, tracer)
                with tracer.trace(f"{color} mission identification"):
                    TheaterCommander(self.game, self.player).plan_missions(now, tracer)
                with tracer.trace(f"{color} carrier buddy-tanker routing"):
                    from game.fourteenth.carrier_ops import (
                        route_carrier_flights_to_buddy_tanker,
                    )

                    route_carrier_flights_to_buddy_tanker(self)
                with tracer.trace(f"{color} mission scheduling"):
                    MissionScheduler(
                        self, self.game.settings.desired_player_mission_duration
                    ).schedule_missions(now)
                if self.player.is_blue:
                    with tracer.trace(f"{color} player QRA alert"):
                        self._plan_player_qra(now)

    def _plan_player_qra(self, now: datetime) -> None:
        """Frag a cold-start, home-defense BARCAP for each squadron put on
        player-manned QRA (``Squadron.qra_player_manned``).

        These alert flights sit over their own field (a ``HomeBaseDefenseZone``
        target) and the player decides when to scramble; the message that a raid is
        inbound is a later phase. The manned airframes are debited from the AI QRA
        dispatcher at mission generation (``AircraftGenerator.spawn_intercept_templates``)
        so a jet is never both on the pad and air-spawned. BLUE only -- the human
        side. See docs/dev/design/414th-qra-player-manning-notes.md.
        """
        from game.ato.flight import Flight
        from game.ato.flightmember import apply_default_player_laser_code
        from game.ato.flighttype import FlightType
        from game.ato.package import Package
        from game.ato.starttype import StartType
        from game.squadrons.intercept_reserve import (
            qra_player_client_slots,
            qra_player_manned_count,
        )
        from game.theater import Airfield, HomeBaseDefenseZone

        for squadron in self.air_wing.iter_squadrons():
            if squadron.qra_player_manned <= 0:
                continue
            # AI QRA only fields at airfields (spawn_intercept_templates); keep the
            # player alert consistent so the dispatcher debit always has a match.
            if not isinstance(squadron.location, Airfield):
                continue
            if not squadron.capable_of(FlightType.BARCAP):
                continue
            if not squadron.aircraft.flyable:
                continue
            manned = qra_player_manned_count(
                squadron.qra_player_manned,
                squadron.intercept_reserve,
                squadron.owned_aircraft,
            )
            if manned <= 0:
                continue

            base = squadron.location
            target = HomeBaseDefenseZone(f"QRA Alert {base.name}", base.position, self)
            package = Package(
                target,
                self.game.db.flights,
                auto_asap=True,
                custom_name=f"QRA Alert ({squadron})",
            )
            # claim_inv=False: these airframes come from the QRA reserve, which is
            # already held out of the squadron's untasked pool -- claiming again
            # would double-spend (and could raise on a depleted pool).
            flight = Flight(
                package,
                squadron,
                manned,
                FlightType.BARCAP,
                StartType.COLD,
                divert=None,
                claim_inv=False,
            )
            # Crew the alert flight: every airframe is a client slot (co-op alert)
            # unless the squadron opted into an AI wingman, in which case only the
            # lead is a client and the rest fly as AI. The roster auto-claimed its
            # pilots on construction; flip the player flag per slot. Laser codes are
            # then allocated (a no-op for AI members / any member without a pilot).
            client_slots = qra_player_client_slots(
                manned, squadron.qra_player_ai_wingman
            )
            for index, member in enumerate(flight.roster.members):
                if member.pilot is not None:
                    member.pilot.player = index < client_slots
            for member in flight.roster.members:
                apply_default_player_laser_code(
                    member, self.game.settings, self.game.laser_code_registry
                )
            package.add_flight(flight)
            flight.recreate_flight_plan()
            package.set_tot_asap(now)
            self.ato.add_package(package)

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
