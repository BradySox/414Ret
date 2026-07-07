"""COIN C1: free, anchored-cap insurgent cell regeneration (design-note §3).

Spec: docs/dev/design/414th-coin-insurgent-replenishment-notes.md. Retribution's
ground economy is a state army's -- budget spent at control points with a ground-unit
*source*, delivered by transfer -- and an insurgency fails every clause of that
sentence (Operation Shattered Dagger ships with the enemy economy zeroed precisely
because the stock loop would have the Taliban buying SAM batteries). This module is
the COIN replacement: **infiltration, not logistics**.

Once per turn (``Game.finish_turn``, next to the §35 trail-convoy hook), every
insurgent-held control point regenerates a small number of garrison units:

* **Real units only** -- two channels, in priority order: units commissioned
  directly into ``cp.base.armor`` (``Base.commission_units`` -- campaigns with
  ground routes), then **reviving the stronghold's own dead TGO cell units** (the
  C3 reality: an air-assault laydown fields no front-line garrisons at all -- the
  insurgent force lives in the vehicle-group TGOs around each FOB). Both are free
  and budget-less and die through the normal loss path. No phantom spawns (the
  §35/§37 lesson); revival is conservation by construction (only what the campaign
  authored can come back), and ``alive_at_last_recon`` is never touched, so the
  player's last recon picture stands until re-flown.
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
from game.sidc import (
    ActivityEntity,
    DismountedIndividualEntity,
    Entity,
    LandUnitEntity,
    SymbolSet,
)

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

#: NATO APP-6(D) map symbols for the COIN-spawned objects. They are all mechanically
#: red vehicle groups (FRONT_LINE/BASE_DEFENSE force groups), so without an override
#: each would render as a hostile tank platoon. The map icon is drawn client-side from
#: the SIDC the server emits (``TheaterGroundObject.sidc_entity_override``), so
#: re-pointing the symbol here needs no client change. Codes verified against
#: milsymbol's own APP-6(D) render tables (see ``game/sidc.py``).
CELL_SIDC: tuple[SymbolSet, Entity] = (SymbolSet.LAND_UNIT, LandUnitEntity.INFANTRY)
IED_SIDC: tuple[SymbolSet, Entity] = (
    SymbolSet.ACTIVITY_EVENT,
    ActivityEntity.IMPROVISED_EXPLOSIVE_DEVICE,
)
HVT_SIDC: tuple[SymbolSet, Entity] = (
    SymbolSet.DISMOUNTED_INDIVIDUAL,
    DismountedIndividualEntity.LEADER,
)


def snapshot_campaign_start_anchors(game: "Game") -> None:
    """Pin the C1 conservation anchors to the true campaign start.

    Called from ``Game.initialize_turn`` at turn 0 (before any mission flies).
    The ``finish_turn`` regen hook only ever runs *after* the turn counter has
    advanced (``self.turn += 1`` precedes it), so it never sees turn 0 -- without
    this snapshot the anchors would first be taken after the first mission's
    losses committed, permanently shrinking the caps and zeroing the
    cache-health suppression for first-mission cache kills.
    """
    if getattr(game, "turn", 0) != 0:
        return
    if not getattr(game.settings, "coin_insurgency", False):
        return
    _ensure_anchors(game)


def regenerate_insurgent_cells(game: "Game", events: Any = None) -> None:
    """Regenerate every insurgent-held CP's garrison toward its anchor. Idempotent
    per turn by construction only when called once -- call it exactly once from
    ``finish_turn`` (the §35 hook pattern).

    No-op unless ``coin_insurgency`` is on; no-op on turn 0 (the anchor snapshot
    turn must not also regenerate) and whenever the faction fields no eligible
    units.
    """
    if not getattr(game.settings, "coin_insurgency", False):
        return
    # Symbol every insurgent garrison as infantry (idempotent, runs each turn incl.
    # turn 0) so a COIN stronghold reads as an insurgency, not an armor park.
    symbol_insurgent_garrisons(game, events)
    if getattr(game, "turn", 0) < 1:
        _ensure_anchors(game)  # snapshot turn 0 so the cap is the true start state
        return

    coalition = game.red
    pool = regen_unit_pool(coalition)
    state = _ensure_anchors(game)
    if state is None:
        return

    for cp in game.theater.controlpoints:
        if not cp.captured.is_red:
            continue
        # _ensure_anchors snapshotted every red-held CP, so the anchor exists. A CP
        # first seen mid-campaign anchors to its *current* garrison -- it refills
        # only after losses, never grows.
        anchor = state[str(cp.id)]

        # Two channels, in priority order: the front-line garrison (Base.armor --
        # campaigns with ground routes), then reviving the stronghold's own dead
        # TGO cells (the C3 reality: an air-assault laydown fields NO front-line
        # garrisons; the insurgent force lives in the vehicle-group TGOs around
        # each FOB). Revival is conservation by construction -- only what the
        # campaign authored can come back -- and recon fog keeps the player's last
        # confirmed picture until re-reconned ("we cleared that position last
        # week; it's shooting again").
        armor_deficit = max(0, anchor["garrison_cap"] - cp.base.total_armor)
        if not pool:
            armor_deficit = 0  # no eligible units to commission
        revivable = _revivable_units(cp)
        tgo_deficit = min(
            len(revivable),
            max(0, anchor.get("tgo_cap", 0) - _alive_cell_count(cp)),
        )
        if armor_deficit + tgo_deficit <= 0:
            continue  # at cap: carry stays frozen, no banked units

        health = cache_health(cp, anchor["cache_total"])
        budget = anchor.get("carry", 0.0) + REGEN_BASE_UNITS_PER_TURN * health
        count = min(int(budget), armor_deficit + tgo_deficit)
        anchor["carry"] = budget - int(budget)
        if count <= 0:
            continue

        commissions = min(count, armor_deficit)
        if commissions and pool:
            # Cycle the pool (cheapest-first order, offset by turn) so garrisons
            # refill with a deterministic mix, not a monoculture of one truck.
            start = game.turn % len(pool)
            for i in range(commissions):
                cp.base.commission_units({pool[(start + i) % len(pool)]: 1})
        for unit in revivable[: count - commissions]:
            _revive(unit, game, events)


def _alive_cell_count(cp: "ControlPoint") -> int:
    """Alive whitelisted vehicle units across the CP's non-cache TGOs."""
    return sum(
        1
        for tgo in cp.ground_objects
        if getattr(tgo, "category", None) != "ammo"
        and not getattr(tgo, "coin_spawned", False)
        for unit in tgo.units
        if unit.alive and _revival_eligible(unit)
    )


