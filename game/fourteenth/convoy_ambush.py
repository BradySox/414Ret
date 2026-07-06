"""Friendly convoy ambush / escort (§50).

The mirror of the Vietnam-Ops convoy interdiction (§35). Where interdiction gives the
player *enemy* convoys to hunt, this gives the player *friendly* convoys that might need
protecting: real, tracked BLUE supply convoys run the roads behind the front, and --
sometimes, it is a chance, never a certainty -- hidden, real RED ambush teams dig in along
their route: one contact, or a gauntlet of several down the same road.

Nothing is telegraphed in the Retribution UI. The convoy looks like any other friendly
convoy, the ambush teams are ``map_hidden`` (no marker, no uncertainty circle, nothing to
right-click or plan against -- see ``TheaterGroundObject.hidden_on_player_map``), and no
escort package is auto-fragged into the ATO. The first sign of trouble is the in-mission
"TROOPS IN CONTACT" call when an ambush springs -- and supporting the column (or not) is
the player's decision.

No phantom spawns (the §35/§37 lesson):

* the convoy is a real ``coalition.transfers`` transfer -- its loss is units that never
  arrive, reconciled in ``MissionResultsProcessor.commit_convoy_losses`` (which iterates
  *both* coalitions' convoys), and
* each ambush team is a real, hidden red TGO placed by
  :func:`game.fourteenth.coin.spawn_red_ground_at` -- killing it is a real red ground loss
  recorded natively at debrief.

The Lua ``convoyambush`` plugin only *springs* the ambushes (each team holds fire until
the convoy closes, then goes weapons-free with a cue) -- movement / cosmetics only, never
a kill it owns. That keeps the loss accounting entirely in the turn-boundary force model.

One turn-boundary step runs from ``Game.finish_turn`` (after the §35 enemy-trail top-up
and the ambient-convoy layer -- ``game/fourteenth/ambient_convoys.py``, which keeps a few
randomized real columns flowing on both sides' roads so an ambushable blue convoy
routinely exists):

* :func:`seed_convoy_ambushes` -- despawn last turn's ambush teams, then roll each active
  blue convoy against :data:`AMBUSH_CHANCE`; a convoy that loses the roll drives an
  ambushed road -- :data:`MIN_AMBUSHES_PER_ROUTE`..:data:`MAX_AMBUSHES_PER_ROUTE` hidden
  teams spread along it, recorded in ``game.convoy_ambush_state`` for the emitter.

The roll covers every blue convoy whatever created it (ambient, §35-style top-ups, the
player's own transfers). Gated by ``convoy_ambush`` (default ON -- the §49 kill-switch
precedent). Fully guarded: no blue convoy, or no red control point to source the ambushers
from => no-op.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint

#: Chance, per active blue convoy per turn, that its route is ambushed at all. Never a
#: certainty -- most of the time the road is quiet, so a sprung ambush stays a surprise.
AMBUSH_CHANCE = 0.5

#: When a route IS ambushed, this many teams dig in along it (rolled uniformly). One
#: contact at the low end; a five-or-six-fight gauntlet down the road at the top.
MIN_AMBUSHES_PER_ROUTE = 1
MAX_AMBUSHES_PER_ROUTE = 6

#: Teams are placed along the middle of the road: never within this fraction of either
#: endpoint, where the control point's own defenses would swamp them.
ROUTE_END_MARGIN = 0.15

#: Real red units per dug-in ambush team. A handful -- a threat to a passing column,
#: cleared by a flight of CAS, never a garrison.
AMBUSH_TEAM_SIZE = 4

#: The dice. Module-level so tests can substitute a deterministic stand-in.
_RNG = random.Random()


def seed_convoy_ambushes(game: "Game", events: Any) -> None:
    """Roll each active blue convoy for an ambush and seed the teams along its road.

    Despawns last turn's surviving ambush teams first (an ambush is a one-mission event --
    cleared or run-past, it does not persist), then rolls each currently-flowing blue
    convoy against :data:`AMBUSH_CHANCE`. An ambushed convoy gets 1..6 real red teams
    spread along the middle of its route, each a ``map_hidden`` TGO -- invisible on the
    campaign map and to both planners, so nothing about the coming fight is telegraphed.
    The pairings (ambush TGO id + convoy name) are recorded on ``game.convoy_ambush_state``
    for the emitter.

    No-op unless ``convoy_ambush`` is on. Guarded: no red control point to give the ambush
    its allegiance, or no blue convoy with a usable road, and nothing is seeded.
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
    for convoy in convoys:
        if _RNG.random() >= AMBUSH_CHANCE:
            continue  # this road is quiet this turn
        count = _RNG.randint(MIN_AMBUSHES_PER_ROUTE, MAX_AMBUSHES_PER_ROUTE)
        for point in _ambush_points(convoy, count):
            red_cp = _nearest_cp(red_cps, point)
            # events=None: a map-hidden TGO must never be pushed to the client,
            # and there is nothing for the UI to update.
            tgo = spawn_red_ground_at(
                game,
                red_cp,
                point,
                GroupTask.FRONT_LINE,
                events=None,
                max_units=AMBUSH_TEAM_SIZE,
            )
            if tgo is None:
                continue
            tgo.map_hidden = True
            ambushes.append({"tgo_id": str(tgo.id), "convoy": str(convoy.name)})

    state["ambushes"] = ambushes


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


def _ambush_points(convoy: Any, count: int) -> list[Any]:
    """Up to *count* dig-in points spread along the middle of the convoy's road.

    The route polyline from ``convoy_route_to`` is walked by length; each team gets one
    stratified-random slot inside the [:data:`ROUTE_END_MARGIN`, 1 - margin] span --
    evenly spread down the road with jitter, so a six-team roll reads as a gauntlet of
    separate contacts, never a stack. Interpolates along the road's segments (the
    §35-standard authored corridors have only a handful of waypoints, far fewer than the
    teams they can host). Returns [] for a missing/degenerate road."""
    try:
        route = convoy.origin.convoy_route_to(convoy.destination)
    except Exception:  # noqa: BLE001 -- a duck-typed / broken convoy is just skipped
        return []
    if not route or len(route) < 2:
        return []

    # (segment start, segment end, cumulative distance at start, segment length)
    legs: list[tuple[Any, Any, float, float]] = []
    total = 0.0
    for a, b in zip(route, route[1:]):
        length = a.distance_to_point(b)
        if length <= 0:
            continue
        legs.append((a, b, total, length))
        total += length
    if not legs or total <= 0:
        return []

    points: list[Any] = []
    span = 1.0 - 2 * ROUTE_END_MARGIN
    for i in range(count):
        frac = ROUTE_END_MARGIN + (i + _RNG.random()) * span / count
        distance = frac * total
        for a, b, start, length in legs:
            if distance <= start + length:
                heading = a.heading_between_point(b)
                points.append(a.point_from_heading(heading, distance - start))
                break
    return points


def _nearest_cp(cps: list["ControlPoint"], point: Any) -> "ControlPoint":
    """The control point in *cps* nearest *point* (cps is non-empty by construction)."""
    return min(cps, key=lambda cp: cp.position.distance_to_point(point))
