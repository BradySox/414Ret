from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from game.ato import FlightType

if TYPE_CHECKING:
    from datetime import datetime

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

# Threat laydown (R9): scattered short-range AAA + an occasional SA-9 — contested,
# but deliberately NOT a SEAD package (no medium/long-range SAMs). These are
# spawned at runtime, so they never trip the planner's auto SEAD-escort request
# (the planner only sees campaign TGOs, resolving spec §10 Q3 for the spawn path).
SCAR_THREAT_ZSU = "ZSU-23-4 Shilka"  # radar AAA
SCAR_THREAT_ZU23 = "ZU-23 Emplacement"  # optical AAA
SCAR_THREAT_SAM = "Strela-1 9P31"  # occasional SA-9
SCAR_THREAT_LAYDOWN: tuple[str, ...] = (
    SCAR_THREAT_ZSU,
    SCAR_THREAT_ZSU,
    SCAR_THREAT_ZU23,
    SCAR_THREAT_ZU23,
    SCAR_THREAT_SAM,
)

SCAR_HVT_SPAWN_OFFSET_M = 4000.0  # HVT spawns this far north of the area center
SCAR_HVT_DEST_OFFSET_M = 4000.0  # HVT no-strike destination this far south
SCAR_FAIL_ZONE_RADIUS_M = 500.0  # HVT entering its destination zone = failed
SCAR_SPREAD_RADIUS_M = 5000.0  # decoys/clutter ring around the area center
SCAR_THREAT_RING_M = 3000.0  # threat ring (inside the convoy traffic)
SCAR_UNIT_SPACING_M = 25.0  # spacing between units within a spawned convoy

# The scenario is anchored to the SCAR flight's TOT (when the player is planned
# to be on station), NOT mission start — otherwise the convoy crosses and the
# SCUD fires while the player is still ~15+ min out (in-game finding 2026-06-17).
# After it goes live the player gets this generous window to find + kill the HVT
# before it "gets away" (spawn) or launches (missile). Tunable.
SCAR_WINDOW_S = 1200.0  # 20 min on-station window after the flight's TOT

# The HVT flees toward the nearest enemy-held control point (the "city" proxy —
# real city coords aren't queryable, but every map has CPs). On reaching it the
# command vehicle slips into the urban area (despawns) = fail. Its speed is set
# so it arrives ~window if the city is within reach; otherwise the window
# expires first. Decoys/clutter just crawl as traffic.
SCAR_CONVOY_SPEED_MS = 5.0  # cosmetic decoy/clutter crawl
SCAR_HVT_SPEED_MIN_MS = 4.0
SCAR_HVT_SPEED_MAX_MS = 15.0
SCAR_CITY_RADIUS_M = 2000.0  # HVT within this of the city = command escapes


@dataclass(frozen=True)
class ScarConvoy:
    """One spawned convoy in a SCAR area.

    ``role`` is "hvt" (the real target — killing it = success, it reaching the
    city = fail), "decoy" (partial signature), "clutter" (plain trucks), or
    "threat" (stationary AAA). Only the HVT's arrival is the fail.
    """

    role: str
    unit_types: tuple[str, ...]
    spawn_x: float
    spawn_y: float
    dest_x: float
    dest_y: float
    speed_ms: float = SCAR_CONVOY_SPEED_MS


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
    coalition: str = ""  # SCAR flight's coalition color ("blue"/"red"); brief addressee
    # Scenario timing (seconds, mission-relative). The fail clock opens at
    # go_live_s (the flight's TOT) and runs for window_s after that.
    go_live_s: float = 0.0
    window_s: float = 0.0
    # variant "missile":
    target_groups: tuple[str, ...] = ()
    # variant "spawn":
    hvt_country_id: int = 0
    convoys: tuple[ScarConvoy, ...] = ()
    fail_zone_radius_m: float = 0.0
    command_type: str = ""  # the HVT's command-vehicle type; despawns in the city


def _ring_point(
    center: "Point", index: int, total: int, radius: float = SCAR_SPREAD_RADIUS_M
) -> tuple[float, float]:
    """Evenly spaced point on a ring around ``center`` (deterministic spread)."""
    angle = 2.0 * math.pi * index / max(total, 1)
    return (
        center.x + radius * math.cos(angle),
        center.y + radius * math.sin(angle),
    )


def _nearest_city(game: "Game", target: object) -> "Point | None":
    """The nearest enemy-held control point to ``target`` (the "city" proxy).

    Real city coordinates aren't exposed, but control points map to towns/bases
    on every theater. Returns None if the target has no control point or no
    enemy-held CP is found, in which case the convoy falls back to a fixed
    no-strike point near the area.
    """
    try:
        target_captured = target.control_point.captured  # type: ignore[attr-defined]
        origin = target.position  # type: ignore[attr-defined]
    except AttributeError:
        return None
    best: "Point | None" = None
    best_distance = 0.0
    for cp in game.theater.controlpoints:
        if cp.captured != target_captured:
            continue
        distance = cp.position.distance_to_point(origin)
        if best is None or distance < best_distance:
            best, best_distance = cp.position, distance
    return best


