from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from dcs.mapping import Point
from pydantic import BaseModel

from game.data.groups import GroupTask
from game.server.leaflet import LeafletPoint
from game.theater import Player
from game.theater.theatergroundobject import ShipGroundObject

if TYPE_CHECKING:
    from game import Game
    from game.theater import TheaterGroundObject

# Concealment: an un-reconned hidden TGO is shown as an "in here somewhere" circle,
# centred on a point jittered off the true position. Two ways in: the COIN spawns
# (roadside IED/VBIED, HVT convoy, dispersed/re-infiltration cells) carry an
# intrinsic `concealed` flag, and — with the `concealed_enemy_forces` setting on —
# enemy FIELD forces qualify by kind (mobile SAMs, deployed vehicle groups, missile
# sites; fixed infrastructure / LORAD / EWRs / ships stay exact). The jitter is
# seeded from the TGO id so it is stable across refreshes/reloads (a wandering
# circle would let the player triangulate), and bounded so the true position always
# sits inside the circle. The exact coordinates never reach the client while
# concealed.
CONCEALED_RADIUS_M = 4000.0
#: Deployed vehicle groups get a tighter circle than a SAM/missile site — they are
#: smaller and there are many of them, so this keeps base clusters readable.
FIELD_FORCE_RADIUS_M = 3000.0
_CONCEALED_MIN_OFFSET = 0.15  # fraction of the radius
_CONCEALED_MAX_OFFSET = 0.60

#: SAM tasks that conceal: the mobile/relocatable belt. LORAD (fixed strategic
#: S-200/S-300 sites) and EWRs (they emit — passively geolocatable) stay exact.
_CONCEALABLE_SAM_TASKS = frozenset({GroupTask.MERAD, GroupTask.SHORAD, GroupTask.AAA})

#: Road-pinned concealment (a TGO carrying `concealed_route` — the roadside IEDs):
#: the suspected-activity centre slides FAR along the route polyline (never off it)
#: by this much, clamped to the road's extent. Deliberately larger than the circle
#: radius — the player knows what highway the device is on, not which stretch, so
#: unlike the radial jitter the truth may sit OUTSIDE the drawn circle; the road
#: itself is the search domain (user call 2026-07-05).
_ROUTE_JITTER_MIN_M = 5_000.0
_ROUTE_JITTER_MAX_M = 25_000.0


def _route_cumulative(route: list[tuple[float, float]]) -> list[float]:
    """Cumulative arc length at each polyline vertex."""
    cum = [0.0]
    for (ax, ay), (bx, by) in zip(route, route[1:]):
        cum.append(cum[-1] + math.hypot(bx - ax, by - ay))
    return cum


def _nearest_arc(
    route: list[tuple[float, float]], cum: list[float], x: float, y: float
) -> float:
    """Arc length of the point on the polyline closest to (x, y)."""
    best_arc = 0.0
    best_dist = math.inf
    for i, ((ax, ay), (bx, by)) in enumerate(zip(route, route[1:])):
        dx, dy = bx - ax, by - ay
        seg_sq = dx * dx + dy * dy
        t = 0.0 if seg_sq == 0.0 else ((x - ax) * dx + (y - ay) * dy) / seg_sq
        t = min(max(t, 0.0), 1.0)
        px, py = ax + t * dx, ay + t * dy
        dist = math.hypot(x - px, y - py)
        if dist < best_dist:
            best_dist = dist
            best_arc = cum[i] + t * (cum[i + 1] - cum[i])
    return best_arc


def _point_at_arc(
    route: list[tuple[float, float]], cum: list[float], s: float
) -> tuple[float, float]:
    """The polyline point at arc length ``s`` (clamped to the route's extent)."""
    s = min(max(s, 0.0), cum[-1])
    for i in range(len(route) - 1):
        if s <= cum[i + 1] or i == len(route) - 2:
            seg = cum[i + 1] - cum[i]
            t = 0.0 if seg == 0.0 else (s - cum[i]) / seg
            (ax, ay), (bx, by) = route[i], route[i + 1]
            return ax + t * (bx - ax), ay + t * (by - ay)
    return route[-1]


