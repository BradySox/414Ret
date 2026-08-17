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

    Holds by construction since 2026-08-17 -- RECOVERY_DECK_VARIANTS is the
    authored data filtered through ``clears_known_spots`` -- so this now guards
    the filter rather than the coordinates.
    """
    for source, item in recovery_phase():
        need = required_spot_clearance_m(item.type)
        for sx, sy in KNOWN_PARKING_SPOTS:
            d = math.hypot(item.x - sx, item.y - sy)
            assert d >= need, f"{source}: {item.type} {d:.1f} m from ({sx}, {sy})"


def test_the_measured_forward_row_is_in_the_spot_table() -> None:
    """Measured 2026-08-17 from five CVN-71 recordings, 6 sightings each: the
    six-pack row continues forward of x=+1.0, where the table used to stop.
    Deleting these re-opens the hole that put a tow tractor 5.8 m from a spawn
    point in the recovery tier."""
    for spot in ((35.6, 36.7), (23.4, 35.5)):
        assert spot in KNOWN_PARKING_SPOTS, f"{spot} lost from the measured set"


def test_the_measured_mid_deck_row_is_in_the_spot_table() -> None:
    """The other half of the same pass: the 63 m starboard band between the
    six-pack row and the El-3 shoulder had NO entry at all, and 52 of the 67
    street-gear placements sit inside it."""
    for spot in ((-89.8, 26.4), (-76.3, 26.4), (-74.6, -38.4)):
        assert spot in KNOWN_PARKING_SPOTS, f"{spot} lost from the measured set"


def test_the_spot_filter_actually_removes_authored_placements() -> None:
    """The filter is load-bearing, not decoration: the authored sets DO place
    gear on measured spots, and a filter that silently passed everything would
    read identically at the call site."""
    from game.data.carrier_deck_decor import (
        _AUTHORED_RECOVERY_VARIANTS,
        clears_known_spots,
    )

    authored = sum(len(v) for v in _AUTHORED_RECOVERY_VARIANTS)
    shipped = sum(len(v) for v in RECOVERY_DECK_VARIANTS)
    assert shipped < authored, "nothing was filtered -- the rule is not applied"
    assert any(
        not clears_known_spots(item)
        for variant in _AUTHORED_RECOVERY_VARIANTS
        for item in variant
    )


def test_no_shipped_recovery_set_is_too_thin_to_read_as_a_respot() -> None:
    """A set filtered down to one tractor looks like a bug, not a re-spotted
    deck, so it is dropped whole instead."""
    from game.data.carrier_deck_decor import MIN_RECOVERY_SET_ITEMS

    assert RECOVERY_DECK_VARIANTS, "every recovery set was filtered away"
    for variant in RECOVERY_DECK_VARIANTS:
        assert len(variant) >= MIN_RECOVERY_SET_ITEMS


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


# ------------------------------------------ launch-cycle gate (flown 2026-08-16)


def test_the_respot_waits_for_the_last_launch_off_that_deck() -> None:
    """Flown: the recovery set spawned at t+79 s of a 2233 s mission -- 375 s
    before the player's own takeoff roll -- putting three static Hornets in his
    taxi lane, one 8.66 m off his track. The plan already knows when the deck
    stops launching."""
    from datetime import timedelta
    from types import SimpleNamespace

    from game.missiongenerator.deckdecorluadata import (
        LAUNCH_CYCLE_MARGIN_S,
        launch_cycle_ends_at,
    )

    def flight(airfield: str, delay_s: int) -> object:
        return SimpleNamespace(
            departure=SimpleNamespace(airfield_name=airfield),
            departure_delay=timedelta(seconds=delay_s),
        )

    mission_data = SimpleNamespace(
        flights=[
            flight("CVN-75 Harry S. Truman", 120),
            flight("CVN-75 Harry S. Truman", 455),  # the player's launch
            flight("Kutaisi", 3000),  # another base entirely
        ]
    )

    ends = launch_cycle_ends_at(mission_data, "CVN-75 Harry S. Truman")  # type: ignore[arg-type]

    assert ends == 455 + LAUNCH_CYCLE_MARGIN_S
    assert ends > 79, "the flown spurious clear must now be held"


def test_a_much_later_package_is_a_different_cycle_and_does_not_hold_the_deck() -> None:
    """Flown 2026-08-16 (5th test): one late flight off CVN-71 held the respot to
    t+11,388 s of a 19-minute mission, so the deck never respotted at all.
    ``departure_delay`` is the whole wait until a flight's scheduled start, which
    for a late package is hours -- a cycle the mission never reaches."""
    from datetime import timedelta
    from types import SimpleNamespace

    from game.missiongenerator.deckdecorluadata import (
        LAUNCH_CYCLE_MARGIN_S,
        launch_cycle_ends_at,
    )

    def flight(delay_s: int) -> object:
        return SimpleNamespace(
            departure=SimpleNamespace(airfield_name="CVN-71 Theodore Roosevelt"),
            departure_delay=timedelta(seconds=delay_s),
        )

    mission_data = SimpleNamespace(flights=[flight(0), flight(300), flight(10788)])

    ends = launch_cycle_ends_at(mission_data, "CVN-71 Theodore Roosevelt")  # type: ignore[arg-type]

    assert ends == 300 + LAUNCH_CYCLE_MARGIN_S
    assert ends < 1500, "the respot must still happen inside the airboss window"


def test_a_cycle_is_unbroken_across_gaps_shorter_than_the_margin() -> None:
    """A deck launching steadily is still launching: only an idle gap longer than
    the margin ends the cycle, so a staggered go is held to its own last jet."""
    from datetime import timedelta
    from types import SimpleNamespace

    from game.missiongenerator.deckdecorluadata import (
        LAUNCH_CYCLE_MARGIN_S,
        launch_cycle_ends_at,
    )

    def flight(delay_s: int) -> object:
        return SimpleNamespace(
            departure=SimpleNamespace(airfield_name="CVN-71 Theodore Roosevelt"),
            departure_delay=timedelta(seconds=delay_s),
        )

    # Emitted out of order on purpose: the flights list follows package order.
    mission_data = SimpleNamespace(
        flights=[flight(900), flight(0), flight(1400), flight(450)]
    )

    ends = launch_cycle_ends_at(mission_data, "CVN-71 Theodore Roosevelt")  # type: ignore[arg-type]

    assert ends == 1400 + LAUNCH_CYCLE_MARGIN_S


def test_a_deck_that_launches_nothing_keeps_the_old_behaviour() -> None:
    """No launches means no launch cycle to protect: the cone and the fallback
    deadline stay in sole charge, exactly as before."""
    from types import SimpleNamespace

    from game.missiongenerator.deckdecorluadata import launch_cycle_ends_at

    mission_data = SimpleNamespace(
        flights=[
            SimpleNamespace(
                departure=SimpleNamespace(airfield_name="Kutaisi"),
                departure_delay=None,
            )
        ]
    )

    assert launch_cycle_ends_at(mission_data, "CVN-75 Harry S. Truman") == 0  # type: ignore[arg-type]
