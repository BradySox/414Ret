"""Cross-turn naval magazines -> Lua config bridge (``dcsRetribution.navalMagazines``).

The §81 emitter. Python owns the campaign side (the persisted per-group
anti-ship stock — ``game/fourteenth/naval_magazines``); this hands the
``navalmagazines`` plugin N2's per-group stock: ``group``/``coalition``/
``remaining`` anti-ship missiles. The plugin counts real ``S_EVENT_SHOT``
releases and drops a spent group back to ``ReturnFire``.

**N1 is not here.** The weapons-release stagger is authored at generation as a
start-conditioned ``ControlledTask`` on each ship group
(``TgoGenerator.set_ship_engagement``), because "at time T, set this group's
ROE" is exactly what a DCS start condition expresses — no runtime needed, and
no plugin a host can untick to silently disable it. Only the magazine, which
must count weapon releases as they happen, needs a script at all.

The plugin mirrors what actually fired into the ``naval_magazines_state``
debrief channel; the turn boundary debits from that report, never from this
emit — so re-generating the mission is free.

Emits nothing unless metering is on and a live naval group exists, so a normal
mission carries no ``navalMagazines`` node and the plugin no-ops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game

    from .luagenerator import LuaData
    from .missiondata import MissionData


def populate_naval_magazines_lua(
    root: "LuaData", game: "Game", mission_data: "MissionData"
) -> None:
    """Build the ``dcsRetribution.navalMagazines`` subtree."""
    if not bool(getattr(game.settings, "naval_magazines", False)):
        return

    from game.fourteenth.naval_magazines import naval_group_magazines

    groups = naval_group_magazines(game)
    if not groups:
        return

    node = root.add_item("navalMagazines")
    group_list = node.add_item("magazines")
    for group in groups:
        rec = group_list.add_item()
        # The exact name Group.getByName needs (TheaterGroup.group_name, what the
        # generator stamps onto the .miz ship group).
        rec.add_key_value("group", group.group_name)
        rec.add_key_value("coalition", group.coalition)
        rec.add_key_value("remaining", str(group.remaining))
