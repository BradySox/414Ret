"""COIN in-mission liveliness -> Lua config bridge (``dcsRetribution.coin``).

The COIN layer (``game/fourteenth/coin*.py``) is a turn-boundary force-model system: it
spawns / ages / despawns recon-fogged red TGOs and adjudicates their consequences (an
IED's fuse, an HVT's strike window) at ``finish_turn``. This emitter adds the things
the force model cannot express -- **in-mission movement and ambient pressure** --
following the Vietnam-Ops / Combat-SAR pattern: Python emits which spawned groups should
move (and which friendly bases sit inside the insurgency's mortar reach), and the
``coin`` plugin drives it all at runtime.

The *consequence* stays entirely in Python (kill the HVT convoy or the VBIED before the
turn ends -> decapitated / intercepted; let it live -> the window / fuse resolves against
the mandate), so the Lua side is **movement + cosmetics only** -- no scoring, no spawns,
no deaths it owns. That keeps the deliberate "COIN is a force-model economy" architecture
intact and means a shot-down mover is recorded natively, exactly like the static objects.

Movers: the HVT convoy (patrol loop), each mobile VBIED (drives at a friendly base), each
C4 **dispersed field cell** (wanders its patch of countryside), and the live C1.5
**re-infiltration cell** (creeps toward the base it is infiltrating). **Harassment**
(``coin_harassment``): each blue-held airfield/FARP/FOB within mortar reach of a red
stronghold draws sporadic insurgent indirect fire at runtime -- the §36
airbase-harassment shape, with the same hard never-a-player-spawn-field guarantee
(filtered here, double-guarded in the Lua).

Emits nothing unless ``coin_insurgency`` is on and at least one mover or harassable base
exists, so a non-COIN mission carries no ``coin`` node and the plugin no-ops. Static
roadside IEDs never move, so they are never emitted here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint

    from .luagenerator import LuaData, LuaItem
    from .missiondata import MissionData

#: How near a red stronghold a blue base must sit to draw insurgent indirect fire.
#: Mortar/rocket teams operate out of the strongholds' orbit -- a base beyond this is
#: outside the insurgency's reach and is never shelled (forward-only by construction,
#: the §36 design rule).
HARASS_STRONGHOLD_REACH_M = 40_000.0


def populate_coin_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Build the ``dcsRetribution.coin`` subtree (movers + base harassment)."""
    settings = game.settings
    if not getattr(settings, "coin_insurgency", False):
        return
    state = getattr(game, "coin_state", None)
    if not isinstance(state, dict):
        state = {}

    hvt = _hvt_movement(game, state) if getattr(settings, "coin_hvt", False) else None
    vbieds = (
        _vbied_movements(game, state) if getattr(settings, "coin_ied", False) else []
    )
    cells = (
        _cell_movements(game, state)
        if getattr(settings, "coin_dispersed_cells", False)
        else []
    )
    infiltrators = (
        _infiltrator_movements(game, state)
        if getattr(settings, "coin_reinfiltration", False)
        else []
    )
    harassment = (
        _harassment_bases(game) if getattr(settings, "coin_harassment", False) else None
    )
    if (
        hvt is None
        and not vbieds
        and not cells
        and not infiltrators
        and harassment is None
    ):
        return

    coin = root.add_item("coin")

    if hvt is not None:
        item = coin.add_item("hvt")
        _emit_groups(item, hvt["groups"])
        # pydcs Point: x = north, y = east. The Lua maps these onto the DCS ground
        # waypoint the same way the Vietnam-Ops emitter does for its impact points.
        item.add_key_value("x", str(hvt["x"]))
        item.add_key_value("y", str(hvt["y"]))

    if vbieds:
        vlist = coin.add_item("vbieds")
        for v in vbieds:
            rec = vlist.add_item()
            _emit_groups(rec, v["groups"])
            rec.add_key_value("x", str(v["x"]))
            rec.add_key_value("y", str(v["y"]))
            rec.add_key_value("targetX", str(v["targetX"]))
            rec.add_key_value("targetY", str(v["targetY"]))

    if cells:
        clist = coin.add_item("cells")
        for c in cells:
            rec = clist.add_item()
            _emit_groups(rec, c["groups"])
            rec.add_key_value("x", str(c["x"]))
            rec.add_key_value("y", str(c["y"]))

    if infiltrators:
        ilist = coin.add_item("infiltrators")
        for rec_data in infiltrators:
            rec = ilist.add_item()
            _emit_groups(rec, rec_data["groups"])
            rec.add_key_value("x", str(rec_data["x"]))
            rec.add_key_value("y", str(rec_data["y"]))
            rec.add_key_value("targetX", str(rec_data["targetX"]))
            rec.add_key_value("targetY", str(rec_data["targetY"]))

    if harassment is not None:
        harass = coin.add_item("harassment")
        blist = harass.add_item("bases")
        for name, x, y in harassment["bases"]:
            rec = blist.add_item()
            rec.add_key_value("name", name)
            rec.add_key_value("x", str(x))
            rec.add_key_value("y", str(y))
        # Defense-in-depth (the §36 double-guard): the runtime only sees eligible
        # bases, but emitting the player-spawn names it must never touch lets the
        # Lua log the guard and skip any name match.
        if harassment["excluded"]:
            excluded_item = harass.add_item("excludedBases")
            for excluded_name in harassment["excluded"]:
                excluded_item.add_item().set_value(excluded_name)


