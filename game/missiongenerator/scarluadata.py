from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from game.ato import FlightType

if TYPE_CHECKING:
    from game import Game
    from game.missiongenerator.luagenerator import LuaData

# --- Bridge-skeleton placeholders (spec docs/dev/design/414th-scar-task-spec.md) ---
# The real SCAR HVT is a multi-unit signature convoy (e.g. SA-9 + command + 2
# trucks) with decoys, clutter, and a threat laydown, composed in a later
# increment. For the integration bridge we emit a SINGLE vanilla truck plus a
# no-strike destination so the Lua side can prove the full loop: spawn -> route
# -> pass (HVT killed) / fail (HVT reaches destination) -> result back to the
# campaign. Coordinates use the DCS vec2 convention (x = north, y = east), so
# pydcs Point.x -> x and Point.y -> y map straight through to the Lua side.
SCAR_HVT_UNIT_TYPE = "Ural-375"  # vanilla DCS truck; placeholder HVT
SCAR_HVT_SPAWN_OFFSET_M = 4000.0  # HVT spawns this far north of the area center
SCAR_HVT_DEST_OFFSET_M = 4000.0  # no-strike destination this far south
SCAR_FAIL_ZONE_RADIUS_M = 500.0  # HVT entering this zone = mission failed


@dataclass(frozen=True)
class ScarTasking:
    """One SCAR area for the Lua scenario layer to run.

    Skeleton shape: enough to spawn a placeholder HVT, route it to a no-strike
    destination, and report pass/fail. Extended (decoys/clutter/threat/
    signature) in later increments.
    """

    tasking_id: str
    coalition: str  # the SCAR flight's coalition color ("blue"/"red")
    hvt_country_id: int  # enemy country id the placeholder HVT spawns under
    hvt_unit_type: str
    area_x: float
    area_y: float
    hvt_spawn_x: float
    hvt_spawn_y: float
    hvt_dest_x: float
    hvt_dest_y: float
    fail_zone_radius_m: float


def build_scar_taskings(game: "Game") -> list[ScarTasking]:
    """Build one ScarTasking per planned SCAR flight, both coalitions.

    Skeleton: derives a placeholder HVT spawn + no-strike destination from each
    SCAR flight's target area. Returns an empty list when no SCAR flight is
    planned (the injection gate), so the plugin is inert unless used.
    """
    taskings: list[ScarTasking] = []
    index = 0
    for coalition in game.coalitions:
        color = "blue" if coalition.player else "red"
        enemy_country_id = coalition.opponent.faction.country.id
        for package in coalition.ato.packages:
            for flight in package.flights:
                if flight.flight_type is not FlightType.SCAR:
                    continue
                pos = package.target.position
                index += 1
                taskings.append(
                    ScarTasking(
                        tasking_id=f"scar-{index}",
                        coalition=color,
                        hvt_country_id=enemy_country_id,
                        hvt_unit_type=SCAR_HVT_UNIT_TYPE,
                        area_x=pos.x,
                        area_y=pos.y,
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
        record.add_key_value("coalition", tasking.coalition)
        record.add_key_value("hvtCountryId", str(tasking.hvt_country_id))
        record.add_key_value("hvtType", tasking.hvt_unit_type)
        record.add_key_value("areaX", str(tasking.area_x))
        record.add_key_value("areaY", str(tasking.area_y))
        record.add_key_value("hvtSpawnX", str(tasking.hvt_spawn_x))
        record.add_key_value("hvtSpawnY", str(tasking.hvt_spawn_y))
        record.add_key_value("hvtDestX", str(tasking.hvt_dest_x))
        record.add_key_value("hvtDestY", str(tasking.hvt_dest_y))
        record.add_key_value("failZoneRadius", str(tasking.fail_zone_radius_m))
