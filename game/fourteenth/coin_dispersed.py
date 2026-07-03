"""COIN dispersed cells -- the insurgency in the countryside, between the strongholds.

The fifth COIN direction (C4). C1/C1.5/IED/HVT all anchor the insurgency to a base --
cells regenerate *in* strongholds, re-infiltrate *toward* bases, leaders surface *near*
them. This layer models the opposite: the insurgency's presence **not tied to any CP** --
small, recon-fogged cells that appear out in the open field between the strongholds and
the coalition, the "everywhere and nowhere" of a guerrilla war. The player has to
**patrol the countryside** (TARPS + CAS), not just hit known positions.

Its distinct hook (not a fourth "hunt the red TGO"): a cell you leave alone **matures and
coalesces into its home stronghold, reviving one of that stronghold's dead ammo caches**
-- re-opening the C1 regeneration throttle you worked to shut off. So an un-patrolled
countryside quietly re-supplies the caches; hunting the field cells is how you *keep* a
stronghold starved. If the stronghold has no dead cache to restore, the cell instead
revives a couple of its dead militia units (bounded by the C1 anchor -- relocate, never
grow). Killing a field cell is ordinary attrition; the point is denying the resupply.

Turn-boundary force-model work only (``Game.finish_turn``, after C1/C1.5/IED/HVT): no Lua,
real recon-fogged red TGOs that die through the normal loss path, reusing the C1 revival
machinery for the coalesce. State lives in ``game.coin_state`` (a ``"field_cells"`` list,
plain primitives, pickled; ``getattr`` default so pre-feature saves are inert).

Behind ``coin_dispersed_cells`` (default OFF, requires ``coin_insurgency``;
campaign-preseeded). No will-weight coupling -- the cost of ignoring the field is the
*material* cache resupply, not a political meter (deferred).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from game.fourteenth.coin import (
    CELL_SIDC,
    _alive_cell_count,
    _despawn,
    _ensure_anchors,
    _revivable_units,
    _revive,
    _tgo_by_id,
    spawn_red_ground_at,
)

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint

#: Concurrent field cells loose in the countryside. More than the one-at-a-time HVT --
#: dispersal is the point -- but small enough to sweep.
MAX_FIELD_CELLS = 3

#: Turns a cell drifts before it coalesces into its home stronghold (if never hunted).
MATURE_TURNS = 3

#: Units in a field cell -- a small, recon-fogged strike target.
FIELD_CELL_UNITS = 2

#: Dead militia units a coalesce revives when the home stronghold has no dead cache to
#: restore (still bounded by the C1 anchor cap -- never grows the stronghold past turn 0).
COALESCE_REVIVE = 2

#: A field cell sits at least this far (metres) from every control point -- it is *in
#: the countryside*, not on a base (that is C1/C1.5/HVT territory).
MIN_FIELD_DIST_M = 12_000.0

#: Fraction of the stronghold->coalition line to place the cell at -- out in the
#: contested ground between the insurgency and the coalition, not hugging either.
FIELD_FRACTION = 0.4


def advance_dispersed_cells(game: "Game", events: Any = None) -> None:
    """Age the field cells (attrite/coalesce) and reseed the countryside. Call exactly
    once per turn from ``finish_turn``, after the C1/C1.5/IED/HVT hooks.

    No-op unless both ``coin_dispersed_cells`` and ``coin_insurgency`` are on, or before
    turn 1.
    """
    if not getattr(game.settings, "coin_dispersed_cells", False):
        return
    if not getattr(game.settings, "coin_insurgency", False):
        return
    if getattr(game, "turn", 0) < 1:
        return

    state = getattr(game, "coin_state", None)
    if not isinstance(state, dict):
        state = {}
        game.coin_state = state
    cells: list[dict[str, Any]] = state.setdefault("field_cells", [])

    _age_cells(game, cells, events)
    _reseed_cells(game, cells, events)


def _age_cells(game: "Game", cells: list[dict[str, Any]], events: Any) -> None:
    survivors: list[dict[str, Any]] = []
    for cell in cells:
        tgo = _tgo_by_id(game, cell.get("tgo_id"))
        if tgo is None:
            continue  # already gone -- drop it
        if not _tgo_alive(tgo):
            # Hunted down: ordinary attrition. The resupply is denied -- that's the win.
            _despawn(game, tgo, events)
            _announce(game, "Insurgent field cell eliminated in the countryside.")
            continue
        cell["age"] = int(cell.get("age", 0)) + 1
        if cell["age"] >= MATURE_TURNS:
            _coalesce(game, cell, tgo, events)
            continue
        survivors.append(cell)
    cells[:] = survivors


def _coalesce(game: "Game", cell: dict[str, Any], tgo: Any, events: Any) -> None:
    """A matured cell reaches its home stronghold: revive a dead cache there (re-opening
    the regen throttle) or, failing that, a couple of dead militia (bounded by the anchor).
    Then the field cell melts into the base (despawned)."""
    home = _cp_by_id(game, cell.get("home_id"))
    _despawn(game, tgo, events)
    if home is None:
        return
    if _revive_dead_cache(game, home, events):
        _announce(
            game,
            f"Insurgent cell reached {home.name} — a supply cache is back in operation.",
        )
    elif _revive_militia(game, home, events):
        _announce(
            game, f"Insurgent cell reached {home.name} — the garrison is reinforced."
        )
    else:
        _announce(game, f"Insurgent cell melted into {home.name}.")


def _revive_dead_cache(game: "Game", cp: "ControlPoint", events: Any) -> bool:
    """Revive one fully-dead ammo cache at *cp* (all its units), or False if none dead."""
    for tgo in cp.ground_objects:
        if getattr(tgo, "category", None) != "ammo":
            continue
        units = list(getattr(tgo, "units", []))
        if units and not any(getattr(u, "alive", False) for u in units):
            for unit in units:
                _revive(unit, game, events)
            return True
    return False


def _revive_militia(game: "Game", cp: "ControlPoint", events: Any) -> bool:
    """Revive up to COALESCE_REVIVE dead militia at *cp*, never past the C1 anchor cap."""
    state = _ensure_anchors(game)
    anchor = state.get(str(cp.id), {}) if isinstance(state, dict) else {}
    cap = int(anchor.get("tgo_cap", 0))
    headroom = max(0, cap - _alive_cell_count(cp))
    revivable = _revivable_units(cp)[: min(COALESCE_REVIVE, headroom)]
    for unit in revivable:
        _revive(unit, game, events)
    return bool(revivable)


def _reseed_cells(game: "Game", cells: list[dict[str, Any]], events: Any) -> None:
    from game.data.groups import GroupTask

    used_homes = {cell["home_id"] for cell in cells if "home_id" in cell}
    while len(cells) < MAX_FIELD_CELLS:
        site = _pick_field_site(game, used_homes)
        if site is None:
            return  # no distinct stronghold left to project a cell from
        home, point = site
        tgo = spawn_red_ground_at(
            game,
            home,
            point,
            GroupTask.FRONT_LINE,
            events,
            max_units=FIELD_CELL_UNITS,
            sidc_override=CELL_SIDC,
        )
        if tgo is None:
            return
        used_homes.add(str(home.id))
        cells.append({"tgo_id": str(tgo.id), "age": 0, "home_id": str(home.id)})
        _announce(
            game,
            f"Intel: insurgent activity reported in the countryside near {home.name}.",
        )


def _pick_field_site(
    game: "Game", used_homes: set[str]
) -> Optional[tuple["ControlPoint", Any]]:
    """A (home red stronghold, open-field point) to seed a cell: out on the line from a
    red stronghold toward the nearest coalition CP, at least MIN_FIELD_DIST_M from every
    CP. One cell per stronghold (``used_homes`` excludes strongholds already projecting
    one), so cells spread across the countryside instead of stacking. The cell attaches
    to the stronghold (allegiance) but sits in the field. Returns None if no eligible
    stronghold+point exists (no reference, all homes used, or every point hugs a base).
    """
    blues = [
        cp
        for cp in game.theater.controlpoints
        if not cp.captured.is_red and not cp.captured.is_neutral
    ]
    reds = [
        cp
        for cp in game.theater.controlpoints
        if cp.captured.is_red and str(cp.id) not in used_homes
    ]
    if not blues or not reds:
        return None

    best: Optional[tuple[float, "ControlPoint", Any]] = None
    for red in reds:
        target = min(blues, key=lambda b: red.position.distance_to_point(b.position))
        heading = red.position.heading_between_point(target.position)
        span = red.position.distance_to_point(target.position)
        for frac in (FIELD_FRACTION, 0.55, 0.3, 0.7):
            point = red.position.point_from_heading(heading, span * frac)
            if not game.theater.is_on_land(point):
                continue
            clearance = min(
                point.distance_to_point(cp.position)
                for cp in game.theater.controlpoints
            )
            if clearance < MIN_FIELD_DIST_M:
                continue
            # Prefer sites nearer the fighting (smaller distance to the coalition CP).
            score = point.distance_to_point(target.position)
            if best is None or score < best[0]:
                best = (score, red, point)
            break
    if best is None:
        return None
    _, home, point = best
    return home, point


def _cp_by_id(game: "Game", cp_id: Optional[str]) -> Optional["ControlPoint"]:
    if cp_id is None:
        return None
    for cp in game.theater.controlpoints:
        if str(cp.id) == cp_id:
            return cp
    return None


def _tgo_alive(tgo: Any) -> bool:
    return any(getattr(unit, "alive", False) for unit in getattr(tgo, "units", []))


def _announce(game: "Game", message: str) -> None:
    try:
        game.message("Insurgent cell", message)
    except Exception:  # noqa: BLE001 -- messaging is best-effort, never break the turn
        pass
