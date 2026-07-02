"""COIN C1: free, anchored-cap insurgent cell regeneration (design-note §3).

Spec: docs/dev/design/414th-coin-insurgent-replenishment-notes.md. Retribution's
ground economy is a state army's -- budget spent at control points with a ground-unit
*source*, delivered by transfer -- and an insurgency fails every clause of that
sentence (Operation Shattered Dagger ships with the enemy economy zeroed precisely
because the stock loop would have the Taliban buying SAM batteries). This module is
the COIN replacement: **infiltration, not logistics**.

Once per turn (``Game.finish_turn``, next to the §35 trail-convoy hook), every
insurgent-held control point regenerates a small number of garrison units:

* **Real units only** -- commissioned directly into ``cp.base.armor``
  (``Base.commission_units``), free and budget-less, dying through the normal loss
  path. No phantom spawns (the §35/§37 lesson).
* **Anchored cap** -- each CP only refills *toward its garrison size when first seen
  insurgent-held* (turn 0 for a preseeded campaign; the ``static_front`` anchor
  pattern). The insurgency refills, it never grows.
* **Cache throttle** -- the regen rate scales with the CP's alive **ammo caches**
  (its ``category == "ammo"`` ground objects, anchored the same way). Destroy the
  caches and the trickle collapses to a residual floor
  (:data:`CACHE_HEALTH_FLOOR`, squadron call §7.1 -- infiltration never fully
  stops; the will economy is what ends the war). A CP authored with *no* caches
  regenerates at full rate (the author opted out of the mechanic there).
* **Hard whitelist** -- only cheap irregular kit regenerates:
  :data:`REGEN_UNIT_CLASSES` **and** price <= :data:`REGEN_MAX_UNIT_PRICE`. The
  class set admits IFV/APC because the insurgent *technicals* are class IFV in the
  unit data (price 2-4); the price ceiling is what keeps BMPs (14-16), Grads (15),
  and everything conventional out. Tanks, ATGMs, SAMs, and radars are never
  admitted regardless of price.

Fractional rates carry over between turns (a deterministic per-CP accumulator), so
the 25% floor of a 2/turn base still lands a unit every other turn instead of
rounding to zero forever.

Everything is behind the ``coin_insurgency`` setting -- default OFF,
campaign-preseeded like the Vietnam Ops suite. Off means this module never runs.
Red-only by design (the insurgent side is the opfor, design-note §5); the §17
boundary stands -- this is an economy layer, never a planner input.

State lives in ``game.coin_state`` (a plain ``{cp_id: {...}}`` dict, pickled;
``getattr`` default so pre-feature saves are untouched until the toggle is on).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from game.data.units import UnitClass

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from game.dcs.groundunittype import GroundUnitType
    from game.theater import ControlPoint

#: Units per turn per CP at full cache health. Deliberately below what a purposeful
#: clearance kills -- BLUE attrition must be able to outpace the trickle locally.
REGEN_BASE_UNITS_PER_TURN = 2.0

#: Residual rate multiplier once every anchored cache is destroyed (squadron call
#: §7.1: 25% floor -- a cleared stronghold decays under pressure but never flatlines).
CACHE_HEALTH_FLOOR = 0.25

#: Unit classes eligible for regeneration. IFV/APC are here because the insurgent
#: technicals are class IFV in the unit data; the price ceiling excludes real IFVs.
REGEN_UNIT_CLASSES = frozenset(
    {
        UnitClass.INFANTRY,
        UnitClass.RECON,
        UnitClass.IFV,
        UnitClass.APC,
        UnitClass.AAA,
        UnitClass.ARTILLERY,
        UnitClass.MANPAD,
    }
)

#: Price ceiling for regenerated units: technicals (2-4), ZU-23s (4-6), and light
#: MLRS trucks (10) are in; BMP-1/2 (14/16) and BM-21 (15) are out.
REGEN_MAX_UNIT_PRICE = 10


def regenerate_insurgent_cells(game: "Game") -> None:
    """Regenerate every insurgent-held CP's garrison toward its anchor. Idempotent
    per turn by construction only when called once -- call it exactly once from
    ``finish_turn`` (the §35 hook pattern).

    No-op unless ``coin_insurgency`` is on; no-op on turn 0 (the anchor snapshot
    turn must not also regenerate) and whenever the faction fields no eligible
    units.
    """
    if not getattr(game.settings, "coin_insurgency", False):
        return
    if getattr(game, "turn", 0) < 1:
        _ensure_anchors(game)  # snapshot turn 0 so the cap is the true start state
        return

    coalition = game.red
    pool = regen_unit_pool(coalition)
    state = _ensure_anchors(game)
    if not pool or state is None:
        return

    for cp in game.theater.controlpoints:
        if not cp.captured.is_red:
            continue
        # _ensure_anchors snapshotted every red-held CP, so the anchor exists. A CP
        # first seen mid-campaign anchors to its *current* garrison -- it refills
        # only after losses, never grows.
        anchor = state[str(cp.id)]

        deficit = anchor["garrison_cap"] - cp.base.total_armor
        if deficit <= 0:
            continue

        health = cache_health(cp, anchor["cache_total"])
        budget = anchor.get("carry", 0.0) + REGEN_BASE_UNITS_PER_TURN * health
        count = min(int(budget), deficit)
        anchor["carry"] = budget - int(budget)

        if count <= 0:
            continue
        # Cycle the pool (cheapest-first order, offset by turn) so garrisons refill
        # with a deterministic mix rather than a monoculture of the cheapest truck.
        start = game.turn % len(pool)
        order = [pool[(start + i) % len(pool)] for i in range(count)]
        for unit_type in order:
            cp.base.commission_units({unit_type: 1})


def regen_unit_pool(coalition: "Coalition") -> list["GroundUnitType"]:
    """The faction's regen-eligible units, cheapest-first (name-tiebroken).

    Filtered by :data:`REGEN_UNIT_CLASSES` AND :data:`REGEN_MAX_UNIT_PRICE` -- the
    hard whitelist. An insurgent faction's technicals/ZU-23s pass; any armor, SAM,
    or conventional IFV a faction carries never does.
    """
    units = getattr(coalition.faction, "frontline_units", None) or set()
    eligible = [
        unit
        for unit in units
        if unit.unit_class in REGEN_UNIT_CLASSES and unit.price <= REGEN_MAX_UNIT_PRICE
    ]
    return sorted(eligible, key=lambda unit: (unit.price, unit.display_name))


def cache_health(cp: "ControlPoint", anchored_total: int) -> float:
    """Alive fraction of the CP's anchored ammo-cache set, floored.

    ``anchored_total == 0`` (a stronghold authored without caches) means the
    campaign opted out of the throttle there: full rate. Otherwise the alive
    fraction, never below :data:`CACHE_HEALTH_FLOOR` (squadron call §7.1).
    """
    if anchored_total <= 0:
        return 1.0
    alive = _alive_cache_count(cp)
    return max(CACHE_HEALTH_FLOOR, min(1.0, alive / anchored_total))


def _alive_cache_count(cp: "ControlPoint") -> int:
    """The CP's alive ammo caches: ``category == 'ammo'`` TGOs with any unit alive."""
    count = 0
    for tgo in cp.ground_objects:
        if getattr(tgo, "category", None) != "ammo":
            continue
        if any(unit.alive for unit in tgo.units):
            count += 1
    return count


def _snapshot(cp: "ControlPoint") -> dict[str, Any]:
    """A CP's anchor: the garrison cap + cache total at first insurgent-held sight."""
    return {
        "garrison_cap": cp.base.total_armor,
        "cache_total": _alive_cache_count(cp),
        "carry": 0.0,
    }


def _ensure_anchors(game: "Game") -> Optional[dict[str, dict[str, Any]]]:
    """The pickled per-CP anchor store, creating it (with turn-appropriate
    snapshots of every currently insurgent-held CP) on first use.

    Plain ``{str(cp.id): {garrison_cap, cache_total, carry}}`` primitives only, so
    old saves unpickle it as a normal dict; ``getattr`` default means pre-feature
    saves carry nothing until the toggle is enabled.
    """
    state: Optional[dict[str, dict[str, Any]]] = getattr(game, "coin_state", None)
    if state is None:
        state = {}
        game.coin_state = state
    for cp in game.theater.controlpoints:
        if cp.captured.is_red and str(cp.id) not in state:
            state[str(cp.id)] = _snapshot(cp)
    return state
