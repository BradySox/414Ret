"""Ambient supply convoys -- a few real columns on the roads, both sides, every mission.

The standardization pass on the §50 convoy layer (squadron call 2026-07-06: "convoys
present in every miz on both blue and red side ... a few convoys per side, some on the
same route, some on different routes, randomized"). Where the §35 trail top-up is
red-only, Vietnam-framed, and budget-driven, and the old §50 blue top-up existed only to
feed the ambush, this layer is the generic background: every turn each side's convoy flow
is topped up to a small **randomized** target on **randomly chosen** same-side road
corridors -- repeats allowed, so two columns sometimes share a road and sometimes spread
out. The roads simply have traffic now.

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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from game.theater import ControlPoint

#: Per side, per turn: the convoy flow is topped up to randint(MIN, MAX) concurrent
#: columns. Never forced -- a side already running that many (organic transfers, the §35
#: trail) gets nothing extra, and a low roll leaves the roads quiet this turn.
MIN_AMBIENT_CONVOYS = 1
MAX_AMBIENT_CONVOYS = 3

#: Real ground units per ambient column -- reads as a column on the road, never a parade.
AMBIENT_CONVOY_UNITS = 8

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

    for _ in range(deficit):
        # Uniform pick WITH repeats: some columns share a road, some spread out --
        # exactly the randomized texture asked for, no distinct-road forcing here.
        source, destination = _RNG.choice(corridors)
        # Skim-only (2026-07-07 design call): relocate units that ALREADY EXIST in the
        # rear base -- no free commissioning. ``new_transfer`` debits the source
        # immediately, so re-picking a source in this loop reads its live (reduced)
        # stock; a source too thin to skim (< 2 armor) yields no column this turn. The
        # generic ambient layer must not inflate both armies for free; the §35 Vietnam
        # trail keeps its own documented external-supply seeding, which this never calls.
        units = _skim_units(source, AMBIENT_CONVOY_UNITS)
        if not units:
            continue
        coalition.transfers.new_transfer(
            TransferOrder(source, destination, units), game.conditions.start_time
        )


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
