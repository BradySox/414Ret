"""Shared placement for theater support racetracks (AEW&C and tankers).

Both support types want the same thing: a racetrack sitting a safe standoff
*behind the front line*, centered on the fighting, flying parallel to the FLOT.
The old per-builder logic anchored the orbit on a control point
(``package.target``) and offset it along the bearing to the nearest enemy
threat-zone boundary. For a rear/flank CP that bearing is unstable -- it swings
as the front shifts -- so AI AWACS in particular got flung hundreds of NM
off-axis (observed: red AWACS anchored on a far-north CP ended up ~175 NM
laterally off the front and ~326 NM behind it). Tankers anchored on their own
departure field could even clamp onto the home runway.

This helper instead anchors on the **front line center** and pushes the orbit
into friendly territory along the stable enemy->friendly axis until it is at
least ``threat_buffer`` from the enemy threat zone. The result is centered on
the front and at the configured standoff regardless of where the supporting
squadron is based.

The one exception is a support orbit tasked to a **carrier/fleet** target: it
holds with its task force (anchored on the carrier, only nudged clear of the
threat zone) instead of marching up to the land FLOT, so a carrier E-2C/tanker
covers the boat rather than flying ~200 NM forward to cover the front.

With **no front line at all** (a pure naval map, or fully disconnected
theaters) the orbit likewise holds at its anchor and is only nudged clear of
the threat zone. The depth march exists to hold support *behind the FLOT*;
with no FLOT there is no "behind", and marching away from the nearest threat
boundary just flees the map (observed: a red A-50 on a carriers-only enemy
anchored on the friendly field farthest from the fleet, then marched another
2.5 x 80 NM = 200 NM straight away from it — 233-322 NM from the fight).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from game.utils import Distance, Heading, meters

if TYPE_CHECKING:
    from dcs.mapping import Point
    from game.theater import ConflictTheater, MissionTarget, Player
    from game.theater.frontline import FrontLine
    from game.threatzones import ThreatZones


# AI (enemy) support orbits sit this many *buffers* behind the FLOT, so red
# tankers/AWACS hold deep in friendly airspace instead of loitering near the
# front like the player's do. The player coalition uses 1x (kept forward for
# coverage). With the default buffers (AEWC 80 NM / tanker 70 NM) this puts AI
# support ~200/175 NM back; with a smaller campaign buffer it scales down.
# Whatever the depth, the orbit is still pushed clear of the enemy threat zone.
AI_SUPPORT_DEPTH_FACTOR = 2.5


def _relevant_front(
    theater: ConflictTheater, target: MissionTarget
) -> Optional[FrontLine]:
    """The active front nearest the supported area (``target``)."""
    fronts = list(theater.conflicts())
    if not fronts:
        return None
    return min(fronts, key=lambda fl: fl.position.distance_to_point(target.position))


def support_orbit_anchor(
    theater: ConflictTheater,
    player: Player,
    threat_zones: ThreatZones,
    target: MissionTarget,
    threat_buffer: Distance,
) -> tuple[Point, Heading]:
    """Where a support racetrack should sit, and which way it faces.

    Returns ``(center, toward_enemy)`` where ``center`` is the racetrack center
    (the standoff point behind the front) and ``toward_enemy`` is the heading
    pointing at the enemy -- callers orient the racetrack perpendicular to it so
    the orbit runs parallel to the FLOT.

    A support orbit tasked to a **carrier/fleet** is the exception: it holds with
    its task force instead of marching up to the land FLOT. So a carrier E-2C (or
    a carrier tanker) covers the boat rather than being flung ~200 NM forward to
    the front. It anchors on the carrier and is only nudged clear of the threat
    zone (no forward/deep standoff march).
    """
    # ControlPoints expose is_carrier/is_fleet; other MissionTargets (front
    # lines, ground objects, refueling points) do not -- treat those as land.
    carrier_target = getattr(target, "is_carrier", False) or getattr(
        target, "is_fleet", False
    )

    front = None if carrier_target else _relevant_front(theater, target)
    if front is None:
        # Either a carrier/fleet orbit (hold with the task force) or no active
        # front (e.g. opening turn): anchor on the target and stand off from the
        # nearest threat boundary.
        anchor = target.position
        boundary = threat_zones.closest_boundary(anchor)
        toward_enemy = Heading.from_degrees(anchor.heading_between_point(boundary))
        if threat_zones.threatened(anchor):
            # From INSIDE the zone the closest boundary is the way OUT, not
            # the way toward the enemy -- flip, or the clearance push below
            # would march the orbit deeper into the threat.
            toward_enemy = toward_enemy.opposite
        center = anchor
    else:
        anchor = front.position
        friendly_cp = front.blue_cp if player.is_blue else front.red_cp
        enemy_cp = front.red_cp if player.is_blue else front.blue_cp
        # Stable axis: it tracks the front, not a wandering boundary bearing.
        toward_enemy = Heading.from_degrees(
            friendly_cp.position.heading_between_point(enemy_cp.position)
        )
        center = anchor

    away_from_enemy = toward_enemy.opposite

    # Base standoff behind the front: the player holds forward at 1x the buffer
    # for coverage; the AI holds deep (AI_SUPPORT_DEPTH_FACTOR x) so red
    # tankers/AWACS don't loiter near the FLOT. A carrier orbit skips this march
    # entirely -- it stays on the fleet and is only pushed clear of the threat
    # zone below. A no-front theater skips it too: the march is a depth *behind
    # the FLOT*, and with no FLOT it just drags the orbit away from the only
    # enemy on the map (the naval-map red-A-50-in-Qatar bug) -- the threat
    # floor below is the whole standoff.
    if not carrier_target and front is not None:
        factor = 1.0 if player.is_blue else AI_SUPPORT_DEPTH_FACTOR
        base_push = threat_buffer * factor
        if base_push > meters(0):
            center = center.point_from_heading(
                away_from_enemy.degrees, base_push.meters
            )

    # Then guarantee it is at least threat_buffer clear of the enemy threat zone,
    # pushing further into friendly airspace if the base standoff left it exposed.
    distance_to_threat = threat_zones.distance_to_threat(center)
    if threat_zones.threatened(center):
        # Inside the threat zone: get clear, then add the buffer.
        extra = distance_to_threat + threat_buffer
    elif distance_to_threat < threat_buffer:
        extra = threat_buffer - distance_to_threat
    else:
        extra = meters(0)

    if extra > meters(0):
        center = center.point_from_heading(away_from_enemy.degrees, extra.meters)

    return center, toward_enemy


def forward_cap_front_anchor(
    theater: ConflictTheater,
    player: Player,
    threat_zones: ThreatZones,
    location: MissionTarget,
    standoff: Distance,
) -> Optional[tuple[Point, Heading]]:
    """Center + enemy-facing heading for an *added* forward-middle BARCAP screen on
    the player's side of the active front.

    Only returns a result when ``location`` is the player's *own* control point on
    an active front -- i.e. a CP that actually anchors the FLOT. For rear/flank CPs,
    or when there is no active front, it returns ``None`` so the caller skips the
    forward layer (the rear/base BARCAP is unchanged and handled elsewhere).

    The center is placed **forward-middle**: roughly halfway from the rear CP to the
    front center, then pushed back toward friendly airspace only if that leaves it
    within ``standoff`` of the *enemy* threat zone (``threat_zones`` is the
    opponent's). ``toward_enemy`` points across the FLOT so the caller can lay the
    racetrack parallel to the front. Front-relative throughout -- no map-specific
    distances -- so it scales across map sizes.
    """
    front = _relevant_front(theater, location)
    if front is None:
        return None
    friendly_cp = front.blue_cp if player.is_blue else front.red_cp
    # Only a CP that actually anchors this front gets the forward screen.
    if location is not friendly_cp:
        return None
    enemy_cp = front.red_cp if player.is_blue else front.blue_cp
    toward_enemy = Heading.from_degrees(
        friendly_cp.position.heading_between_point(enemy_cp.position)
    )
    away_from_enemy = toward_enemy.opposite

    # Forward-middle: roughly halfway from the rear CP to the front center, along the
    # stable friendly->enemy axis.
    rear = friendly_cp.position
    to_flot = rear.distance_to_point(front.position)
    center = rear.point_from_heading(toward_enemy.degrees, to_flot * 0.5)

    # Keep clear of the enemy threat zone by `standoff`, pulling back toward friendly
    # airspace only if the forward-middle point is too exposed.
    distance_to_threat = threat_zones.distance_to_threat(center)
    if threat_zones.threatened(center):
        extra = distance_to_threat + standoff
    elif distance_to_threat < standoff:
        extra = standoff - distance_to_threat
    else:
        extra = meters(0)
    if extra > meters(0):
        center = center.point_from_heading(away_from_enemy.degrees, extra.meters)

    return center, toward_enemy
