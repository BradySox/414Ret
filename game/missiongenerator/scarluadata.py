from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from game.ato import FlightType

if TYPE_CHECKING:
    from datetime import datetime

    from dcs.mapping import Point

    from game import Game
    from game.missiongenerator.luagenerator import LuaData, LuaItem

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

# Moving targets travel a long path so they're a sustained, dynamic intercept
# (in-game feedback 2026-06-18: "needs a min distance of ~15 NM ... doing more
# for longer"). All first-pass tunables.
SCAR_TRAVEL_M = 27780.0  # ~15 NM: how far a moving target runs / relocates
SCAR_MIN_FLEE_M = SCAR_TRAVEL_M  # bound (armor) target always runs at least this far
SCAR_START_LEAD_S = 600.0  # start moving this long BEFORE the flight's TOT
SCAR_HVT_SPAWN_OFFSET_M = SCAR_TRAVEL_M  # HVT spawns this far from the area center
SCAR_HVT_DEST_OFFSET_M = SCAR_TRAVEL_M  # fallback no-strike dest (no city found)
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
SCAR_SCUD_RACE_M = SCAR_TRAVEL_M  # how far a SCUD relocates toward its target to fire


@dataclass(frozen=True)
class ScarConvoy:
    """One spawned convoy in a SCAR area.

    ``role`` is "hvt" (the real target — killing it = success, it reaching the
    city = fail), "command" (the armor variant's command vehicle, riding with the
    real group; tracked + despawns on arrival), "decoy" (partial signature),
    "clutter" (plain trucks), or "threat" (stationary AAA). Only the HVT's (or
    the bound real group's) arrival is the fail.
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

    Three variants, by what the SCAR flight targets:

    * ``spawn``  — generic target (e.g. a rare convoy): the generator spawns the
      whole ground picture (``convoys``: HVT + decoys + clutter + threats) fleeing
      to a city. success = HVT killed; fail = it reaches the city or the window.
    * ``armor``  — a real ``VehicleGroupGroundObject``: bind that real group as the
      HVT (it flees to the city) and mix in spawned decoys/clutter (``convoys``)
      derived from its real composition. success = real group killed; fail = it
      reaches the city or the window. (BAI stays the AI/auto-planner task.)
    * ``missile`` — a real surface-to-surface missile site (SCUD): it races from
      its location to a firing position and launches on arrival. success =
      killed first; fail = it reaches the firing position (or the window ends)
      and fires at its target city.
    """

    tasking_id: str
    variant: str  # "spawn" | "missile" | "armor"
    coalition: str = ""  # SCAR flight's coalition color ("blue"/"red"); brief addressee
    # Scenario timing (seconds, mission-relative). The fail clock opens at
    # go_live_s (the flight's TOT) and runs for window_s after that.
    go_live_s: float = 0.0
    window_s: float = 0.0
    # variants "missile" + "armor": the real campaign group(s) to bind.
    target_groups: tuple[str, ...] = ()
    # variants "armor" + "missile": the bound group races to (dest_x, dest_y) at
    # flee_speed_ms — a city safe-haven (armor) or a firing position (missile).
    dest_x: float = 0.0
    dest_y: float = 0.0
    flee_speed_ms: float = 0.0
    # variant "missile": where the SCUD fires when it reaches its firing position.
    fire_target_x: float = 0.0
    fire_target_y: float = 0.0
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


def _paced_speed(route_len_m: float, travel_time_s: float) -> float:
    """Speed (m/s) to cover ``route_len_m`` in ``travel_time_s``, clamped so a
    moving HVT crawls within a sane band rather than racing or stalling."""
    return min(
        SCAR_HVT_SPEED_MAX_MS,
        max(SCAR_HVT_SPEED_MIN_MS, route_len_m / max(travel_time_s, 1.0)),
    )


def _real_signature(target: object) -> tuple[str, ...]:
    """The DCS unit-type ids making up a real TGO's group(s), defensively."""
    sig: list[str] = []
    try:
        for group in target.groups:  # type: ignore[attr-defined]
            for unit in group.units:
                type_id = getattr(getattr(unit, "type", None), "id", None)
                if isinstance(type_id, str) and type_id:
                    sig.append(type_id)
    except (AttributeError, TypeError):
        return ()
    return tuple(sig)


