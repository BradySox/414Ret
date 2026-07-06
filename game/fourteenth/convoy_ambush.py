"""Friendly convoy ambush / escort (§50).

The mirror of the Vietnam-Ops convoy interdiction (§35). Where interdiction gives the
player *enemy* convoys to hunt, this gives the player *friendly* convoys to protect: real,
tracked BLUE supply convoys run the roads behind the front, and concealed, real RED ambush
teams dig in along their route. Left un-escorted, the ambush wears the convoy down and the
supplies never arrive; fly CAS/Armed Recon to clear the ambush and it gets through. An
escort package is auto-fragged into the ATO so the mission exists whether or not the player
mans it (the AI flies it otherwise).

No phantom spawns (the §35/§37 lesson):

* the convoy is a real ``coalition.transfers`` transfer -- its loss is units that never
  arrive, reconciled in ``MissionResultsProcessor.commit_convoy_losses`` (which iterates
  *both* coalitions' convoys), and
* each ambush team is a real, concealed red TGO placed by
  :func:`game.fourteenth.coin.spawn_red_ground_at` -- killing it is a real red ground loss
  recorded natively at debrief.

The Lua ``convoyambush`` plugin only *springs* the ambush (holds fire until the convoy
closes, then goes weapons-free with a cue) -- movement / cosmetics only, never a kill it
owns. That keeps the loss accounting entirely in the turn-boundary force model.

Two turn-boundary steps run from ``Game.finish_turn`` (after the enemy-trail convoy top-up):

* :func:`ensure_blue_escort_convoy` -- top the player's own convoy flow up to a small
  budget so an escortable convoy reliably exists (the symmetric analog of
  ``ensure_enemy_trail_convoy``; it reuses that module's coalition-generic corridor / seed
  / skim helpers).
* :func:`seed_convoy_ambushes` -- despawn last turn's surviving ambush teams, then seed a
  fresh concealed red ambush team on the route of each active blue convoy, recording the
  pairing in ``game.convoy_ambush_state`` for the emitter and the auto-frag.

Plus one plan-pass step from ``Coalition.plan_missions``:

* :func:`plan_convoy_escort` -- frag one BAI escort package per ambushed convoy onto the
  ambush team via the engine's own ``PackageFulfiller``.

All gated by ``convoy_ambush`` (default OFF, campaign-preseeded). Fully guarded: no blue
convoy, no red control point to source the ambushers from, no blue road corridor => no-op.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from datetime import datetime

    from game import Game
    from game.coalition import Coalition
    from game.profiling import MultiEventTracer
    from game.theater import ControlPoint

#: Concurrent blue supply convoys the escort layer keeps flowing (the player can only
#: shepherd so many at once -- a small, sustainable number, not a parade).
BLUE_CONVOY_BUDGET = 2

#: Real ground units a single escort convoy carries. Big enough to read as a column and to
#: survive a glancing ambush if the escort clears it in time, small enough that an unescorted
#: run is genuinely ground down.
CONVOY_UNITS = 8

#: At most this many of the active blue convoys get an ambush seeded per turn (matches the
#: convoy budget -- one escort mission per convoy, no more).
MAX_AMBUSHED_CONVOYS = 2

#: Real red units per dug-in ambush team. A handful -- a threat to a passing column, cleared
#: by the auto-fragged two-ship, never a garrison.
AMBUSH_TEAM_SIZE = 4

#: Aircraft in each auto-fragged escort (BAI) package.
ESCORT_FLIGHT_SIZE = 2


def ensure_blue_escort_convoy(game: "Game") -> None:
    """Top the player's blue convoy flow up to :data:`BLUE_CONVOY_BUDGET`.

    The symmetric analog of ``ensure_enemy_trail_convoy`` -- it reuses that module's
    coalition-generic corridor pick / source seed / unit skim so a blue rear base feeds a
    real convoy toward the forward blue control point. No-op unless ``convoy_ambush`` is on.
    Idempotent per turn: it creates at most (budget - currently flowing) convoys, so an
    organic blue transfer this turn just leaves fewer for it to add.
    """
    if not game.settings.convoy_ambush:
        return
    if game.turn < 1:
        return

    coalition = game.blue
    active = list(coalition.transfers.convoys)
    deficit = BLUE_CONVOY_BUDGET - len(active)
    if deficit <= 0:
        return

    from game.fourteenth.vietnam_convoy import (
        _pick_trail_corridor,
        _seed_trail_source,
        _skim_units,
    )
    from game.transfers import TransferOrder

    # Spread concurrent convoys across distinct roads (the §35 exclude-sources pattern).
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
        tried_sources.add(source)

        # Blue draws its column from its own front-line roster (never the COIN insurgent
        # whitelist -- that is a red-insurgency pool), topped up as external logistics so a
        # turn-1 empty rear base still fields a convoy.
        _seed_trail_source(game, coalition, source, CONVOY_UNITS, coin=False)
        units = _skim_units(source, CONVOY_UNITS)
        if not units:
            continue

        coalition.transfers.new_transfer(
            TransferOrder(source, destination, units), game.conditions.start_time
        )
        created += 1


def seed_convoy_ambushes(game: "Game", events: Any) -> None:
    """Seed a fresh concealed red ambush team on each active blue convoy's route.

    Despawns last turn's surviving ambush teams first (an ambush is a one-mission event --
    cleared or run-past, it does not persist), then, for up to :data:`MAX_AMBUSHED_CONVOYS`
    of the currently-flowing blue convoys, drops a small real red TGO on a mid-route
    waypoint. The pairing (ambush TGO id + convoy name) is recorded on
    ``game.convoy_ambush_state`` for the emitter and :func:`plan_convoy_escort`.

    No-op unless ``convoy_ambush`` is on. Guarded: no red control point to give the ambush
    its allegiance, or no blue convoy with a long-enough road, and nothing is seeded.
    """
    if not game.settings.convoy_ambush:
        return

    state = _state(game)
    _despawn_prior_ambushes(game, state, events)

    red_cps = [cp for cp in game.theater.controlpoints if cp.captured.is_red]
    if not red_cps:
        return
    convoys = list(game.blue.transfers.convoys)
    if not convoys:
        return

    from game.data.groups import GroupTask
    from game.fourteenth.coin import spawn_red_ground_at

    ambushes: list[dict[str, Any]] = []
    for convoy in convoys[:MAX_AMBUSHED_CONVOYS]:
        point = _ambush_point(convoy)
        if point is None:
            continue
        red_cp = _nearest_cp(red_cps, point)
        tgo = spawn_red_ground_at(
            game,
            red_cp,
            point,
            GroupTask.FRONT_LINE,
            events,
            max_units=AMBUSH_TEAM_SIZE,
            concealed=True,
        )
        if tgo is None:
            continue
        ambushes.append({"tgo_id": str(tgo.id), "convoy": str(convoy.name)})

    state["ambushes"] = ambushes


def plan_convoy_escort(
    coalition: "Coalition", now: "datetime", tracer: "MultiEventTracer"
) -> None:
    """Frag one BAI escort package per ambushed convoy onto its ambush team.

    Mirrors ``plan_carrier_strike``: it builds a real package through the engine's own
    ``PackageFulfiller`` (proper flight plan, waypoints, fuel, TOT) so the AI flies it if
    the player does not. BAI is the tasking the commander itself uses against a vehicle
    group (``PlanBai`` / ``PlanConvoyInterdiction``), so a two-ship onto the ambush TGO is
    "go clear this ground threat" -- exactly the escort's job.

    No-op unless ``convoy_ambush`` is on and this is the BLUE coalition. Idempotent per plan
    pass: ``_already_planned_against`` skips an ambush that already has its escort package.
    """
    game = coalition.game
    if not coalition.player.is_blue:
        return
    if not getattr(game.settings, "convoy_ambush", False):
        return
    state = getattr(game, "convoy_ambush_state", None)
    if not isinstance(state, dict):
        return

    from game.ato.flighttype import FlightType
    from game.commander.missionproposals import ProposedFlight, ProposedMission
    from game.commander.packagefulfiller import PackageFulfiller
    from game.fourteenth.coin import _tgo_by_id
    from game.fourteenth.phases import roe_blocks_target

    fulfiller = PackageFulfiller(
        coalition, game.theater, game.db.flights, game.settings
    )
    planned = 0
    for record in state.get("ambushes", []):
        if planned >= MAX_AMBUSHED_CONVOYS:
            break
        tgo = _tgo_by_id(game, record.get("tgo_id"))
        if tgo is None:
            continue
        if not any(unit.alive for unit in tgo.units):
            continue
        if roe_blocks_target(game, tgo):
            continue
        if _already_planned_against(coalition, tgo):
            continue
        flights = [ProposedFlight(FlightType.BAI, ESCORT_FLIGHT_SIZE)]
        with tracer.trace("Blue convoy escort"):
            package = fulfiller.plan_mission(
                ProposedMission(tgo, flights, asap=False),
                0,  # purchase_multiplier: never buy jets for the escort, use what's home
                now,
                tracer,
            )
        if package is None:
            continue
        coalition.ato.add_package(package)
        planned += 1


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------


def _state(game: "Game") -> dict[str, Any]:
    """The pickled convoy-ambush state dict, created on first use (getattr-guarded so old
    saves without the attribute migrate cleanly)."""
    state = getattr(game, "convoy_ambush_state", None)
    if not isinstance(state, dict):
        state = {}
        game.convoy_ambush_state = state
    return state


def _despawn_prior_ambushes(game: "Game", state: dict[str, Any], events: Any) -> None:
    """Remove every ambush TGO seeded last turn (survivors and all -- the ambush is over)."""
    from game.fourteenth.coin import _despawn, _tgo_by_id

    for record in state.get("ambushes", []):
        tgo = _tgo_by_id(game, record.get("tgo_id"))
        if tgo is not None:
            _despawn(game, tgo, events)
    state["ambushes"] = []


def _ambush_point(convoy: Any) -> Any:
    """A mid-route waypoint on the convoy's road, or None if the road is too short to hold
    an ambush between the origin and the destination.

    The route from ``convoy_route_to`` includes both control-point endpoints; the ambush
    digs in on a waypoint in the middle so the column drives into it (never on top of either
    base, where the CP's own defenses would swamp it)."""
    try:
        route = convoy.origin.convoy_route_to(convoy.destination)
    except Exception:  # noqa: BLE001 -- a duck-typed / broken convoy is just skipped
        return None
    if not route or len(route) < 3:
        return None
    return route[len(route) // 2]


def _nearest_cp(cps: list["ControlPoint"], point: Any) -> "ControlPoint":
    """The control point in *cps* nearest *point* (cps is non-empty by construction)."""
    return min(cps, key=lambda cp: cp.position.distance_to_point(point))


def _already_planned_against(coalition: "Coalition", tgo: Any) -> bool:
    """True if the ATO already holds a BAI package aimed at this ambush TGO."""
    from game.ato.flighttype import FlightType

    for package in coalition.ato.packages:
        if package.target is tgo and any(
            flight.flight_type is FlightType.BAI for flight in package.flights
        ):
            return True
    return False
