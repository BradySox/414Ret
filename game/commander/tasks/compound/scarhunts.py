from collections.abc import Iterator

from game.commander.tasks.primitive.scar import PlanScar
from game.commander.tasks.targetorder import shuffled_by_priority
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method


class PlanScarHunts(CompoundTask[TheaterState]):
    """Phase 3: make player-flyable SCAR hunts show up in the blue ATO automatically.

    Opt-in (``scar_autoplan``, default off) and **blue-only** — SCAR is a human
    discrimination puzzle, so the AI keeps using BAI for anti-armor and never frags
    SCAR for itself. When enabled, it proposes up to ``scar_autoplan_per_turn`` SCAR
    packages per turn against enemy armor concentrations near the front (each
    ``PlanScar`` consumes its battle position, so the hunts land on *different*
    targets, not stacked on one). Selection runs through ``shuffled_by_priority``, so
    the ``ownfor_planner_unpredictability`` lever varies which groups get hunted
    turn-to-turn (at 0 — the default — it is the deterministic priority order). This
    **augments** BAI rather than replacing it: SCAR claims a couple of armor groups
    for the player; BAI (planned earlier, also consuming) covers the rest for the AI.

    Yields nothing (a strict no-op) when the setting is off, the planner is red,
    the per-turn cap is already met, or there is no battle position to hunt.
    """

    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        if not state.context.settings.scar_autoplan:
            return
        if not state.context.coalition.player.is_blue:
            return
        if state.scar_hunts_planned >= state.context.settings.scar_autoplan_per_turn:
            return
        battle_positions = [
            battle_position
            for group in state.enemy_battle_positions.values()
            for battle_position in group.in_priority_order
        ]
        for battle_position in shuffled_by_priority(battle_positions, state):
            yield [PlanScar(battle_position)]
