"""Ambient supply convoys -- a few real columns on the roads, both sides, every mission.

The standardization pass on the §50 convoy layer (squadron call 2026-07-06: "convoys
present in every miz on both blue and red side ... a few convoys per side, some on the
same route, some on different routes, randomized"). Where the §35 trail top-up is
red-only, Vietnam-framed, and budget-driven, and the old §50 blue top-up existed only to
feed the ambush, this layer is the generic background: every turn each side's convoy flow
is topped up to a small **randomized** target on **randomly chosen DISTINCT** same-side
road corridors -- one column per road, so a side runs at most as many as it has roads and
which roads carry traffic varies turn to turn. The roads simply have traffic now.

(The columns ride *distinct* roads rather than the originally-sketched "repeats allowed,
some share a road" because the convoy map keys transports by ``(origin, destination)`` --
two transfers on one corridor coalesce into a single oversized group that line-spawns into
unauthored positions and deadlocks at mission start, the flown S5 regression. Shared-road
columns were never actually two columns; they were one parked blob.)

Everything is the engine's own convoy machinery (the §35/§37 no-phantom-spawn
discipline): each column is a real ``coalition.transfers`` transfer that spawns as a
road-moving group, is a native Armed Recon / BAI target, and reconciles its losses at
debrief (killed units never arrive). The §50 ambush chance rolls over blue's convoys
whatever created them, so ambient blue columns are ambushable like any other; red's
columns are the player's interdiction targets. The §35 Vietnam trail top-up composes: it
runs first and counts toward the ambient target, so a Vietnam campaign's trail war is
unchanged and ambience only adds columns where the budget still has room.

**Skim-only -- no free unit seeding (2026-07-07 design call).** Ambient columns
**relocate units that already exist** in a rear base; they do *not* commission free ones.
The §35 Vietnam trail keeps its documented external-supply seeding (matériel from
China/the USSR -- red-only, Vietnam-gated, its historical character), but generalizing
that free-seed to every campaign on both sides would inject un-budgeted reinforcements
into both armies every turn -- a firehose the squadron asked for *traffic*, not for. So a
rear base too thin to skim simply yields no column this turn: the roads carry traffic
wherever the economy supports it and stay quiet where it doesn't, and the engine's organic
convoys still serve.

Runs once per turn from ``Game.finish_turn`` (after the §35 top-up, before the §50 ambush
seeding). Gated by ``ambient_supply_convoys`` (default ON -- the §49 kill-switch
precedent). Fully guarded: a side with no same-side road corridor (island maps, all-red
graphs) is a silent no-op, and the engine's organic convoys still serve.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from game.theater import ControlPoint

#: Per side, per turn: the convoy flow is topped up to randint(MIN, MAX) concurrent
#: columns, further capped at the side's distinct-corridor count (one column per road).
#: Never forced -- a side already running that many (organic transfers, the §35 trail)
#: gets nothing extra, and a low roll leaves the roads quiet this turn.
MIN_AMBIENT_CONVOYS = 1
MAX_AMBIENT_CONVOYS = 3

#: Real ground units per ambient column -- reads as a column on the road, never a parade.
AMBIENT_CONVOY_UNITS = 8

#: Garrison-skim fallback floors (BLUE only; the 2026-07-18 audit's §50 call).
#: COIN blue laydowns hold their whole force as TGO garrisons (``Base.armor`` = 0),
#: which silently disabled ambient blue columns — and with them the §50 ambush — on
#: exactly the two campaigns that preseed it (measured: ZERO blue convoys in 33
#: self-played turns on ER/IR). When the stock skim comes up empty, a few garrison
#: vehicles move INTO the base's stock so the normal skim path can run: real units,
#: conservation exact (a mapped unit leaves its group as a stock unit appears), and
#: the base stays defensible — the CP keeps at least this many garrison vehicles...
GARRISON_SKIM_FLOOR = 6
#: ...and every group keeps at least this many alive (no group visually empties).
GARRISON_SKIM_GROUP_KEEP = 2

#: The dice. Module-level so tests can substitute a deterministic stand-in.
_RNG = random.Random()


def ensure_ambient_convoys(game: "Game") -> None:
    """Top BOTH sides' convoy flow up to this turn's randomized ambient target.

    No-op unless ``ambient_supply_convoys`` is on. Idempotent per turn: each side gets at
    most (rolled target - currently flowing) new columns, so organic transfers and the
    §35 trail convoys count toward the ambience rather than stacking on top of it.
    """
    if not getattr(game.settings, "ambient_supply_convoys", False):
        return
    if game.turn < 1:
        return
    for coalition in (game.blue, game.red):
        _top_up_side(game, coalition)


def _top_up_side(game: "Game", coalition: "Coalition") -> None:
    from game.fourteenth.vietnam_convoy import _skim_units
    from game.transfers import TransferOrder

    corridors = _same_side_corridors(game, coalition)
    if not corridors:
        return

    target = _RNG.randint(MIN_AMBIENT_CONVOYS, MAX_AMBIENT_CONVOYS)
    deficit = target - len(list(coalition.transfers.convoys))
    if deficit <= 0:
        return

    # DISTINCT roads, one transfer per corridor per turn (2026-07-07 S5 fix). The convoy
    # map keys transports by ``(origin, destination)`` (``TransportMap.add`` in
    # ``game/transfers.py``), so two transfers on the SAME corridor coalesce into ONE
    # group -- and a large merged column line-spawns into unauthored positions and
    # deadlocks at mission start (the flown S5 regression: a 24-vehicle blue column
    # parked at Baghdad and never moved, which also blocked the §50 ambush spring).
    # Sampling *distinct* corridors caps a side at its road count and keeps every column a
    # separate, driveable group -- so "two columns" means two roads, never one merged
    # blob. (This does trade away the earlier "repeats allowed, some share a road" texture,
    # which the merge made unachievable anyway -- shared-road columns were the deadlock.)
    picks = _RNG.sample(corridors, min(deficit, len(corridors)))

    for source, destination in picks:
        # Skim-only (2026-07-07 design call): relocate units that ALREADY EXIST in the
        # rear base -- no free commissioning. ``new_transfer`` debits the source
        # immediately (so two distinct corridors sharing a rear hub read its live,
        # reduced stock); a source too thin to skim (< 2 armor) yields no column this
        # turn. The generic ambient layer must not inflate both armies for free; the §35
        # Vietnam trail keeps its own documented external-supply seeding, not called here.
        units = _skim_units(source, AMBIENT_CONVOY_UNITS)
        if not units and coalition is game.blue:
            # BLUE garrison-skim fallback (2026-07-18 audit call): move a few
            # garrison vehicles into the stock, then skim normally. Blue-only —
            # red's militia is the C1-anchored insurgency (regen would just be
            # asked to refill what this drained), and §35 already feeds red's
            # flow. The 2x covers the skim's half-take (MAX_SOURCE_FRACTION).
            if _garrison_to_stock(source, AMBIENT_CONVOY_UNITS * 2):
                units = _skim_units(source, AMBIENT_CONVOY_UNITS)
        if not units:
            continue
        coalition.transfers.new_transfer(
            TransferOrder(source, destination, units), game.conditions.start_time
        )


def _garrison_to_stock(cp: "ControlPoint", needed: int) -> int:
    """Move up to ``needed`` alive garrison vehicles into ``Base.armor``; return
    the count moved.

    Real units only, conservation exact: each moved vehicle leaves its theater
    group (despawned WITHOUT a kill — it drove off to form the column, it did
    not die) as one stock unit of the same type appears. Guards keep the base
    defensible: the CP keeps ≥ ``GARRISON_SKIM_FLOOR`` garrison vehicles in
    total, every group keeps ≥ ``GARRISON_SKIM_GROUP_KEEP`` alive, and
    ``coin_spawned`` / ``user_placed`` / ``map_hidden`` groups are never
    touched. Unmapped unit types (no ``GroundUnitType``) are skipped."""
    eligible: list[tuple[Any, Any, Any]] = []
    total_alive = 0
    for tgo in getattr(cp, "connected_objectives", None) or ():
        if getattr(tgo, "category", None) != "armor":
            continue
        if getattr(tgo, "coin_spawned", False) or getattr(tgo, "user_placed", False):
            continue
        if getattr(tgo, "map_hidden", False):
            continue
        for group in getattr(tgo, "groups", []):
            alive = [
                unit
                for unit in group.units
                if getattr(unit, "alive", False) and getattr(unit, "is_vehicle", False)
            ]
            total_alive += len(alive)
            for unit in alive[GARRISON_SKIM_GROUP_KEEP:]:
                eligible.append((tgo, group, unit))
    budget = min(needed, total_alive - GARRISON_SKIM_FLOOR)
    if budget <= 0:
        return 0
    moved = 0
    for tgo, group, unit in eligible:
        if moved >= budget:
            break
        try:
            unit_type = unit.unit_type
        except StopIteration:
            continue  # no registered GroundUnitType -- can't ride a transfer
        group.units.remove(unit)
        cp.base.commission_units({unit_type: 1})
        tgo.invalidate_threat_poly()
        moved += 1
    return moved


def _same_side_corridors(
    game: "Game", coalition: "Coalition"
) -> list[tuple["ControlPoint", "ControlPoint"]]:
    """Every same-side road corridor, oriented rear -> front (source, destination).

    Enumerates each ``convoy_routes`` edge linking two of *coalition*'s control points
    once, and points the flow at the end nearer the fighting (fronts, or the opposing
    CPs on a front-less laydown -- the shared §35 reference). [] when the side has no
    road between two of its own bases, or there is no war to supply toward.
    """
    from game.fourteenth.vietnam_convoy import _reference_points

    reference = _reference_points(game, coalition)
    if not reference:
        return []

    def distance_to_front(cp: "ControlPoint") -> float:
        return min(point.distance_to_point(cp.position) for point in reference)

    corridors: list[tuple["ControlPoint", "ControlPoint"]] = []
    seen: set[tuple[str, str]] = set()
    for cp in game.theater.controlpoints:
        if cp.captured != coalition.player:
            continue
        for other in cp.convoy_routes.keys():
            if other.captured != coalition.player:
                continue
            a, b = str(cp.name), str(other.name)
            key = (a, b) if a <= b else (b, a)
            if key in seen:
                continue
            seen.add(key)
            if distance_to_front(cp) <= distance_to_front(other):
                corridors.append((other, cp))
            else:
                corridors.append((cp, other))
    return corridors
