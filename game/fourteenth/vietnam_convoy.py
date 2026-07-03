"""Vietnam Ops convoy interdiction -> real, tracked enemy convoys (§35).

The Steel Tiger / Ho Chi Minh Trail interdiction feature used to spawn a *phantom*
truck column at runtime (``coalition.addGroup`` in the ``vietnamops`` plugin). Those
trucks existed only inside the generated ``.miz`` -- Retribution's force model and
debrief never knew about them, so killing the convoy cost the enemy nothing (a "free,
non-existent unit"). This module replaces that with the engine's *real* convoy system.

Retribution already models convoys: ``coalition.transfers.convoys`` carry actual ground
units between control points, spawn as road-moving groups (``ConvoyGenerator``), are
already Armed-Recon / BAI targets (``ObjectiveFinder.convoys``), and their destruction is
recorded (``Debriefing.dead_ground_units`` -> ``enemy_convoy``) so the transferred units
never arrive. So the fix is: don't invent a convoy -- make sure a *real* one is flowing on
the trail.

``ensure_enemy_trail_convoy`` runs once per turn (from ``finish_turn``, after the AI's own
transfer processing). When ``vietnam_convoy_interdiction`` is on and the opfor is running
fewer than its concurrent-convoy budget, it tops that budget up by moving a few of the
opfor's **real** rear-area ground units forward along a road corridor toward the front. The
units are debited from the origin base (``new_transfer`` -> ``commit_losses``), so this is
genuine force planning: interdict the convoy and those reinforcements never reach the line;
let it through and they do.

**More than one convoy, on distinct roads (2026-07-03 rework).** Several campaigns
(Yankee Station / Steel Tiger's full Ho Chi Minh Trail network, Khe Sanh's two rear feeder
roads, Red Flag 81-2's aggressor corridors) author more than one opfor-to-opfor road. The
original version only ever picked the single best corridor, so raising the convoy cap just
stacked extra columns onto the same road. ``_pick_trail_corridor`` now takes an
``exclude_sources`` set, and the driver loop fills its budget by repeatedly picking the best
*remaining* corridor, excluding sources already committed this call -- so each concurrent
convoy actually rides a different road when the campaign's laydown offers one, and falls
back to re-using a road (via a fresh pick next turn) when it doesn't. A campaign with no
opfor-opfor road at all (no ``supply_routes`` linking two enemy control points -- e.g. an
island chain with no roads between bases) still gets nothing, same as before.

Fully guarded -- if any precondition is missing (no front, no rear units, no road corridor)
it is a no-op and the engine's organic convoys still serve as targets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from game.dcs.groundunittype import GroundUnitType
    from game.theater import ControlPoint

#: Most units a single nudged convoy carries. Small on purpose -- this is a hunt target
#: and a trickle of reinforcements, not a war-winning column -- but bumped 2026-07-03
#: (a flown session's Armed Recon found only 3 vehicles worth chasing) so a found convoy
#: is a meatier kill without approaching a war-winning column.
MAX_CONVOY_UNITS = 6

#: Baseline concurrent convoys the opfor keeps flowing (raised alongside MAX_CONVOY_UNITS,
#: 2026-07-03 -- with it, a campaign whose laydown offers more than one opfor-opfor road
#: (Yankee Station / Steel Tiger's full trail network, Khe Sanh's two rear feeders, Red Flag
#: 81-2's aggressor corridors) actually runs convoys on distinct roads instead of stacking
#: extra columns onto the single busiest one).
BASE_MAX_CONVOYS = 2

#: Under a W6 trail_surge >= 2.0, one more concurrent convoy on top of the baseline.
SURGE_MAX_CONVOYS = 3

#: Never strip a source base below this fraction of its armour; the nudge only ever skims
#: spare rear units, so a source is never gutted to feed the trail.
MAX_SOURCE_FRACTION = 0.5


def ensure_enemy_trail_convoy(game: "Game") -> None:
    """Top the opfor's concurrent trail convoys up to budget when interdiction is enabled.

    No-op unless ``vietnam_convoy_interdiction`` is set. Idempotent per turn by
    construction: it creates at most (budget - currently flowing) new convoys, so calling it
    again (or on a turn where the AI already ordered a transfer) never overshoots the budget.
    Each new convoy prefers a corridor whose source isn't already committed this call, so a
    campaign with more than one opfor-opfor road actually spreads its convoys across them.
    """
    if not game.settings.vietnam_convoy_interdiction:
        return
    if game.turn < 1:
        return

    # The opfor of the (BLUE) human -- the side whose trail the player interdicts.
    coalition = game.red

    # W6 red tempo: an authored phase's trail_surge widens the flow -- one more
    # concurrent column is allowed and each carries a bigger (still capped-source)
    # budget. Baseline (no authored phase / surge 1.0) keeps the base budget.
    from game.fourteenth.red_tempo import trail_surge_multiplier

    surge = trail_surge_multiplier(game)
    max_convoys = SURGE_MAX_CONVOYS if surge >= 2.0 else BASE_MAX_CONVOYS

    active = list(coalition.transfers.convoys)
    deficit = max_convoys - len(active)
    if deficit <= 0:
        return

    # COIN (coin_insurgency): the insurgency has no factories or transfers, so the
    # rear strongholds hold no Base.armor to skim -- the ratline is EXTERNAL
    # support entering at the rear. Seed the source with a small stock of
    # whitelisted irregular kit before skimming (bounded: just enough that the
    # skim fraction yields one convoy load; the remainder is the rear buffer).
    coin = getattr(game.settings, "coin_insurgency", False)
    load = round(MAX_CONVOY_UNITS * surge)

    from game.transfers import TransferOrder

    # Sources already feeding an in-flight convoy -- try a different road first so
    # concurrent convoys spread out rather than stacking on the busiest corridor.
    tried_sources: set["ControlPoint"] = {
        origin for convoy in active if (origin := getattr(convoy, "origin", None))
    }

    created = 0
    while created < deficit:
        corridor = _pick_trail_corridor(
            game,
            coalition,
            allow_empty_source=coin,
            exclude_sources=frozenset(tried_sources),
        )
        if corridor is None:
            return
        source, destination = corridor
        tried_sources.add(
            source
        )  # never repick the same source this call, hit or miss.

        if coin:
            _seed_ratline_source(game, coalition, source, load)
        units = _skim_units(source, load)
        if not units:
            continue  # this source too thin -- try the next-best distinct corridor.

        coalition.transfers.new_transfer(
            TransferOrder(source, destination, units), game.conditions.start_time
        )
        created += 1


def _pick_trail_corridor(
    game: "Game",
    coalition: "Coalition",
    allow_empty_source: bool = False,
    exclude_sources: Optional[frozenset["ControlPoint"]] = None,
) -> Optional[tuple["ControlPoint", "ControlPoint"]]:
    """Pick (source, destination) for the trail convoy: a rear opfor base with spare armour
    feeding the road-connected opfor base nearest the front.

    Mirrors the old emitter's "enemy road nearest the fighting" selection, but resolved on
    the real control-point graph so the transfer produces a real convoy. ``exclude_sources``
    skips corridors whose source is already committed this call, so a campaign with more than
    one opfor-opfor road spreads concurrent convoys across distinct roads instead of always
    picking the single best one. Returns None if no (non-excluded) opfor-to-opfor road
    corridor with a stocked rear source exists.
    """
    # "Toward the fighting": front lines when the campaign has them; on a
    # front-less laydown (the COIN air-assault geometry -- no CP adjacency, no
    # conflicts) fall back to the opposing coalition's control points, so the
    # trail still flows toward where the enemy actually is. No fronts AND no
    # opposing CPs means there is genuinely no war to supply -- no corridor.
    fronts = list(game.theater.conflicts())
    if fronts:
        reference = [front.position for front in fronts]
    else:
        reference = [
            cp.position
            for cp in game.theater.controlpoints
            if cp.captured != coalition.player
            and not getattr(cp.captured, "is_neutral", False)
        ]
    if not reference:
        return None

    def distance_to_front(cp: "ControlPoint") -> float:
        return min(point.distance_to_point(cp.position) for point in reference)

    best: Optional[tuple["ControlPoint", "ControlPoint"]] = None
    best_front_distance = float("inf")
    for cp in game.theater.controlpoints:
        if cp.captured != coalition.player:
            continue
        for other in cp.convoy_routes.keys():
            # Only opfor -> opfor roads (a supply corridor behind the lines); an
            # opfor -> friendly road is the contested front itself.
            if other.captured != coalition.player:
                continue
            # The end nearer the front is the destination; the farther is the source.
            if distance_to_front(cp) <= distance_to_front(other):
                destination, source = cp, other
            else:
                destination, source = other, cp
            if exclude_sources and source in exclude_sources:
                continue
            if source.base.total_armor <= 0 and not allow_empty_source:
                continue
            front_distance = distance_to_front(destination)
            if front_distance < best_front_distance:
                best_front_distance = front_distance
                best = (source, destination)
    return best


def _seed_ratline_source(
    game: "Game", coalition: "Coalition", source: "ControlPoint", load: int
) -> None:
    """Top the rear source up to twice a convoy load with whitelisted units (COIN).

    ``_skim_units`` takes at most :data:`MAX_SOURCE_FRACTION` (half) of the source's
    stock, so a 2x-load stock yields exactly one full convoy and leaves the rest as
    the rear buffer -- stable across cycles, never a growing pile. Free by design
    (the external-support framing, design note §3.3); the units only ever exist to
    ride the trail, where interdicting them is a real loss and a resolve drain.
    Uses the C1 regen whitelist, cycled by turn for a mixed column.
    """
    from game.fourteenth.coin import regen_unit_pool

    pool = regen_unit_pool(coalition)
    if not pool:
        return
    deficit = 2 * load - source.base.total_armor
    if deficit <= 0:
        return
    start = getattr(game, "turn", 0) % len(pool)
    for i in range(deficit):
        source.base.commission_units({pool[(start + i) % len(pool)]: 1})


def _skim_units(source: "ControlPoint", cap: int) -> dict["GroundUnitType", int]:
    """Take up to ``cap`` real ground units off ``source`` without gutting it.

    Never removes more than :data:`MAX_SOURCE_FRACTION` of the base's armour, so a nudged
    convoy is always spare rear stock. Returns {} if the source is too thin to skim.
    """
    budget = min(cap, int(source.base.total_armor * MAX_SOURCE_FRACTION))
    if budget < 1:
        return {}

    units: dict["GroundUnitType", int] = {}
    # Prefer the most numerous types so we skim depth, not a base's only unit of a kind.
    for unit_type, count in sorted(
        source.base.armor.items(), key=lambda kv: kv[1], reverse=True
    ):
        if budget <= 0:
            break
        take = min(count, budget)
        if take <= 0:
            continue
        units[unit_type] = take
        budget -= take
    return units