def _revivable_units(cp: "ControlPoint") -> list[Any]:
    """The CP's dead, whitelist-eligible TGO cell units, in deterministic order."""
    dead = []
    for tgo in sorted(
        cp.ground_objects, key=lambda t: getattr(t, "name", "") or str(id(t))
    ):
        if getattr(tgo, "category", None) == "ammo":
            continue  # caches are the throttle, never the militia
        if getattr(tgo, "coin_spawned", False):
            continue  # transient spawns have their own lifecycle -- never revived
        for unit in tgo.units:
            if not unit.alive and _revival_eligible(unit):
                dead.append(unit)
    return dead


def _revival_eligible(unit: Any) -> bool:
    """The C1 whitelist applied to a theater unit: cheap irregular kit only.

    Reads the unit's GroundUnitType (class + price); anything unmapped (statics,
    types without unit data) is never revived. StopIteration-guarded: a dcs type
    with no registered GroundUnitType simply isn't eligible.
    """
    if not getattr(unit, "is_vehicle", False):
        return False
    try:
        unit_type = unit.unit_type
    except StopIteration:
        return False
    if unit_type is None:
        return False
    return (
        unit_type.unit_class in REGEN_UNIT_CLASSES
        and unit_type.price <= REGEN_MAX_UNIT_PRICE
    )


def symbol_insurgent_garrisons(game: "Game", events: Any = None) -> None:
    """Render every insurgent-held CP's militia as **infantry** on the map, so a COIN
    stronghold reads as an insurgency rather than an armor park (the discrete cell /
    IED / HVT spawns already carry their own symbol; this covers the standing garrison
    the campaign authored). Idempotent -- safe to call every turn.

    Scope by *composition*, not class import: only a non-cache TGO whose units are all
    C1-whitelist-eligible (:func:`_revival_eligible` -- irregular infantry/technicals/
    AAA) is re-symboled. That cleanly leaves the fixed radar-SAM crust and EWRs alone
    (their launchers/radars fail the whitelist), skips ammo caches (their own symbol),
    and never re-points a discrete COIN spawn (it already has an override).
    """
    if not getattr(game.settings, "coin_insurgency", False):
        return
    for cp in game.theater.controlpoints:
        if not cp.captured.is_red:
            continue
        for tgo in cp.ground_objects:
            if getattr(tgo, "category", None) == "ammo":
                continue
            if getattr(tgo, "sidc_entity_override", None) is not None:
                continue
            units = list(tgo.units)
            if not units or not all(_revival_eligible(u) for u in units):
                continue
            tgo.sidc_entity_override = CELL_SIDC
            if events is not None:
                events.update_tgo(tgo)


def _revive(unit: Any, game: "Game", events: Any) -> None:
    """The inverse of TheaterUnit.kill, minus the recon ledger.

    ``alive_at_last_recon`` is deliberately untouched: the player's last confirmed
    picture stands until a new recon pass -- the COIN fog behaviour for free.
    """
    unit.alive = True
    tgo = getattr(unit, "ground_object", None)
    if tgo is None:
        return
    invalidate = getattr(tgo, "invalidate_threat_poly", None)
    if invalidate is not None:
        invalidate()
    if events is not None:
        events.update_tgo(tgo)
        if getattr(tgo, "is_iads", False):
            game.theater.iads_network.update_tgo(tgo, events)


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
    """A CP's anchor at first insurgent-held sight: garrison cap, the alive TGO
    cell count (the revival ceiling), and the cache total."""
    return {
        "garrison_cap": cp.base.total_armor,
        "tgo_cap": _alive_cell_count(cp),
        "cache_total": _alive_cache_count(cp),
        "carry": 0.0,
    }


