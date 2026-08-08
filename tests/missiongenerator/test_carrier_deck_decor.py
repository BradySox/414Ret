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
    LSO_PLATFORM_CREW,
    FORWARD_DECK_ENVELOPE,
    FOOTPRINT_EXTRA_M,
    LSO_PLATFORM_ENVELOPE,
    RECOVERY_DECK_VARIANTS,
    ROUND_DOWN_VARIANTS,
    STATIC_META,
    STREET_VARIANTS,
    deck_layout_for,
    launch_phase_dressing_for,
    recovery_dressing_for,
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


def everything() -> Iterator[tuple[str, DeckStatic]]:
    yield from permanent_gear()
    yield from launch_phase()


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


def test_only_launch_phase_may_stand_in_the_ramp_crossing_keep_out() -> None:
    """Permanent placements stay out of the stern threshold / wires zone
    every recovering aircraft crosses a few metres above the deck.
    Launch-phase items may stand there -- the deckdecor plugin strikes them
    below before recovery."""
    for source, item in permanent_gear():
        assert not in_box(
            item.x, item.y, LANDING_AREA_KEEP_OUT
        ), f"{source}: {item} is inside the landing-area keep-out"


def test_launch_phase_stands_only_inside_the_recovery_corridor() -> None:
    """Launch-phase dressing may only stand INSIDE the recovery-corridor
    keep-out box -- the one zone the deckdecor plugin clears before recovery,
    and by definition not a parking area. The flown CVN-71 (2026-07-21) proved
    the looser 'aft of x' rule was insufficient: the removed port junk row was
    aft but sat forward/port of the box, in the port-quarter parking row, and
    clipped a spawning Hornet."""
    for source, item in launch_phase():
        assert in_box(
            item.x, item.y, LANDING_AREA_KEEP_OUT
        ), f"{source}: {item} is outside the recovery-corridor keep-out"


def test_launch_phase_composition_and_gating() -> None:
    """Launch-phase = one round-down variant (the port junk row was removed);
    empty without the tier or off a Nimitz deck; deterministic per
    (carrier, turn)."""
    lp = launch_phase_dressing_for(CVN_71.id, "CSG 1", 3, True)
    assert lp in ROUND_DOWN_VARIANTS
    assert lp == launch_phase_dressing_for(CVN_71.id, "CSG 1", 3, True)
    assert launch_phase_dressing_for(CVN_71.id, "CSG 1", 3, False) == []
    assert launch_phase_dressing_for(LHA_Tarawa.id, "ESG 1", 3, True) == []
    # Both round-down positions appear across turns.
    seen_round = {
        launch_phase_dressing_for(CVN_71.id, "CSG 1", turn, True)[0].x
        for turn in range(8)
    }
    assert len(seen_round) == len(ROUND_DOWN_VARIANTS)


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

    decor = generate_carrier_deck_decorations(
        mission, country, ship_group, heading, 3, include_aircraft=True
    )
    clear_names = decor.clear_names

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


def recovery_phase() -> Iterator[tuple[str, DeckStatic]]:
    for i, variant in enumerate(RECOVERY_DECK_VARIANTS):
        for item in variant:
            yield f"recovery variant {i}", item


def test_recovery_tier_stays_inside_the_forward_deck_box() -> None:
    """The recovery tier lives on the bow and the forward mid-deck strip.

    It must never reach the angled deck, the waist or the port side, so the
    box is entirely to starboard.
    """
    assert FORWARD_DECK_ENVELOPE[2] > 0.0, "box must be entirely to starboard"
    for source, item in recovery_phase():
        assert in_box(item.x, item.y, FORWARD_DECK_ENVELOPE), f"{source}: {item}"


def test_recovery_and_street_zones_never_overlap() -> None:
    """The two boxes must be disjoint, and no recovery item may land in the
    street box.

    The permanent street gear stands there for the whole mission, so recovery
    gear spawned on top of it would interpenetrate -- statics have no collision
    resolution. This is what excluded the campaign A mission 7/12/13 forward clusters,
    which are otherwise perfectly good sets: they sit inside the street box.
    """
    fx0, fx1, fy0, fy1 = FORWARD_DECK_ENVELOPE
    sx0, sx1, sy0, sy1 = ISLAND_STREET_ENVELOPE
    overlap_x = fx0 <= sx1 and sx0 <= fx1
    overlap_y = fy0 <= sy1 and sy0 <= fy1
    assert not (overlap_x and overlap_y), "forward-deck and street boxes overlap"
    for source, item in recovery_phase():
        assert not in_box(
            item.x, item.y, ISLAND_STREET_ENVELOPE
        ), f"{source}: {item} would spawn on the permanent street gear"


