"""Carrier deck decoration generator (§72).

Places the curated deck-dressing statics (game/data/carrier_deck_decor.py)
onto a generated carrier, linked to the hull so they ride the moving ship.

A ship-linked static is serialized across three levels of the mission format
(none of which stock pydcs fully covers):

- ``linkUnit`` (the carrier's unit id) on the static group's first route point,
- ``linkOffset = true`` at the group level (pydcs native),
- ``offsets = {x, y, angle}`` (the ship-frame placement) on the unit.

DCS re-derives each linked static's world position from the offsets every
frame, so the absolute x/y written here only matter as a sane t=0 fallback;
they are still computed properly (ship position + rotated offset) so the
mission file reads correctly in the ME.
"""

from __future__ import annotations

import logging
from math import cos, radians, sin
from typing import Any, Dict, Optional

from dcs import Mission, Point
from dcs.country import Country
from dcs.point import StaticPoint
from dcs.unit import Static
from dcs.unitgroup import ShipGroup, StaticGroup

from game.data.carrier_deck_decor import STATIC_META, deck_layout_for
from game.utils import Heading


class DeckDecorStatic(Static):
    """A static carrying the ship-frame ``offsets`` table."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.deck_offsets: Optional[tuple[float, float, float]] = None

    def dict(self) -> Dict[str, Any]:
        d = super().dict()
        if self.deck_offsets is not None:
            x, y, angle_rad = self.deck_offsets
            d["offsets"] = {
                "x": x,
                "y": y,
                "angle": round(angle_rad, 13),
            }
        return d


class DeckDecorPoint(StaticPoint):
    """A static route point carrying the ``linkUnit`` reference."""

    def __init__(self, position: Any, link_unit_id: int) -> None:
        super().__init__(position)
        self.link_unit_id = link_unit_id

    def dict(self) -> Dict[str, Any]:
        d = super().dict()
        d["linkUnit"] = self.link_unit_id
        return d


def generate_carrier_deck_decorations(
    mission: Mission,
    country: Country,
    ship_group: ShipGroup,
    heading: Heading,
    turn: int,
) -> int:
    """Dress the flagship's deck. Returns the number of statics placed."""
    carrier = ship_group.units[0]
    layout = deck_layout_for(carrier.type, ship_group.name, turn)
    if not layout:
        return 0

    h = radians(heading.degrees)
    for i, item in enumerate(layout):
        # Ship frame -> world: DCS map x is north, y is east; ship forward is
        # (cos h, sin h), starboard is (-sin h, cos h).
        world = Point(
            carrier.position.x + item.x * cos(h) - item.y * sin(h),
            carrier.position.y + item.x * sin(h) + item.y * cos(h),
            mission.terrain,
        )
        name = f"{ship_group.name} deck decor {i + 1:02d}"
        static = DeckDecorStatic(
            mission.next_unit_id(), f"{name} object", item.type, mission.terrain
        )
        category, shape_name = STATIC_META[item.type]
        static.category = category
        static.shape_name = shape_name
        static.position = world
        static.heading = (heading.degrees + item.angle_deg) % 360
        static.deck_offsets = (item.x, item.y, radians(item.angle_deg))

        group = StaticGroup(mission.next_group_id(), name)
        group.add_unit(static)
        # pydcs annotates StaticGroup.heading as int but serializes any real
        # number; keep the authored sub-degree facing.
        group.heading = static.heading  # type: ignore[assignment]
        group.link_offset = True
        group.add_point(DeckDecorPoint(static.position, carrier.id))
        country.add_static_group(group)

    logging.debug(
        f"Placed {len(layout)} deck decorations on {ship_group.name} "
        f"({carrier.type})"
    )
    return len(layout)
