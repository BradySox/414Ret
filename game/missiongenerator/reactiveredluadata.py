"""Reactive red -> Lua config bridge (``dcsRetribution.reactiveRed``, §89 P5).

The war reacts to being hit: with both §89 gates on, the ``reactivered``
plugin watches the red objectives blue's own ATO is tasked against; when one
of their units dies, ONE red reaction-alert flight launches after a tasking
delay and flies a defensive CAP orbit over the struck objective.

The safety shape is the standard positive list, both halves emitted here and
neither widenable by Lua:

* **What may be reacted to** -- only red ground objects that are actual
  targets of blue ATO packages this turn (name, position, alive unit names:
  the death events the plugin listens for).
* **Who may react** -- only the reaction-alert flights the planner really
  fragged (``plan_red_reactions``, real claimed airframes in the red ATO,
  parked past the mission until activated). The pool is the cap.

The plugin's only powers are ``Group.activate()`` on a listed group and an
orbit task over a listed objective -- no spawns, no kills, no new force.
Emits nothing when either gate is off, no watched objective exists, or no
reaction flight was fragged; the plugin then idles with a log line.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from game.fourteenth.living_battlespace import REACTION_PACKAGE_PREFIX

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData


@dataclass
class WatchedObjective:
    """One red objective blue is tasked against: the display name, the map
    position the reaction orbits, and the alive unit names whose death events
    the plugin listens for."""

    name: str
    x: float
    y: float
    unit_names: list[str]


@dataclass
class ReactiveRedInfo:
    """The mission's reaction plan, stored on ``MissionData.reactive_red``."""

    watched: list[WatchedObjective] = field(default_factory=list)
    reaction_groups: list[str] = field(default_factory=list)


def plan_reactive_red(
    game: Game, mission_data: MissionData
) -> Optional[ReactiveRedInfo]:
    """Build the reaction plan, or None when the feature has nothing to do."""
    settings = game.settings
    if not getattr(settings, "living_battlespace_preroll", False):
        return None
    if not getattr(settings, "living_battlespace_reactive_red", False):
        return None
    watched = _watched_objectives(game)
    groups = _reaction_groups(mission_data)
    if not watched or not groups:
        if groups and not watched:
            logging.info("REACTRED: no blue-targeted red objective; plugin idle")
        return None
    return ReactiveRedInfo(watched, groups)


def _watched_objectives(game: Game) -> list[WatchedObjective]:
    """Red ground objects that are targets of blue ATO packages this turn."""
    out: list[WatchedObjective] = []
    seen: set[str] = set()
    for package in game.blue.ato.packages:
        target = package.target
        cp = getattr(target, "control_point", None)
        captured = getattr(cp, "captured", None)
        if captured is None or not getattr(captured, "is_red", False):
            continue
        unit_names = _alive_unit_names(target)
        position = getattr(target, "position", None)
        if not unit_names or position is None or not hasattr(position, "x"):
            continue
        name = str(getattr(target, "name", "objective"))
        if name in seen:
            continue
        seen.add(name)
        out.append(WatchedObjective(name, position.x, position.y, unit_names))
    return out


def _alive_unit_names(tgo: Any) -> list[str]:
    names: list[str] = []
    for group in getattr(tgo, "groups", []):
        for unit in getattr(group, "units", []):
            unit_name = getattr(unit, "unit_name", None)
            if unit_name and getattr(unit, "alive", False):
                names.append(unit_name)
    return names


def _reaction_groups(mission_data: MissionData) -> list[str]:
    """The generated reaction-alert groups, found by their package name.

    Reads mission_data.FLIGHTS, never .packages: generate_flights clears
    .packages per coalition, so only the last ATO survives it (the 2026-08-15
    turn-3 smoke-generation finding).
    """
    out: list[str] = []
    for flight_data in getattr(mission_data, "flights", []):
        side = getattr(flight_data, "friendly", None)
        if side is None or not getattr(side, "is_red", False):
            continue
        # The marker lives on the PACKAGE. FlightData.custom_name is the
        # flight's own (always None for these flights) -- matching it left
        # reactive red silently empty (the 2026-08-15 spectator-cut finding).
        package = getattr(flight_data, "package", None)
        custom = getattr(package, "custom_name", None) or ""
        if not str(custom).startswith(REACTION_PACKAGE_PREFIX):
            continue
        out.append(flight_data.group_name)
    return sorted(out)


def populate_reactive_red_lua(root: LuaData, mission_data: MissionData) -> None:
    """Emit the ``dcsRetribution.reactiveRed`` subtree from the stored plan."""
    info = getattr(mission_data, "reactive_red", None)
    if info is None or not info.watched or not info.reaction_groups:
        return
    node = root.add_item("reactiveRed")
    node.add_data_array("groups", info.reaction_groups)
    objective_list = node.add_item("objectives")
    for objective in info.watched:
        rec = objective_list.add_item()
        rec.add_key_value("name", objective.name)
        rec.add_data_array("units", objective.unit_names)
        rec.add_key_value("x", str(objective.x))
        rec.add_key_value("y", str(objective.y))