def _ensure_anchors(game: "Game") -> Optional[dict[str, Any]]:
    """The pickled per-CP anchor store, creating it (with turn-appropriate
    snapshots of every currently insurgent-held CP) on first use.

    Plain ``{str(cp.id): {garrison_cap, cache_total, carry}}`` primitives only, so
    old saves unpickle it as a normal dict; ``getattr`` default means pre-feature
    saves carry nothing until the toggle is enabled.

    Non-CP bookkeeping keys (``_red_cp_turn0``, ``reinfiltration``) live in the same
    dict; the CP accessors are keyed by ``str(cp.id)`` and never iterate the store,
    so the extra keys are inert to C1.
    """
    state: Optional[dict[str, Any]] = getattr(game, "coin_state", None)
    if state is None:
        state = {}
        game.coin_state = state
    for cp in game.theater.controlpoints:
        if cp.captured.is_red and str(cp.id) not in state:
            state[str(cp.id)] = _snapshot(cp)
    # The conservation baseline: how many CPs the insurgency held when the store was
    # first built (turn 0 for a preseeded campaign). Set once; re-infiltration may
    # relocate a stronghold but the red CP count must never exceed this.
    if "_red_cp_turn0" not in state:
        state["_red_cp_turn0"] = sum(
            1 for cp in game.theater.controlpoints if cp.captured.is_red
        )
    return state


# --- C1.5 re-infiltration (the insurgency retakes ungarrisoned ground) ---------
# Design: docs/dev/design/414th-coin-reinfiltration-notes.md. A staged, announced,
# counterable pipeline -- cell -> cache -> flip -- over ~4 turns, one attempt active
# theater-wide, evaluated once per turn from finish_turn right after C1's regen.

#: A BLUE garrison at or below this many ground units is "under-held" -- a token
#: picket does not count as holding ground (design §3.0 / squadron call §8.1).
HOLD_THRESHOLD = 4

#: A stronghold can only project into a target within this range (metres, §3.0).
INFILTRATION_RANGE_M = 60_000.0

#: A stronghold whose C1 cache health is below this cannot project -- strangling the
#: source suppresses both regeneration AND expansion (design §3.0).
SOURCE_HEALTH_GATE = 0.5

#: Turns the cell must survive under-held before the cache seeds (§3.2).
STAGE1_TURNS = 2

#: Turns after the cache before the CP flips (§3.3) -- ~4 turns of warnings total.
STAGE2_TURNS = 2

#: Turns the pipeline cools down after an aborted attempt before trying anywhere (§3.1).
COOLDOWN_TURNS = 3

#: Units commissioned into a flipped CP -- a weak re-anchor, well below any original
#: stronghold, so a retaken CP comes back weak and regrows under the cache throttle.
REINFIL_GARRISON = 6

#: Cap on the infiltration cell's size so it reads as a cell, not a garrison (§3.1).
CELL_MAX_UNITS = 3


def advance_reinfiltration(game: "Game", events: Any = None) -> None:
    """Advance the one active re-infiltration attempt (or start one). Call exactly
    once per turn from ``finish_turn``, right after ``regenerate_insurgent_cells``.

    No-op unless both ``coin_reinfiltration`` and ``coin_insurgency`` are on (it
    reads C1's anchors + cache health), before turn 1, or off the BLUE plan pass.
    """
    if not getattr(game.settings, "coin_reinfiltration", False) or not getattr(
        game.settings, "coin_insurgency", False
    ):
        # Mid-campaign toggle-off: abort the live attempt so its cell/cache TGOs
        # aren't stranded near the target forever.
        state = getattr(game, "coin_state", None)
        rf = state.get("reinfiltration") if isinstance(state, dict) else None
        if isinstance(rf, dict) and rf.get("active"):
            attempt = rf["active"]
            _abort_attempt(
                game,
                rf,
                events,
                _tgo_by_id(game, attempt.get("cell_tgo")),
                _tgo_by_id(game, attempt.get("cache_tgo")),
            )
        return
    if getattr(game, "turn", 0) < 1:
        return

    state = _ensure_anchors(game)
    if state is None:
        return
    rf = state.setdefault("reinfiltration", {"cooldown": 0, "active": None})

    if rf.get("cooldown", 0) > 0:
        rf["cooldown"] -= 1
        return

    if rf.get("active"):
        _advance_active_attempt(game, state, rf, events)
    else:
        _try_start_attempt(game, state, rf, events)