def _route_jitter(tgo: TheaterGroundObject) -> Optional[tuple[float, float]]:
    """A deterministic point FAR along the TGO's pinned route, or None if the TGO
    carries no usable route (the caller falls back to the radial jitter)."""
    route_raw = getattr(tgo, "concealed_route", None)
    if not route_raw or len(route_raw) < 2:
        return None
    route = [(float(x), float(y)) for x, y in route_raw]
    cum = _route_cumulative(route)
    if cum[-1] <= 0.0:
        return None
    s0 = _nearest_arc(route, cum, tgo.position.x, tgo.position.y)
    rng = random.Random(tgo.id.int)
    dist = rng.uniform(_ROUTE_JITTER_MIN_M, _ROUTE_JITTER_MAX_M)
    direction = 1.0 if rng.random() < 0.5 else -1.0
    s = s0 + direction * dist
    if s < 0.0 or s > cum[-1]:
        s = s0 - direction * dist  # bounce off the road's end, stay on the road
    return _point_at_arc(route, cum, s)


def _concealed_radius(tgo: TheaterGroundObject) -> Optional[float]:
    """The uncertainty radius for this TGO, or None if it shows an exact marker."""
    if getattr(tgo, "concealed", False):
        # COIN hidden objects: intrinsic, independent of the setting.
        return CONCEALED_RADIUS_M
    if tgo.user_placed:
        # The player placed it (drop-spawn) — they know exactly where it is.
        return None
    settings = tgo.control_point.coalition.game.settings
    if not getattr(settings, "concealed_enemy_forces", False):
        return None
    if tgo.category == "armor":
        return FIELD_FORCE_RADIUS_M
    if tgo.category == "missile":
        return CONCEALED_RADIUS_M
    if tgo.category == "aa" and tgo.task in _CONCEALABLE_SAM_TASKS:
        return CONCEALED_RADIUS_M
    return None


def concealed_uncertainty(tgo: TheaterGroundObject) -> Optional[tuple[Any, float]]:
    """(jittered centre point, radius m) for a concealed, un-reconned enemy TGO.

    None when the TGO shows an exact marker: nothing conceals it, or the BLUE
    viewer already knows it (TARPS/attack discovery, recon fog off, or the
    fog-overview reveal — all via ``known_for``, which also short-circuits
    friendly/neutral sites).
    """
    if tgo.known_for(Player.BLUE):
        return None
    radius = _concealed_radius(tgo)
    if radius is None:
        return None
    pos = tgo.position
    # Road-pinned (roadside IEDs): slide far ALONG the route, never off it.
    on_route = _route_jitter(tgo)
    if on_route is not None:
        return Point(on_route[0], on_route[1], pos._terrain), radius
    rng = random.Random(tgo.id.int)
    theta = rng.uniform(0.0, math.tau)
    dist = rng.uniform(_CONCEALED_MIN_OFFSET, _CONCEALED_MAX_OFFSET) * radius
    # Build a PLAIN pydcs Point, never pos.__class__: a real TGO's position is a
    # PresetLocation (PointWithHeading), whose constructor signature differs —
    # reusing the subclass here mis-bound the arguments and 500'd the whole /game
    # payload (the 2026-07-05 "fog on = blank map" regression). pydcs keeps the
    # terrain private; PresetLocation reads it the same way.
    jittered = Point(
        pos.x + dist * math.cos(theta), pos.y + dist * math.sin(theta), pos._terrain
    )
    return jittered, radius


