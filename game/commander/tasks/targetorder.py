"""Priority-weighted target ordering for the theater commander's HTN tasks.

The auto-planner's compound tasks yield candidate targets in a deterministic,
strict-priority order, so the same campaign state always produces the same red
(or blue) plan -- which reads as "scripted" in game. ``shuffled_by_priority``
reorders an already-prioritized candidate list with a tunable amount of
randomness so the planner sometimes services a lower-priority *opportunistic*
target first, without ever abandoning a real defensive threat response (callers
keep their reactive tiers deterministic and only pass opportunistic tiers here).

The strength comes from ``ownfor_/opfor_planner_unpredictability`` (0-100). At 0
-- the default -- the original order is returned unchanged, preserving the
deterministic planner and all existing tests.
"""

from __future__ import annotations

import random
from typing import Iterable, TYPE_CHECKING, TypeVar

from game.fourteenth.c2_decapitation import unpredictability_bonus

if TYPE_CHECKING:
    from game.commander.theaterstate import TheaterState

T = TypeVar("T")


def _unpredictability_for(state: TheaterState) -> int:
    settings = state.context.settings
    coalition = state.context.coalition
    if coalition.player.is_blue:
        base = settings.ownfor_planner_unpredictability
    else:
        base = settings.opfor_planner_unpredictability
    # §52 Feature A: a decapitated command network plans sloppier -- add
    # unpredictability in proportion to this side's dead command centers. 0 when
    # the feature is off or the network is intact, so the base setting is
    # preserved byte-identically. Clamped to the shuffler's 0-100 domain.
    bonus = unpredictability_bonus(coalition, state.context.theater, settings)
    return min(100, base + bonus)


def shuffled_by_priority(
    items: Iterable[T],
    state: TheaterState,
    rng: random.Random | None = None,
) -> list[T]:
    """Reorder ``items`` (already in descending priority) with weighted randomness.

    With unpredictability 0 the input order is returned unchanged. Higher values
    progressively flatten the priority weighting so lower-priority targets are
    increasingly likely to be serviced first, while the highest-priority target
    remains the single most likely pick at any non-extreme setting.
    """
    ordered = list(items)
    strength = _unpredictability_for(state)
    if strength <= 0 or len(ordered) < 2:
        return ordered

    r = rng if rng is not None else random
    # decay in (0, 1): ->0 keeps strict priority, ->1 approaches a uniform shuffle.
    decay = min(strength / 100.0, 0.999)

    # Efraimidis-Spirakis weighted sampling without replacement: each item gets a
    # key u**(1/weight); sorting by key descending yields a weighted random order.
    # weight = decay**rank, so rank 0 (highest priority) has weight 1 and lower
    # ranks decay toward 0, biasing them later unless strength is high.
    keyed: list[tuple[float, T]] = []
    for rank, item in enumerate(ordered):
        weight = decay**rank
        if weight <= 0.0:
            key = 0.0
        else:
            # r.random() is in [0, 1); nudge off zero so key stays well-defined.
            key = max(r.random(), 1e-12) ** (1.0 / weight)
        keyed.append((key, item))

    # Stable sort on the key only (never the item) so equal keys keep priority
    # order and non-comparable items never get compared.
    keyed.sort(key=lambda ki: ki[0], reverse=True)
    return [item for _key, item in keyed]
