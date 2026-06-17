from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from game.ato import FlightType

if TYPE_CHECKING:
    from game import Game
    from game.missiongenerator.luagenerator import LuaData

# --- Spawned-HVT parameters (the "spawn" variant) ---------------------------------
# AI convoys are rare, so SCAR can't rely on the campaign producing a moving
# target; the generator spawns one so the task is always available (spec §5).
# v1 is a SINGLE vanilla truck routed to a no-strike destination; the real
# signature convoy (SA-9 + command + trucks) + decoys/clutter is a later
# increment. Coordinates use the DCS vec2 convention (x = north, y = east), so
# pydcs Point.x -> x and Point.y -> y map straight through to the Lua side.
SCAR_HVT_UNIT_TYPE = "Ural-375"  # vanilla DCS truck; placeholder HVT
SCAR_HVT_SPAWN_OFFSET_M = 4000.0  # HVT spawns this far north of the area center
SCAR_HVT_DEST_OFFSET_M = 4000.0  # no-strike destination this far south
SCAR_FAIL_ZONE_RADIUS_M = 500.0  # HVT entering this zone = mission failed


@dataclass(frozen=True)
class ScarTasking:
    """One SCAR area for the Lua scenario layer to run.

    Two variants (decided 2026-06-17 — spawn by default since AI convoys are
    rare, but bind to a real missile site when the player targets one):

    * ``spawn``  — the generator spawns a moving HVT and routes it to a
      no-strike destination. success = HVT destroyed; fail = HVT reaches the
      destination zone. Always available.
    * ``missile`` — the SCAR target IS a real surface-to-surface missile site
      (``MissileSiteGroundObject``, the SCUD variant). Watch-only, no spawn.
      success = site destroyed; fail = it launches.

    Only the fields for the active variant are meaningful; the rest stay at
    their defaults and are not emitted.
    """

    tasking_id: str
    variant: str  # "spawn" | "missile"
    # variant "missile":
    target_groups: tuple[str, ...] = ()
    # variant "spawn":
    hvt_country_id: int = 0
    hvt_unit_type: str = ""
    hvt_spawn_x: float = 0.0
    hvt_spawn_y: float = 0.0
    hvt_dest_x: float = 0.0
    hvt_dest_y: float = 0.0
    fail_zone_radius_m: float = 0.0


def build_scar_taskings(game: "Game") -> list[ScarTasking]:
    """Build one ScarTasking per planned SCAR flight.

    A SCAR flight against a real missile site binds to it ("missile"); every
    other SCAR flight gets a spawned HVT ("spawn") derived from its target area.
    Returns an empty list when no SCAR flight is planned (the injection gate).
    """
    from game.theater.theatergroundobject import MissileSiteGroundObject

    taskings: list[ScarTasking] = []
    index = 0
    for coalition in game.coalitions:
        enemy_country_id = coalition.opponent.faction.country.id
        for package in coalition.ato.packages:
            for flight in package.flights:
                if flight.flight_type is not FlightType.SCAR:
                    continue
                target = package.target
                index += 1
                if isinstance(target, MissileSiteGroundObject):
                    groups = tuple(g.group_name for g in target.groups)
                    if not groups:
                        index -= 1
                        continue
                    taskings.append(
                        ScarTasking(
                            tasking_id=f"scar-{index}",
                            variant="missile",
                            target_groups=groups,
                        )
                    )
                else:
                    pos = target.position
                    taskings.append(
                        ScarTasking(
                            tasking_id=f"scar-{index}",
                            variant="spawn",
                            hvt_country_id=enemy_country_id,
                            hvt_unit_type=SCAR_HVT_UNIT_TYPE,
                            hvt_spawn_x=pos.x + SCAR_HVT_SPAWN_OFFSET_M,
                            hvt_spawn_y=pos.y,
                            hvt_dest_x=pos.x - SCAR_HVT_DEST_OFFSET_M,
                            hvt_dest_y=pos.y,
                            fail_zone_radius_m=SCAR_FAIL_ZONE_RADIUS_M,
                        )
                    )
    return taskings


def populate_scar_lua(root: "LuaData", taskings: Iterable[ScarTasking]) -> None:
    """Build the ``dcsRetribution.Scar`` subtree (mirrors the intercept pattern).

    Numeric fields are emitted as strings (the LuaData serializer quotes all
    values), so the Lua side ``tonumber()``s them.
    """
    scar = root.add_item("Scar")
    taskings_item = scar.get_or_create_item("taskings")
    for tasking in taskings:
        record = taskings_item.add_item()
        record.add_key_value("taskingId", tasking.tasking_id)
        record.add_key_value("variant", tasking.variant)
        if tasking.variant == "missile":
            record.add_data_array("targetGroups", list(tasking.target_groups))
        else:
            record.add_key_value("hvtCountryId", str(tasking.hvt_country_id))
            record.add_key_value("hvtType", tasking.hvt_unit_type)
            record.add_key_value("hvtSpawnX", str(tasking.hvt_spawn_x))
            record.add_key_value("hvtSpawnY", str(tasking.hvt_spawn_y))
            record.add_key_value("hvtDestX", str(tasking.hvt_dest_x))
            record.add_key_value("hvtDestY", str(tasking.hvt_dest_y))
            record.add_key_value("failZoneRadius", str(tasking.fail_zone_radius_m))
