from __future__ import annotations

import logging
import random
from typing import Any, TYPE_CHECKING
from uuid import UUID

from game.ato.flighttype import FlightType
from game.debriefing import Debriefing
from game.data.units import FRONTLINE_UNIT_CLASSES
from game.fourteenth.c2_decapitation import c2_status_line
from game.ground_forces.combat_stance import CombatStance
from game.missiongenerator.interceptattrition import (
    fielded_qra_by_squadron,
    reconcile_intercept_losses,
)
from game.profiling import logged_duration
from game.sitrep import Sitrep
from game.squadrons.csarservice import CsarService
from game.squadrons.downedpilot import DownedPilot
from game.squadrons.squadron import Squadron
from game.theater.theatergroundobject import TheaterGroundObject
from game.theater import ControlPoint, Player
from .gameupdateevents import GameUpdateEvents
from ..ato.airtaaskingorder import AirTaskingOrder

if TYPE_CHECKING:
    from ..game import Game
    from game.dcs.groundunittype import GroundUnitType


MINOR_DEFEAT_INFLUENCE = 0.1
DEFEAT_INFLUENCE = 0.3
STRONG_DEFEAT_INFLUENCE = 0.5

#: Rung B: the share of a won assault the attacker spends taking the ground. The
#: loser still yields the full delta -- only the winner's bank is discounted, and
#: only when it was the side pushing forward. See the long-view note, seam 4.
ASSAULT_COST_FRACTION = 0.4

OFFENSIVE_STANCES = (
    CombatStance.AGGRESSIVE,
    CombatStance.ELIMINATION,
    CombatStance.BREAKTHROUGH,
)


