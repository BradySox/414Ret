from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from game.debriefing import Debriefing
from game.data.units import FRONTLINE_UNIT_CLASSES
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
            with logged_duration("commit_scar_results"):
                self.commit_scar_results(debriefing)
            # Spend SOF while bases still have their pre-mission ownership. If a
            # source base was captured this mission, flipping ownership first
            # would make its deployed team disappear from the side's accounting.
            with logged_duration("commit_sof_deployments"):
                self.commit_sof_deployments(debriefing)
            with logged_duration("commit_sof_strandings"):
                self.commit_sof_strandings(debriefing)
            # Recover stranded teams (refunds inventory) before captures flip base
            # ownership, so a recovered team's refund can't land on a base that is
            # about to change hands.
            with logged_duration("commit_sof_recoveries"):
                self.commit_sof_recoveries(debriefing)
            with logged_duration("commit_pow_recoveries"):
                self.commit_pow_recoveries(debriefing)
            with logged_duration("commit_captures"):
                self.commit_captures(debriefing, events)
            with logged_duration("record_carcasses"):
                self.record_carcasses(debriefing)
            with logged_duration("record_sitrep"):
                self.record_sitrep(debriefing)

    def record_sitrep(self, debriefing: Debriefing) -> None:
        # Capture a one-turn campaign summary for the next turn's kneeboard cover
        # band (§29). Reads numbers the debriefing already tallied; commit() runs
        # before the turn increments, so game.turn/current_day are the just-played
        # turn. All inputs are debriefing-derived and unaffected by commit order,
        # so this can run last.
        self.game.last_sitrep = Sitrep.from_debriefing(
            debriefing, self.game.turn, self.game.current_day
        )

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
        """Hold each captured pilot as a recoverable POW.

        ``commit_air_losses`` already spared the kill (a POW is not KIA); here we
        create the recovery objective -- a ``PendingPowRecovery`` on the SURVIVOR's
        coalition (the side that wants its aviator back) carrying the airframe unit
        name (to spare the aviator on a successful recovery) and the capture position
        (the POW is held at the nearest enemy airfield, resolved when the objective is
        surfaced). The capture record's ``coalition`` is the survivor's side, so a blue
        survivor -> blue recovery and a red survivor -> red recovery. Fail-safe: an
        empty capture list (the normal case) is a no-op.
        """
        from game.pow_recovery import PendingPowRecovery

        rescued = self._combat_sar_rescued_unit_ids(debriefing)
        for unit_name, x, y, color in (
            getattr(debriefing.state_data, "combat_sar_captures", []) or []
        ):
            flying = debriefing.unit_map.flight(unit_name)
            if flying is not None and id(flying) in rescued:
                # Defensive: a pilot recorded as both rescued and captured is
                # treated as rescued (the rescue already spared them).
                continue
            # Hold the captured aviator so the campaign can free them on a recovery
            # raid (commit_pow_recoveries) or kill them if the POW is abandoned
            # (Coalition.end_turn -> surviving_pows).
            pilot = flying.pilot if flying is not None else None
            coalition = self.game.red if color == "red" else self.game.blue
            coalition.pending_pow_recoveries.append(
                PendingPowRecovery(airframe_unit_name=unit_name, x=x, y=y, pilot=pilot)
            )

    def commit_pow_recoveries(self, debriefing: Debriefing) -> None:
        """Free POWs raided out this mission.

        A surviving CSAR flight fragged against a captured-pilot objective frees
        that POW: the held aviator stays in the squadron and the
        ``PendingPowRecovery`` is cleared (matched back by the airframe unit name
        the objective carries). Mirrors ``commit_sof_recoveries``' surviving-CSAR-
        flight detection. No-op when nothing was recovered. (The other recovery
        paths -- recapturing the holding airfield, or the abandon-timeout kill --
        run at turn end in ``surviving_pows``.)
        """
        from game.theater.theatergroundobject import CapturedPilotGroundObject

        recovered_names: set[str] = set()
        for coalition in self.game.coalitions:
            for package in coalition.ato.packages:
                target = package.target
                if not isinstance(target, CapturedPilotGroundObject):
                    continue
                csar_flights = [
                    f for f in package.flights if f.flight_type is FlightType.CSAR
                ]
                if csar_flights and any(
                    debriefing.air_losses.surviving_flight_members(f) > 0
                    for f in csar_flights
                ):
                    name = getattr(target, "airframe_unit_name", "")
                    if name:
                        recovered_names.add(name)
        if not recovered_names:
            return
        for coalition in self.game.coalitions:
            kept = []
            for pow_entry in coalition.pending_pow_recoveries:
                if pow_entry.airframe_unit_name in recovered_names:
                    logging.info(
                        f"POW {pow_entry.airframe_unit_name} recovered by a CSAR "
                        "raid; the aviator returns to the squadron."
                    )
                else:
                    kept.append(pow_entry)
            coalition.pending_pow_recoveries = kept

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

    @staticmethod
    def _scar_tasking_is_blue(tasking_id: str) -> bool:
        # Tasking IDs now carry their coalition. Legacy unprefixed IDs came from
        # the player-side-only implementation and remain BLUE for save / debrief
        # compatibility.
        return tasking_id.startswith("blue-") or not tasking_id.startswith("red-")

    def commit_scar_results(self, debriefing: Debriefing) -> None:
        """Ingest SCAR per-area outcomes back into the campaign.

        Two carryovers are wired: a ``captured`` commander reveals the enemy's
        command posts next turn (Phase 1, gated by ``scar_command_post_intel``),
        and a mis-ID — prosecuting one of an area's decoy/clutter convoys —
        debits the offending side's budget (R7, gated by ``scar_misid_penalty``).

        Under the loiter-and-task model the target is a REAL campaign TGO, so a
        kill attrits the enemy through the normal ground-loss/debrief path — there
        is deliberately no SCAR-specific success/failed scoring. The ``success`` /
        ``failed`` / ``launched`` statuses the plugin still emits are therefore
        log-only here (not a missing hook). Additive — a no-op when the plugin /
        settings are off.
        """
        blue_captures = 0
        for tasking_id, status in debriefing.state_data.scar_results.items():
            logging.info(f"SCAR area {tasking_id}: {status}")
            if status == "captured" and self._scar_tasking_is_blue(tasking_id):
                blue_captures += 1
        if blue_captures and self.game.settings.scar_command_post_intel:
            self.game.blue.captured_commander = True
            # The team escapes with the hostage ("no one dares attack while the
            # commander is hostage"), so it returns to the pool — netting out the
            # debit-on-frag for a clean capture.
            self._refund_sof_teams(blue_captures)
            logging.info("SCAR: commander captured — enemy command posts revealed.")

        self._commit_scar_misid(debriefing)

    def _commit_scar_misid(self, debriefing: Debriefing) -> None:
        """Charge the R7 mis-ID penalty: each decoy/clutter convoy a side
        destroyed on a SCAR sortie debits ``scar_misid_penalty`` budget points
        from that side. Always logs the mis-ID; only debits when the penalty is
        positive."""
        scar_misid = getattr(debriefing.state_data, "scar_misid", {}) or {}
        if not scar_misid:
            return
        blue_misid = 0
        red_misid = 0
        for tasking_id, count in scar_misid.items():
            if count <= 0:
                continue
            logging.info(f"SCAR area {tasking_id}: {count} mis-ID(s) (wrong convoy)")
            if self._scar_tasking_is_blue(tasking_id):
                blue_misid += count
            else:
                red_misid += count
        penalty = self.game.settings.scar_misid_penalty
        if penalty <= 0:
            return
        for coalition, count in (
            (self.game.blue, blue_misid),
            (self.game.red, red_misid),
        ):
            if count <= 0:
                continue
            cost = count * penalty
            coalition.adjust_budget(-cost)
            side = "BLUE" if coalition.player.is_blue else "RED"
            logging.info(
                f"SCAR: {side} charged {cost} budget for {count} mis-ID(s) "
                f"({penalty} each)."
            )

    def _refund_sof_teams(self, count: int) -> None:
        """Return ``count`` bought SOF teams to a blue-held base (a captured
        commander's escort self-extracts). No-op if the SOF unit type isn't
        present or blue holds no base."""
        from game.dcs.groundunittype import GroundUnitType
        from game.scar_rescue import SCAR_SOF_UNIT_BLUE

        try:
            unit = GroundUnitType.named(SCAR_SOF_UNIT_BLUE)
        except KeyError:
            return
        for cp in self.game.theater.controlpoints:
            if cp.captured.is_blue:
                cp.base.commission_units({unit: count})
                return

    def _refund_sof_teams_to(self, player: Player, unit_name: str, count: int) -> None:
        """Return ``count`` SOF teams to any base held by ``player``. No-op if the
        SOF unit type isn't present or the side holds no base."""
        from game.dcs.groundunittype import GroundUnitType

        try:
            unit = GroundUnitType.named(unit_name)
        except KeyError:
            return
        for cp in self.game.theater.controlpoints:
            if cp.captured is player:
                cp.base.commission_units({unit: count})
                return

    @staticmethod
    def _same_strand_point(
        ax: float, ay: float, bx: float, by: float, tolerance: float = 1.0
    ) -> bool:
        # The objective is built at exactly the rescue's (x, y), so equality holds;
        # a small tolerance guards against float round-trips through generation.
        return abs(ax - bx) <= tolerance and abs(ay - by) <= tolerance

    def commit_sof_recoveries(self, debriefing: Debriefing) -> None:
        """Recover SOF teams stranded by a botched capture (Phase 2c-3, slice C4).

        A team is recovered either way the rescue can be flown:

        - A dedicated ``FlightType.CSAR`` helo flew at the "downed SOF team"
          objective standing on the team's position and survived the sortie (the
          deep-penetration recovery leg -- a surviving helo is a real
          accomplishment).
        - **Combat SAR** extracted it in-mission: the ``combatsar`` plugin spawned
          the stranded team as a CASEVAC and a Combat SAR rescue helo delivered it
          to a friendly field, reported by its ``SOFRESCUE_<x>_<y>`` name (blue
          only -- the MOOSE CSAR engine is blue-side).

        Either path refunds one bought SOF team to a friendly base and clears the
        pending rescue (a team recovered by both still refunds once). No-op when
        the feature is off.
        """
        if not self.game.settings.scar_command_post_intel:
            return
        from game.theater.theatergroundobject import DownedSofGroundObject
        from game.scar_rescue import (
            SCAR_SOF_UNIT_BLUE,
            SCAR_SOF_UNIT_RED,
            sof_rescue_pickup_name,
        )

        # state_data is only absent on lightweight Debriefings built for tests; a
        # real debrief always carries it (see qra_losses_by_type for the same guard).
        state_data = getattr(debriefing, "state_data", None)
        delivered_sof = set(getattr(state_data, "combat_sar_sof_recoveries", []) or [])
        for coalition, unit_name in (
            (self.game.blue, SCAR_SOF_UNIT_BLUE),
            (self.game.red, SCAR_SOF_UNIT_RED),
        ):
            recovered_points: list[tuple[float, float]] = []
            for package in coalition.ato.packages:
                target = package.target
                if not isinstance(target, DownedSofGroundObject):
                    continue
                csar_flights = [
                    f for f in package.flights if f.flight_type is FlightType.CSAR
                ]
                if csar_flights and any(
                    debriefing.air_losses.surviving_flight_members(f) > 0
                    for f in csar_flights
                ):
                    recovered_points.append((target.position.x, target.position.y))
            # Combat SAR in-mission extractions are blue-only (the engine is blue).
            sof_names = delivered_sof if coalition.player.is_blue else set()
            if not recovered_points and not sof_names:
                continue
            remaining = []
            recovered = 0
            for rescue in coalition.pending_csars:
                point_match = any(
                    self._same_strand_point(rescue.x, rescue.y, px, py)
                    for px, py in recovered_points
                )
                name_match = sof_rescue_pickup_name(rescue) in sof_names
                if point_match or name_match:
                    recovered += 1
                else:
                    remaining.append(rescue)
            coalition.pending_csars = remaining
            if recovered:
                self._refund_sof_teams_to(coalition.player, unit_name, recovered)

    def commit_sof_deployments(self, debriefing: Debriefing) -> None:
        """Spend one bought SOF team per SCAR target that had a SOF insert flown
        against it (Phase 2c-2).

        Fragging the insert debits the team from inventory regardless of the
        capture outcome (the team deployed). A clean capture refunds it (the team
        escapes with the hostage); a botch strands it for a next-turn CSAR pickup
        (2c-3); an un-rescued team stays lost. Deduped by target so multiple
        inserts on one HVT (which still delivers a single team) can't
        double-charge. No-op when the feature is off or the SOF unit isn't present.
        """
        if not self.game.settings.scar_command_post_intel:
            return
        from game.dcs.groundunittype import GroundUnitType
        from game.scar_rescue import (
            SCAR_SOF_UNIT_BLUE,
            SCAR_SOF_UNIT_RED,
        )

        for coalition, unit_name in (
            (self.game.blue, SCAR_SOF_UNIT_BLUE),
            (self.game.red, SCAR_SOF_UNIT_RED),
        ):
            try:
                unit = GroundUnitType.named(unit_name)
            except KeyError:
                continue
            spent_targets: set[int] = set()
            for package in coalition.ato.packages:
                insert = next(
                    (f for f in package.flights if f.flight_type is FlightType.SOF),
                    None,
                )
                if insert is None or id(package.target) in spent_targets:
                    continue
                spent_targets.add(id(package.target))
                self._spend_sof_team(unit, insert.departure)

    def _spend_sof_team(self, unit: "GroundUnitType", origin: ControlPoint) -> None:
        """Debit one bought SOF team for a flown insert: prefer the flight's
        origin base, else any same-side base that still holds one. No-op if none
        is in stock (the offering doesn't hard-block planning without a team)."""
        if origin.base.armor.get(unit, 0) > 0:
            origin.base.commit_losses({unit: 1})
            return
        for cp in self.game.theater.controlpoints:
            if cp.captured == origin.captured and cp.base.armor.get(unit, 0) > 0:
                cp.base.commit_losses({unit: 1})
                return

    def commit_sof_strandings(self, debriefing: Debriefing) -> None:
        """Record SOF teams stranded by a botched capture as pending CSAR pickups
        (Phase 2c-3). Each becomes a persisted next-turn rescue objective on the
        owning coalition; the tasking id's prefix picks the side. No-op when the
        feature is off or nothing was stranded."""
        if not self.game.settings.scar_command_post_intel:
            return
        from game.scar_rescue import PendingSofRescue

        for tasking_id, x, y in debriefing.state_data.sof_strandings:
            is_blue = tasking_id.startswith("blue-") or not tasking_id.startswith(
                "red-"
            )
            coalition = self.game.blue if is_blue else self.game.red
            coalition.pending_csars.append(PendingSofRescue(x=x, y=y))

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
                        cp.base.affect_strength(delta)
                        enemy_cp.base.affect_strength(-delta)
                        self.game.message(
                            "Frontline Report",
                            f"Our ground forces from {cp.name} are making progress toward {enemy_cp.name}. {status_msg}",
                        )
                    else:
                        print(status_msg)
                        enemy_cp.base.affect_strength(delta)
                        cp.base.affect_strength(-delta)
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
