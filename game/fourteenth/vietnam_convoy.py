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
transfer processing). When ``vietnam_convoy_interdiction`` is on and the opfor has no convoy
already travelling, it moves a few of the opfor's **real** rear-area ground units forward
along the road corridor nearest the front. The units are debited from the origin base
(``new_transfer`` -> ``commit_losses``), so this is genuine force planning: interdict the
convoy and those reinforcements never reach the line; let it through and they do.

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
#: and a trickle of reinforcements, not a war-winning column.
MAX_CONVOY_UNITS = 4

#: Never strip a source base below this fraction of its armour; the nudge only ever skims
#: spare rear units, so a source is never gutted to feed the trail.
MAX_SOURCE_FRACTION = 0.5


def ensure_enemy_trail_convoy(game: "Game") -> None:
    """Ensure the opfor has a real convoy on the trail when interdiction is enabled.

    No-op unless ``vietnam_convoy_interdiction`` is set. Idempotent per turn by
    construction: it does nothing if the opfor already has a convoy travelling, so calling
    it again (or on a turn where the AI already ordered a transfer) never stacks columns.
    """
    if not game.settings.vietnam_convoy_interdiction:
        return
    if game.turn < 1:
        return

    # The opfor of the (BLUE) human -- the side whose trail the player interdicts.
    coalition = game.red

    # W6 red tempo: an authored phase's trail_surge widens the flow -- a second
    # concurrent column is allowed and each carries a bigger (still capped-source)
    # budget. Baseline (no authored phase / surge 1.0) keeps the one-convoy rule.
    from game.fourteenth.red_tempo import trail_surge_multiplier

    surge = trail_surge_multiplier(game)
    max_convoys = 2 if surge >= 2.0 else 1

    # Enough real convoys flowing? Let them be the hunt targets; add nothing.
    if sum(1 for _ in coalition.transfers.convoys) >= max_convoys:
        return

    # COIN (coin_insurgency): the insurgency has no factories or transfers, so the
    # rear strongholds hold no Base.armor to skim -- the ratline is EXTERNAL
    # support entering at the rear. Seed the source with a small stock of
    # whitelisted irregular kit before skimming (bounded: just enough that the
    # skim fraction yields one convoy load; the remainder is the rear buffer).
    coin = getattr(game.settings, "coin_insurgency", False)

    corridor = _pick_trail_corridor(game, coalition, allow_empty_source=coin)
    if corridor is None:
        return
    source, destination = corridor

    load = round(MAX_CONVOY_UNITS * surge)
    if coin:
        _seed_ratline_source(game, coalition, source, load)
    units = _skim_units(source, load)
    if not units:
        return

    from game.transfers import TransferOrder

    coalition.transfers.new_transfer(
        TransferOrder(source, destination, units), game.conditions.start_time
    )


def _pick_trail_corridor(
    game: "Game", coalition: "Coalition", allow_empty_source: bool = False
) -> Optional[tuple["ControlPoint", "ControlPoint"]]:
    """Pick (source, destination) for the trail convoy: a rear opfor base with spare armour
    feeding the road-connected opfor base nearest the front.

    Mirrors the old emitter's "enemy road nearest the fighting" selection, but resolved on
    the real control-point graph so the transfer produces a real convoy. Returns None if no
    opfor-to-opfor road corridor with a stocked rear source exists.
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
