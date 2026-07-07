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
    ied_emplacement_unit_types,
    ied_unit_types,
    spawn_red_ground_at,
)

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint

#: Concurrent live IEDs on the ratline. Small -- a sweep-able handful, not a minefield.
MAX_ACTIVE_IEDS = 2

#: Turns a *static* roadside IED sits armed before it detonates under a passing convoy.
FUSE_TURNS = 3

#: Turns a *mobile* VBIED (a suicide vehicle bomb) takes to reach friendly lines. Shorter
#: than the static fuse -- it is actively driving at a base, so the interdiction window is
#: tighter. (The ``coin`` plugin drives it in-mission; this is the turn-boundary deadline.)
VBIED_FUSE_TURNS = 2

#: Units in a mobile VBIED -- a lone suicide vehicle, a small recon-fogged intercept.
VBIED_UNITS = 1

#: Units in a static emplacement -- the device (a barrel static) + a two-man security
#: team around it, so finding the bomb reads as finding *people digging it in*, not a
#: lone parked truck.
IED_EMPLACEMENT_UNITS = 3


def _fuse_for(ied: dict[str, Any]) -> int:
    """A mobile VBIED reaches friendly lines faster than a buried device goes off."""
    return VBIED_FUSE_TURNS if ied.get("kind") == "vbied" else FUSE_TURNS


def advance_roadside_ieds(game: "Game", events: Any = None) -> None:
    """Age the live IEDs (clear/detonate) and top the ratline back up. Call exactly
    once per turn from ``finish_turn``, after the C1/C1.5 hooks.

    No-op unless both ``coin_ied`` and ``coin_insurgency`` are on, or before turn 1.
    """
    if not getattr(game.settings, "coin_ied", False) or not getattr(
        game.settings, "coin_insurgency", False
    ):
        _sweep_disabled(game, events)
        return
    if getattr(game, "turn", 0) < 1:
        return

    state = getattr(game, "coin_state", None)
    if not isinstance(state, dict):
        state = {}
        game.coin_state = state
    ieds: list[dict[str, Any]] = state.setdefault("ieds", [])

    _age_live_ieds(game, state, ieds, events)
    _replenish_ieds(game, state, ieds, events)


def _sweep_disabled(game: "Game", events: Any) -> None:
    """Mid-campaign toggle-off: despawn any live IED/VBIED TGOs so they don't sit
    frozen mid-fuse (with their 'suspected activity' circles) forever."""
    state = getattr(game, "coin_state", None)
    if not isinstance(state, dict) or not state.get("ieds"):
        return
    for ied in state["ieds"]:
        _despawn(game, _tgo_by_id(game, ied.get("tgo_id")), events)
    state["ieds"] = []


def _age_live_ieds(
    game: "Game", state: dict[str, Any], ieds: list[dict[str, Any]], events: Any
) -> None:
    survivors: list[dict[str, Any]] = []
    for ied in ieds:
        tgo = _tgo_by_id(game, ied.get("tgo_id"))
        if tgo is None:
            continue  # already gone (removed elsewhere) -- drop it silently
        where = ied.get("where", "the trail")
        is_vbied = ied.get("kind") == "vbied"
        if not _ied_intact(tgo, is_vbied):
            # The player found and struck it: cleared/intercepted, no detonation.
            _despawn(game, tgo, events)
            if is_vbied:
                _announce(
                    game,
                    f"VBIED intercepted near {where} before it reached friendly lines.",
                )
            else:
                _announce(game, f"Roadside IED near {where} cleared.")
            continue
        ied["armed"] = int(ied.get("armed", 0)) + 1
        if ied["armed"] >= _fuse_for(ied):
            state["ied_detonations"] = int(state.get("ied_detonations", 0)) + 1
            _despawn(game, tgo, events)
            if is_vbied:
                dest = ied.get("target", "friendly lines")
                _announce(
                    game,
                    f"VBIED reached {dest} — coalition casualties reported.",
                )
            else:
                _announce(
                    game,
                    f"IED detonation near {where} — coalition casualties reported.",
                )
            continue
        survivors.append(ied)
    ieds[:] = survivors


