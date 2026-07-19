"""Carrier deck decorations (§72): the parking-spot guards over the curated
layout data (footprint-aware for aircraft statics), the placement-class rules
(permanent / aircraft tier / launch-phase), the hull gate / per-turn rotation,
and the three-level linked-static serialization (group linkOffset / point
linkUnit / unit offsets).
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
    LAUNCH_PHASE_MAX_X,
    LSO_PLATFORM_CREW,
    LSO_PLATFORM_ENVELOPE,
    PORT_JUNK_VARIANTS,
    ROUND_DOWN_VARIANTS,
    STATIC_META,
    STREET_VARIANTS,
    deck_layout_for,
    launch_phase_dressing_for,
    required_spot_clearance_m,
)
from game.missiongenerator.carrierdeckdecor import generate_carrier_deck_decorations
from game.utils import Heading


def permanent_gear() -> Iterator[tuple[str, DeckStatic]]:
    for item in LSO_PLATFORM_CREW:
        yield "lso", item
    for i, variant in enumerate(STREET_VARIANTS):
        for item in variant:
            yield f"street variant {i}", item


def launch_phase() -> Iterator[tuple[str, DeckStatic]]:
    for i, variant in enumerate(ROUND_DOWN_VARIANTS):
        for item in variant:
            yield f"round-down variant {i}", item
    for i, variant in enumerate(PORT_JUNK_VARIANTS):
        for item in variant:
            yield f"port-junk variant {i}", item


def everything() -> Iterator[tuple[str, DeckStatic]]:
    yield from permanent_gear()
    yield from launch_phase()


def in_box(x: float, y: float, box: tuple[float, float, float, float]) -> bool:
    return box[0] <= x <= box[1] and box[2] <= y <= box[3]


def test_permanent_gear_is_inside_a_safe_envelope() -> None:
    """Permanent gear only where parking is impossible: the off-deck LSO
    sponson or the island street strip."""
    for source, item in permanent_gear():
        assert in_box(item.x, item.y, LSO_PLATFORM_ENVELOPE) or in_box(
            item.x, item.y, ISLAND_STREET_ENVELOPE
        ), f"{source}: {item} escapes the safe envelopes"


def test_every_placement_clears_every_known_spot() -> None:
    """EVERY placement -- permanent and launch-phase -- must clear every known
    spot by the footprint-aware margin. Late-activated groups spawn INTO
    statics standing on spots (the flown CVN-73 A-6-in-the-Seahawks clip,
    2026-07-18), so no static may stand on any spot, ever."""
    for source, item in everything():
        required = required_spot_clearance_m(item.type)
        for sx, sy in KNOWN_PARKING_SPOTS:
            clearance = math.hypot(item.x - sx, item.y - sy)
            assert clearance >= required, (
                f"{source}: {item} is {clearance:.1f} m from the known "
                f"spot at ({sx}, {sy}); needs {required:.1f}"
            )


def test_no_permanent_static_aircraft_exist() -> None:
    """The permanent layout is gear/crew ONLY: parked static aircraft on real
    spots are a proven late-activation spawn-clip hazard; the parked-aircraft
    look comes from Retribution's real deck population."""
    for hull in (Stennis.id, CVN_71.id):
        for turn in range(12):
            for item in deck_layout_for(hull, "CSG 1", turn):
                assert STATIC_META[item.type][0] not in ("Planes", "Helicopters")


def test_envelopes_stay_off_catapults_and_landing_area() -> None:
    """Guard the envelope constants themselves against accidental widening.

    Street: starboard of the landing-area foul line (y >= +12.5), against the
    island (never reaching the six-pack row, whose forward-most measured spot
    clearance is covered by the test above), between the corral (~-38) and the
    island's aft corner (~-75; the junkyard's own spots sit x <= -80 per the
    SC manual's diagrams). LSO box: the port-aft sponson, off the deck edge.
    The bow catapults live at x > +30 -- neither envelope reaches them.
    """
    sx0, sx1, sy0, sy1 = ISLAND_STREET_ENVELOPE
    assert sy0 >= 12.5
    assert sy1 <= 27.0
    assert -75.0 <= sx0 and sx1 <= -38.0
    lx0, lx1, ly0, ly1 = LSO_PLATFORM_ENVELOPE
    assert ly1 <= -18.0
    assert lx1 <= -100.0


def test_every_type_has_static_meta() -> None:
    for source, item in everything():
        assert item.type in STATIC_META, f"{source}: no meta for {item.type}"


def test_only_launch_phase_may_stand_in_the_ramp_crossing_keep_out() -> None:
    """Permanent placements stay out of the stern threshold / wires zone
    every recovering aircraft crosses a few metres above the deck.
    Launch-phase items may stand there -- the deckdecor plugin strikes them
    below before recovery."""
    for source, item in permanent_gear():
        assert not in_box(
            item.x, item.y, LANDING_AREA_KEEP_OUT
        ), f"{source}: {item} is inside the landing-area keep-out"


def test_launch_phase_is_aft_dressing_only() -> None:
    """Nothing launch-phase forward of the recovery corridor -- a forward
    static would stand in the bow-catapult taxi flow exactly during the
    launch cycle (why M4's bow set stays excluded)."""
    for source, item in launch_phase():
        assert item.x <= LAUNCH_PHASE_MAX_X, f"{source}: {item} is not aft"


def test_launch_phase_composition_and_gating() -> None:
    """Launch-phase = one round-down variant + one port junk-row variant;
    empty without the tier or off a Nimitz deck; deterministic per
    (carrier, turn)."""
    lp = launch_phase_dressing_for(CVN_71.id, "CSG 1", 3, True)
    assert lp[:1] in ROUND_DOWN_VARIANTS
    assert lp[1:] in PORT_JUNK_VARIANTS
    assert lp == launch_phase_dressing_for(CVN_71.id, "CSG 1", 3, True)
    assert launch_phase_dressing_for(CVN_71.id, "CSG 1", 3, False) == []
    assert launch_phase_dressing_for(LHA_Tarawa.id, "ESG 1", 3, True) == []
    # Both round-down positions and both port sets appear across turns.
    seen_round = set()
    seen_port = set()
    for turn in range(8):
        lp = launch_phase_dressing_for(CVN_71.id, "CSG 1", turn, True)
        seen_round.add(lp[0].x)
        seen_port.add(lp[1].x)
    assert len(seen_round) == len(ROUND_DOWN_VARIANTS)
    assert len(seen_port) == len(PORT_JUNK_VARIANTS)


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

    clear_names = generate_carrier_deck_decorations(
        mission, country, ship_group, heading, 3, include_aircraft=True
    )

    layout = deck_layout_for(CVN_71.id, "CSG 1", 3) + launch_phase_dressing_for(
        CVN_71.id, "CSG 1", 3, True
    )
    launch_count = len(launch_phase_dressing_for(CVN_71.id, "CSG 1", 3, True))
    statics = list(country.static_group)
    assert len(layout) == len(statics)
    # The launch-phase statics (placed last) are exactly the clear list the
    # deckdecor plugin receives.
    assert clear_names == [str(g.units[0].name) for g in statics[-launch_count:]]
    assert all("deck decor" in n and n.endswith("object") for n in clear_names)

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