class TgoJs(BaseModel):
    id: UUID
    name: str
    control_point_name: str
    category: str
    blue: bool
    position: LeafletPoint
    units: list[str]  # TODO: Event stream
    threat_ranges: list[float]  # TODO: Event stream
    detection_ranges: list[float]  # TODO: Event stream
    dead: bool  # TODO: Event stream
    sidc: str  # TODO: Event stream
    task: Optional[GroupTask]
    mobile: bool
    destination: Optional[LeafletPoint]
    user_placed: bool
    # ROE escalation (campaign phases W4): True while the active authored phase
    # forbids offensive tasking here (inside a restricted zone or a still-locked
    # target class). The site stays visible and targetable -- the defining Rolling
    # Thunder frustration -- it just wears a RESTRICTED badge. `roe_reason` says
    # WHY ("factory targets are locked this phase" / "inside Hanoi sanctuary") so
    # a class-locked site far from any circle doesn't read as a render bug.
    roe_restricted: bool = False
    roe_reason: str | None = None
    # COIN concealment: set while this TGO's map presence is an uncertainty area.
    # `position` is then the JITTERED circle centre, not the true location.
    uncertainty_radius_m: float | None = None

    class Config:
        title = "Tgo"

    @staticmethod
    def for_tgo(tgo: TheaterGroundObject) -> TgoJs:
        blue = tgo.control_point.captured.is_blue
        threat_ranges: list[float]
        detection_ranges: list[float]
        units: list[str]
        if tgo.known_for(Player.BLUE):
            threat_ranges = [
                group.max_threat_range(Player.BLUE).meters for group in tgo.groups
            ]
            detection_ranges = [
                group.max_detection_range(Player.BLUE).meters for group in tgo.groups
            ]
            units = [unit.display_name_for(Player.BLUE) for unit in tgo.units]
            dead = tgo.is_dead(Player.BLUE)
        else:
            # Recon intel-fog: the site stays on the map and remains targetable
            # (position, category, allegiance), but its actual composition and
            # threat/detection rings are hidden until it is attacked, scouted, or
            # has a unit destroyed.
            threat_ranges = []
            detection_ranges = []
            units = []
            dead = False
        mobile = isinstance(tgo, ShipGroundObject) and blue
        destination: Optional[LeafletPoint] = None
        if (
            isinstance(tgo, ShipGroundObject)
            and blue
            and tgo.target_position is not None
        ):
            destination = LeafletPoint.from_latlng(tgo.target_position.latlng())
        from game.fourteenth.phases import roe_restriction_reason

        roe_reason = (
            None
            if blue
            else roe_restriction_reason(tgo.control_point.coalition.game, tgo)
        )
        roe_restricted = roe_reason is not None
        uncertainty = concealed_uncertainty(tgo)
        position = (uncertainty[0] if uncertainty else tgo.position).latlng()
        return TgoJs(
            id=tgo.id,
            name=tgo.name,
            control_point_name=tgo.control_point.name,
            category=tgo.category,
            blue=blue,
            position=position,
            units=units,
            threat_ranges=threat_ranges,
            detection_ranges=detection_ranges,
            dead=dead,
            sidc=str(tgo.sidc_for(Player.BLUE)),
            task=tgo.groups[0].ground_object.task if tgo.groups else None,
            mobile=mobile,
            destination=destination,
            user_placed=tgo.user_placed,
            roe_restricted=roe_restricted,
            roe_reason=roe_reason,
            uncertainty_radius_m=uncertainty[1] if uncertainty else None,
        )

    @staticmethod
    def all_in_game(game: Game) -> list[TgoJs]:
        tgos = []
        for control_point in game.theater.controlpoints:
            for tgo in control_point.connected_objectives:
                if tgo.is_control_point:
                    continue
                # SCAR campaign engine: an unrevealed enemy command post is hidden
                # from the player's map entirely (not just composition-fogged), so
                # it can't be seen or struck until a commander is captured or the
                # site is discovered. AI/planner use ground truth (viewer=None).
                if tgo.hidden_on_player_map(Player.BLUE):
                    continue
                tgos.append(TgoJs.for_tgo(tgo))
        return tgos
