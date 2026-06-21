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
SCAR_HVT_SPAWN_OFFSET_M = SCAR_TRAVEL_M  # HVT spawns this far from the area center
SCAR_HVT_DEST_OFFSET_M = SCAR_TRAVEL_M  # fallback no-strike dest (no city found)
SCAR_FAIL_ZONE_RADIUS_M = 500.0  # HVT entering its destination zone = failed
SCAR_SPREAD_RADIUS_M = 5000.0  # decoys/clutter ring around the area center
SCAR_THREAT_RING_M = 3000.0  # threat ring (inside the convoy traffic)
SCAR_UNIT_SPACING_M = 25.0  # spacing between units within a spawned convoy

# TIMING (2026-06-21): the scenario now goes live AT SPAWN (mission start) — the
# whole picture is present and the HVT is already moving when the player arrives,
# regardless of when they push (in-game feedback 2026-06-20: targets only started
# moving "right as we fired Mavs" because the old TOT anchor assumed the flight
# flew to its planned TOT, which MP play does not). This reverses the earlier
# TOT-anchor (2026-06-17, which guarded against the convoy crossing / the SCUD
# firing before the player arrived); the new guard is the slow pace below — the HVT
# is paced to take the WHOLE window to crawl its route, so it stays catchable for
# the bulk of the mission instead of racing off early. go_live is still emitted
# (for reference) but no longer gates activation. Tunable; needs an in-game pass.
SCAR_WINDOW_S = 3600.0  # 60 min hunt window, measured from spawn (the HVT reaches
#                         its destination / the fail clock ends ~this long in)

# Some vehicle groups include towed/emplaced units (towed AAA, static guns) that
# cannot drive. Binding such a group as a fleeing "armor" HVT strands those units
# (in-game feedback 2026-06-20: "flak gun in the target group was not mobile"), so
# a group containing any of these is routed to the fully-mobile SPAWN picture
# instead of being bound. pydcs exposes no ground-mobility flag, so this is a
# curated set of vanilla immobile ground types; a miss degrades to one stranded
# unit, never a crash. Extend as needed.
SCAR_IMMOBILE_GROUND_TYPES: frozenset[str] = frozenset(
    {
        "KS-19",  # 100mm towed AAA (the 2026-06-20 flak gun)
        "S-60_Type59_Artillery",  # 57mm towed AAA
        "SON_9",  # Fire Can AAA radar (static)
        "2B11 mortar",
        "L118_Unit",  # 105mm towed howitzer
        "ZU-23 Emplacement",
        "ZU-23 Emplacement Closed",
        "ZU-23 Insurgent",
        "ZU-23 Closed Insurgent",
    }
)

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

# Phase 2a — scripted SOF "ambush" capture, gated behind scar_command_post_intel.
# When the feature is on, a friendly SOF team is dropped on the HVT's flee route
# ahead of it (armor/spawn only). If the un-killed command vehicle reaches them it
# is CAPTURED ("captured" result -> reveals enemy command posts next turn) instead
# of escaping. First pass: always dropped + guaranteed on proximity; finite /
# player-delivered SOF is Phase 2c-2.
SCAR_SOF_CAPTURE_RADIUS_M = 600.0  # command vehicle within this of the SOF = captured
SCAR_SOF_LEAD_FRAC = 0.7  # SOF sits this fraction along the HVT's spawn->dest route

# Phase 2c — the SOF team is a finite, BOUGHT inventory unit (dedicated GroundUnitType
# per side). The drop only happens while the side has teams in its bases; each capture
# consumes one. These names must match the variant_ids in resources/units/ground_units/.
SCAR_SOF_UNIT_BLUE = "SOF Team (BLUFOR)"
SCAR_SOF_UNIT_RED = "SOF Team (OPFOR)"


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
    # Area center (the target's position): the F10 "search area" cue the Lua marks,
    # instead of a pin on the exact HVT (in-game feedback 2026-06-20: a steerpoint/
    # mark on the one correct group made it trivial to find).
    center_x: float = 0.0
    center_y: float = 0.0
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
    # Phase 2a SOF ambush (armor/spawn only, and only when scar_command_post_intel
    # is on). A friendly SOF team waits at (sof_x, sof_y); the HVT command vehicle
    # reaching it = captured. sof_country_id is the SCAR flight's own (friendly)
    # side. sof_radius_m == 0 means "no SOF" (the Lua gate).
    sof_x: float = 0.0
    sof_y: float = 0.0
    sof_radius_m: float = 0.0
    sof_country_id: int = 0
    sof_unit_type: str = ""  # DCS unit id the Lua spawns for the SOF team


