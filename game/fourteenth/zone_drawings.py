"""ROE zones Path B: read author-drawn Mission-Editor shapes back from the campaign
``.miz``.

Path A let a campaign author *type* restricted-zone geometry (circle/box/corridor)
into the ``phases:`` YAML. Path B lets them **draw** it in the Mission Editor instead
and reference it by name -- no hand-authored polygon vertices. DCS stores map drawings
in the mission's ``drawings`` table and pydcs parses them back into typed objects on
load (``Mission`` -> ``Drawings.load_from_dict``), so this module is just the read +
normalize step: it walks a loaded :class:`~dcs.mission.Mission`'s drawing layers and
turns each supported shape into a :class:`DrawnZone` keyed by the drawing's name.

The phases layer (``game/fourteenth/phases.py``) resolves a ``from_drawing: "<name>"``
zone by looking the name up in this index and building the same
``ResolvedZone``/shapely geometry Path A produces -- so a drawn shape gates the planner
and is painted on the F10/web map identically to a typed one.

v1 reads the two geometry types whose interpretation is unambiguous:

* **Circle** -- ``position`` is the centre, ``radius`` the radius (metres).
* **FreeFormPolygon** -- an absolute ring (``position`` + each local-offset vertex).
  A box, a corridor, a traced town or Route Package are all drawn with the polygon
  tool, so this one shape covers every non-circular case.

Rectangle/Oval are deliberately NOT read yet: their centre-vs-corner + width-axis
convention can't be confirmed without an in-game pass, and drawing the box as a 4-point
free polygon sidesteps it. TextBox/Icon/Arrow/Line and empty-named drawings are skipped
(a zone must have a name to be referenced).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from dcs.drawing.polygon import Circle, FreeFormPolygon

if TYPE_CHECKING:
    from dcs.drawing.drawing import Drawing
    from dcs.mission import Mission


@dataclass(frozen=True)
class DrawnZone:
    """A zone shape read from a Mission-Editor drawing (theater ``x``/``y`` metres).

    Mirrors the fields ``phases.ResolvedZone`` needs so the phases layer can build a
    ``ResolvedZone`` from it without importing pydcs: a circle carries ``center_xy`` +
    ``radius_m``; a polygon carries ``outline_xy`` (the ring) and a centroid
    ``center_xy`` label anchor.
    """

    name: str
    kind: str  # "circle" | "polygon"
    center_xy: tuple[float, float]
    radius_m: float = 0.0
    outline_xy: tuple[tuple[float, float], ...] = field(default=())


def _drawing_to_zone(obj: "Drawing") -> Optional[DrawnZone]:
    """Normalize one supported drawing to a :class:`DrawnZone`, or None to skip it."""
    name = (getattr(obj, "name", "") or "").strip()
    if not name:
        return None  # unnamed drawings can't be referenced from the YAML
    if isinstance(obj, Circle):
        pos = obj.position
        radius = float(getattr(obj, "radius", 0.0) or 0.0)
        if radius <= 0.0:
            return None
        return DrawnZone(
            name=name, kind="circle", center_xy=(pos.x, pos.y), radius_m=radius
        )
    if isinstance(obj, FreeFormPolygon):
        pos = obj.position
        # Stored points are local offsets from the drawing position; the first is (0,0).
        ring = [(pos.x + p.x, pos.y + p.y) for p in obj.points]
        if len(ring) > 1 and ring[0] == ring[-1]:
            ring = ring[:-1]
        if len(ring) < 3:
            return None  # a degenerate polygon is not an area
        cx = sum(p[0] for p in ring) / len(ring)
        cy = sum(p[1] for p in ring) / len(ring)
        return DrawnZone(
            name=name,
            kind="polygon",
            center_xy=(cx, cy),
            outline_xy=tuple(ring),
        )
    return None


def read_zone_drawings(mission: "Mission") -> dict[str, DrawnZone]:
    """Index a loaded mission's supported drawings by name.

    Reads every layer (author drawings usually land on the ``Author`` layer, but a
    campaign may draw anywhere); the ``from_drawing`` reference in the phase YAML is the
    real selector, so unreferenced decorations (a place-label circle, a compass rose)
    simply go unused. On a duplicate name the last drawing wins (logged) -- names are
    the reference key and should be unique.
    """
    zones: dict[str, DrawnZone] = {}
    for layer in mission.drawings.layers:
        for obj in getattr(layer, "objects", []):
            zone = _drawing_to_zone(obj)
            if zone is None:
                continue
            if zone.name in zones:
                logging.warning(
                    "ROE zone drawing %r appears more than once; using the last",
                    zone.name,
                )
            zones[zone.name] = zone
    return zones