def _partial_signatures(sig: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    """Up to two PARTIAL versions of a signature (decoys — never the full set).

    Drops a distinct vehicle type (the discrimination tell) where possible; for a
    homogeneous group, drops one unit (a count tell). Returns () if no meaningful
    partial exists (a single-unit group).
    """
    if len(sig) <= 1:
        return ()
    distinct = list(dict.fromkeys(sig))
    partials: list[tuple[str, ...]] = []
    if len(distinct) >= 2:
        for drop in (distinct[-1], distinct[0]):
            partial = tuple(unit for unit in sig if unit != drop)
            if partial and partial != sig and partial not in partials:
                partials.append(partial)
    else:
        partials.append(sig[:-1])
    return tuple(partials[:2])


def _supporting_convoys(
    center: "Point",
    dest_x: float,
    dest_y: float,
    decoy_sigs: tuple[tuple[str, ...], ...],
    speed: float = SCAR_CONVOY_SPEED_MS,
) -> list[ScarConvoy]:
    """Decoy + plain-truck clutter convoys on a ring, all heading to ``dest``."""
    others: list[tuple[str, tuple[str, ...]]] = [
        ("decoy", sig) for sig in decoy_sigs
    ] + [("clutter", SCAR_CLUTTER_SIGNATURE) for _ in range(SCAR_CLUTTER_COUNT)]
    convoys: list[ScarConvoy] = []
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
                speed_ms=speed,
            )
        )
    return convoys


def _nearest_cp(game: "Game", target: object, same_side: bool) -> "Point | None":
    """Nearest control point to ``target``, on its own side or the enemy side.

    Real city coordinates aren't exposed, but control points map to towns/bases
    on every theater. ``same_side=True`` finds the target's own side (a "city" it
    flees to); ``same_side=False`` finds the enemy side (a SCUD's fire target).
    Returns None if the target has no control point or none is found.
    """
    try:
        target_captured = target.control_point.captured  # type: ignore[attr-defined]
        origin = target.position  # type: ignore[attr-defined]
    except AttributeError:
        return None
    best: "Point | None" = None
    best_distance = 0.0
    for cp in game.theater.controlpoints:
        if (cp.captured == target_captured) != same_side:
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
    hvt_speed = _paced_speed(route_len, window_s + SCAR_START_LEAD_S)

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

    convoys.extend(_supporting_convoys(center, dest_x, dest_y, SCAR_DECOY_SIGNATURES))

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
    from game.theater.theatergroundobject import (
        MissileSiteGroundObject,
        VehicleGroupGroundObject,
    )

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
                # The SCUD races from its site toward a firing position (forward,
                # toward its target city) and launches on arrival. The player must
                # kill it before it reaches the firing position.
                origin = target.position
                fire_target = _nearest_cp(game, target, same_side=False)
                if fire_target is not None:
                    fx, fy = fire_target.x, fire_target.y
                    dx, dy = fx - origin.x, fy - origin.y
                    norm = math.hypot(dx, dy) or 1.0
                    race = min(SCAR_SCUD_RACE_M, norm)
                    dest_x = origin.x + dx / norm * race
                    dest_y = origin.y + dy / norm * race
                else:
                    dest_x, dest_y = origin.x + SCAR_SCUD_RACE_M, origin.y
                    fx, fy = dest_x, dest_y
                route_len = math.hypot(origin.x - dest_x, origin.y - dest_y)
                flee_speed = _paced_speed(route_len, SCAR_WINDOW_S + SCAR_START_LEAD_S)
                taskings.append(
                    ScarTasking(
                        tasking_id=f"scar-{index}",
                        variant="missile",
                        coalition=color,
                        go_live_s=go_live_s,
                        window_s=SCAR_WINDOW_S,
                        target_groups=groups,
                        dest_x=dest_x,
                        dest_y=dest_y,
                        flee_speed_ms=flee_speed,
                        fire_target_x=fx,
                        fire_target_y=fy,
                        fail_zone_radius_m=SCAR_CITY_RADIUS_M,
                    )
                )
            elif isinstance(target, VehicleGroupGroundObject):
                # Bind the REAL armor group: it bugs out toward the city when the
                # window opens; success = killed, fail = it reaches the city or
                # the window expires. (BAI stays the AI/auto-planner task.)
                groups = tuple(g.group_name for g in target.groups)
                if not groups:
                    index -= 1
                    seen_targets.discard(id(target))
                    continue
                city = _nearest_cp(game, target, same_side=True)
                origin = target.position
                city_dist = (
                    math.hypot(origin.x - city.x, origin.y - city.y)
                    if city is not None
                    else 0.0
                )
                if city is not None and city_dist >= SCAR_MIN_FLEE_M:
                    # The nearest enemy city is a real run away: flee straight to it.
                    dest_x, dest_y, fail_radius = (
                        city.x,
                        city.y,
                        SCAR_CITY_RADIUS_M,
                    )
                else:
                    # No city, or the nearest is too close to make a chase of it
                    # (in-game feedback 2026-06-18: target + hide point sat almost
                    # on top of each other). Flee to a generic exit a minimum run
                    # away — along the city axis if we have one, else due -x.
                    if city is not None and city_dist > 0.0:
                        dx, dy = city.x - origin.x, city.y - origin.y
                        dest_x = origin.x + dx / city_dist * SCAR_MIN_FLEE_M
                        dest_y = origin.y + dy / city_dist * SCAR_MIN_FLEE_M
                    else:
                        dest_x = origin.x - SCAR_HVT_DEST_OFFSET_M
                        dest_y = origin.y
                    fail_radius = SCAR_FAIL_ZONE_RADIUS_M
                route_len = math.hypot(
                    target.position.x - dest_x, target.position.y - dest_y
                )
                flee_speed = _paced_speed(route_len, SCAR_WINDOW_S + SCAR_START_LEAD_S)
                # Give the hunted column a command vehicle so the player can pick
                # the real HVT out of the decoys (like the spawn variant). The full
                # signature is the real armor PLUS a command vehicle; decoys are
                # PARTIAL versions of that, so some decoys also carry a command
                # vehicle and the player must match the whole signature, not just
                # spot the antenna. The command vehicle is spawned co-located with
                # the real group and rides with it; it's tracked in the Lua so it
                # must die too, and it's the unit that "escapes into the city".
                hvt_signature = _real_signature(target) + (SCAR_COMMAND,)
                decoy_sigs = _partial_signatures(hvt_signature) or (
                    SCAR_CLUTTER_SIGNATURE,
                )
                convoys = [
                    ScarConvoy(
                        role="command",
                        unit_types=(SCAR_COMMAND,),
                        spawn_x=target.position.x + SCAR_UNIT_SPACING_M,
                        spawn_y=target.position.y,
                        dest_x=dest_x,
                        dest_y=dest_y,
                        speed_ms=flee_speed,
                    )
                ]
                convoys.extend(
                    _supporting_convoys(
                        target.position, dest_x, dest_y, decoy_sigs, flee_speed
                    )
                )
                taskings.append(
                    ScarTasking(
                        tasking_id=f"scar-{index}",
                        variant="armor",
                        coalition=color,
                        go_live_s=go_live_s,
                        window_s=SCAR_WINDOW_S,
                        target_groups=groups,
                        dest_x=dest_x,
                        dest_y=dest_y,
                        flee_speed_ms=flee_speed,
                        fail_zone_radius_m=fail_radius,
                        hvt_country_id=enemy_country_id,
                        convoys=tuple(convoys),
                        command_type=SCAR_COMMAND,
                    )
                )
            else:
                city = _nearest_cp(game, target, same_side=True)
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