def test_recovery_aircraft_footprints_clear_the_street_gear() -> None:
    """Box disjointness is not enough once the tier carries aircraft.

    The envelope guards check item CENTRES. A parked Tomcat is ~19 m long, so
    its footprint reaches far aft of its centre — far enough to matter, since
    the permanent street gear stands there for the whole mission and statics
    have no collision resolution. This checks the footprint edge, not the
    centre.
    """
    street_forward_edge = ISLAND_STREET_ENVELOPE[1]
    for source, item in recovery_phase():
        extra = FOOTPRINT_EXTRA_M.get(item.type, 0.0)
        aft_edge = item.x - extra
        assert aft_edge > street_forward_edge, (
            f"{source}: {item.type} at x={item.x} reaches x={aft_edge:.1f}, "
            f"into the street box (forward edge {street_forward_edge})"
        )


def test_recovery_tier_may_carry_aircraft_but_permanent_gear_may_not() -> None:
    """The split that keeps the 2026-07-18 lesson intact.

    Static aircraft ARE allowed in the recovery tier (explicit call,
    2026-08-07: the clipping that banned them was a placement problem, not an
    aircraft problem, and this tier only stands once launches are over). They
    remain banned from the permanent layout, which is up the whole mission
    while every spawn path runs.
    """
    recovery_types = {item.type for _, item in recovery_phase()}
    assert any(
        STATIC_META[t][0] in ("Planes", "Helicopters") for t in recovery_types
    ), "recovery tier is allowed aircraft; if none remain, drop this test"
    for hull in (Stennis.id, CVN_71.id):
        for turn in range(12):
            for item in deck_layout_for(hull, "CSG 1", turn):
                assert STATIC_META[item.type][0] not in ("Planes", "Helicopters")


def test_recovery_tier_has_more_than_one_variant() -> None:
    """The recovery deck rotates like the street does.

    Shipped 2026-08-07 with a single campaign A mission 4 set, which meant every
    recovery on every carrier looked identical. Four sets now rotate on the
    same (carrier, turn) seed as the street.
    """
    assert len(RECOVERY_DECK_VARIANTS) >= 4
    seen = {
        tuple(recovery_dressing_for(CVN_71.id, "CSG 1", turn, True))
        for turn in range(12)
    }
    assert len(seen) == len(RECOVERY_DECK_VARIANTS), "not every variant is reachable"


def test_recovery_tier_clears_every_known_spot() -> None:
    """Every known spot, with the same margin the permanent gear keeps.

    NOTE this proves less than it reads: KNOWN_PARKING_SPOTS holds 11 of the
    Supercarrier guide's 16 spots, and the five it lacks include the bow-edge
    spots nearest this tier. That is why the tier is default-OFF. See the
    design note's "The 11-vs-16 spot gap".
    """
    for source, item in recovery_phase():
        need = required_spot_clearance_m(item.type)
        for sx, sy in KNOWN_PARKING_SPOTS:
            d = math.hypot(item.x - sx, item.y - sy)
            assert d >= need, f"{source}: {item.type} {d:.1f} m from ({sx}, {sy})"


def test_recovery_tier_never_touches_the_landing_area() -> None:
    """Recovery dressing exists FOR the recovery -- it cannot be in the way."""
    for source, item in recovery_phase():
        assert not in_box(
            item.x, item.y, LANDING_AREA_KEEP_OUT
        ), f"{source}: {item} stands in the recovery corridor"


def test_recovery_tier_has_static_meta() -> None:
    for source, item in recovery_phase():
        assert item.type in STATIC_META, f"{source}: {item.type} missing STATIC_META"


def test_recovery_tier_is_gated_and_rotates() -> None:
    assert recovery_dressing_for(CVN_71.id, "CSG 1", 3, False) == []
    assert recovery_dressing_for("Stennis-not-a-hull", "CSG 1", 3, True) == []
    picked = recovery_dressing_for(CVN_71.id, "CSG 1", 3, True)
    assert picked and picked in RECOVERY_DECK_VARIANTS
    # Deterministic across regeneration of the same turn.
    assert picked == recovery_dressing_for(CVN_71.id, "CSG 1", 3, True)


def test_recovery_tier_is_never_written_into_the_mission() -> None:
    """The whole point: the bow stays a launch deck until the plugin says so.

    A recovery placement that reached the .miz would stand there from mission
    start, which is exactly the spawn-clip failure this feature has already
    paid for twice.
    """
    mission = Mission()
    mission.coalition["blue"].add_country(USA())
    country = mission.country(USA.name)
    heading = Heading.from_degrees(80)
    ship_group = mission.ship_group(
        country, "CSG 1", CVN_71, Point(-350000, 250000, mission.terrain), heading=80
    )

    decor = generate_carrier_deck_decorations(
        mission,
        country,
        ship_group,
        heading,
        3,
        include_aircraft=False,
        include_recovery=True,
    )

    assert decor.recovery_specs, "recovery tier should have been picked"
    permanent = deck_layout_for(CVN_71.id, "CSG 1", 3)
    statics = list(country.static_group)
    assert len(statics) == len(permanent), "only the permanent set may be generated"
    for spec in decor.recovery_specs:
        for group in statics:
            unit = group.units[0]
            offsets = getattr(unit, "deck_offsets", None)
            assert offsets is None or (
                abs(offsets[0] - spec.x) > 0.01 or abs(offsets[1] - spec.y) > 0.01
            ), f"recovery placement {spec} leaked into the mission"
