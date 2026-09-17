"""Adaptive procurement (§68): the AI economy reads the war.

``ProcurementAi`` was the flattest brain in the engine: a fixed air/ground
budget slider, doctrine-fixed class ratios, and ``random.choice`` over
whatever was affordable. This module adds two couplings:

1. **Air-defense site repair.** Nothing ever rebuilt a dead SAM -- the enemy
   IADS only decayed, so Rollback was a one-way ratchet. With
   ``auto_repair_air_defenses`` on, each side's AI commander repairs a couple
   of destroyed SAM/EWR *units* per turn at existing sites (the same
   pay-full-price, flip-alive repair the player has always had on the base
   card), degraded-but-alive sites first, radars before launchers. Command
   centers and comms nodes are deliberately NOT repairable -- §51/§52
   decapitation stays a permanent strategic payoff.
2. **Capability-weighted unit choice.** The ground-unit buy stops picking
   uniformly at random among affordable types and weights the roll by price
   (the capability proxy the model actually has), so the enemy fields T-72s
   more often than gun trucks when it can afford them. Variety is preserved --
   it is a weighting, not a max.

The capability weighting is gated by ``adaptive_procurement`` (default ON); the
site repair is its own ``auto_repair_air_defenses`` gate (default OFF -- it
materially changes campaign difficulty: the SAM belt regenerates unless the
player keeps pressure on it).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterable, List, Tuple

from dcs.mapping import Point

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint
    from game.theater.theatergroup import TheaterUnit

#: How many destroyed air-defense units a side may repair per turn. Two keeps
#: it a slow regeneration -- standing pressure on the belt, never whack-a-mole
#: against the player's whole DEAD effort.
MAX_AIR_DEFENSE_REPAIRS_PER_TURN = 2

#: The TGO categories the repair covers: SAM/AAA sites and EWRs. Command
#: centers, comms and power nodes are excluded by design (§51/§52 kills stay
#: permanent), as is everything mobile the turn model owns elsewhere.
REPAIRABLE_CATEGORIES = ("aa", "ewr")


def _repair_candidates(
    control_points: Iterable["ControlPoint"],
) -> List[Tuple[int, float, int, "TheaterUnit"]]:
    """Dead, repairable air-defense units, best repair value first.

    Sort key: degraded-but-alive sites before fully-dead ones (restoring a
    blinded site's radar buys the most capability per dollar), then the
    priciest unit first (radars over launchers), index as the tiebreak."""
    candidates: List[Tuple[int, float, int, "TheaterUnit"]] = []
    for cp in control_points:
        for tgo in cp.ground_objects:
            if getattr(tgo, "category", None) not in REPAIRABLE_CATEGORIES:
                continue
            units = [u for g in tgo.groups for u in g.units]
            site_alive = any(u.alive for u in units)
            for unit in units:
                if unit.alive or not unit.repairable or unit.unit_type is None:
                    continue
                candidates.append(
                    (
                        0 if site_alive else 1,
                        -unit.unit_type.price,
                        len(candidates),
                        unit,
                    )
                )
    candidates.sort(key=lambda c: (c[0], c[1], c[2]))
    return candidates


def _clear_wreck_near(game: "Game", unit: "TheaterUnit") -> None:
    """Drop the persisted wreck marker at a repaired unit's position.

    The same cleanup the player's repair button does -- without it the repaired
    unit spawns alongside its own burnt-out model next mission."""
    try:
        destroyed = game.get_destroyed_units()
    except AttributeError:
        return
    for d in list(destroyed):
        try:
            p = Point(float(d["x"]), float(d["z"]), game.theater.terrain)
            if p.distance_to_point(unit.position) < 15:
                destroyed.remove(d)
        except (KeyError, TypeError, ValueError):
            continue


def repair_air_defenses(
    game: "Game", control_points: Iterable["ControlPoint"], budget: float
) -> float:
    """Repair up to the per-turn cap of dead SAM/EWR units; returns the leftover.

    Pays the full unit price (the player's repair rate). A candidate the budget
    can't cover is skipped, not blocking -- the commander repairs what it can
    afford this turn. No-op (byte-identical budget) when the gate is off."""
    if not getattr(game.settings, "auto_repair_air_defenses", False):
        return budget
    repaired = 0
    for _, _, _, unit in _repair_candidates(control_points):
        if repaired >= MAX_AIR_DEFENSE_REPAIRS_PER_TURN:
            break
        assert unit.unit_type is not None  # filtered in _repair_candidates
        price = unit.unit_type.price
        if price > budget:
            continue
        budget -= price
        unit.alive = True
        # The mirror of TheaterUnit.kill(): the cached threat polygon must
        # follow the aliveness flip or the site's rings stay shrunk.
        invalidate = getattr(unit.ground_object, "invalidate_threat_poly", None)
        if invalidate is not None:
            invalidate()
        repaired += 1
        _clear_wreck_near(game, unit)
        logging.info(
            "Air-defense repair: %s restored at %s for %dM",
            unit.unit_name,
            getattr(unit.ground_object, "name", "site"),
            price,
        )
    return budget