def _emit_convoys(record: "LuaItem", convoys: tuple[ScarConvoy, ...]) -> None:
    convoys_item = record.add_item("convoys")
    for convoy in convoys:
        convoy_rec = convoys_item.add_item()
        convoy_rec.add_key_value("role", convoy.role)
        convoy_rec.add_data_array("units", list(convoy.unit_types))
        convoy_rec.add_key_value("spawnX", str(convoy.spawn_x))
        convoy_rec.add_key_value("spawnY", str(convoy.spawn_y))
        convoy_rec.add_key_value("destX", str(convoy.dest_x))
        convoy_rec.add_key_value("destY", str(convoy.dest_y))
        convoy_rec.add_key_value("speed", str(convoy.speed_ms))


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
            record.add_item("destX").set_value(str(tasking.dest_x))
            record.add_item("destY").set_value(str(tasking.dest_y))
            record.add_item("fleeSpeed").set_value(str(tasking.flee_speed_ms))
            record.add_item("fireTargetX").set_value(str(tasking.fire_target_x))
            record.add_item("fireTargetY").set_value(str(tasking.fire_target_y))
            record.add_item("failZoneRadius").set_value(str(tasking.fail_zone_radius_m))
            continue
        if tasking.variant == "armor":
            record.add_item("targetGroups").set_data_array(list(tasking.target_groups))
            record.add_item("destX").set_value(str(tasking.dest_x))
            record.add_item("destY").set_value(str(tasking.dest_y))
            record.add_item("fleeSpeed").set_value(str(tasking.flee_speed_ms))
            record.add_item("failZoneRadius").set_value(str(tasking.fail_zone_radius_m))
            record.add_item("hvtCountryId").set_value(str(tasking.hvt_country_id))
            _emit_convoys(record, tasking.convoys)
            continue
        record.add_item("hvtCountryId").set_value(str(tasking.hvt_country_id))
        record.add_item("failZoneRadius").set_value(str(tasking.fail_zone_radius_m))
        record.add_item("commandType").set_value(tasking.command_type)
        _emit_convoys(record, tasking.convoys)