def _advance_active_attempt(
    game: "Game", state: dict[str, Any], rf: dict[str, Any], events: Any
) -> None:
    attempt = rf["active"]
    target = _cp_by_id(game, attempt["cp_id"])
    source = _cp_by_id(game, attempt["source_id"])
    cell = _tgo_by_id(game, attempt.get("cell_tgo"))

    # Abort conditions (any stage): the target is now genuinely held, the cell is
    # dead, or the source/target disappeared. Holding ground works without a shot.
    if target is None or source is None or target.captured.is_red:
        # target vanished or already red -- clean up quietly.
        _abort_attempt(
            game, rf, events, cell, _tgo_by_id(game, attempt.get("cache_tgo"))
        )
        return
    if _garrison_count(target) > HOLD_THRESHOLD:
        _announce(
            game,
            events,
            f"Infiltration near {target.name} abandoned — position secured.",
        )
        _abort_attempt(
            game, rf, events, cell, _tgo_by_id(game, attempt.get("cache_tgo"))
        )
        return
    if cell is None or not _tgo_alive(cell):
        _announce(game, events, f"Infiltration cell near {target.name} eliminated.")
        _abort_attempt(
            game, rf, events, None, _tgo_by_id(game, attempt.get("cache_tgo"))
        )
        return

    if attempt["stage"] == 1:
        attempt["turns"] += 1
        if attempt["turns"] >= STAGE1_TURNS:
            cache = _spawn_cache(game, source, target, cell, events)
            if cache is not None:
                attempt["cache_tgo"] = str(cache.id)
                attempt["stage"] = 2
                attempt["turns"] = 0
                _announce(
                    game,
                    events,
                    f"Infiltrators are established near {target.name} — a supply cache has been located.",
                )
        return

    # Stage 2: killing the cache knocks the attempt back to stage 1.
    cache = _tgo_by_id(game, attempt.get("cache_tgo"))
    if cache is None or not _tgo_alive(cache):
        attempt["stage"] = 1
        attempt["turns"] = 0
        attempt["cache_tgo"] = None
        _announce(
            game,
            events,
            f"Insurgent cache near {target.name} destroyed — infiltrators fall back.",
        )
        return
    attempt["turns"] += 1
    if attempt["turns"] >= STAGE2_TURNS:
        # Re-validate the start-time invariants at flip time: the theater may
        # have changed over the ~4-turn pipeline. The conservation bound (red
        # CP count never exceeds turn 0) can be re-reached by an in-mission red
        # capture, and the player may have since based a squadron at the target
        # (the §36 player-field exclusion).
        red_now = sum(1 for cp in game.theater.controlpoints if cp.captured.is_red)
        if red_now >= state.get("_red_cp_turn0", red_now) or str(
            target.id
        ) in _player_field_ids(game):
            _announce(
                game,
                events,
                f"Infiltration near {target.name} abandoned — the cells disperse.",
            )
            _abort_attempt(game, rf, events, cell, cache)
            return
        _flip(game, state, rf, target, source, cell, cache, events)


def _try_start_attempt(
    game: "Game", state: dict[str, Any], rf: dict[str, Any], events: Any
) -> None:
    pair = _best_target(game, state)
    if pair is None:
        return
    target, source = pair
    cell = _spawn_cell(game, source, target, events)
    if cell is None:
        return
    rf["active"] = {
        "cp_id": str(target.id),
        "source_id": str(source.id),
        "stage": 1,
        "turns": 0,
        "cell_tgo": str(cell.id),
        "cache_tgo": None,
    }
    _announce(game, events, f"Intel: infiltration reported near {target.name}.")


def _best_target(
    game: "Game", state: dict[str, Any]
) -> Optional[tuple["ControlPoint", "ControlPoint"]]:
    """The best (target, source) infiltration pair, or None. Prefers formerly-red
    CPs (retaking home turf), then the eligible CP nearest a live stronghold."""
    from game.theater import ControlPoint

    red_now = sum(1 for cp in game.theater.controlpoints if cp.captured.is_red)
    if red_now >= state.get("_red_cp_turn0", red_now):
        return None  # conservation: relocate, never grow

    sources = [
        cp
        for cp in game.theater.controlpoints
        if cp.captured.is_red
        and cache_health(cp, state.get(str(cp.id), {}).get("cache_total", 0))
        >= SOURCE_HEALTH_GATE
    ]
    if not sources:
        return None

    excluded = _player_field_ids(game)
    candidates: list[tuple[bool, float, "ControlPoint", "ControlPoint"]] = []
    for cp in game.theater.controlpoints:
        if cp.captured.is_red:
            continue
        if not (cp.captured.is_blue or cp.captured.is_neutral):
            continue
        if getattr(cp, "is_fleet", False) or getattr(cp, "is_carrier", False):
            continue
        # Off-map spawns can never be captured (their capture() raises), so an
        # attempt against one would crash finish_turn at flip time.
        from game.theater.controlpoint import OffMapSpawn

        if isinstance(cp, OffMapSpawn):
            continue
        if str(cp.id) in excluded:
            continue
        if _garrison_count(cp) > HOLD_THRESHOLD:
            continue
        nearest = min(sources, key=lambda s: cp.position.distance_to_point(s.position))
        dist = cp.position.distance_to_point(nearest.position)
        if dist > INFILTRATION_RANGE_M:
            continue
        formerly_red = bool(state.get(str(cp.id)))  # had a C1 anchor => was red
        candidates.append((not formerly_red, dist, cp, nearest))

    if not candidates:
        return None
    candidates.sort(key=lambda c: (c[0], c[1]))  # formerly-red first, then nearest
    _, _, target, source = candidates[0]
    return target, source