class MissionResultsProcessor:
    def __init__(self, game: Game) -> None:
        self.game = game

    def commit(self, debriefing: Debriefing, events: GameUpdateEvents) -> None:
        with logged_duration("Committing mission results"):
            # Resolve rescues before processing losses so a pilot rescued this
            # mission is not also reprocessed as a fresh loss.
            with logged_duration("commit_csar_results"):
                self.commit_csar_results(debriefing)
            with logged_duration("commit_air_losses"):
                self.commit_air_losses(debriefing)
            with logged_duration("commit_intercept_losses"):
                self.commit_intercept_losses(debriefing)
            with logged_duration("commit_pilot_experience"):
                self.commit_pilot_experience()
            with logged_duration("commit_front_line_losses"):
                self.commit_front_line_losses(debriefing)
            with logged_duration("commit_motorpool_losses"):
                self.commit_motorpool_losses(debriefing)
            with logged_duration("commit_convoy_losses"):
                self.commit_convoy_losses(debriefing)
            with logged_duration("commit_cargo_ship_losses"):
                self.commit_cargo_ship_losses(debriefing)
            with logged_duration("commit_airlift_losses"):
                self.commit_airlift_losses(debriefing)
            with logged_duration("commit_ground_losses"):
                self.commit_ground_losses(debriefing, events)
            with logged_duration("commit_damaged_runways"):
                self.commit_damaged_runways(debriefing)
            # Score the front line before capturing bases: casualty_count
            # attributes a dead front-line unit to its origin CP regardless of
            # side, so a base's defenders (origin == that base) would be
            # miscounted as the new owner's casualties once a capture flips
            # ownership, turning a win into a defeat.
            with logged_duration("commit_front_line_battle_impact"):
                self.commit_front_line_battle_impact(debriefing, events)
            with logged_duration("commit_captures"):
                self.commit_captures(debriefing, events)
            with logged_duration("record_carcasses"):
                self.record_carcasses(debriefing)
            with logged_duration("commit_super_gaggle"):
                self.commit_super_gaggle(debriefing)
            with logged_duration("commit_minefields"):
                self.commit_minefields(debriefing)
            with logged_duration("commit_cruise_missiles"):
                self.commit_cruise_missiles(debriefing)
            with logged_duration("commit_naval_magazines"):
                self.commit_naval_magazines(debriefing)
            # §70 COMINT (C0): bank this mission's collection. Commit runs before
            # the turn increments, so the stamp is the just-played turn.
            with logged_duration("record_comint_collection"):
                self.record_comint_collection(debriefing)
            with logged_duration("record_sitrep"):
                self.record_sitrep(debriefing)

    def record_comint_collection(self, debriefing: Debriefing) -> None:
        # §70 COMINT (C0): stamp the turn when a surviving blue collector (a §2
        # JAMMING flight or a drone) flew, unlocking Tier 2 (tasking leak +
        # concealed-site reveal) for the NEXT turn. No-op unless comint_collection
        # is on; a shot-down collector banks nothing.
        from game.fourteenth.comint import record_comint_collection

        record_comint_collection(self.game, debriefing)

    def commit_super_gaggle(self, debriefing: Debriefing) -> None:
        # Vietnam Ops §37: charge Super Gaggle airframe losses back to the real BLUE
        # squadrons that flew them, and credit the outpost on delivery. No-op when there was
        # no committed gaggle this turn.
        from game.fourteenth.super_gaggle import reconcile_super_gaggle

        reconcile_super_gaggle(self.game, debriefing)

    def commit_minefields(self, debriefing: Debriefing) -> None:
        # §57 Phase 2: fold the minefields plugin's end-of-mission field report into
        # game.minefields, carrying undisturbed air-dropped fields across the turn. No-op
        # when air_droppable_minefields is off or the plugin reported nothing.
        from game.fourteenth.minefields import reconcile_minefields

        reconcile_minefields(self.game, debriefing)

    def commit_cruise_missiles(self, debriefing: Debriefing) -> None:
        # §63: debit each launching ship group's persisted campaign magazine by what
        # the cruisemissiles plugin reported fired -- the only debit site, so mission
        # re-generation never double-counts. No-op when nothing was reported.
        from game.fourteenth.cruise_raids import reconcile_cruise_missiles

        reconcile_cruise_missiles(self.game, debriefing)

    def commit_naval_magazines(self, debriefing: Debriefing) -> None:
        # §81: debit each naval group's persisted anti-ship magazine by what the
        # navalmagazines plugin reported fired -- the only debit site, so mission
        # re-generation never double-counts. The weapon set is disjoint from §63's,
        # so a shot is never charged twice. No-op when nothing was reported.
        from game.fourteenth.naval_magazines import reconcile_naval_magazines

        reconcile_naval_magazines(self.game, debriefing)

    def record_sitrep(self, debriefing: Debriefing) -> None:
        # Capture a one-turn campaign summary for the next turn's kneeboard cover
        # band (§29). Reads numbers the debriefing already tallied; commit() runs
        # before the turn increments, so game.turn/current_day are the just-played
        # turn. All inputs are debriefing-derived and unaffected by commit order,
        # so this can run last.
        # §75: the alternate-ending progress digest -- empty (and hidden) unless
        # the campaign authors a `victory:` block or a knob is on.
        from game.fourteenth.victory import victory_sitrep_lines

        self.game.last_sitrep = Sitrep.from_debriefing(
            debriefing,
            self.game.turn,
            self.game.current_day,
            pilots_mia=self._downed_pilot_sitrep_lines(),
            red_c2_status=c2_status_line(self.game, Player.RED),
            victory_lines=victory_sitrep_lines(self.game),
        )

    def _downed_pilot_sitrep_lines(self) -> list[str]:
        """One player-facing line per BLUE survivor still awaiting rescue.

        Reads upstream #929's downed-pilot list rather than a pilot-status scan, so
        the SITREP shows exactly what the map and the auto-planner are working from.
        """
        lines: list[str] = []
        for downed in getattr(self.game.blue, "downed_pilots", None) or []:
            name = getattr(getattr(downed, "pilot", None), "name", None) or "Aircrew"
            turns = getattr(downed, "turns_remaining", None)
            where = self.game.theater.closest_control_point(downed.position)
            near = f" near {where.name}" if where is not None else ""
            clock = f" ({turns} turn{'s' if turns != 1 else ''} left)" if turns else ""
            lines.append(f"{name} — down{near}{clock}")
        return lines

    def commit_csar_results(self, debriefing: Debriefing) -> None:
        """Returns rescued downed pilots to recovery (hybrid resolution).

        Ops.CSAR pickups reported in state.json are authoritative. For AI-flown
        CSAR flights (and skipped/simulated turns, which produce no state.json), a
        surviving CSAR flight that targeted a downed pilot rescues them.
        """
        csar = CsarService(self.game)
        rescued: set[DownedPilot] = set()

        # Authoritative: pilots confirmed rescued in-mission by Ops.CSAR.
        for uuid_str in debriefing.state_data.rescued_pilot_ids:
            try:
                downed = self.game.db.downed_pilots.get(UUID(uuid_str))
            except (KeyError, ValueError):
                logging.warning(f"Ignoring unknown rescued pilot id {uuid_str}")
                continue
            rescued.add(downed)

        # Fallback: AI-flown CSAR flights that reached the pilot and survived.
        for coalition in self.game.coalitions:
            for package in coalition.ato.packages:
                for flight in package.flights:
                    if flight.flight_type is not FlightType.CSAR:
                        continue
                    target = flight.package.target
                    if not isinstance(target, DownedPilot) or target in rescued:
                        continue
                    if flight.client_count > 0:
                        # Player-flown: only the Ops.CSAR result counts, so an
                        # unflown or botched player CSAR correctly fails.
                        continue
                    if debriefing.air_losses.surviving_flight_members(flight) > 0:
                        rescued.add(target)

        for downed in rescued:
            # Record before rescuing: csar.rescue removes the pilot from the db,
            # and the debriefing windows read this to report the recovery.
            debriefing.record_rescue(downed)
            csar.rescue(downed)

    def commit_air_losses(self, debriefing: Debriefing) -> None:
        csar = CsarService(self.game)
        for loss in debriefing.air_losses.losses:
            self._process_lost_pilot(loss, debriefing, csar)
            squadron = loss.flight.squadron
            aircraft = loss.flight.unit_type
            available = squadron.owned_aircraft
            if available <= 0:
                logging.error(
                    f"Found killed {aircraft} from {squadron} but that airbase has "
                    "none available."
                )
                continue

            logging.info(f"{aircraft} destroyed from {squadron}")
            squadron.owned_aircraft -= 1
            squadron.destroyed_aircraft += 1

    def commit_intercept_losses(self, debriefing: Debriefing) -> None:
        all_squadrons: list[Squadron] = list(
            self.game.blue.air_wing.iter_squadrons()
        ) + list(self.game.red.air_wing.iter_squadrons())
        fielded_by_squadron, squadrons_by_id = fielded_qra_by_squadron(all_squadrons)

        if not fielded_by_squadron:
            return

        losses = reconcile_intercept_losses(
            fielded_by_squadron, debriefing.state_data.intercept_survivors
        )
        for squadron_id, loss in losses.items():
            if loss <= 0:
                continue
            squadron = squadrons_by_id.get(squadron_id)
            if squadron is None:
                continue
            logging.info(f"{loss} QRA aircraft lost from {squadron}")
            squadron.owned_aircraft = max(0, squadron.owned_aircraft - loss)
            squadron.lose_pilots(loss)

    def _process_lost_pilot(
        self, loss: Any, debriefing: Debriefing, csar: CsarService
    ) -> None:
        """Decides the fate of a lost aircraft's pilot: safe, downed, or killed.

        Airframe loss accounting is handled by the caller and is unaffected by the
        outcome here.
        """
        pilot = loss.pilot
        if pilot is None:
            return

        # Invulnerable player pilots survive untouched, exactly as before.
        if pilot.player and self.game.settings.invulnerable_player_pilots:
            return

        flight = loss.flight
        if not csar.csar_enabled_for(flight.squadron.player):
            pilot.kill()
            return

        # A real in-mission ejection always produces a downed pilot at the recorded
        # landing position. Otherwise roll the survival chance and scatter near the
        # flight's target (the only position we have for AI/simulated losses).
        ejection_pos = debriefing.ejected_pilot_positions.get(id(pilot))
        if ejection_pos is not None:
            position = ejection_pos
        elif random.randint(1, 100) <= self.game.settings.csar_ejection_chance:
            position = csar.fallback_position_for(flight)
        else:
            pilot.kill()
            return

        if csar.down_pilot(flight, pilot, pilot.player, position) is None:
            # No landable spot nearby; treat as killed.
            pilot.kill()

    @staticmethod
    def _commit_pilot_experience(ato: AirTaskingOrder) -> None:
        for package in ato.packages:
            for flight in package.flights:
                for idx, pilot in enumerate(flight.roster.iter_pilots()):
                    if pilot is None:
                        logging.error(
                            f"Cannot award experience to pilot #{idx} of {flight} "
                            "because no pilot is assigned"
                        )
                        continue
                    pilot.record.missions_flown += 1

    def commit_pilot_experience(self) -> None:
        self._commit_pilot_experience(self.game.blue.ato)
        self._commit_pilot_experience(self.game.red.ato)

    @staticmethod
    def commit_front_line_losses(debriefing: Debriefing) -> None:
        for loss in debriefing.front_line_losses:
            unit_type = loss.unit_type
            control_point = loss.origin
            available = control_point.base.total_units_of_type(unit_type)
            if available <= 0:
                logging.error(
                    f"Found killed {unit_type} from {control_point} but that "
                    "airbase has none available."
                )
                continue

            logging.info(f"{unit_type} destroyed from {control_point}")
            control_point.base.armor[unit_type] -= 1

    @staticmethod
    def commit_motorpool_losses(debriefing: Debriefing) -> None:
        for loss in debriefing.motorpool_losses:
            unit_type = loss.unit_type
            control_point = loss.origin
            available = control_point.base.total_units_of_type(unit_type)
            if available <= 0:
                logging.error(
                    f"Found killed motorpool {unit_type} from {control_point} but "
                    "that base has none available."
                )
                continue
            logging.info(f"Motorpool {unit_type} destroyed from {control_point}")
            control_point.base.armor[unit_type] -= 1

    @staticmethod
    def commit_convoy_losses(debriefing: Debriefing) -> None:
        for loss in debriefing.convoy_losses:
            unit_type = loss.unit_type
            convoy = loss.convoy
            available = loss.convoy.units.get(unit_type, 0)
            convoy_name = f"convoy from {convoy.origin} to {convoy.destination}"
            if available <= 0:
                logging.error(
                    f"Found killed {unit_type} in {convoy_name} but that convoy has "
                    "none available."
                )
                continue

            logging.info(f"{unit_type} destroyed in {convoy_name}")
            convoy.kill_unit(unit_type)

    @staticmethod
    def commit_cargo_ship_losses(debriefing: Debriefing) -> None:
        # §77: each sunk hull kills only its own share of the shipment (proportional
        # losses), so a convoy that runs the coastal gauntlet loses reinforcements in
        # proportion to how many ships went down. A single-hull convoy carries the whole
        # transfer, so this reproduces the legacy all-or-nothing loss.
        for hull in debriefing.cargo_ship_losses:
            ship = hull.ship
            for unit_type, count in hull.cargo:
                for _ in range(count):
                    try:
                        ship.kill_unit(unit_type)
                    except KeyError:
                        # Already reconciled by another sunk hull of the same convoy
                        # (or delivered) -- nothing left of this type to lose.
                        pass
            manifest = ", ".join(
                f"{count} {unit_type}" for unit_type, count in hull.cargo
            )
            logging.info(
                f"Cargo ship sunk in shipment from {ship.origin} to "
                f"{ship.destination}: lost {manifest or '(empty hull)'}."
            )

    @staticmethod
    def commit_airlift_losses(debriefing: Debriefing) -> None:
        for loss in debriefing.airlift_losses:
            transfer = loss.transfer
            airlift_name = f"airlift from {transfer.origin} to {transfer.destination}"
            for unit_type in loss.cargo:
                try:
                    transfer.kill_unit(unit_type)
                    logging.info(f"{unit_type} destroyed in {airlift_name}")
                except KeyError:
                    logging.exception(
                        f"Found killed {unit_type} in {airlift_name} but that airlift "
                        "has none available."
                    )

    def commit_ground_losses(
        self, debriefing: Debriefing, events: GameUpdateEvents
    ) -> None:
        struck_tgos: set[TheaterGroundObject] = set()
        for ground_object_loss in debriefing.ground_object_losses:
            struck_tgos.add(ground_object_loss.theater_unit.ground_object)
            ground_object_loss.theater_unit.kill(events)
        for scenery_object_loss in debriefing.scenery_object_losses:
            struck_tgos.add(scenery_object_loss.ground_unit.ground_object)
            scenery_object_loss.ground_unit.kill(events)
        self.update_confirmed_bda(struck_tgos, debriefing, events)

    def update_confirmed_bda(
        self,
        struck_tgos: set[TheaterGroundObject],
        debriefing: Debriefing,
        events: GameUpdateEvents,
    ) -> None:
        # Friendly targets always stay in sync with truth; only enemy BDA is allowed to
        # lag behind until recon confirms it.
        for tgo in struck_tgos:
            if tgo.is_friendly(Player.BLUE):
                tgo.sync_confirmed_status()
                events.update_tgo(tgo)

        for tgo in self.reconned_tgos_this_turn(debriefing):
            tgo.sync_confirmed_status()
            events.update_tgo(tgo)

        # TARS recon (when the plugin is enabled) reports the exact enemy units a
        # surviving recon sortie photographed, so we can confirm precisely what was
        # seen rather than revealing a whole package target on overflight. Additive:
        # the list is empty when TARS is off, so this is a no-op for the legacy path.
        for tgo in self.tars_reconned_tgos(debriefing):
            tgo.sync_confirmed_status()
            events.update_tgo(tgo)

        self.reveal_discovered_sites(struck_tgos, debriefing, events)

    def reveal_discovered_sites(
        self,
        struck_tgos: set[TheaterGroundObject],
        debriefing: Debriefing,
        events: GameUpdateEvents,
    ) -> None:
        """Recon intel-fog: flip enemy sites to "known" once the player has engaged
        them this turn.

        A site is discovered (composition + threat rings revealed, permanently) once
        it is attacked (units destroyed), scouted (recon/TARPS), or otherwise reached
        by an offensive sortie. Discovery is independent of post-strike BDA damage
        confirmation — you learn *what* is there, but whether your strike killed it
        still lags until recon confirms. Only enemy sites are gated; friendly/neutral
        and the omniscient planner are never fogged.
        """
        discovered: set[TheaterGroundObject] = set()
        discovered |= struck_tgos
        discovered |= self.reconned_tgos_this_turn(debriefing)
        discovered |= self.tars_reconned_tgos(debriefing)
        discovered |= self.attacked_tgos_this_turn(debriefing)
        for tgo in discovered:
            if tgo.is_friendly(Player.BLUE):
                continue
            if not tgo.discovered_by_player:
                tgo.discovered_by_player = True
                events.update_tgo(tgo)

    def attacked_tgos_this_turn(
        self, debriefing: Debriefing
    ) -> set[TheaterGroundObject]:
        # A surviving offensive sortie that reached its target reveals the site even
        # with no kills — the pilots saw what was there. Mirrors the TARPS recon
        # helper but for strike-type flights, blue ATO only (the player's knowledge).
        attacked: set[TheaterGroundObject] = set()
        offensive = {
            FlightType.STRIKE,
            FlightType.DEAD,
            FlightType.SEAD,
            FlightType.ANTISHIP,
        }
        for package in self.game.blue.ato.packages:
            target = package.target
            if not isinstance(target, TheaterGroundObject):
                continue
            for flight in package.flights:
                if (
                    flight.flight_type in offensive
                    and debriefing.air_losses.surviving_flight_members(flight) > 0
                ):
                    attacked.add(target)
                    break
        return attacked

    @staticmethod
    def tars_reconned_tgos(debriefing: Debriefing) -> set[TheaterGroundObject]:
        reconned: set[TheaterGroundObject] = set()
        # Lightweight Debriefings built for tests/UI may omit state_data/unit_map.
        state_data = getattr(debriefing, "state_data", None)
        unit_map = getattr(debriefing, "unit_map", None)
        if state_data is None or unit_map is None:
            return reconned
        for unit_name in state_data.tars_recon_captures:
            mapping = unit_map.theater_units(unit_name)
            if mapping is None:
                continue
            reconned.add(mapping.theater_unit.ground_object)
        return reconned

    def reconned_tgos_this_turn(
        self, debriefing: Debriefing
    ) -> set[TheaterGroundObject]:
        reconned: set[TheaterGroundObject] = set()
        for ato in (self.game.blue.ato, self.game.red.ato):
            reconned.update(self._reconned_tgos_from_ato(ato, debriefing))
        return reconned

    @staticmethod
    def _reconned_tgos_from_ato(
        ato: AirTaskingOrder, debriefing: Debriefing
    ) -> set[TheaterGroundObject]:
        reconned: set[TheaterGroundObject] = set()
        for package in ato.packages:
            target = package.target
            if not isinstance(target, TheaterGroundObject):
                continue
            for flight in package.flights:
                if (
                    flight.flight_type is FlightType.TARPS
                    and debriefing.air_losses.surviving_flight_members(flight) > 0
                ):
                    reconned.add(target)
                    break
        return reconned

    @staticmethod
    def commit_damaged_runways(debriefing: Debriefing) -> None:
        for damaged_runway in debriefing.damaged_runways:
            damaged_runway.damage_runway()

    def commit_captures(self, debriefing: Debriefing, events: GameUpdateEvents) -> None:
        for captured in debriefing.base_captures:
            try:
                if captured.captured_by_player.is_blue:
                    self.game.message(
                        f"{captured.control_point} captured!",
                        f"We took control of {captured.control_point}.",
                    )
                else:
                    self.game.message(
                        f"{captured.control_point} lost!",
                        f"The enemy took control of {captured.control_point}.",
                    )

                captured.control_point.capture(
                    self.game, events, captured.captured_by_player
                )
            except Exception:
                logging.exception(f"Could not process base capture {captured}")

        for captured in debriefing.base_captures:
            logging.info(f"Will run redeploy for {captured.control_point}")
            self.redeploy_units(captured.control_point)

    def record_carcasses(self, debriefing: Debriefing) -> None:
        for destroyed_unit in debriefing.state_data.destroyed_statics:
            self.game.add_destroyed_units(destroyed_unit)

    def commit_front_line_battle_impact(
        self, debriefing: Debriefing, events: GameUpdateEvents
    ) -> None:
        for cp in self.game.theater.player_points():
            enemy_cps = [e for e in cp.connected_points if e.captured.is_red]
            for enemy_cp in enemy_cps:
                front_line = cp.front_line_with(enemy_cp)
                front_line.update_position()
                events.update_front_line(front_line)

                print(
                    "Compute frontline progression for : "
                    + cp.name
                    + " to "
                    + enemy_cp.name
                )

                delta = 0.0
                player_won = True
                status_msg: str = ""
                ally_casualties = debriefing.casualty_count(cp)
                enemy_casualties = debriefing.casualty_count(enemy_cp)
                ally_units_alive = cp.base.total_frontline_units
                enemy_units_alive = enemy_cp.base.total_frontline_units

                print(f"Remaining allied units: {ally_units_alive}")
                print(f"Remaining enemy units: {enemy_units_alive}")
                print(f"Allied casualties {ally_casualties}")
                print(f"Enemy casualties {enemy_casualties}")

                ratio = (1.0 + enemy_casualties) / (1.0 + ally_casualties)

                player_aggresive = cp.stances[enemy_cp.id] in [
                    CombatStance.AGGRESSIVE,
                    CombatStance.ELIMINATION,
                    CombatStance.BREAKTHROUGH,
                ]

                if ally_units_alive == 0:
                    player_won = False
                    delta = STRONG_DEFEAT_INFLUENCE
                    status_msg = f"No allied units alive at {cp.name}-{enemy_cp.name} frontline.  Allied ground forces suffer a strong defeat."
                elif enemy_units_alive == 0:
                    player_won = True
                    delta = STRONG_DEFEAT_INFLUENCE
                    status_msg = f"No enemy units alive at {cp.name}-{enemy_cp.name} frontline.  Allied ground forces win a strong victory."
                elif cp.stances[enemy_cp.id] == CombatStance.RETREAT:
                    player_won = False
                    delta = STRONG_DEFEAT_INFLUENCE
                    status_msg = f"Allied forces are retreating along the {cp.name}-{enemy_cp.name} frontline, suffering a strong defeat."
                else:
                    if enemy_casualties > ally_casualties:
                        player_won = True
                        if cp.stances[enemy_cp.id] == CombatStance.BREAKTHROUGH:
                            delta = STRONG_DEFEAT_INFLUENCE
                            status_msg = f"Allied forces break through the {cp.name}-{enemy_cp.name} frontline, winning a strong victory"
                        else:
                            if ratio > 3:
                                delta = STRONG_DEFEAT_INFLUENCE
                                status_msg = f"Enemy casualties massively outnumber allied casualties along the {cp.name}-{enemy_cp.name} frontline.  Allied forces win a strong victory."
                            elif ratio < 1.5:
                                delta = MINOR_DEFEAT_INFLUENCE
                                status_msg = f"Enemy casualties minorly outnumber allied casualties along the {cp.name}-{enemy_cp.name} frontline.  Allied forces win a minor victory."
                            else:
                                delta = DEFEAT_INFLUENCE
                                status_msg = f"Enemy casualties outnumber allied casualties along the {cp.name}-{enemy_cp.name} frontline.  Allied forces claim a victory."
                    elif ally_casualties > enemy_casualties:
                        if (
                            ally_units_alive > 2 * enemy_units_alive
                            and player_aggresive
                        ):
                            # Even with casualties if the enemy is overwhelmed, they are going to lose ground
                            player_won = True
                            delta = MINOR_DEFEAT_INFLUENCE
                            status_msg = f"Despite suffering losses, allied forces still outnumber enemy forces along the {cp.name}-{enemy_cp.name} frontline.  Due to allied force's aggressive posture, allied forces claim a minor victory."
                        elif (
                            ally_units_alive > 3 * enemy_units_alive
                            and player_aggresive
                        ):
                            player_won = True
                            delta = STRONG_DEFEAT_INFLUENCE
                            status_msg = f"Despite suffering losses, allied forces still heavily outnumber enemy forces along the {cp.name}-{enemy_cp.name} frontline.  Due to allied force's aggressive posture, allied forces claim a major victory."
                        else:
                            # But if the enemy is not outnumbered, we lose
                            player_won = False
                            if cp.stances[enemy_cp.id] == CombatStance.BREAKTHROUGH:
                                delta = STRONG_DEFEAT_INFLUENCE
                                status_msg = f"Allied casualties outnumber enemy casualties along the {cp.name}-{enemy_cp.name} frontline.  Allied forces have overextended themselves, suffering a major defeat."
                            else:
                                delta = DEFEAT_INFLUENCE
                                status_msg = f"Allied casualties outnumber enemy casualties along the {cp.name}-{enemy_cp.name} frontline.  Allied forces suffer a defeat."

                    # No progress with defensive strategies
                    if player_won and cp.stances[enemy_cp.id] in [
                        CombatStance.DEFENSIVE,
                        CombatStance.AMBUSH,
                    ]:
                        print(
                            f"Allied forces have adopted a defensive stance along the {cp.name}-{enemy_cp.name} "
                            f"frontline, making only limited progress."
                        )
                        delta = MINOR_DEFEAT_INFLUENCE

                # Handle the case where there are no casualties at all on either side but both sides still have units
                if delta == 0.0:
                    print(status_msg)
                    self.game.message(
                        "Frontline Report",
                        f"Our ground forces from {cp.name} reached a stalemate with enemy forces from {enemy_cp.name}.",
                    )
                else:
                    if player_won:
                        print(status_msg)
                        self.apply_battle_result(
                            winner=cp,
                            loser=enemy_cp,
                            delta=delta,
                            winner_attacked=player_aggresive,
                        )
                        self.game.message(
                            "Frontline Report",
                            f"Our ground forces from {cp.name} are making progress toward {enemy_cp.name}. {status_msg}",
                        )
                    else:
                        print(status_msg)
                        self.apply_battle_result(
                            winner=enemy_cp,
                            loser=cp,
                            delta=delta,
                            winner_attacked=enemy_cp.stances.get(
                                cp.id, CombatStance.DEFENSIVE
                            )
                            in OFFENSIVE_STANCES,
                        )
                        self.game.message(
                            "Frontline Report",
                            f"Our ground forces from {cp.name} are losing ground against the enemy forces from "
                            f"{enemy_cp.name}. {status_msg}",
                        )

    def apply_battle_result(
        self,
        winner: ControlPoint,
        loser: ControlPoint,
        delta: float,
        winner_attacked: bool,
    ) -> None:
        """Move ground between two control points after a front-line battle.

        Rung B: the loser always yields the full delta, but a winner that was
        pushing forward banks less than it took -- the assault costs it. A
        defender that holds pays nothing, so ground is dearer to take than to
        keep. With the setting off this is the original straight swap.
        """
        loser.base.affect_strength(-delta)
        if winner_attacked and self.game.settings.assault_costs_the_attacker:
            winner.base.affect_strength(delta * (1.0 - ASSAULT_COST_FRACTION))
        else:
            winner.base.affect_strength(delta)

    def redeploy_units(self, cp: ControlPoint) -> None:
        """ "
        Auto redeploy units to newly captured base
        """
        enemy_connected_cps = [
            ocp for ocp in cp.connected_points if cp.captured != ocp.captured
        ]

        # If the newly captured cp does not have enemy connected cp,
        # then it is not necessary to redeploy frontline units there.
        if len(enemy_connected_cps) == 0:
            return

        ally_connected_cps = [
            ocp
            for ocp in cp.transitive_connected_friendly_destinations()
            if cp.captured == ocp.captured and ocp.base.total_frontline_units
        ]

        settings = cp.coalition.game.settings
        factor = (
            settings.frontline_reserves_factor
            if cp.captured.is_blue
            else settings.frontline_reserves_factor_red
        )

        # From each ally cp, send reinforcements
        for ally_cp in sorted(
            ally_connected_cps,
            key=lambda x: len(
                [cp for cp in x.connected_points if x.captured != cp.captured]
            ),
        ):
            self.redeploy_between(cp, ally_cp)
            if cp.base.total_frontline_units > factor * cp.deployable_front_line_units:
                break

    def redeploy_between(self, destination: ControlPoint, source: ControlPoint) -> None:
        total_units_redeployed = 0
        moved_units = {}

        settings = source.coalition.game.settings
        reserves = max(
            1,
            (
                settings.reserves_procurement_target
                if source.captured.is_blue
                else settings.reserves_procurement_target_red
            ),
        )
        total_units = source.base.total_frontline_units
        if total_units <= 0:
            return
        reserves_factor = (reserves - 1) / total_units  # slight underestimation

        source_frontline_count = len(
            [cp for cp in source.connected_points if not source.is_friendly_to(cp)]
        )

        move_factor = max(0.0, 1 / (source_frontline_count + 1) - reserves_factor)

        for frontline_unit, count in source.base.armor.items():
            if frontline_unit.unit_class not in FRONTLINE_UNIT_CLASSES:
                continue
            moved_count = int(count * move_factor)
            moved_units[frontline_unit] = moved_count
            total_units_redeployed += moved_count

        destination.base.commission_units(moved_units)
        source.base.commit_losses(moved_units)

        # Also transfer pending deliveries.
        for unit_type, count in list(source.ground_unit_orders.units.items()):
            move_count = int(count * move_factor)
            source.ground_unit_orders.sell({unit_type: move_count})
            destination.ground_unit_orders.order({unit_type: move_count})
            total_units_redeployed += move_count

        if total_units_redeployed > 0:
            self.game.message(
                "Units redeployed",
                f"{total_units_redeployed}  units have been redeployed from "
                f"{source.name} to {destination.name}",
            )