def _replenish_ieds(
    game: "Game", state: dict[str, Any], ieds: list[dict[str, Any]], events: Any
) -> None:
    used = {tuple(ied["road"]) for ied in ieds if "road" in ied}
    while len(ieds) < MAX_ACTIVE_IEDS:
        site = _pick_ied_site(game, used)
        if site is None:
            return
        red_cp, point, road_key, road = site
        from game.data.groups import GroupTask

        # Alternate static device and mobile VBIED (deterministic -- saves must be stable):
        # every other plant is a suicide vehicle that races for the nearest friendly base.
        # The kind decides the metal: a static plant is the emplaced device (a barrel
        # static) with a small security team around it; a VBIED is a lone soft vehicle.
        planted = int(state.get("ied_planted", 0))
        kind = "vbied" if planted % 2 == 1 else "ied"
        if kind == "vbied":
            max_units, fiction_kit = VBIED_UNITS, ied_unit_types(game)
        else:
            # Size the emplacement to the kit: normally the device + its security
            # team, but a faction with no eligible infantry gets the bare device --
            # never three cycled copies of it (_retype_units repeats a short kit).
            fiction_kit = ied_emplacement_unit_types(game)
            max_units = min(IED_EMPLACEMENT_UNITS, max(1, len(fiction_kit)))
        tgo = spawn_red_ground_at(
            game,
            red_cp,
            point,
            GroupTask.FRONT_LINE,
            events,
            max_units=max_units,
            sidc_override=IED_SIDC,
            unit_types=fiction_kit,
            concealed=True,
        )
        if tgo is None:
            return
        # Pin the concealment to the road: the map's "suspected activity" circle
        # slides FAR along this polyline instead of a small radial offset (user
        # call 2026-07-05 -- "we know what highway it's on but not which street").
        # A short/absent authored path (< 2 points) falls back to the radial jitter.
        if len(road) >= 2:
            tgo.concealed_route = [(p.x, p.y) for p in road]
        used.add(road_key)
        state["ied_planted"] = planted + 1
        record: dict[str, Any] = {
            "tgo_id": str(tgo.id),
            "armed": 0,
            "road": list(road_key),
            "where": red_cp.name,
            "kind": kind,
        }
        if record["kind"] == "vbied":
            target = _nearest_blue_cp(game, point)
            record["target"] = target.name if target is not None else "friendly lines"
            ieds.append(record)
            _announce(
                game,
                f"Intel: a VBIED (suicide vehicle) is moving from near {red_cp.name} "
                f"toward {record['target']} — intercept it before it arrives.",
            )
        else:
            ieds.append(record)
            _announce(
                game, f"Intel: IED activity reported on the road near {red_cp.name}."
            )


def _nearest_blue_cp(game: "Game", point: Any) -> Optional["ControlPoint"]:
    """The friendly (blue) control point nearest *point* -- the VBIED's objective."""
    best: Optional[tuple[float, "ControlPoint"]] = None
    for cp in game.theater.controlpoints:
        if not cp.captured.is_blue:
            continue
        dist = point.distance_to_point(cp.position)
        if best is None or dist < best[0]:
            best = (dist, cp)
    return best[1] if best is not None else None


def _pick_ied_site(
    game: "Game", used: set[tuple[Any, Any]]
) -> Optional[tuple["ControlPoint", Any, tuple[Any, Any], list[Any]]]:
    """A (red CP, road point, road key, road waypoints) to mine: the red-to-red supply
    road nearest the fighting whose road isn't already mined. Returns None if none is
    available.

    Mirrors the §35 trail picker's "enemy road nearest the front" selection on the same
    ``convoy_routes`` graph; the IED attaches to the red endpoint nearer the front (so it
    renders RED -- a TGO's allegiance is its parent CP's) and sits on a mid-road waypoint.
    The waypoints are returned so the plant can pin the TGO's concealment to the road
    (the suspected-activity circle slides ALONG the route, never off into the fields).
    """
    reference = _front_reference(game)
    if not reference:
        return None

    def dist_to_front(cp: "ControlPoint") -> float:
        return min(p.distance_to_point(cp.position) for p in reference)

    best: Optional[tuple[float, "ControlPoint", Any, tuple[Any, Any], list[Any]]] = None
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
                best = (score, forward, point, key, list(waypoints or []))
    if best is None:
        return None
    _, red_cp, point, road_key, road = best
    return red_cp, point, road_key, road


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


def _ied_intact(tgo: Any, is_vbied: bool) -> bool:
    """Whether the emplacement is still a live threat.

    A *static* emplacement is anchored on its **device** (the static object): killing
    the security team alone does not clear the bomb, and a dead device clears it even
    if the team survives (they melt away with the despawn). A VBIED -- and any
    pre-rework save whose emplacement is a lone vehicle with no static -- is live
    while any unit is.
    """
    units = list(getattr(tgo, "units", []))
    if not is_vbied:
        statics = [u for u in units if getattr(u, "is_static", False)]
        if statics:
            return any(getattr(u, "alive", False) for u in statics)
    return any(getattr(unit, "alive", False) for unit in units)


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