def _emit_groups(item: "LuaItem", names: list[str]) -> None:
    """Emit ``groups = { "<DCS group name>", ... }`` -- the exact names
    ``Group.getByName`` needs (``TheaterGroup.group_name``, what the generator stamps onto
    the .miz vehicle group). A data-array (not a child object) so it can share the record
    with the position key-values (a LuaData item serializes either child objects *or*
    key-values, never both)."""
    item.add_data_array("groups", names)


def _hvt_movement(game: "Game", state: dict[str, Any]) -> Optional[dict[str, Any]]:
    hvt = state.get("hvt") or {}
    active = hvt.get("active")
    if not isinstance(active, dict):
        return None
    tgo = _tgo_by_id(game, active.get("tgo_id"))
    if tgo is None:
        return None
    names = _group_names(tgo)
    pos = _position(tgo)
    if not names or pos is None:
        return None
    return {"groups": names, "x": pos.x, "y": pos.y}


def _vbied_movements(game: "Game", state: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ied in state.get("ieds", []):
        if not isinstance(ied, dict) or ied.get("kind") != "vbied":
            continue
        tgo = _tgo_by_id(game, ied.get("tgo_id"))
        if tgo is None:
            continue
        names = _group_names(tgo)
        pos = _position(tgo)
        if not names or pos is None:
            continue
        target = _nearest_blue_cp(game, pos)
        if target is None:
            continue
        out.append(
            {
                "groups": names,
                "x": pos.x,
                "y": pos.y,
                "targetX": target.position.x,
                "targetY": target.position.y,
            }
        )
    return out


def _cell_movements(game: "Game", state: dict[str, Any]) -> list[dict[str, Any]]:
    """The C4 dispersed field cells -- each wanders a small loop around its own patch
    of countryside (the plugin's cell mover), so patrolling for them means catching
    something *moving*, not overflying a parked marker."""
    out: list[dict[str, Any]] = []
    for cell in state.get("field_cells", []):
        if not isinstance(cell, dict):
            continue
        tgo = _tgo_by_id(game, cell.get("tgo_id"))
        if tgo is None:
            continue
        names = _group_names(tgo)
        pos = _position(tgo)
        if not names or pos is None:
            continue
        out.append({"groups": names, "x": pos.x, "y": pos.y})
    return out


def _infiltrator_movements(game: "Game", state: dict[str, Any]) -> list[dict[str, Any]]:
    """The live C1.5 re-infiltration cell -- creeps slowly toward the base it is
    infiltrating (movement only; the staged flip stays in the turn model)."""
    rf = state.get("reinfiltration")
    if not isinstance(rf, dict):
        return []
    active = rf.get("active")
    if not isinstance(active, dict):
        return []
    tgo = _tgo_by_id(game, active.get("cell_tgo"))
    if tgo is None:
        return []
    names = _group_names(tgo)
    pos = _position(tgo)
    target = _cp_by_id(game, active.get("cp_id"))
    if not names or pos is None or target is None:
        return []
    return [
        {
            "groups": names,
            "x": pos.x,
            "y": pos.y,
            "targetX": target.position.x,
            "targetY": target.position.y,
        }
    ]


def _harassment_bases(game: "Game") -> Optional[dict[str, Any]]:
    """Blue-held airfields/FARPs/FOBs within :data:`HARASS_STRONGHOLD_REACH_M` of a
    red stronghold, minus every player-spawn field this mission (the hard §36
    anti-grief guarantee -- filtered here, never emitted). ``None`` when no base
    qualifies (no red CPs left, nothing in reach), so the plugin no-ops."""
    from game.theater import ControlPointType

    harassable = {
        ControlPointType.AIRBASE,
        ControlPointType.FARP,
        ControlPointType.FOB,
    }
    reds = [cp for cp in game.theater.controlpoints if cp.captured.is_red]
    if not reds:
        return None

    excluded = _client_spawn_control_points(game)
    bases: list[tuple[str, float, float]] = []
    for cp in game.theater.controlpoints:
        if not cp.captured.is_blue:
            continue
        if getattr(cp, "cptype", None) not in harassable:
            continue
        if any(other is cp for other in excluded):
            continue
        reach = min(red.position.distance_to_point(cp.position) for red in reds)
        if reach > HARASS_STRONGHOLD_REACH_M:
            continue
        bases.append((_cp_name(cp), cp.position.x, cp.position.y))

    if not bases:
        return None
    return {"bases": bases, "excluded": [_cp_name(cp) for cp in excluded]}


def _client_spawn_control_points(game: "Game") -> list["ControlPoint"]:
    """Fields a player flight uses this mission -- the hard *never-harass* exclude set
    (the §36 walk: every client flight's departure/arrival/divert on both sides).
    Identity-deduplicated list (not a set, so duck-typed CPs need no __hash__)."""
    excluded: list["ControlPoint"] = []

    def add(cp: Any) -> None:
        if cp is not None and not any(other is cp for other in excluded):
            excluded.append(cp)

    for coalition in getattr(game, "coalitions", []):
        for package in coalition.ato.packages:
            for flight in package.flights:
                if flight.client_count <= 0:
                    continue
                add(flight.departure)
                add(flight.arrival)
                add(flight.divert)
    return excluded


def _cp_name(cp: Any) -> str:
    return str(getattr(cp, "full_name", None) or getattr(cp, "name", ""))


def _cp_by_id(game: "Game", cp_id: Any) -> Optional["ControlPoint"]:
    if cp_id is None:
        return None
    for cp in game.theater.controlpoints:
        if str(cp.id) == str(cp_id):
            return cp
    return None


def _group_names(tgo: Any) -> list[str]:
    return [
        g.group_name
        for g in getattr(tgo, "groups", [])
        if getattr(g, "group_name", None)
    ]


def _position(tgo: Any) -> Any:
    pos = getattr(tgo, "position", None)
    if pos is None or not hasattr(pos, "x") or not hasattr(pos, "y"):
        return None
    return pos


def _tgo_by_id(game: "Game", tgo_id: Optional[str]) -> Any:
    if tgo_id is None:
        return None
    for cp in game.theater.controlpoints:
        for tgo in cp.ground_objects:
            if str(tgo.id) == str(tgo_id):
                return tgo
    return None


def _nearest_blue_cp(game: "Game", point: Any) -> Optional["ControlPoint"]:
    best: Optional[tuple[float, "ControlPoint"]] = None
    for cp in game.theater.controlpoints:
        if not cp.captured.is_blue:
            continue
        dist = point.distance_to_point(cp.position)
        if best is None or dist < best[0]:
            best = (dist, cp)
    return best[1] if best is not None else None