def _ring_point(
    center: "Point", index: int, total: int, radius: float = SCAR_SPREAD_RADIUS_M
) -> tuple[float, float]:
    """Evenly spaced point on a ring around ``center`` (deterministic spread)."""
    angle = 2.0 * math.pi * index / max(total, 1)
    return (
        center.x + radius * math.cos(angle),
        center.y + radius * math.sin(angle),
    )


# Golden angle (~137.5°): a sunflower/phyllotaxis spiral that fills a disk evenly
# but without the regular spokes of a fixed-radius ring.
_GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))


def _scatter_point(
    center: "Point", index: int, total: int, radius: float = SCAR_SPREAD_RADIUS_M
) -> tuple[float, float]:
    """A point scattered through the disk around ``center`` (deterministic).

    Decoys/clutter on a single fixed-radius ring read as an obviously artificial
    circle (in-game feedback 2026-06-18: "decoy generation looks very uniform").
    A golden-angle spiral with a sqrt-spaced radius spreads them across the whole
    area at varied ranges/bearings, so the column looks like scattered traffic.
    A floor on the radius keeps them off the HVT itself.
    """
    angle = index * _GOLDEN_ANGLE
    frac = (index + 0.5) / max(total, 1)
    r = radius * (0.35 + 0.65 * math.sqrt(frac))
    return (
        center.x + r * math.cos(angle),
        center.y + r * math.sin(angle),
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


def _group_is_mobile(target: object) -> bool:
    """True if every unit in the target's group(s) can drive (no towed/static units).

    Real armor groups can include towed AAA or static guns that strand when the
    column flees (the 2026-06-20 flak gun). Such a target is routed to the spawned
    mobile picture instead of bound. Unknown composition is treated as mobile (bind
    as before) so we never regress a group we can't read.
    """
    sig = _real_signature(target)
    if not sig:
        return True
    return all(unit not in SCAR_IMMOBILE_GROUND_TYPES for unit in sig)


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
        spawn_x, spawn_y = _scatter_point(center, index, len(others))
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

    # Pace the HVT to reach the destination ~window (clamped to a sane crawl). It
    # starts moving at spawn, so the window IS the full crawl time — a slow pace
    # keeps it catchable for the whole hunt instead of escaping before contact.
    route_len = math.hypot(hvt_spawn_x - dest_x, hvt_spawn_y - dest_y)
    hvt_speed = _paced_speed(route_len, window_s)

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


def _sof_ambush(
    spawn_x: float,
    spawn_y: float,
    dest_x: float,
    dest_y: float,
    country_id: int,
) -> tuple[float, float, float, int]:
    """SOF ambush point a fixed fraction along the HVT's spawn->dest route, plus the
    capture radius and the friendly country to spawn the team under. The HVT drives
    into the waiting team (it can't be chased on foot)."""
    sof_x = spawn_x + (dest_x - spawn_x) * SCAR_SOF_LEAD_FRAC
    sof_y = spawn_y + (dest_y - spawn_y) * SCAR_SOF_LEAD_FRAC
    return sof_x, sof_y, SCAR_SOF_CAPTURE_RADIUS_M, country_id


def _sof_asset(game: "Game", coalition: object) -> tuple[int, str]:
    """The side's bought SOF pool: (count across its bases, DCS unit id to spawn).

    Returns (0, "") if the dedicated SOF unit type isn't available. INFANTRY units
    sit in base.armor but are never front-line-deployed or AI-procured (see the
    Phase 2c design note), so this count is exactly the player's reserve of teams.
    """
    from game.dcs.groundunittype import GroundUnitType

    name = SCAR_SOF_UNIT_BLUE if coalition.player.is_blue else SCAR_SOF_UNIT_RED  # type: ignore[attr-defined]
    try:
        unit = GroundUnitType.named(name)
    except KeyError:
        return 0, ""
    count = 0
    for cp in game.theater.controlpoints:
        if cp.captured == coalition.player:  # type: ignore[attr-defined]
            count += cp.base.armor.get(unit, 0)
    return count, unit.dcs_unit_type.id


def _on_land(game: "Game", x: float, y: float) -> tuple[float, float]:
    """Snap a computed point onto land if it fell in the sea.

    Ground units can't path offshore: for a coastal target the HVT spawn (offset
    away from an inland city) or a flee destination (a city across a bay, or a
    projected exit) can land in the water, and the column then drives toward the
    ocean and never reaches the SOF / city (in-game finding 2026-06-18). Pulls such
    a point to the nearest land. No-op when the theater has no landmap.
    """
    from dcs.mapping import Point

    theater = game.theater
    point = Point(x, y, theater.terrain)
    if theater.is_in_sea(point):
        land = theater.nearest_land_pos(point)
        return land.x, land.y
    return x, y


def _convoys_on_land(
    game: "Game", convoys: tuple[ScarConvoy, ...]
) -> tuple[ScarConvoy, ...]:
    """Snap every convoy's spawn + dest onto land (see ``_on_land``)."""
    from dataclasses import replace

    snapped: list[ScarConvoy] = []
    for convoy in convoys:
        sx, sy = _on_land(game, convoy.spawn_x, convoy.spawn_y)
        dx, dy = _on_land(game, convoy.dest_x, convoy.dest_y)
        snapped.append(replace(convoy, spawn_x=sx, spawn_y=sy, dest_x=dx, dest_y=dy))
    return tuple(snapped)


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
    sof_enabled = game.settings.scar_command_post_intel
    for coalition in game.coalitions:
        color = "blue" if coalition.player.is_blue else "red"
        enemy_country_id = coalition.opponent.faction.country.id
        friendly_country_id = coalition.faction.country.id
        # Finite SOF pool (Phase 2c): only drop a team while the side has bought
        # some, capped per turn at the count on hand. sof_unit_type is the DCS id
        # the Lua spawns.
        sof_budget, sof_unit_type = (
            _sof_asset(game, coalition) if sof_enabled else (0, "")
        )
        # Phase 2c-2: the SOF team is delivered by a player-flown insert, so a drop
        # is emitted only against targets that actually have a SOF flight fragged
        # (still capped by the finite pool). Targets without an insert get no team.
        sof_targets: set[int] = (
            {
                id(package.target)
                for package in coalition.ato.packages
                if any(f.flight_type is FlightType.SOF for f in package.flights)
            }
            if sof_enabled
            else set()
        )
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
                # Keep the SCUD's firing position on land (it can't drive offshore).
                dest_x, dest_y = _on_land(game, dest_x, dest_y)
                route_len = math.hypot(origin.x - dest_x, origin.y - dest_y)
                flee_speed = _paced_speed(route_len, SCAR_WINDOW_S)
                taskings.append(
                    ScarTasking(
                        tasking_id=f"{color}-scar-{index}",
                        variant="missile",
                        coalition=color,
                        center_x=origin.x,
                        center_y=origin.y,
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
            elif isinstance(target, VehicleGroupGroundObject) and _group_is_mobile(
                target
            ):
                # Bind the REAL armor group: it bugs out toward the city at spawn;
                # success = killed, fail = it reaches the city or the window expires.
                # (BAI stays the AI/auto-planner task.) Only fully-mobile groups are
                # bound — groups with towed/static units fall through to the spawned
                # mobile picture below so nothing strands (2026-06-20 flak gun).
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
                # Keep the flee destination on land: a city across a bay or a
                # projected exit can land in the sea, sending the column toward the
                # ocean where it can't path (in-game finding 2026-06-18).
                dest_x, dest_y = _on_land(game, dest_x, dest_y)
                route_len = math.hypot(
                    target.position.x - dest_x, target.position.y - dest_y
                )
                flee_speed = _paced_speed(route_len, SCAR_WINDOW_S)
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
                sof_x, sof_y, sof_radius, sof_country = 0.0, 0.0, 0.0, 0
                sof_type = ""
                if sof_budget > 0 and id(target) in sof_targets:
                    sof_x, sof_y, sof_radius, sof_country = _sof_ambush(
                        origin.x, origin.y, dest_x, dest_y, friendly_country_id
                    )
                    sof_x, sof_y = _on_land(game, sof_x, sof_y)
                    sof_type = sof_unit_type
                    sof_budget -= 1
                taskings.append(
                    ScarTasking(
                        tasking_id=f"{color}-scar-{index}",
                        variant="armor",
                        coalition=color,
                        center_x=target.position.x,
                        center_y=target.position.y,
                        go_live_s=go_live_s,
                        window_s=SCAR_WINDOW_S,
                        target_groups=groups,
                        dest_x=dest_x,
                        dest_y=dest_y,
                        flee_speed_ms=flee_speed,
                        fail_zone_radius_m=fail_radius,
                        hvt_country_id=enemy_country_id,
                        convoys=_convoys_on_land(game, tuple(convoys)),
                        command_type=SCAR_COMMAND,
                        sof_x=sof_x,
                        sof_y=sof_y,
                        sof_radius_m=sof_radius,
                        sof_country_id=sof_country,
                        sof_unit_type=sof_type,
                    )
                )
            else:
                city = _nearest_cp(game, target, same_side=True)
                fail_radius = (
                    SCAR_CITY_RADIUS_M if city is not None else SCAR_FAIL_ZONE_RADIUS_M
                )
                # Snap the whole picture onto land first: the HVT spawns offset away
                # from the (inland) city, which for a coastal target lands in the
                # sea — the convoy then can't path (in-game finding 2026-06-18).
                spawn_convoys = _convoys_on_land(
                    game, _compose_convoys(target.position, city, SCAR_WINDOW_S)
                )
                sof_x, sof_y, sof_radius, sof_country = (0.0, 0.0, 0.0, 0)
                sof_type = ""
                if sof_budget > 0 and id(target) in sof_targets:
                    hvt = next((c for c in spawn_convoys if c.role == "hvt"), None)
                    if hvt is not None:
                        sof_x, sof_y, sof_radius, sof_country = _sof_ambush(
                            hvt.spawn_x,
                            hvt.spawn_y,
                            hvt.dest_x,
                            hvt.dest_y,
                            friendly_country_id,
                        )
                        sof_x, sof_y = _on_land(game, sof_x, sof_y)
                        sof_type = sof_unit_type
                        sof_budget -= 1
                taskings.append(
                    ScarTasking(
                        tasking_id=f"{color}-scar-{index}",
                        variant="spawn",
                        coalition=color,
                        center_x=target.position.x,
                        center_y=target.position.y,
                        go_live_s=go_live_s,
                        window_s=SCAR_WINDOW_S,
                        hvt_country_id=enemy_country_id,
                        convoys=spawn_convoys,
                        fail_zone_radius_m=fail_radius,
                        command_type=SCAR_COMMAND,
                        sof_x=sof_x,
                        sof_y=sof_y,
                        sof_radius_m=sof_radius,
                        sof_country_id=sof_country,
                        sof_unit_type=sof_type,
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


def _emit_sof(record: "LuaItem", tasking: ScarTasking) -> None:
    """Emit the Phase 2a SOF ambush fields (only when a SOF team is set)."""
    if tasking.sof_radius_m <= 0:
        return
    record.add_item("sofX").set_value(str(tasking.sof_x))
    record.add_item("sofY").set_value(str(tasking.sof_y))
    record.add_item("sofRadius").set_value(str(tasking.sof_radius_m))
    record.add_item("sofCountryId").set_value(str(tasking.sof_country_id))
    if tasking.sof_unit_type:
        record.add_item("sofUnitType").set_value(tasking.sof_unit_type)


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
        record.add_item("centerX").set_value(str(tasking.center_x))
        record.add_item("centerY").set_value(str(tasking.center_y))
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
            _emit_sof(record, tasking)
            _emit_convoys(record, tasking.convoys)
            continue
        record.add_item("hvtCountryId").set_value(str(tasking.hvt_country_id))
        record.add_item("failZoneRadius").set_value(str(tasking.fail_zone_radius_m))
        record.add_item("commandType").set_value(tasking.command_type)
        _emit_sof(record, tasking)
        _emit_convoys(record, tasking.convoys)
