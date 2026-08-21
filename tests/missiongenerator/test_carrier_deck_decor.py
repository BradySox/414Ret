"""Carrier deck decorations (§72): the parking-spot guards over the curated
layout data, the safe envelopes, the hull gate / per-turn rotation, and the
three-level linked-static serialization (group linkOffset / point linkUnit /
unit offsets).

One tier only. The launch-phase round-down E-2C and the recovery-phase bow
respot were removed 2026-08-20, so every placement here stands for the whole
mission and there is no runtime clear or spawn to guard.
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
    LANDING_AREA_KEEP_OUT,
    LSO_PLATFORM_CREW,
    LSO_PLATFORM_ENVELOPE,
    MIN_SPOT_CLEARANCE_M,
    STATIC_META,
    STREET_VARIANTS,
    deck_layout_for,
)
from game.missiongenerator.carrierdeckdecor import generate_carrier_deck_decorations
from game.utils import Heading


def everything() -> Iterator[tuple[str, DeckStatic]]:
    for item in LSO_PLATFORM_CREW:
        yield "lso", item
    for i, variant in enumerate(STREET_VARIANTS):
        for item in variant:
            yield f"street variant {i}", item


def in_box(x: float, y: float, box: tuple[float, float, float, float]) -> bool:
    return box[0] <= x <= box[1] and box[2] <= y <= box[3]


def test_every_street_variant_carries_enough_gear() -> None:
    """A street set thinner than five items reads as a bare deck, not a dressed one.

    This is the curation floor applied when the campaign A mining was completed
    (2026-08-07): missions 1/2/4/5 cleared it and shipped, missions 7 (4 items
    inside the envelope) and 8 (2) did not and were deliberately left unmined.
    """
    for i, variant in enumerate(STREET_VARIANTS):
        assert len(variant) >= 5, f"street variant {i} has only {len(variant)} items"


def test_gear_is_inside_a_safe_envelope() -> None:
    """Dressing only where parking is impossible: the off-deck LSO sponson or
    the island street strip."""
    for source, item in everything():
        assert in_box(item.x, item.y, LSO_PLATFORM_ENVELOPE) or in_box(
            item.x, item.y, ISLAND_STREET_ENVELOPE
        ), f"{source}: {item} escapes the safe envelopes"


def test_every_placement_clears_every_known_spot() -> None:
    """Every placement must clear every known spot. Late-activated groups spawn
    INTO statics standing on spots (the flown CVN-73 A-6-in-the-Seahawks clip,
    2026-07-18), so no static may stand on any spot, ever."""
    for source, item in everything():
        for sx, sy in KNOWN_PARKING_SPOTS:
            clearance = math.hypot(item.x - sx, item.y - sy)
            assert clearance >= MIN_SPOT_CLEARANCE_M, (
                f"{source}: {item} is {clearance:.1f} m from the known "
                f"spot at ({sx}, {sy}); needs {MIN_SPOT_CLEARANCE_M:.1f}"
            )


def test_no_static_aircraft_exist() -> None:
    """Gear and crew ONLY. Parked static aircraft on real spots are a proven
    late-activation spawn-clip hazard at any hour of the mission (test 11 saw
    14 aircraft activate onto the deck up to t+39 min); the parked-aircraft
    look comes from Retribution's real deck population."""
    for _, item in everything():
        assert STATIC_META[item.type][0] not in ("Planes", "Helicopters")
    for hull in (Stennis.id, CVN_71.id):
        for turn in range(12):
            for item in deck_layout_for(hull, "CSG 1", turn):
                assert STATIC_META[item.type][0] not in ("Planes", "Helicopters")


def test_envelopes_stay_off_catapults_and_landing_area() -> None:
    """Guard the envelope constants themselves against accidental widening.

    Island street (after the 2026-07-27 reposition): the clear strip ALONGSIDE
    the island, starboard of centerline (y >= 0, clear of the port angled deck)
    but inboard of the six-pack row (y <= +25, i.e. >= 9 m off the y = +34
    spots), aft of the bow catapults (x <= -8, cats live at x > +30) yet forward
    of the aft junkyard/El-3 spots (x >= -70, spots at x <= -98). LSO box: the
    port-aft sponson, off the deck edge.
    """
    sx0, sx1, sy0, sy1 = ISLAND_STREET_ENVELOPE
    assert sy0 >= 0.0
    assert sy1 <= 25.0
    assert -70.0 <= sx0 and sx1 <= -8.0
    lx0, lx1, ly0, ly1 = LSO_PLATFORM_ENVELOPE
    assert ly1 <= -18.0
    assert lx1 <= -100.0


def test_every_type_has_static_meta() -> None:
    for source, item in everything():
        assert item.type in STATIC_META, f"{source}: no meta for {item.type}"


def test_nothing_stands_in_the_ramp_crossing_keep_out() -> None:
    """Nothing may stand in the stern threshold / wires zone every recovering
    aircraft crosses a few metres above the deck. Nothing is struck below any
    more, so there is no exemption to this."""
    for source, item in everything():
        assert not in_box(
            item.x, item.y, LANDING_AREA_KEEP_OUT
        ), f"{source}: {item} is inside the landing-area keep-out"


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
    # ... and every street variant appears across consecutive turns.
    layouts = {tuple(deck_layout_for(CVN_71.id, "CSG 1", turn)) for turn in range(12)}
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

    generate_carrier_deck_decorations(mission, country, ship_group, heading, 3)

    layout = deck_layout_for(CVN_71.id, "CSG 1", 3)
    statics = list(country.static_group)
    assert len(layout) == len(statics)

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


def test_a_non_nimitz_hull_is_left_bare() -> None:
    mission = Mission()
    mission.coalition["blue"].add_country(USA())
    country = mission.country(USA.name)
    ship_group = mission.ship_group(
        country,
        "ESG 1",
        LHA_Tarawa,
        Point(-350000, 250000, mission.terrain),
        heading=80,
    )
    generate_carrier_deck_decorations(
        mission, country, ship_group, Heading.from_degrees(80), 3
    )
    assert list(country.static_group) == []


def test_the_measured_forward_row_is_in_the_spot_table() -> None:
    """Measured 2026-08-17 from five CVN-71 recordings, 6 sightings each: the
    six-pack row continues forward of x=+1.0, where the table used to stop.
    Deleting these re-opens the hole that put a tow tractor 5.8 m from a spawn
    point."""
    for spot in ((35.6, 36.7), (23.4, 35.5)):
        assert spot in KNOWN_PARKING_SPOTS, f"{spot} lost from the measured set"


def test_the_measured_mid_deck_row_is_in_the_spot_table() -> None:
    """The other half of the same pass: the 63 m starboard band between the
    six-pack row and the El-3 shoulder had NO entry at all, and 52 of the 67
    street-gear placements sit inside it."""
    for spot in ((-89.8, 26.4), (-76.3, 26.4), (-74.6, -38.4)):
        assert spot in KNOWN_PARKING_SPOTS, f"{spot} lost from the measured set"
