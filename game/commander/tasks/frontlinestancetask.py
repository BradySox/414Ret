from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from game.commander.tasks.theatercommandertask import TheaterCommanderTask
from game.commander.theaterstate import TheaterState
from game.ground_forces.combat_stance import CombatStance
from game.theater import FrontLine

if TYPE_CHECKING:
    from game.coalition import Coalition
    from game.theater.player import Player


#: §55 P3 (seam 4): the attacking stances whose balance threshold RED's posture biases.
#: Only these are tuned (surge commits sooner, consolidate husbands); the defensive/
#: neutral stances keep the raw balance, so consolidate never forces a retreat.
_ATTACK_STANCES = (
    CombatStance.AGGRESSIVE,
    CombatStance.ELIMINATION,
    CombatStance.BREAKTHROUGH,
)


class FrontLineStanceTask(TheaterCommanderTask, ABC):
    def __init__(self, front_line: FrontLine, player: Player) -> None:
        self.front_line = front_line
        self.friendly_cp = self.front_line.control_point_friendly_to(player)
        self.enemy_cp = self.front_line.control_point_hostile_to(player)

    @property
    @abstractmethod
    def stance(self) -> CombatStance: ...

    @staticmethod
    def management_allowed(state: TheaterState) -> bool:
        return (
            not state.context.coalition.player.is_blue
            or state.context.settings.automate_front_line_stance
        )

    def better_stance_already_set(self, state: TheaterState) -> bool:
        current_stance = state.front_line_stances[self.front_line]
        if current_stance is None:
            return False
        preference = (
            CombatStance.RETREAT,
            CombatStance.DEFENSIVE,
            CombatStance.AMBUSH,
            CombatStance.AGGRESSIVE,
            CombatStance.ELIMINATION,
            CombatStance.BREAKTHROUGH,
        )
        current_rating = preference.index(current_stance)
        new_rating = preference.index(self.stance)
        return current_rating >= new_rating

    @property
    @abstractmethod
    def have_sufficient_front_line_advantage(self) -> bool: ...

    @property
    def ground_force_balance(self) -> float:
        # TODO: Planned CAS missions should reduce the expected opposing force size.
        friendly_forces = self.friendly_cp.deployable_front_line_units
        enemy_forces = self.enemy_cp.deployable_front_line_units
        if enemy_forces == 0:
            return math.inf
        return (friendly_forces / enemy_forces) * self._posture_commit_factor()

    def _posture_commit_factor(self) -> float:
        """§55 P3 (seam 4): RED's posture biases the ATTACK-stance thresholds only.

        SURGE inflates the perceived balance (red commits reserves at a lower real
        advantage), CONSOLIDATE deflates it (red husbands). Returns 1.0 for blue, a
        stock/observing red, the defensive/neutral stances, and while an authored
        red_tempo pulse owns the stances -- so the raw balance (and every existing
        stance test) is preserved unless red is actively surging or consolidating.
        """
        if self.stance not in _ATTACK_STANCES:
            return 1.0
        coalition = self.friendly_cp.coalition
        if coalition.player.is_blue:
            return 1.0
        from game.fourteenth.red_intent import stance_commit_factor

        # Pass this task's front so red uses its PER-FRONT posture (D) -- committing on
        # the front it is winning, husbanding on the one it is losing. Falls back to the
        # theater-wide posture when per-front is off or the front doesn't resolve.
        return stance_commit_factor(coalition.game, self.front_line)

    def preconditions_met(self, state: TheaterState) -> bool:
        if not self.management_allowed(state):
            return False
        if self.better_stance_already_set(state):
            return False
        if self.friendly_cp.deployable_front_line_units == 0:
            return False
        return self.have_sufficient_front_line_advantage

    def apply_effects(self, state: TheaterState) -> None:
        state.front_line_stances[self.front_line] = self.stance

    def execute(self, coalition: Coalition) -> None:
        self.friendly_cp.stances[self.enemy_cp.id] = self.stance
