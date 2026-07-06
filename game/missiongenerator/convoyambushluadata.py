"""Convoy ambush -> Lua config bridge (``dcsRetribution.convoyAmbush``).

The runtime half of the convoy ambush feature (§50). The turn-boundary force model
(``game/fourteenth/convoy_ambush.py``) has already rolled each active blue supply convoy
for an ambush and, where the roll hit, seeded 1..6 real, map-hidden red ambush teams along
its road, recording each pairing on ``game.convoy_ambush_state``. This emitter lists, for
each pairing, the ambush team's DCS group names + position and the targeted convoy's group
name, and the ``convoyambush`` plugin *springs* the ambush at runtime: the team digs in
holding fire (alarm-green / weapons-hold) until the convoy closes inside a trigger radius,
then goes weapons-free with a "troops in contact" cue + an F10 mark. Nothing about the
ambush shows in the campaign UI beforehand -- the in-mission call is the first sign, and
supporting the column is the player's decision.

**Cosmetics / ROE only** -- the plugin owns no kills. The convoy and the ambushers are
real, tracked units, so whatever the firefight resolves is reconciled natively at debrief
(dead convoy units never arrive; dead ambushers are a real red ground loss). The plugin
just decides *when* a dug-in team opens up; a team the convoy never reaches stays silent.

Emits nothing unless ``convoy_ambush`` is on and at least one live ambush pairing exists,
so a normal mission carries no ``convoyAmbush`` node and the plugin no-ops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData


def populate_convoy_ambush_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Build the ``dcsRetribution.convoyAmbush`` subtree (the spring-the-ambush movers)."""
    if not getattr(game.settings, "convoy_ambush", False):
        return
    state = getattr(game, "convoy_ambush_state", None)
    if not isinstance(state, dict):
        return

    ambushes: list[dict[str, Any]] = []
    for record in state.get("ambushes", []):
        if not isinstance(record, dict):
            continue
        tgo = _tgo_by_id(game, record.get("tgo_id"))
        if tgo is None:
            continue
        groups = _alive_group_names(tgo)
        pos = _position(tgo)
        if not groups or pos is None:
            continue
        entry: dict[str, Any] = {"groups": groups, "x": pos.x, "y": pos.y}
        convoy_name = record.get("convoy")
        if convoy_name:
            entry["convoyGroups"] = [str(convoy_name)]
        ambushes.append(entry)

    if not ambushes:
        return

    node = root.add_item("convoyAmbush")
    ambush_list = node.add_item("ambushes")
    for ambush in ambushes:
        rec = ambush_list.add_item()
        # The exact names Group.getByName needs (TheaterGroup.group_name / the convoy's
        # generated VehicleGroup name).
        rec.add_data_array("groups", ambush["groups"])
        # pydcs Point: x = north, y = east (the frame the coin / mobile-missile plugins
        # share; mist.utils maps it straight onto the DCS position).
        rec.add_key_value("x", str(ambush["x"]))
        rec.add_key_value("y", str(ambush["y"]))
        if "convoyGroups" in ambush:
            rec.add_data_array("convoyGroups", ambush["convoyGroups"])


def _tgo_by_id(game: "Game", tgo_id: Optional[str]) -> Any:
    if tgo_id is None:
        return None
    for cp in game.theater.controlpoints:
        for tgo in cp.ground_objects:
            if str(tgo.id) == str(tgo_id):
                return tgo
    return None


def _alive_group_names(tgo: Any) -> list[str]:
    """The TGO's groups that still hold at least one alive unit -- the metal the plugin can
    route / arm. A fully-dead team has nothing to spring and is dropped."""
    names: list[str] = []
    for group in getattr(tgo, "groups", []):
        name = getattr(group, "group_name", None)
        if not name:
            continue
        if any(getattr(u, "alive", False) for u in getattr(group, "units", [])):
            names.append(name)
    return names


def _position(tgo: Any) -> Any:
    pos = getattr(tgo, "position", None)
    if pos is None or not hasattr(pos, "x") or not hasattr(pos, "y"):
        return None
    return pos
