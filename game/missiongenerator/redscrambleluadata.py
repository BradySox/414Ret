"""Host red-scramble -> Lua config bridge (``dcsRetribution.redScramble``).

The "give the boys something to shoot" button (§61): with ``host_red_scramble`` on,
the mission carries cold late-activation red interceptor templates (built by
``AircraftGenerator.spawn_red_scramble_templates``, the QRA clone pattern) plus the
list of red airfields, and the ``redscramble`` plugin exposes a host-only F10 menu
that clones a flight from any listed base and force-vectors it onto the nearest
airborne BLUE fighters -- an emergency GM tool for a multiplayer event gone quiet
after the first wave.

Who sees the menu is a *runtime* decision (the plugin's ``hostPlayers`` option, a
comma-separated DCS player-name list) because Retribution cannot know multiplayer
player names at generation time. This module only decides *what exists*:

* ``templates`` -- up to :data:`MAX_RED_SCRAMBLE_TYPES` distinct red fighter types
  (best BARCAP airframe first, so the menu leads with the sharpest interceptor and
  the plugin's one-click EMERGENCY command launches it).
* ``bases`` -- every red-held airfield, sorted nearest-front first so the most
  useful fields survive the Lua side's menu cap.

**Spawns are untracked by design** (the §20 drop-spawn cheat precedent, not the
§35/§37 no-phantom-spawn force-model rule): a host-summoned bandit is an event-tool
freebie -- red pays nothing, its loss changes nothing next turn -- so this must stay
a deliberate host action, never an automatic system.

Emits nothing when the setting is off, no template could be built, or no red
airfield exists -- such missions carry no ``redScramble`` node and the plugin
no-ops.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData

#: How many distinct red fighter types get a clone template (menu breadth; each is
#: one more late-activation group in the .miz).
MAX_RED_SCRAMBLE_TYPES = 4


@dataclass(frozen=True)
class RedScrambleTemplate:
    """One cold late-activation red interceptor template the plugin may clone."""

    #: Exact .miz group name (what MOOSE ``SPAWN:NewWithAlias`` needs).
    group_name: str
    #: Menu label (the airframe's variant id, e.g. "MiG-29S").
    label: str


def populate_red_scramble_lua(
    root: "LuaData", game: "Game", mission_data: Optional["MissionData"] = None
) -> None:
    """Build the ``dcsRetribution.redScramble`` subtree (templates + red bases)."""
    if not getattr(game.settings, "host_red_scramble", False):
        return
    templates = mission_data.red_scramble_templates if mission_data else []
    if not templates:
        return
    bases = _red_airfields_front_first(game)
    if not bases:
        return

    node = root.add_item("redScramble")
    template_node = node.get_or_create_item("templates")
    for template in templates:
        record = template_node.add_item()
        record.add_key_value("group", template.group_name)
        record.add_key_value("label", template.label)
    base_node = node.get_or_create_item("bases")
    for name in bases:
        record = base_node.add_item()
        record.add_key_value("name", name)


def _red_airfields_front_first(game: "Game") -> list[str]:
    """Red-held airfield names, nearest active front first.

    The Lua side caps the menu at its per-level item budget, so ordering decides
    which bases a big theater keeps: the fields closest to the fight are the ones
    a host actually scrambles from. A front-less theater lists alphabetically
    (every distance is 0 and the name tiebreak decides), which also keeps the
    emit deterministic.
    """
    from game.theater import Airfield

    front_positions = [front.position for front in game.theater.conflicts()]

    entries: list[tuple[float, str]] = []
    for cp in game.theater.controlpoints:
        if not isinstance(cp, Airfield):
            continue
        if cp.captured.is_blue or cp.captured.is_neutral:
            continue
        distance = 0.0
        if front_positions:
            distance = min(
                cp.position.distance_to_point(position) for position in front_positions
            )
        entries.append((distance, cp.name))
    entries.sort(key=lambda entry: (entry[0], entry[1]))
    return [name for _, name in entries]