def _flip(
    game: "Game",
    state: dict[str, Any],
    rf: dict[str, Any],
    target: "ControlPoint",
    source: "ControlPoint",
    cell: Any,
    cache: Any,
    events: Any,
) -> None:
    """Flip the target CP to RED: engine-native capture, then re-anchor it weak from
    the seeded cell + cache (reparented) and a small commissioned garrison."""
    from game.ato.flighttype import FlightType  # noqa: F401  (import warms game pkg)
    from game.theater.controlpoint import ControlPoint  # noqa: F401

    player_red = game.red.player
    if events is not None:
        target.capture(game, events, player_red)
    else:  # headless probe path
        target._coalition = game.red

    # Reparent the infiltration cell + cache so the new stronghold owns them (and they
    # render RED now the CP is red); commission a weak garrison from the C1 pool. They
    # stop being transient spawns here -- the cell IS the new stronghold's militia and
    # the cache its first cache, so the fresh anchor below must count them.
    for tgo in (cell, cache):
        _reparent(source, target, tgo, events)
        if tgo is not None:
            tgo.coin_spawned = False
    pool = regen_unit_pool(game.red)
    if pool:
        for i in range(REINFIL_GARRISON):
            target.base.commission_units({pool[i % len(pool)]: 1})

    # Fresh weak anchor: C1 now refills this CP toward the small garrison + one cache.
    state[str(target.id)] = _snapshot(target)
    rf["active"] = None
    rf["cooldown"] = COOLDOWN_TURNS
    rf.setdefault("pending_flips", 0)
    rf["pending_flips"] += 1  # consumed by the next update_political_will
    _announce(game, events, f"{target.name} has fallen to the insurgency.")


def consume_reinfiltration_flips(game: "Game") -> int:
    """Number of re-infiltration flips since the last call, cleared to zero.

    The will layer calls this to charge a flip as a lost base -- a ``finish_turn``
    flip never appears in the debriefing's in-mission ``bases_lost`` count.
    """
    state = getattr(game, "coin_state", None)
    if not isinstance(state, dict):
        return 0
    rf = state.get("reinfiltration")
    if not isinstance(rf, dict):
        return 0
    flips = int(rf.get("pending_flips", 0))
    rf["pending_flips"] = 0
    return flips


def _abort_attempt(
    game: "Game", rf: dict[str, Any], events: Any, cell: Any, cache: Any
) -> None:
    for tgo in (cell, cache):
        _despawn(game, tgo, events)
    rf["active"] = None
    rf["cooldown"] = COOLDOWN_TURNS


def _spawn_cell(
    game: "Game", source: "ControlPoint", target: "ControlPoint", events: Any
) -> Any:
    """A small red ground cell near *target*, attached to the red *source* stronghold
    (so it renders RED -- TGO allegiance follows its parent CP), trimmed to a cell and
    re-typed to insurgent kit (an armed technical + infantry, not the faction armor)."""
    from game.data.groups import GroupTask

    unit_types = cell_unit_types(game)
    tgo = _spawn_red_ground(
        game,
        source,
        target,
        GroupTask.FRONT_LINE,
        events,
        sidc_override=CELL_SIDC,
        max_units=CELL_MAX_UNITS,
        unit_types=unit_types,
        concealed=True,
    )
    if tgo is None:
        tgo = _spawn_red_ground(
            game,
            source,
            target,
            GroupTask.BASE_DEFENSE,
            events,
            sidc_override=CELL_SIDC,
            max_units=CELL_MAX_UNITS,
            unit_types=unit_types,
            concealed=True,
        )
    return tgo


def _spawn_cache(
    game: "Game", source: "ControlPoint", target: "ControlPoint", near: Any, events: Any
) -> Any:
    from game.data.groups import GroupTask

    return _spawn_red_ground(game, source, target, GroupTask.AMMO, events)


