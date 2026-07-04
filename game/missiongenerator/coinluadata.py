"""COIN in-mission movement -> Lua config bridge (``dcsRetribution.coin``).

The COIN layer (``game/fourteenth/coin*.py``) is a turn-boundary force-model system: it
spawns / ages / despawns recon-fogged red TGOs and adjudicates their consequences (an
IED's fuse, an HVT's strike window) at ``finish_turn``. This emitter adds the one thing
the force model cannot express -- **in-mission movement** -- following the Vietnam-Ops /
Combat-SAR pattern: Python emits which spawned groups should move and where, and the
``coin`` plugin drives them at runtime.

The *consequence* stays entirely in Python (kill the HVT convoy or the VBIED before the
turn ends -> decapitated / intercepted; let it live -> the window / fuse resolves against
the mandate), so the Lua side is **movement only** -- no scoring, no spawns, no deaths it
owns. That keeps the deliberate "COIN is a force-model economy" architecture intact and
means a shot-down mover is recorded natively, exactly like the static objects.

Emits nothing unless ``coin_insurgency`` is on and at least one moving object exists
(a live HVT and/or a live mobile VBIED), so a non-COIN mission carries no ``coin`` node
and the plugin no-ops. Static roadside IEDs never move, so they are never emitted here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint

    from .luagenerator import LuaData, LuaItem
    from .missiondata import MissionData


def populate_coin_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Build the ``dcsRetribution.coin`` subtree (HVT patrol + mobile VBIED drives)."""
    settings = game.settings
    if not getattr(settings, "coin_insurgency", False):
        return
    state = getattr(game, "coin_state", None)
    if not isinstance(state, dict):
        return

    hvt = _hvt_movement(game, state) if getattr(settings, "coin_hvt", False) else None
    vbieds = (
        _vbied_movements(game, state) if getattr(settings, "coin_ied", False) else []
    )
    if hvt is None and not vbieds:
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
