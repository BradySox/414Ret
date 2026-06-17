from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from game.ato import FlightType

if TYPE_CHECKING:
    from dcs.mapping import Point

    from game import Game
    from game.missiongenerator.luagenerator import LuaData

# --- Spawned ground picture (the "spawn" variant, spec §5) -------------------------
# AI convoys are rare, so SCAR can't rely on the campaign producing a moving
# target; the generator spawns the whole picture so the task is always available.
#
# The discrimination puzzle (spec R2-R4): the HVT carries a complete,
# glance-readable signature; each decoy is a PARTIAL signature (drops one
# distinctive element); clutter is plain trucks. All vanilla DCS units. Unit-type
# ids verified against pydcs. Coordinates use the DCS vec2 convention (x = north,
# y = east), so pydcs Point.x -> x and Point.y -> y map straight to the Lua side.
SCAR_HVT_SAM = "Strela-1 9P31"  # SA-9 — the distinctive element
SCAR_COMMAND = "Ural-375 PBU"  # command vehicle
SCAR_TRUCK = "Ural-375"  # support / clutter truck

# Full HVT signature: SA-9 + command + 2 support trucks.
SCAR_HVT_SIGNATURE: tuple[str, ...] = (
    SCAR_HVT_SAM,
    SCAR_COMMAND,
    SCAR_TRUCK,
    SCAR_TRUCK,
)
# Decoys (<=2), each PARTIAL — never the full element set: one drops the SA-9, the
# other drops the command vehicle.
SCAR_DECOY_SIGNATURES: tuple[tuple[str, ...], ...] = (
    (SCAR_COMMAND, SCAR_TRUCK, SCAR_TRUCK),  # no SA-9
    (SCAR_HVT_SAM, SCAR_TRUCK),  # no command
)
# Clutter: plain-truck convoys, obviously not it.
SCAR_CLUTTER_SIGNATURE: tuple[str, ...] = (SCAR_TRUCK, SCAR_TRUCK)
SCAR_CLUTTER_COUNT = 3

SCAR_HVT_SPAWN_OFFSET_M = 4000.0  # HVT spawns this far north of the area center
SCAR_HVT_DEST_OFFSET_M = 4000.0  # HVT no-strike destination this far south
SCAR_FAIL_ZONE_RADIUS_M = 500.0  # HVT entering its destination zone = failed
SCAR_SPREAD_RADIUS_M = 5000.0  # decoys/clutter ring around the area center
SCAR_UNIT_SPACING_M = 25.0  # spacing between units within a spawned convoy


@dataclass(frozen=True)
class ScarConvoy:
    """One spawned convoy in a SCAR area.

    ``role`` is "hvt" (the real target — killing it = success, it reaching its
    destination = fail), "decoy" (partial signature), or "clutter" (plain
    trucks). Only the HVT's destination is the no-strike fail zone.
    """

    role: str
    unit_types: tuple[str, ...]
    spawn_x: float
    spawn_y: float
    dest_x: float
    dest_y: float


@dataclass(frozen=True)
class ScarTasking:
    """One SCAR area for the Lua scenario layer to run.

    Two variants (spawn by default since AI convoys are rare; bind to a real
    missile site when the player targets one):

    * ``spawn``  — the generator spawns the ground picture (``convoys``: one HVT
      + decoys + clutter) and routes it. success = HVT destroyed; fail = the HVT
      reaches its destination zone. Always available.
    * ``missile`` — the SCAR target IS a real surface-to-surface missile site
      (the SCUD variant). Watch-only; success = destroyed, fail = it launches.
    """

    tasking_id: str
    variant: str  # "spawn" | "missile"
    # variant "missile":
    target_groups: tuple[str, ...] = ()
    # variant "spawn":
    hvt_country_id: int = 0
    convoys: tuple[ScarConvoy, ...] = ()
    fail_zone_radius_m: float = 0.0


def _ring_point(center: "Point", index: int, total: int) -> tuple[float, float]:
    """Evenly spaced point on a ring around ``center`` (deterministic spread)."""
    angle = 2.0 * math.pi * index / max(total, 1)
    return (
        center.x + SCAR_SPREAD_RADIUS_M * math.cos(angle),
        center.y + SCAR_SPREAD_RADIUS_M * math.sin(angle),
    )


def _compose_convoys(center: "Point") -> tuple[ScarConvoy, ...]:
    """Compose the HVT + decoys + clutter for a SCAR area around ``center``.

    The HVT runs from north of the area to a no-strike destination south of it
    (its arrival = fail). Decoys/clutter spawn on a ring and head toward the area
    center (they mill through the box but never near the HVT's fail zone), so the
    player must pick the full-signature convoy out of the traffic.
    """
    convoys: list[ScarConvoy] = [
        ScarConvoy(
            role="hvt",
            unit_types=SCAR_HVT_SIGNATURE,
            spawn_x=center.x + SCAR_HVT_SPAWN_OFFSET_M,
            spawn_y=center.y,
            dest_x=center.x - SCAR_HVT_DEST_OFFSET_M,
            dest_y=center.y,
        )
    ]

    others: list[tuple[str, tuple[str, ...]]] = [
        ("decoy", sig) for sig in SCAR_DECOY_SIGNATURES
    ] + [("clutter", SCAR_CLUTTER_SIGNATURE) for _ in range(SCAR_CLUTTER_COUNT)]
    for index, (role, sig) in enumerate(others):
        spawn_x, spawn_y = _ring_point(center, index, len(others))
        convoys.append(
            ScarConvoy(
                role=role,
                unit_types=sig,
                spawn_x=spawn_x,
                spawn_y=spawn_y,
                dest_x=center.x,
                dest_y=center.y,
            )
        )
    return tuple(convoys)


def build_scar_taskings(game: "Game") -> list[ScarTasking]:
    """Build one ScarTasking per planned SCAR flight.

    A SCAR flight against a real missile site binds to it ("missile"); every
    other SCAR flight gets a spawned ground picture ("spawn") composed around its
    target area. Returns an empty list when no SCAR flight is planned (the
    injection gate).
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
                    taskings.append(
                        ScarTasking(
                            tasking_id=f"scar-{index}",
                            variant="spawn",
                            hvt_country_id=enemy_country_id,
                            convoys=_compose_convoys(target.position),
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
        # The tasking record must hold ONLY child items (the LuaData serializer
        # drops key-values on a node that also has child objects), so scalars are
        # emitted as named children alongside the nested ``convoys`` list.
        record = taskings_item.add_item()
        record.add_item("taskingId").set_value(tasking.tasking_id)
        record.add_item("variant").set_value(tasking.variant)
        if tasking.variant == "missile":
            record.add_item("targetGroups").set_data_array(list(tasking.target_groups))
            continue
        record.add_item("hvtCountryId").set_value(str(tasking.hvt_country_id))
        record.add_item("failZoneRadius").set_value(str(tasking.fail_zone_radius_m))
        convoys_item = record.add_item("convoys")
        for convoy in tasking.convoys:
            convoy_rec = convoys_item.add_item()
            convoy_rec.add_key_value("role", convoy.role)
            convoy_rec.add_data_array("units", list(convoy.unit_types))
            convoy_rec.add_key_value("spawnX", str(convoy.spawn_x))
            convoy_rec.add_key_value("spawnY", str(convoy.spawn_y))
            convoy_rec.add_key_value("destX", str(convoy.dest_x))
            convoy_rec.add_key_value("destY", str(convoy.dest_y))
