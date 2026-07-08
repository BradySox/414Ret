"""War economy (§53) -- the produce -> transport -> store -> consume supply loop.

Stock Retribution's economy is a single ``Coalition.budget`` scalar fed by a flat
cash trickle; nothing you bomb traceably changes what the enemy can field, and the
front moves off an abstract ``strength`` ratio decoupled from materiel. This module
adds a per-base **supply stockpile** (``Base.supply``): production sources (factories,
oil/derricks) make it, it accumulates toward a per-CP capacity buffer, and -- from
§53 P2 -- it will gate frontline combat effectiveness so interdicting the enemy's
production/transport visibly thins their front.

**P0 (this initial form) is observe-only.** It seeds each control point's stockpile
to capacity on the first turn, computes production, accrues it (capped), and reports
the per-side numbers so the meters can be read and balanced *before* any gameplay
bite. There is no consumption, no transport, and no FLOT effect yet (those are P1/P2).

Two public read accessors are exposed now because the red-intent feature (§55)
consumes :func:`coalition_supply_health` at its P4, and the §53 P2 combat bite will
consume :func:`supply_factor` -- both are **pure reads with no side effects**, safe
to call whether or not the feature is on.

Gated by ``war_economy`` (Campaign Management, default OFF, campaign-preseeded). Off
/ no producers / no active front => the advance is a no-op and the accessors read as
fully supplied (1.0).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from game.theater.controlpoint import ControlPoint

#: Supply consumed per turn to keep one deployable front-line unit fully effective.
SUPPLY_PER_FRONTLINE_UNIT = 2.0

#: A full stockpile holds this many turns of a front's demand -- the reserve buffer
#: that lets a stockpile *accumulate* (decision 1a) and a blockade take several turns
#: to starve rather than biting instantly.
STOCKPILE_TURNS = 3.0

#: Demand floor so a quiet / rear CP still has a small capacity to hold a buffer.
MIN_DEMAND = 4.0

#: Supply produced per alive static, by ``REWARDS`` category. Only *production*
#: sources count -- storage depots (ammo/fuel/warehouse) hold materiel rather than
#: make it, and gate transport/consumption in later phases, not production here.
_PRODUCTION_RATES: dict[str, float] = {
    "factory": 8.0,
    "oil": 6.0,
    "derrick": 5.0,
}


def _clamp01(value: float) -> float:
    return 0.0 if value < 0.0 else 1.0 if value > 1.0 else value


def frontline_demand(cp: "ControlPoint") -> float:
    """Supply this CP's front consumes per turn to stay fully effective.

    Zero for a CP with no active front -- there is nothing to starve.
    """
    if not cp.has_active_frontline:
        return 0.0
    return SUPPLY_PER_FRONTLINE_UNIT * cp.deployable_front_line_units


def stockpile_capacity(cp: "ControlPoint") -> float:
    """Full-stockpile size: a buffer of :data:`STOCKPILE_TURNS` turns of demand.

    A rear producer with no front still needs room to hold what it makes, so
    production counts toward the buffer alongside frontline demand (and the floor) --
    otherwise a factory would be capped at the tiny no-front floor and could never
    serve as a supply source for the fronts it feeds.
    """
    return STOCKPILE_TURNS * max(frontline_demand(cp), production_rate(cp), MIN_DEMAND)


def production_rate(cp: "ControlPoint") -> float:
    """Supply produced at this CP per turn from its alive production sources."""
    total = 0.0
    for tgo in cp.ground_objects:
        rate = _PRODUCTION_RATES.get(tgo.category)
        if rate is None:
            continue
        total += rate * sum(1 for static in tgo.statics if static.alive)
    return total


def supply_factor(cp: "ControlPoint") -> float:
    """Materiel readiness of this CP's front in ``[0.0, 1.0]`` -- PURE READ.

    ``1.0`` = at least a full turn's demand in stock (or no front to supply);
    ``0.0`` = starved. This is the per-CP input the §53 P2 combat bite will consume
    and, aggregated by :func:`coalition_supply_health`, the signal §55 red-intent
    reads. No side effects.
    """
    demand = frontline_demand(cp)
    if demand <= 0.0:
        return 1.0
    return _clamp01(cp.base.supply / demand)


def coalition_supply_health(game: "Game", coalition: "Coalition") -> float:
    """Mean :func:`supply_factor` over ``coalition``'s active-front CPs -- PURE READ.

    ``1.0`` for a coalition with no active front (no fight to starve). This is the
    read-only accessor the red-intent feature (§55) consumes at its P4 to let
    materiel starvation force red to consolidate; it never mutates state, so it is
    safe to call before the economy has produced anything.
    """
    total = 0.0
    count = 0
    for cp in game.theater.control_points_for(coalition.player):
        if not cp.has_active_frontline:
            continue
        total += supply_factor(cp)
        count += 1
    return 1.0 if count == 0 else total / count


def _seed_supply(game: "Game") -> None:
    """One-time fill of every CP's stockpile to capacity.

    Campaigns don't open with empty depots; without this a freshly-enabled feature
    would read every front as starved on turn 1. Runs once, latched by
    ``game.war_economy_seeded``.
    """
    for cp in game.theater.controlpoints:
        cp.base.supply = stockpile_capacity(cp)
    game.war_economy_seeded = True


def _external_supply_sources(cp: "ControlPoint") -> list["ControlPoint"]:
    """Connected friendly CPs (excluding ``cp`` itself) that produce supply.

    A front refills from these over the transit graph. If the graph is cut so none
    are reachable (a captured/severed link, a lost rear base), the front is isolated
    and cannot resupply -- it draws down its buffer as it consumes. This is the
    interdiction throttle: sever the route to the producers and the front starves.
    """
    sources: list["ControlPoint"] = []
    for other in cp.transitive_connected_friendly_destinations():
        if other is cp:
            continue
        if production_rate(other) > 0.0:
            sources.append(other)
    return sources


def _draw_supply(sources: list["ControlPoint"], amount: float) -> float:
    """Draw up to ``amount`` total from ``sources`` (fullest first); return the drawn."""
    remaining = amount
    for source in sorted(sources, key=lambda s: s.base.supply, reverse=True):
        if remaining <= 0.0:
            break
        take = min(remaining, source.base.supply)
        source.base.supply -= take
        remaining -= take
    return amount - remaining


def advance_war_economy(game: "Game") -> None:
    """Per-turn war-economy step -- produce, transport to the front, consume.

    No-op unless ``war_economy`` is on. Seeds stockpiles once, then each turn:
    producers accrue output (capped at capacity); every active-front CP consumes a
    turn's demand from its own stock; and it refills toward capacity from its
    connected producers (:func:`_external_supply_sources`), neediest front first.
    A front cut off from production cannot refill and drains -- the interdiction
    loop. **No FLOT effect yet**: supply levels moving is *material* only; the combat
    bite (recovery / cap / delta) is §53 P2. Reports the per-side flow.
    """
    if not game.settings.war_economy:
        return
    if not getattr(game, "war_economy_seeded", False):
        _seed_supply(game)
    for coalition in (game.blue, game.red):
        cps = list(game.theater.control_points_for(coalition.player))
        produced = 0.0
        for cp in cps:
            rate = production_rate(cp)
            if rate <= 0.0:
                continue
            produced += rate
            cp.base.supply = min(cp.base.supply + rate, stockpile_capacity(cp))
        consumed = 0.0
        delivered = 0.0
        fronts = [cp for cp in cps if cp.has_active_frontline]
        # Neediest fronts draw first when resupply is scarce.
        for cp in sorted(fronts, key=supply_factor):
            spent = min(cp.base.supply, frontline_demand(cp))
            cp.base.supply -= spent
            consumed += spent
            need = stockpile_capacity(cp) - cp.base.supply
            if need > 0.0:
                drawn = _draw_supply(_external_supply_sources(cp), need)
                cp.base.supply += drawn
                delivered += drawn
        starving = sum(1 for cp in fronts if supply_factor(cp) < 1.0)
        health = coalition_supply_health(game, coalition)
        side = "BLUE" if coalition.player.is_blue else "RED"
        short = f" ({starving} front(s) short)" if starving else ""
        game.message(
            "War economy",
            f"{side} logistics: +{produced:.0f} produced, {delivered:.0f} moved "
            f"forward, {consumed:.0f} consumed; front supply "
            f"{health * 100:.0f}%{short}.",
        )
