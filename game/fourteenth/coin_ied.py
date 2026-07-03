"""COIN roadside IEDs -- the insurgent ratline is mined; sweep it or pay.

Design: the third COIN direction (after C1 replenishment + C1.5 re-infiltration). The
insurgency's real threat to a coalition is not its air force -- it is the improvised
device on the road. This layer plants **hidden IED emplacements on the insurgent supply
roads** (the §35 ratline -- the red-to-red ``convoy_routes`` graph). Each is an ordinary
recon-fogged red TGO: the player must **find it (TARPS/ISR) and strike it (CAS/Armed
Recon)** within a fuse window, or it **detonates on the coalition** and drains the
mandate (the political price of an un-secured AO). Clearing it costs the insurgency
nothing but the device; leaving it costs Washington.

Turn-boundary force-model work only (``Game.finish_turn``, after C1/C1.5): no Lua, real
TGOs that fight and die through the normal loss path, recon fog for free (a TGO is hidden
until reconned, per §3). State lives in ``game.coin_state`` (an ``"ieds"`` list + an
``"ied_detonations"`` counter, plain primitives, pickled; ``getattr`` default so
pre-feature saves are inert until the toggle is on).

Everything is behind ``coin_ied`` (default OFF, requires ``coin_insurgency`` for the
red-road laydown; campaign-preseeded). The will drain is priced by the campaign's
``will:`` profile via ``blue_ied_detonation`` (default 0.0 -- inert until weighted up).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from game.fourteenth.coin import (
    IED_SIDC,
    _despawn,
    _tgo_by_id,
    spawn_red_ground_at,
)

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint

#: Concurrent live IEDs on the ratline. Small -- a sweep-able handful, not a minefield.
MAX_ACTIVE_IEDS = 2

#: Turns an IED sits armed before it detonates (if the player never clears it).
FUSE_TURNS = 3

#: Units in an emplacement -- a lone device/team, a small recon-fogged strike target.
IED_UNITS = 1


def advance_roadside_ieds(game: "Game", events: Any = None) -> None:
    """Age the live IEDs (clear/detonate) and top the ratline back up. Call exactly
    once per turn from ``finish_turn``, after the C1/C1.5 hooks.

    No-op unless both ``coin_ied`` and ``coin_insurgency`` are on, or before turn 1.
    """
    if not getattr(game.settings, "coin_ied", False):
        return
    if not getattr(game.settings, "coin_insurgency", False):
        return
    if getattr(game, "turn", 0) < 1:
        return

    state = getattr(game, "coin_state", None)
    if not isinstance(state, dict):
        state = {}
        game.coin_state = state
    ieds: list[dict[str, Any]] = state.setdefault("ieds", [])

    _age_live_ieds(game, state, ieds, events)
    _replenish_ieds(game, ieds, events)


def _age_live_ieds(
    game: "Game", state: dict[str, Any], ieds: list[dict[str, Any]], events: Any
) -> None:
    survivors: list[dict[str, Any]] = []
    for ied in ieds:
        tgo = _tgo_by_id(game, ied.get("tgo_id"))
        if tgo is None:
            continue  # already gone (removed elsewhere) -- drop it silently
        if not _tgo_alive(tgo):
            # The player found and struck it: cleared, no detonation.
            _despawn(game, tgo, events)
            _announce(
                game, f"Roadside IED near {ied.get('where', 'the trail')} cleared."
            )
            continue
        ied["armed"] = int(ied.get("armed", 0)) + 1
        if ied["armed"] >= FUSE_TURNS:
            state["ied_detonations"] = int(state.get("ied_detonations", 0)) + 1
            _despawn(game, tgo, events)
            _announce(
                game,
                f"IED detonation near {ied.get('where', 'the trail')} — coalition casualties reported.",
            )
            continue
        survivors.append(ied)
    ieds[:] = survivors


def _replenish_ieds(game: "Game", ieds: list[dict[str, Any]], events: Any) -> None:
    used = {tuple(ied["road"]) for ied in ieds if "road" in ied}
    while len(ieds) < MAX_ACTIVE_IEDS:
        site = _pick_ied_site(game, used)
        if site is None:
            return
        red_cp, point, road_key = site
        from game.data.groups import GroupTask

        tgo = spawn_red_ground_at(
            game,
            red_cp,
            point,
            GroupTask.FRONT_LINE,
            events,
            max_units=IED_UNITS,
            sidc_override=IED_SIDC,
        )
        if tgo is None:
            return
        used.add(road_key)
        ieds.append(
            {
                "tgo_id": str(tgo.id),
                "armed": 0,
                "road": list(road_key),
                "where": red_cp.name,
            }
        )
        _announce(game, f"Intel: IED activity reported on the road near {red_cp.name}.")


def _pick_ied_site(
    game: "Game", used: set[tuple[Any, Any]]
) -> Optional[tuple["ControlPoint", Any, tuple[Any, Any]]]:
    """A (red CP, road point, road key) to mine: the red-to-red supply road nearest the
    fighting whose road isn't already mined. Returns None if none is available.

    Mirrors the §35 trail picker's "enemy road nearest the front" selection on the same
    ``convoy_routes`` graph; the IED attaches to the red endpoint nearer the front (so it
    renders RED -- a TGO's allegiance is its parent CP's) and sits on a mid-road waypoint.
    """
    reference = _front_reference(game)
    if not reference:
        return None

    def dist_to_front(cp: "ControlPoint") -> float:
        return min(p.distance_to_point(cp.position) for p in reference)

    best: Optional[tuple[float, "ControlPoint", Any, tuple[Any, Any]]] = None
    for cp in game.theater.controlpoints:
        if not cp.captured.is_red:
            continue
        for other, waypoints in getattr(cp, "convoy_routes", {}).items():
            if not other.captured.is_red:
                continue  # red -> red roads only (the ratline behind the lines)
            key = tuple(sorted((cp.id, other.id), key=str))
            if key in used:
                continue
            forward = cp if dist_to_front(cp) <= dist_to_front(other) else other
            point = _mid_waypoint(waypoints, forward)
            if point is None:
                continue
            score = dist_to_front(forward)
            if best is None or score < best[0]:
                best = (score, forward, point, key)
    if best is None:
        return None
    _, red_cp, point, road_key = best
    return red_cp, point, road_key


def _front_reference(game: "Game") -> list[Any]:
    """Positions to measure 'toward the fighting' -- front lines, else the opposing
    coalition's CPs (the front-less COIN air-assault geometry, mirroring §35)."""
    fronts = list(game.theater.conflicts())
    if fronts:
        return [front.position for front in fronts]
    return [
        cp.position
        for cp in game.theater.controlpoints
        if not cp.captured.is_red and not cp.captured.is_neutral
    ]


def _mid_waypoint(waypoints: Any, forward: "ControlPoint") -> Any:
    """A point on the road: the middle authored waypoint, else the forward endpoint."""
    points = list(waypoints or [])
    if points:
        return points[len(points) // 2]
    return getattr(forward, "position", None)


def _tgo_alive(tgo: Any) -> bool:
    return any(getattr(unit, "alive", False) for unit in getattr(tgo, "units", []))


def consume_ied_detonations(game: "Game") -> int:
    """Number of IED detonations since the last call, cleared to zero. The will layer
    charges these against the mandate (a finish_turn event, never in the debriefing)."""
    state = getattr(game, "coin_state", None)
    if not isinstance(state, dict):
        return 0
    count = int(state.get("ied_detonations", 0))
    state["ied_detonations"] = 0
    return count


def _announce(game: "Game", message: str) -> None:
    try:
        game.message("Roadside IED", message)
    except Exception:  # noqa: BLE001 -- messaging is best-effort, never break the turn
        pass
