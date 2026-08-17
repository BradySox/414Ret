"""Where a flight's REFUEL waypoint should actually send it.

The planner picks the refuel point purely geometrically -- 75 % of the way from
home to the join point (``RefuelZoneGeometry``) -- and never consults the tankers
that are flying. The tankers are placed by a different rule again: a theater
tanker stations ``tanker_threat_buffer_min_distance`` outside the threat ring of
its own package target. The two have no term in common, so the waypoint routinely
points at empty sky while the tanker orbits somewhere else entirely.

This resolves the waypoint against the tankers that exist in the generated .miz,
at generation time, so the plan and the planner are untouched.

Rationale and the flown evidence live in
``docs/dev/414th-features.md`` §8.
"""

from __future__ import annotations

from typing import Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from dcs import Point

    from game.dcs.aircrafttype import AircraftType
    from game.missiongenerator.missiondata import TankerInfo


def nearest_point_on_leg(target: "Point", start: "Point", end: "Point") -> "Point":
    """The point on segment ``start``-``end`` closest to ``target``.

    A tanker orbit is a 40 nm racetrack, so treating it as its centre can be 20 nm
    out on its own. Clamped to the segment: the orbit's ends are where the tanker
    turns, not waypoints it flies past.
    """
    ax, ay = start.x, start.y
    dx, dy = end.x - ax, end.y - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= 0.0:
        return start
    t = ((target.x - ax) * dx + (target.y - ay) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    return start.new_in_same_map(ax + t * dx, ay + t * dy)


def refuel_rendezvous(
    receiver: "AircraftType",
    receiver_is_blue: bool,
    planned: "Point",
    tankers: Iterable["TankerInfo"],
) -> Optional["Point"]:
    """The orbit point to send ``receiver`` to, or None if no tanker can serve it.

    None means the waypoint has no rendezvous behind it and should be dropped --
    which subsumes the "no tanker flying at all" case, and additionally covers a
    probe-only receiver whose side is flying nothing but a boom tanker.
    """
    best: Optional["Point"] = None
    best_distance = 0.0
    for tanker in tankers:
        if not _serves(tanker, receiver, receiver_is_blue):
            continue
        start = getattr(tanker, "orbit_start", None)
        if start is None:
            # Registered before this data existed, or a plan with no patrol
            # layout. It is still a real tanker, so it must not read as "none
            # flying" -- fall back to leaving the planned point alone.
            return planned
        end = getattr(tanker, "orbit_end", None) or start
        candidate = nearest_point_on_leg(planned, start, end)
        distance = planned.distance_to_point(candidate)
        if best is None or distance < best_distance:
            best = candidate
            best_distance = distance
    return best


def _serves(
    tanker: "TankerInfo", receiver: "AircraftType", receiver_is_blue: bool
) -> bool:
    side = getattr(tanker, "blue", None)
    if side is not None and bool(getattr(side, "is_blue", side)) != receiver_is_blue:
        return False
    if getattr(tanker, "recovery", False):
        # A recovery tanker orbits astern of the boat to catch aircraft coming
        # aboard. Routing a passing striker to it is not a rendezvous, it is a
        # detour to the carrier.
        return False
    tanker_type = getattr(tanker, "aircraft_type", None)
    if tanker_type is not None and not receiver.can_refuel_from(tanker_type):
        return False
    return True
