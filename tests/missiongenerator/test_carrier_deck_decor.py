"""Carrier deck decorations (§72): the parking-spot guard over the curated
layout data, the hull gate / per-turn rotation, and the three-level
linked-static serialization (group linkOffset / point linkUnit / unit offsets).
"""

from __future__ import annotations

import math
from typing import Iterator

import pytest
from dcs.countries import USA
from dcs.mapping import Point
from dcs.mission import Mission
from dcs.ships import CVN_71, KUZNECOW, LHA_Tarawa, Stennis

from game.data.carrier_deck_decor import (
    DeckStatic,
    ISLAND_STREET_ENVELOPE,
    KNOWN_PARKING_SPOTS,
    LSO_PLATFORM_CREW,
    LSO_PLATFORM_ENVELOPE,
    MIN_SPOT_CLEARANCE_M,
    STATIC_META,
    STREET_VARIANTS,
    deck_layout_for,
)
from game.missiongenerator.carrierdeckdecor import generate_carrier_deck_decorations
from game.utils import Heading


def all_placements() -> Iterator[tuple[str, DeckStatic]]:
    for item in LSO_PLATFORM_CREW:
        yield "lso", item
    for i, variant in enumerate(STREET_VARIANTS):
        for item in variant:
            yield f"variant {i}", item


def in_box(x: float, y: float, box: tuple[float, float, float, float]) -> bool:
    return box[0] <= x <= box[1] and box[2] <= y <= box[3]


def test_every_placement_is_inside_a_safe_envelope() -> None:
    """The hard §72 constraint: decorations only where parking is impossible.

    The LSO platform is an off-deck sponson; the island street is flanked by
    the six-pack row, the corral and the junkyard with no parking location
    inside it. Anything outside those two envelopes could sit on a spot.
    """
    for source, item in all_placements():
        assert in_box(item.x, item.y, LSO_PLATFORM_ENVELOPE) or in_box(
            item.x, item.y, ISLAND_STREET_ENVELOPE
        ), f"{source}: {item} escapes the safe envelopes"


def test_every_placement_clears_every_known_parking_spot() -> None:
    for source, item in all_placements():
        for sx, sy in KNOWN_PARKING_SPOTS:
            clearance = math.hypot(item.x - sx, item.y - sy)
            assert clearance >= MIN_SPOT_CLEARANCE_M, (
                f"{source}: {item} is {clearance:.1f} m from the parking "
                f"spot at ({sx}, {sy})"
            )


def test_envelopes_stay_off_catapults_and_landing_area() -> None:
    """Guard the envelope constants themselves against accidental widening.

    Street: starboard of the landing-area foul line (y >= +12.5), well inboard
    of the six-pack row at y = +34, between the island's forward face (~-38)
    and the junkyard (~-72). LSO box: the port-aft sponson, aft of the port
    quarter spots and off the deck edge (y <= -18). The bow catapults live at
    x > +30 and the waist catapult tracks port of centreline -- neither
    envelope reaches them.
    """
    sx0, sx1, sy0, sy1 = ISLAND_STREET_ENVELOPE
    assert sy0 >= 12.5
    assert sy1 <= 34.0 - MIN_SPOT_CLEARANCE_M
    assert -72.0 <= sx0 and sx1 <= -38.0
    lx0, lx1, ly0, ly1 = LSO_PLATFORM_ENVELOPE
    assert ly1 <= -18.0
    assert lx1 <= -100.0


def test_every_type_has_static_meta() -> None:
    for source, item in all_placements():
        assert item.type in STATIC_META, f"{source}: no meta for {item.type}"


def test_layout_gating_and_rotation() -> None:
    # Nimitz-family decks are dressed; every layout leads with the LSO crew.
    for hull in (Stennis.id, CVN_71.id):
        layout = deck_layout_for(hull, "CSG 1", 3)
        assert layout[: len(LSO_PLATFORM_CREW)] == LSO_PLATFORM_CREW
        assert len(layout) > len(LSO_PLATFORM_CREW)
    # Deterministic for the same (carrier, turn) so regeneration is stable.
    assert deck_layout_for(CVN_71.id, "CSG 1", 3) == deck_layout_for(
        CVN_71.id, "CSG 1", 3
    )
    # ... and rotates across turns.
    layouts = {tuple(deck_layout_for(CVN_71.id, "CSG 1", turn)) for turn in range(8)}
    assert len(layouts) == len(STREET_VARIANTS)
    # Non-Nimitz decks are untouched (their spot geography is different).
    assert deck_layout_for(LHA_Tarawa.id, "ESG 1", 3) == []
    assert deck_layout_for(KUZNECOW.id, "Red CSG", 3) == []


def test_linked_static_serialization() -> None:
    mission = Mission()
    mission.coalition["blue"].add_country(USA())
    country = mission.country(USA.name)
    heading = Heading.from_degrees(80)
    ship_group = mission.ship_group(
        country, "CSG 1", CVN_71, Point(-350000, 250000, mission.terrain), heading=80
    )
    carrier = ship_group.units[0]

    count = generate_carrier_deck_decorations(mission, country, ship_group, heading, 3)

    layout = deck_layout_for(CVN_71.id, "CSG 1", 3)
    statics = list(country.static_group)
    assert count == len(layout) == len(statics)

    names = set()
    h = math.radians(80)
    for item, group in zip(layout, statics):
        d = group.dict()
        names.add(d["name"])
        # group level: linked, riding the ship
        assert d["linkOffset"] is True
        # route point level: linked to the carrier hull
        assert d["route"]["points"][1]["linkUnit"] == carrier.id
        # unit level: the ship-frame offsets, verbatim from the layout table
        unit = d["units"][1]
        offsets = unit["offsets"]
        assert offsets["x"] == item.x
        assert offsets["y"] == item.y
        assert offsets["angle"] == round(math.radians(item.angle_deg), 13)
        assert unit["category"] == STATIC_META[item.type][0]
        assert unit["type"] == item.type
        # world-frame fallback position: ship position + rotated offset
        expected_x = carrier.position.x + item.x * math.cos(h) - item.y * math.sin(h)
        expected_y = carrier.position.y + item.x * math.sin(h) + item.y * math.cos(h)
        assert unit["x"] == pytest.approx(expected_x, abs=1e-6)
        assert unit["y"] == pytest.approx(expected_y, abs=1e-6)
        # world heading = ship heading + relative angle
        assert unit["heading"] == pytest.approx(
            math.radians((80 + item.angle_deg) % 360), abs=1e-6
        )
    assert len(names) == len(statics), "deck decor group names must be unique"