def _spawn_red_ground(
    game: "Game",
    source: "ControlPoint",
    target: "ControlPoint",
    task: Any,
    events: Any,
    sidc_override: Optional[tuple[SymbolSet, Entity]] = None,
    max_units: Optional[int] = None,
    unit_types: Optional[list[Any]] = None,
    concealed: bool = False,
) -> Any:
    """Generate a red ForceGroup for *task* at a point near *target*, attached to the
    red *source* CP. Returns the TGO or None if the faction has no group for the task.
    """
    point = _infiltration_point(game, source, target)
    return spawn_red_ground_at(
        game,
        source,
        point,
        task,
        events,
        max_units=max_units,
        sidc_override=sidc_override,
        unit_types=unit_types,
        concealed=concealed,
    )


def spawn_red_ground_at(
    game: "Game",
    red_cp: "ControlPoint",
    point: Any,
    task: Any,
    events: Any,
    max_units: Optional[int] = None,
    sidc_override: Optional[tuple[SymbolSet, Entity]] = None,
    unit_types: Optional[list[Any]] = None,
    concealed: bool = False,
) -> Any:
    """Generate a red ForceGroup for *task* at *point*, attached to the red *red_cp*
    (whose ownership gives the TGO its RED allegiance -- a TGO renders as its parent
    CP's coalition). Optionally trim to *max_units*. Returns the TGO or None.

    Shared by C1.5 re-infiltration (a cell/cache near a target) and the roadside-IED
    layer (an emplacement on the ratline); the caller supplies the point + red CP.

    *sidc_override* re-points the map *symbol* (a ``(SymbolSet, Entity)`` pair, e.g.
    :data:`CELL_SIDC` / :data:`IED_SIDC` / :data:`HVT_SIDC`) so the spawned object
    renders as its real NATO symbol rather than the vehicle-group default of a tank
    platoon. ``None`` keeps the class default.

    *unit_types* re-points the actual DCS *unit types* of the trimmed group (see
    :func:`_retype_units`) so the metal under the symbol matches the fiction -- a lone
    supply truck for an IED, a leader's jeep + rifles for an HVT -- instead of the
    faction's default front-line kit. An empty/``None`` list leaves the generated
    units as-is.

    *concealed* marks the TGO so that, while un-reconned, the player map shows a
    jittered "in here somewhere" uncertainty circle instead of an exact marker
    (built in the server TGO model); recon/attack discovery snaps it to the real
    position. Used by the hidden COIN objects (IED/VBIED, HVT, cells) -- a cache
    is infrastructure and stays exact.
    """
    from game.naming import namegen
    from game.theater import PresetLocation
    from game.utils import Heading

    group = game.red.armed_forces.random_group_for_task(task)
    if group is None:
        return None
    heading = game.theater.heading_to_conflict_from(point) or Heading.from_degrees(0)
    location = PresetLocation(namegen.random_objective_name(), point, heading)
    tgo = group.generate(location.original_name, location, red_cp, game, task)
    if sidc_override is not None:
        tgo.sidc_entity_override = sidc_override
    tgo.concealed = concealed
    # Transient COIN spawns (HVT convoy, IED security team, infiltration/field
    # cells) have their own lifecycle; they never count toward -- nor are revived
    # by -- the C1 anchor machinery (_alive_cell_count/_revivable_units). A
    # reinfiltration flip clears the flag when the cell becomes the new
    # stronghold's militia.
    tgo.coin_spawned = True
    red_cp.connected_objectives.append(tgo)
    game.db.tgos.add(tgo.id, tgo)
    if max_units is not None:
        _trim_to(tgo, max_units)
    if unit_types:
        _retype_units(tgo, unit_types)
    if events is not None:
        events.update_tgo(tgo)
    return tgo


def _infiltration_point(
    game: "Game", source: "ControlPoint", target: "ControlPoint"
) -> Any:
    """A land point a few km off the target toward the source (the cell sits between
    the stronghold and the base it is infiltrating)."""
    hdg = target.position.heading_between_point(source.position)
    for dist in (6000.0, 3000.0, 1500.0, 0.0):
        point = target.position.point_from_heading(hdg, dist)
        if dist == 0.0 or game.theater.is_on_land(point):
            return point
    return target.position


def _reparent(
    source: "ControlPoint", target: "ControlPoint", tgo: Any, events: Any
) -> None:
    if tgo is None:
        return
    if tgo in source.connected_objectives:
        source.connected_objectives.remove(tgo)
    tgo.control_point = target
    if tgo not in target.connected_objectives:
        target.connected_objectives.append(tgo)
    if events is not None:
        events.update_tgo(tgo)


def _despawn(game: "Game", tgo: Any, events: Any) -> None:
    if tgo is None:
        return
    cp = getattr(tgo, "control_point", None)
    if cp is not None and tgo in cp.connected_objectives:
        cp.connected_objectives.remove(tgo)
    try:
        game.db.tgos.remove(tgo.id)
    except Exception:  # noqa: BLE001 -- best-effort cleanup, never break the turn
        pass
    if events is not None:
        try:
            # delete_tgo takes the TGO's id, not the object -- passing the object
            # poisons GameUpdateEventsJs serialization and drops the SSE stream.
            events.delete_tgo(tgo.id)
        except Exception:  # noqa: BLE001
            pass