def _compose_convoys(
    center: "Point", city: "Point | None", window_s: float
) -> tuple[ScarConvoy, ...]:
    """Compose the HVT + decoys + clutter + threats for a SCAR area.

    The HVT runs from the far side of the area toward ``city`` (the nearest
    enemy-held CP), so the player intercepts it crossing the box; reaching the
    city = its command vehicle escapes (fail). If no city is found it falls back
    to a fixed no-strike point south of the area. Decoys/clutter crawl as
    traffic; threats hold station.
    """
    if city is not None:
        dx, dy = center.x - city.x, center.y - city.y
        norm = math.hypot(dx, dy) or 1.0
        ux, uy = dx / norm, dy / norm  # unit vector area -> away from city
        hvt_spawn_x = center.x + ux * SCAR_HVT_SPAWN_OFFSET_M
        hvt_spawn_y = center.y + uy * SCAR_HVT_SPAWN_OFFSET_M
        dest_x, dest_y = city.x, city.y
    else:
        hvt_spawn_x = center.x + SCAR_HVT_SPAWN_OFFSET_M
        hvt_spawn_y = center.y
        dest_x = center.x - SCAR_HVT_DEST_OFFSET_M
        dest_y = center.y

    # Pace the HVT to reach the destination ~window (clamped to a sane crawl).
    route_len = math.hypot(hvt_spawn_x - dest_x, hvt_spawn_y - dest_y)
    hvt_speed = min(
        SCAR_HVT_SPEED_MAX_MS,
        max(SCAR_HVT_SPEED_MIN_MS, route_len / max(window_s, 1.0)),
    )

    convoys: list[ScarConvoy] = [
        ScarConvoy(
            role="hvt",
            unit_types=SCAR_HVT_SIGNATURE,
            spawn_x=hvt_spawn_x,
            spawn_y=hvt_spawn_y,
            dest_x=dest_x,
            dest_y=dest_y,
            speed_ms=hvt_speed,
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
                dest_x=dest_x,
                dest_y=dest_y,
            )
        )

    # Threat laydown (R9): stationary AAA/SA-9 on an inner ring (dest == spawn).
    # Untracked; they just make the box contested.
    for index, unit_type in enumerate(SCAR_THREAT_LAYDOWN):
        tx, ty = _ring_point(
            center, index, len(SCAR_THREAT_LAYDOWN), radius=SCAR_THREAT_RING_M
        )
        convoys.append(
            ScarConvoy(
                role="threat",
                unit_types=(unit_type,),
                spawn_x=tx,
                spawn_y=ty,
                dest_x=tx,
                dest_y=ty,
                speed_ms=0.0,
            )
        )
    return tuple(convoys)


def build_scar_taskings(game: "Game", mission_start: "datetime") -> list[ScarTasking]:
    """Build one ScarTasking per SCAR-tasked target (deduped by target).

    A SCAR package against a real missile site binds to it ("missile"); any other
    SCAR target gets a spawned ground picture ("spawn"). Each tasking is anchored
    to the package's TOT relative to ``mission_start`` (``go_live_s``) so the fail
    clock only opens when the player is planned to be on station. Returns an empty
    list when no SCAR flight is planned (the injection gate).
    """
    from game.theater.theatergroundobject import MissileSiteGroundObject

    taskings: list[ScarTasking] = []
    index = 0
    seen_targets: set[int] = set()
    for coalition in game.coalitions:
        color = "blue" if coalition.player else "red"
        enemy_country_id = coalition.opponent.faction.country.id
        for package in coalition.ato.packages:
            if not any(f.flight_type is FlightType.SCAR for f in package.flights):
                continue
            target = package.target
            # One scenario per target, even with multiple SCAR flights on it.
            if id(target) in seen_targets:
                continue
            seen_targets.add(id(target))

            try:
                go_live_s = max(
                    0.0, (package.time_over_target - mission_start).total_seconds()
                )
            except (TypeError, AttributeError):
                go_live_s = 0.0

            index += 1
            if isinstance(target, MissileSiteGroundObject):
                groups = tuple(g.group_name for g in target.groups)
                if not groups:
                    index -= 1
                    seen_targets.discard(id(target))
                    continue
                taskings.append(
                    ScarTasking(
                        tasking_id=f"scar-{index}",
                        variant="missile",
                        coalition=color,
                        go_live_s=go_live_s,
                        window_s=SCAR_WINDOW_S,
                        target_groups=groups,
                    )
                )
            else:
                city = _nearest_city(game, target)
                fail_radius = (
                    SCAR_CITY_RADIUS_M if city is not None else SCAR_FAIL_ZONE_RADIUS_M
                )
                taskings.append(
                    ScarTasking(
                        tasking_id=f"scar-{index}",
                        variant="spawn",
                        coalition=color,
                        go_live_s=go_live_s,
                        window_s=SCAR_WINDOW_S,
                        hvt_country_id=enemy_country_id,
                        convoys=_compose_convoys(target.position, city, SCAR_WINDOW_S),
                        fail_zone_radius_m=fail_radius,
                        command_type=SCAR_COMMAND,
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
        record.add_item("coalition").set_value(tasking.coalition)
        record.add_item("goLive").set_value(str(tasking.go_live_s))
        record.add_item("window").set_value(str(tasking.window_s))
        if tasking.variant == "missile":
            record.add_item("targetGroups").set_data_array(list(tasking.target_groups))
            continue
        record.add_item("hvtCountryId").set_value(str(tasking.hvt_country_id))
        record.add_item("failZoneRadius").set_value(str(tasking.fail_zone_radius_m))
        record.add_item("commandType").set_value(tasking.command_type)
        convoys_item = record.add_item("convoys")
        for convoy in tasking.convoys:
            convoy_rec = convoys_item.add_item()
            convoy_rec.add_key_value("role", convoy.role)
            convoy_rec.add_data_array("units", list(convoy.unit_types))
            convoy_rec.add_key_value("spawnX", str(convoy.spawn_x))
            convoy_rec.add_key_value("spawnY", str(convoy.spawn_y))
            convoy_rec.add_key_value("destX", str(convoy.dest_x))
            convoy_rec.add_key_value("destY", str(convoy.dest_y))
            convoy_rec.add_key_value("speed", str(convoy.speed_ms))
