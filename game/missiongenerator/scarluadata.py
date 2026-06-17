from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from game.ato import FlightType

if TYPE_CHECKING:
    from game import Game
    from game.missiongenerator.luagenerator import LuaData


@dataclass(frozen=True)
class ScarTasking:
    """One SCAR area, bound to units Retribution already generates.

    Rather than spawning a bespoke HVT, SCAR targets the moving/strategic ground
    content the campaign already produces (decided 2026-06-17):

    * ``convoy``  — an enemy ground transfer (``game.transfers.Convoy``). It is
      already a moving, targetable group, and killing it already denies the
      reinforcement via the existing convoy-loss economy. Success = destroyed;
      surviving the mission = the transfer completes (handled by the economy, so
      the bridge just reports it).
    * ``missile`` — a surface-to-surface missile site (``MissileSiteGroundObject``,
      category "missile"). The SCUD variant: success = destroyed before it fires;
      fail = it launches.

    ``target_groups`` are the DCS group names the Lua watches (one for a convoy,
    one-or-more for a missile site's groups).
    """

    tasking_id: str
    variant: str  # "convoy" | "missile"
    target_groups: tuple[str, ...]


def build_scar_taskings(game: "Game") -> list[ScarTasking]:
    """Build one ScarTasking per planned SCAR flight whose target is a convoy or
    missile site.

    SCAR flights against any other target type emit no tasking (the flight still
    flies its area plan, just without a SCAR scenario). Returns an empty list
    when nothing qualifies, which is the injection gate.
    """
    from game.theater.theatergroundobject import MissileSiteGroundObject
    from game.transfers import Convoy

    taskings: list[ScarTasking] = []
    index = 0
    for coalition in game.coalitions:
        for package in coalition.ato.packages:
            for flight in package.flights:
                if flight.flight_type is not FlightType.SCAR:
                    continue
                target = package.target
                if isinstance(target, Convoy):
                    variant = "convoy"
                    groups: tuple[str, ...] = (target.name,)
                elif isinstance(target, MissileSiteGroundObject):
                    variant = "missile"
                    groups = tuple(g.group_name for g in target.groups)
                else:
                    continue
                if not groups:
                    continue
                index += 1
                taskings.append(
                    ScarTasking(
                        tasking_id=f"scar-{index}",
                        variant=variant,
                        target_groups=groups,
                    )
                )
    return taskings


def populate_scar_lua(root: "LuaData", taskings: Iterable[ScarTasking]) -> None:
    """Build the ``dcsRetribution.Scar`` subtree (mirrors the intercept pattern)."""
    scar = root.add_item("Scar")
    taskings_item = scar.get_or_create_item("taskings")
    for tasking in taskings:
        record = taskings_item.add_item()
        record.add_key_value("taskingId", tasking.tasking_id)
        record.add_key_value("variant", tasking.variant)
        record.add_data_array("targetGroups", list(tasking.target_groups))
