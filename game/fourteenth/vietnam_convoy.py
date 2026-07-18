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

**The trail is now externally supplied, not economy-gated (same-day follow-up).** A live
probe across the 4 land Vietnam campaigns found every rear opfor CP's ``Base.armor`` at
**zero** at turn 0 -- it is the coalition's turn-by-turn production/income stock, not a
static garrison, so a fresh campaign's trail was never actually gated by
:data:`MAX_CONVOY_UNITS`; it was gated by how little the rear base had *accumulated* yet.
Every corridor pick now tops its source up to a standing stock before skimming
(:func:`_seed_trail_source`, mirroring the pre-existing COIN ratline design), framed as
external logistics support (matériel from China/the USSR) rather than local production --
which is the Ho Chi Minh Trail's actual historical character. Bounded exactly like the COIN
version: topped to 2x a convoy load, never grown past it.

Fully guarded -- if any precondition is missing (no front, no road corridor, no unit pool to
seed from and nothing already on hand) it is a no-op and the engine's organic convoys still
serve as targets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from game.dcs.groundunittype import GroundUnitType
    from game.theater import ControlPoint

#: Vehicles a single convoy carries. Bumped 2026-07-03 (twice, same day): first
#: 4 -> 6 off "only 3 vehicles" feedback, then 6 -> 10 once the real gate (an empty
#: rear Base.armor, not this cap) was found and fixed by seeding -- a proper trail
#: column now, not a token trickle.
MAX_CONVOY_UNITS = 10

#: Baseline concurrent convoys the opfor keeps flowing (raised alongside MAX_CONVOY_UNITS,
#: 2026-07-03 -- with it, a campaign whose laydown offers more than one opfor-opfor road
#: (Yankee Station / Steel Tiger's full trail network, Khe Sanh's two rear feeders, Red Flag
#: 81-2's aggressor corridors) actually runs convoys on distinct roads instead of stacking
#: extra columns onto the single busiest one).
BASE_MAX_CONVOYS = 2

#: Under a W6 trail_surge >= 2.0, one more concurrent convoy on top of the baseline.
SURGE_MAX_CONVOYS = 3

#: Never strip a source base below this fraction of its armour; the nudge only ever skims
#: spare rear units, so a source is never gutted to feed the trail. With the seeding above,
#: this now clamps a topped-up standing stock rather than the coalition's own thin economy.
MAX_SOURCE_FRACTION = 0.5

#: A destination already banking this much armour stops drawing new trail convoys.
#: The 2026-07-18 audit measured the external-support seeding as an UNBOUNDED pump on
#: front-less COIN maps — red ``Base.armor`` grew +20/turn linearly (0 -> 186 in 8
#: self-played turns) because the source re-tops after every delivery and nothing
#: consumes the sink. On fronted maps the front drains the stock so this rarely
#: binds; on front-less maps it bounds each corridor's bank at ~3 convoy loads.
TRAIL_DESTINATION_STOCK_CAP = 3 * MAX_CONVOY_UNITS


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

    # The trail runs on EXTERNAL logistics support, not the coalition's own organic
    # economy (2026-07-03 -- the historically-accurate framing for the Ho Chi Minh
    # Trail specifically: matériel arriving from China/the USSR, not local Base
    # production). A fresh rear CP's Base.armor is genuinely empty turn 1 (it only
    # fills from each turn's production/income), which is why a flown session
    # found the trail thin -- the constraint was never the convoy-size cap, it was
    # the coalition's own accumulated stock. So every corridor pick now tops its
    # source up to a standing stock before skimming, regardless of what the CP's
    # ledger happens to hold -- bounded exactly like the pre-existing COIN ratline
    # (topped to 2x a convoy load, never grown past it: relocate, never grow).
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
            allow_empty_source=True,
            exclude_sources=frozenset(tried_sources),
        )
        if corridor is None:
            return
        source, destination = corridor
        tried_sources.add(
            source
        )  # never repick the same source this call, hit or miss.

        if destination.base.total_armor >= TRAIL_DESTINATION_STOCK_CAP:
            continue  # the sink is full -- externally-supplied convoys stop here.

        _seed_trail_source(game, coalition, source, load, coin=coin)
        units = _skim_units(source, load)
        if not units:
            continue  # no unit pool available to seed from -- try the next road.

        coalition.transfers.new_transfer(
            TransferOrder(source, destination, units), game.conditions.start_time
        )
        created += 1


def _reference_points(game: "Game", coalition: "Coalition") -> list[Any]:
    """Where "the fighting" is for *coalition*'s supply flow to orient toward.

    Front lines when the campaign has them; on a front-less laydown (the COIN
    air-assault geometry -- no CP adjacency, no conflicts) fall back to the opposing
    coalition's control points, so the flow still runs toward where the enemy actually
    is. Empty means there is genuinely no war to supply. Shared by the trail picker
    below and the §50 ambient-convoy layer (``game/fourteenth/ambient_convoys.py``).
    """
    fronts = list(game.theater.conflicts())
    if fronts:
        return [front.position for front in fronts]
    return [
        cp.position
        for cp in game.theater.controlpoints
        if cp.captured != coalition.player
        and not getattr(cp.captured, "is_neutral", False)
    ]


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
    reference = _reference_points(game, coalition)
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


def _seed_trail_source(
    game: "Game",
    coalition: "Coalition",
    source: "ControlPoint",
    load: int,
    coin: bool,
) -> None:
    """Top the rear source up to twice a convoy load with real units (2026-07-03).

    ``_skim_units`` takes at most :data:`MAX_SOURCE_FRACTION` (half) of the source's
    stock, so a 2x-load stock yields exactly one full convoy and leaves the rest as
    the rear buffer -- stable across cycles, never a growing pile. Free by design
    (the external-support framing: the Ho Chi Minh Trail ran on matériel arriving
    from China/the USSR, not the rear base's own local production, so its stock
    isn't gated on the coalition's turn-by-turn economy); the units only ever
    exist to ride the trail, where interdicting them is a real loss.

    ``coin`` (COIN's insurgency, design note §3.3) draws from the tight regen
    whitelist (:func:`game.fourteenth.coin.regen_unit_pool` -- infantry/technicals/
    AAA under a price ceiling). Every other Vietnam campaign draws from the
    faction's own real ground roster (``Faction.frontline_units`` -- e.g.
    PT-76/T-54/Grad-URAL), so the seeded convoy looks like the coalition's actual
    order of battle rather than insurgent kit. No pool available (a fake/duck-typed
    coalition in a test, or a faction with an empty roster) is a silent no-op --
    the caller falls back to whatever the source's ledger already holds.
    """
    if coin:
        from game.fourteenth.coin import regen_unit_pool

        pool = regen_unit_pool(coalition)
    else:
        faction = getattr(coalition, "faction", None)
        pool = sorted(
            getattr(faction, "frontline_units", None) or (),
            key=lambda unit: (unit.price, unit.display_name),
        )
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