def _trim_to(tgo: Any, max_units: int) -> None:
    """Keep at most *max_units* units across the TGO's groups (a cell, not a garrison)."""
    kept = 0
    for group in list(getattr(tgo, "groups", [])):
        units = list(getattr(group, "units", []))
        for unit in units:
            if kept < max_units:
                kept += 1
            else:
                group.units.remove(unit)


def _retype_units(tgo: Any, dcs_types: list[Any]) -> None:
    """Re-point the surviving units' DCS *types* (and display names) to *dcs_types*,
    cycling if the group holds more units than the composition lists.

    The COIN objects are all generated as trimmed FRONT_LINE/BASE_DEFENSE force groups
    (the faction's armor/technicals) with only the map *symbol* overridden. Everything
    downstream -- mission generation, threat rings, recon fog, loss accounting, the
    tooltip -- reads ``TheaterUnit.type``, so swapping the type here fully re-skins the
    group to the fiction (a device truck, a leader's jeep, an insurgent technical). An
    empty list is a no-op, so a faction that can't fill the roles keeps its generated
    group rather than crashing.
    """
    if not dcs_types:
        return
    index = 0
    for group in getattr(tgo, "groups", []):
        for unit in getattr(group, "units", []):
            new_type = dcs_types[index % len(dcs_types)]
            unit.type = new_type
            new_name = getattr(new_type, "name", None) or getattr(new_type, "id", None)
            if new_name:
                unit.name = new_name
            index += 1
    # The generated group cached a threat polygon from the old (armor) types; drop it so
    # the soft re-typed kit no longer projects a phantom ring. Best-effort.
    try:
        tgo.invalidate_threat_poly()
    except Exception:  # noqa: BLE001 -- lazy threat cache; never break the turn
        pass


def _pick_faction_unit(
    rosters: list[Any],
    *,
    classes: Optional[frozenset[UnitClass]] = None,
    name_hints: tuple[str, ...] = (),
    max_price: Optional[int] = None,
) -> Any:
    """The best-matching unit's DCS type from *rosters* (an ordered list of the red
    faction's unit sets), or ``None`` when nothing fits.

    A ``name_hints`` match wins (so we can prefer, e.g., the DShK gun-truck over a plain
    pickup); otherwise the cheapest eligible class match, deterministic by (price, name).
    Anti-air kit is always excluded -- an IED or a leader team is never a SAM/AAA piece.
    Selecting from the faction's own resolved roster means we only ever return a unit the
    campaign actually loaded (no hardcoded, possibly-unregistered DCS ids).
    """
    from game.data.units import ANTI_AIR_UNIT_CLASSES

    candidates: list[Any] = []
    for roster in rosters:
        candidates.extend(sorted(roster, key=lambda u: u.variant_id))

    def eligible(u: Any) -> bool:
        if u.unit_class in ANTI_AIR_UNIT_CLASSES:
            return False
        if max_price is not None and getattr(u, "price", 0) > max_price:
            return False
        if classes is not None and u.unit_class not in classes:
            return False
        return True

    for hint in name_hints:
        for u in candidates:
            if eligible(u) and hint.lower() in u.variant_id.lower():
                return u.dcs_unit_type
    matches = sorted(
        (u for u in candidates if eligible(u)),
        key=lambda u: (getattr(u, "price", 0), u.variant_id),
    )
    return matches[0].dcs_unit_type if matches else None


def _red_faction(game: "Game") -> Any:
    """The red faction, or ``None`` -- so the composition builders degrade to an empty
    list (keep the generated group) for a headless/fake game with no coalition."""
    return getattr(getattr(game, "red", None), "faction", None)


def _infantry_type(faction: Any) -> Any:
    """A rifleman -- the insurgent AK, else any non-crew-served infantry."""
    return _pick_faction_unit(
        [getattr(faction, "infantry_units", ())],
        classes=frozenset({UnitClass.INFANTRY}),
        name_hints=("insurgent", "ak", "rifle"),
    )


def _technical_type(faction: Any) -> Any:
    """An armed gun-truck for a fighting cell: an MG-mounted technical first, else any
    cheap IFV/APC-classed technical (price-capped like the C1 whitelist so a real IFV is
    never picked)."""
    return _pick_faction_unit(
        [getattr(faction, "frontline_units", ())],
        classes=frozenset({UnitClass.IFV, UnitClass.APC}),
        name_hints=("dshk", "kord", "scout", "technical", "toyota"),
        max_price=REGEN_MAX_UNIT_PRICE,
    )


def _jeep_type(faction: Any) -> Any:
    """A leader's light vehicle: a jeep/UAZ, else any soft logistics vehicle."""
    return _pick_faction_unit(
        [
            getattr(faction, "logistics_units", ()),
            getattr(faction, "frontline_units", ()),
        ],
        name_hints=("uaz", "jeep", "luv", "buggy", "pickup"),
    )


