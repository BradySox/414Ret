from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from game.debriefing import Debriefing
from game.data.units import FRONTLINE_UNIT_CLASSES
from game.fourteenth.c2_decapitation import c2_status_line
from game.fourteenth.war_economy import supply_effectiveness
from game.ground_forces.combat_stance import CombatStance
from game.missiongenerator.interceptattrition import (
    fielded_qra_by_squadron,
    reconcile_intercept_losses,
)
from game.profiling import logged_duration
from game.sitrep import Sitrep
from game.squadrons.squadron import Squadron
from game.theater.theatergroundobject import TheaterGroundObject
from game.theater import ControlPoint, Player
from ..ato.flighttype import FlightType
from .gameupdateevents import GameUpdateEvents
from ..ato.airtaaskingorder import AirTaskingOrder

if TYPE_CHECKING:
    from ..game import Game
    from game.dcs.groundunittype import GroundUnitType


MINOR_DEFEAT_INFLUENCE = 0.1
DEFEAT_INFLUENCE = 0.3
STRONG_DEFEAT_INFLUENCE = 0.5


class MissionResultsProcessor:
    def __init__(self, game: Game) -> None:
        self.game = game

    def commit(self, debriefing: Debriefing, events: GameUpdateEvents) -> None:
        with logged_duration("Committing mission results"):
            with logged_duration("commit_air_losses"):
                self.commit_air_losses(debriefing)
            with logged_duration("record_pow_captures"):
                self.record_pow_captures(debriefing)
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
            # Political will feeds AFTER the loss/POW/capture steps (so the held-POW
            # trickle reads post-recovery state) and BEFORE the SITREP (so the band
            # shows this turn's fresh values).
            with logged_duration("record_political_will"):
                self.record_political_will(debriefing)
            with logged_duration("record_sitrep"):
                self.record_sitrep(debriefing)

    def record_political_will(self, debriefing: Debriefing) -> None:
        # Vietnam campaign layer W1 (observe-only): feed both sides' political will
        # from the turn's debriefing. No-op unless vietnam_political_will is on.
        from game.fourteenth.political_will import update_political_will

        update_political_will(self.game, debriefing)

    def commit_super_gaggle(self, debriefing: Debriefing) -> None:
        # Vietnam Ops §37: charge Super Gaggle airframe losses back to the real BLUE
        # squadrons that flew them, and credit the outpost on delivery. No-op when there was
        # no committed gaggle this turn.
        from game.fourteenth.super_gaggle import reconcile_super_gaggle

        reconcile_super_gaggle(self.game, debriefing)

    def record_sitrep(self, debriefing: Debriefing) -> None:
        # Capture a one-turn campaign summary for the next turn's kneeboard cover
        # band (§29). Reads numbers the debriefing already tallied; commit() runs
        # before the turn increments, so game.turn/current_day are the just-played
        # turn. All inputs are debriefing-derived and unaffected by commit order,
        # so this can run last.
        # The will band rides along only when tracking is on (W1): record_political_will
        # has already run this commit, so these are the turn's fresh values -- and the
        # ledger's latest entry is this turn's attribution (the movers lines).
        will_on = getattr(self.game.settings, "vietnam_political_will", False)
        blue_note: Optional[str] = None
        red_note: Optional[str] = None
        if will_on:
            from game.fourteenth.political_will import ledger_notes

            blue_note, red_note = ledger_notes(self.game)
        # War economy (§53 P4): the front-supply band rides along when the economy is
        # on, so the player can read why a front stalled (the P2 bite). Enemy claimed.
        blue_supply: Optional[float] = None
        red_supply: Optional[float] = None
        if getattr(self.game.settings, "war_economy", False):
            from game.fourteenth.war_economy import coalition_supply_health

            blue_supply = coalition_supply_health(self.game, self.game.blue)
            red_supply = coalition_supply_health(self.game, self.game.red)
        # §55: red's posture line + the detail (intensity + trend drivers, so the smart
        # read shows on the kneeboard). Both None unless red_intent is on.
        from game.fourteenth.red_intent import (
            sitrep_posture_detail,
            sitrep_posture_line,
        )

        self.game.last_sitrep = Sitrep.from_debriefing(
            debriefing,
            self.game.turn,
            self.game.current_day,
            blue_will=self.game.blue.political_will if will_on else None,
            red_will=self.game.red.political_will if will_on else None,
            blue_will_note=blue_note,
            red_will_note=red_note,
            pows_held=self._pow_sitrep_lines(),
            red_c2_status=c2_status_line(self.game, Player.RED),
            blue_supply=blue_supply,
            red_supply=red_supply,
            red_posture=sitrep_posture_line(self.game),
            red_posture_detail=sitrep_posture_detail(self.game),
        )

    def _pow_sitrep_lines(self) -> list[str]:
        """One player-facing line per BLUE aviator currently held POW.

        Named by pilot, located at the holding enemy field, with the lever spelled
        out: a turn countdown on a normal campaign, "(held)" on a will campaign
        where the hold is indefinite (freed only by recapture or the war's end).
        """
        will_economy = bool(
            getattr(self.game.settings, "vietnam_political_will", False)
        )
        lines: list[str] = []
        for entry in self.game.blue.pending_pow_recoveries:
            name = entry.pilot.name if entry.pilot is not None else "Downed aviator"
            where = "an unknown location"
            if entry.holding_cp_id is not None:
                try:
                    cp = self.game.theater.find_control_point_by_id(entry.holding_cp_id)
                    where = cp.name
                except KeyError:
                    pass
            if will_economy:
                clock = "held"
            else:
                turns = max(entry.turns_remaining, 0)
                clock = f"{turns} turn{'s' if turns != 1 else ''} left"
            lines.append(f"{name} — held at {where} ({clock})")
        return lines

    @staticmethod
    def _combat_sar_rescued_unit_ids(debriefing: Debriefing) -> set[int]:
        """Identity set of the FlyingUnit losses whose pilot Combat SAR delivered
        home this mission.

        ``combat_sar_rescues`` carries the ejected aircraft's original DCS unit
        name, which is the same name the loss was mapped from, so resolving it
        through the unit map yields the very FlyingUnit in ``air_losses``. Matching
        on object identity keeps this robust even if a name somehow recurs.
        """
        rescued: set[int] = set()
        for unit_name in debriefing.state_data.combat_sar_rescues:
            flying = debriefing.unit_map.flight(unit_name)
            if flying is not None:
                rescued.add(id(flying))
        return rescued

    @staticmethod
    def _combat_sar_captured_unit_ids(debriefing: Debriefing) -> set[int]:
        """Identity set of the FlyingUnit losses whose pilot the enemy CAPTURED
        (the Combat SAR snatch party reached them before rescue).

        Like the rescue set, each capture carries the ejected aircraft's original
        DCS unit name, so it resolves through the unit map to the FlyingUnit in
        ``air_losses``. A captured pilot is held as a POW, not killed.
        """
        captured: set[int] = set()
        for unit_name, _x, _y, _color in (
            getattr(debriefing.state_data, "combat_sar_captures", []) or []
        ):
            flying = debriefing.unit_map.flight(unit_name)
            if flying is not None:
                captured.add(id(flying))
        return captured

    def record_pow_captures(self, debriefing: Debriefing) -> None:
        """Hold each captured pilot as a POW.

        ``commit_air_losses`` already spared the kill (a POW is not KIA); here we
        hold the aviator -- a ``PendingPowRecovery`` on the SURVIVOR's coalition
        (the side that lost them) carrying the airframe unit name and the capture
        position, with the holding enemy airfield resolved immediately. The POW
        is freed if the holding field falls, killed when the hold clock expires
        (``Coalition.end_turn`` -> ``surviving_pows``), and drains political will
        per turn held. The shelved recovery raid offered no other path (CSAR
        rescope 2026-07-03). Fail-safe: an empty capture list (the normal case)
        is a no-op.
        """
        from game.pow_recovery import PendingPowRecovery, resolve_holding_airfield

        rescued = self._combat_sar_rescued_unit_ids(debriefing)
        for unit_name, x, y, color in (
            getattr(debriefing.state_data, "combat_sar_captures", []) or []
        ):
            flying = debriefing.unit_map.flight(unit_name)
            if flying is not None and id(flying) in rescued:
                # Defensive: a pilot recorded as both rescued and captured is
                # treated as rescued (the rescue already spared them).
                continue
            pilot = flying.pilot if flying is not None else None
            coalition = self.game.red if color == "red" else self.game.blue
            if pilot is not None:
                # Flip the aviator to POW so the squadron stops scheduling them
                # while captive (active_pilots excludes POWs) -- they were still
                # Active after the mission otherwise, and could fly next turn.
                pilot.capture()
            entry = PendingPowRecovery(
                airframe_unit_name=unit_name,
                x=x,
                y=y,
                pilot=pilot,
                captured_turn=self.game.turn,
            )
            resolve_holding_airfield(self.game, coalition, entry)
            coalition.pending_pow_recoveries.append(entry)

    def commit_air_losses(self, debriefing: Debriefing) -> None:
        # A Combat SAR pickup loses the airframe but saves the aviator; an enemy
        # capture loses the airframe but holds the aviator as a POW. Either way the
        # loss is still attrited below, only the pilot is spared the kill (a POW is
        # recoverable -- record_pow_captures hangs the recovery objective).
        rescued_unit_ids = self._combat_sar_rescued_unit_ids(debriefing)
        captured_unit_ids = self._combat_sar_captured_unit_ids(debriefing)
        for loss in debriefing.air_losses.losses:
            rescued = id(loss) in rescued_unit_ids
            captured = (id(loss) in captured_unit_ids) and not rescued
            if rescued and loss.pilot is not None:
                logging.info(
                    f"Combat SAR recovered the pilot of {loss.flight.unit_type} "
                    f"from {loss.flight.squadron}; airframe lost, aviator saved."
                )
            elif captured and loss.pilot is not None:
                logging.info(
                    f"Enemy captured the pilot of {loss.flight.unit_type} from "
                    f"{loss.flight.squadron}; airframe lost, aviator held as POW."
                )
            if (
                loss.pilot is not None
                and not rescued
                and not captured
                and (
                    not loss.pilot.player
                    or not self.game.settings.invulnerable_player_pilots
                )
            ):
                loss.pilot.kill()
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
        for ship in debriefing.cargo_ship_losses:
            logging.info(
                f"All units destroyed in cargo ship from {ship.origin} to "
                f"{ship.destination}."
            )
            ship.kill_all()

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
                        # War economy (§53 P2): a starved winner converts a win into
                        # less ground -- scale the shift by the *winner's* supply so
                        # interdiction slows an advance. x1.0 no-op unless on+seeded;
                        # symmetric (whichever side wins). Scales both the winner's
                        # gain and the loser's loss equally.
                        won = delta * supply_effectiveness(cp)
                        cp.base.affect_strength(won)
                        enemy_cp.base.affect_strength(-won)
                        self.game.message(
                            "Frontline Report",
                            f"Our ground forces from {cp.name} are making progress toward {enemy_cp.name}. {status_msg}",
                        )
                    else:
                        print(status_msg)
                        won = delta * supply_effectiveness(enemy_cp)
                        enemy_cp.base.affect_strength(won)
                        cp.base.affect_strength(-won)
                        self.game.message(
                            "Frontline Report",
                            f"Our ground forces from {cp.name} are losing ground against the enemy forces from "
                            f"{enemy_cp.name}. {status_msg}",
                        )

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
