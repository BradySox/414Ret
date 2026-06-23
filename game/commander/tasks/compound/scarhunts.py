from collections.abc import Iterator

from game.commander.tasks.primitive.scar import PlanScar
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method


class PlanScarHunts(CompoundTask[TheaterState]):
    """Phase 3: make a SCAR hunt show up in the blue ATO automatically.

    Opt-in (``scar_autoplan``, default off) and **blue-only** — SCAR is a human
    discrimination puzzle, so the AI keeps using BAI for anti-armor and never
    frags SCAR for itself. When enabled, it proposes a single SCAR package per
    turn against the highest-priority enemy armor concentration near the front,
    so the player can just claim a slot and fly it instead of hand-building one.
    Yields nothing (a strict no-op) when the setting is off, the planner is red,
    or there is no battle position to hunt.
    """

    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        if not state.context.settings.scar_autoplan:
            return
        if not state.context.coalition.player.is_blue:
            return
        for group in state.enemy_battle_positions.values():
            for battle_position in group.in_priority_order:
                yield [PlanScar(battle_position)]
                # One auto-fragged SCAR hunt per turn — keep it a single,
                # deliberate hunt, not a sweep of every armor group.
                return