def _truck_type(faction: Any) -> Any:
    """A soft supply truck -- the device vehicle on the road; falls back to a jeep."""
    return _pick_faction_unit(
        [getattr(faction, "logistics_units", ())],
        name_hints=("truck", "ural", "kamaz", "zil", "cargo"),
    ) or _jeep_type(faction)


def ied_unit_types(game: "Game") -> list[Any]:
    """Fiction kit for a *mobile* VBIED: a lone soft vehicle (a suspected suicide
    truck), so the device is findable and killable but not a combat platoon. Empty when
    the faction has no light vehicle at all (the group then keeps its generated units).
    """
    faction = _red_faction(game)
    if faction is None:
        return []
    device = _truck_type(faction) or _infantry_type(faction)
    return [device] if device is not None else []


def ied_emplacement_unit_types(game: "Game") -> list[Any]:
    """Fiction kit for a *static* roadside IED: the emplaced device itself -- a roadside
    barrel **static object** (vanilla DCS, faction-independent, so this never degrades)
    -- plus a two-man security team dug in around it from the faction's own infantry.
    Killing the device clears the bomb; the team is texture and local defense, not the
    objective (see ``coin_ied._ied_intact``)."""
    from dcs.statics import Fortification

    comp: list[Any] = [Fortification.Oil_Barrel]
    faction = _red_faction(game)
    if faction is not None:
        rifle = _infantry_type(faction)
        if rifle is not None:
            comp.extend([rifle, rifle])
    return comp


def hvt_unit_types(game: "Game") -> list[Any]:
    """Fiction kit for a high-value target: a small **convoy** -- the leader's command
    vehicle, an armed technical escort, and a rifle pair (up to four units, matching
    ``HVT_UNITS``). The leader moves with a guard detail, so hunting him reads as running
    down a small column, not a lone jeep."""
    faction = _red_faction(game)
    if faction is None:
        return []
    leader = _jeep_type(faction) or _truck_type(faction)
    escort = _technical_type(faction)
    rifle = _infantry_type(faction)
    comp: list[Any] = []
    if leader is not None:
        comp.append(leader)
    if escort is not None:
        comp.append(escort)
    if rifle is not None:
        comp.extend([rifle, rifle])
    return comp


def cell_unit_types(game: "Game") -> list[Any]:
    """Fiction kit for an insurgent cell (C1.5 re-infiltration + C4 dispersed): an armed
    technical plus infantry; falls back to whatever soft kit exists, else empty (keep the
    generated group)."""
    faction = _red_faction(game)
    if faction is None:
        return []
    tech = _technical_type(faction)
    rifle = _infantry_type(faction)
    comp: list[Any] = []
    if tech is not None:
        comp.append(tech)
    if rifle is not None:
        comp.append(rifle)
    if not comp:
        fallback = _jeep_type(faction)
        if fallback is not None:
            comp.append(fallback)
    return comp


def _garrison_count(cp: "ControlPoint") -> int:
    """BLUE (or the CP owner's) ground-unit strength holding the CP: front-line armor
    plus alive vehicle-TGO units. Neutral CPs have none."""
    if cp.captured.is_neutral:
        return 0
    tgo_units = sum(
        1
        for tgo in cp.ground_objects
        if getattr(tgo, "category", None) != "ammo"
        for unit in tgo.units
        if getattr(unit, "alive", False) and getattr(unit, "is_vehicle", False)
    )
    return int(getattr(cp.base, "total_armor", 0)) + tgo_units


def _player_field_ids(game: "Game") -> set[str]:
    """CP ids that host a based BLUE squadron -- the §36 anti-grief exclusion applied
    to ground (never infiltrate a field the human operates from)."""
    excluded: set[str] = set()
    for cp in game.theater.controlpoints:
        if not cp.captured.is_blue:
            continue
        if any(True for _ in getattr(cp, "squadrons", [])):
            excluded.add(str(cp.id))
    return excluded


def _cp_by_id(game: "Game", cp_id: Optional[str]) -> Optional["ControlPoint"]:
    if cp_id is None:
        return None
    for cp in game.theater.controlpoints:
        if str(cp.id) == cp_id:
            return cp
    return None


def _tgo_by_id(game: "Game", tgo_id: Optional[str]) -> Any:
    if tgo_id is None:
        return None
    for cp in game.theater.controlpoints:
        for tgo in cp.ground_objects:
            if str(tgo.id) == tgo_id:
                return tgo
    return None


def _tgo_alive(tgo: Any) -> bool:
    return any(getattr(unit, "alive", False) for unit in getattr(tgo, "units", []))


def _announce(game: "Game", events: Any, message: str) -> None:
    """Push an intel line to the Information feed (client events + SITREP). Best-effort:
    a fake game in a unit test may not carry the feed."""
    try:
        game.message("Re-infiltration", message)
    except Exception:  # noqa: BLE001 -- messaging is best-effort, never break the turn
        pass
