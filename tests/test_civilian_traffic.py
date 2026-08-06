"""Civilian background-traffic planning (Python side).

The civilian layer is planned in ``game/missiongenerator/civiliantraffic.py`` and
spawned via pydcs (no MOOSE RAT -- see that module's header for why RAT stays
retired). The geometry is plain Python, so unlike the old RAT plugin it is exercised
here.

Rebuilt 2026-08-05 against the DM's two named issues, and these tests are shaped to
pin exactly those:

* **airways, not milk runs** -- a fixed-wing route is now ONE long transit, not a
  chain of five short rear-area hops;
* **civil identity is a data table** -- fleet, operators and cruise levels are chosen
  per region, and 1944 theatres field no civil traffic at all.
"""

from __future__ import annotations

import random

from dcs.helicopters import Mi_8MT, UH_1H
from dcs.mapping import Point
from dcs.planes import An_26B, C_130, IL_76MD, Yak_40

from game.missiongenerator.civilianfleet import (
    CIVIL_TRAFFIC_NONE,
    CRUISE_PROFILE,
    REGIONS,
    region_for,
)
from game.missiongenerator.civiliantraffic import (
    AIR_START_MIN_ALT_M,
    HELO_MAXDIST_M,
    KEEPOUT_M,
    MIN_TRANSIT_M,
    _Field,
    admit_field,
    airway_pairs,
    density,
    plan_airways,
    plan_local_rotary,
    prune_to_reachable,
)

_T = None  # terrain only passed through; never dereferenced in planning


def _pt(x: float, y: float) -> Point:
    return Point(x, y, _T)  # type: ignore[arg-type]  # terrain never dereferenced


def _field(name: str, x: float, y: float) -> _Field:
    return _Field(name=name, point=_pt(x, y))


def _spread(n: int, spacing: float = 120_000) -> list[_Field]:
    """Fields far enough apart that airway pairs genuinely exist."""
    return [_field(chr(65 + i), i * spacing, 0) for i in range(n)]


# --- front keep-out and pool geometry (unchanged behaviour) --------------------


def test_admit_field_clear_of_front_is_always_admitted() -> None:
    assert admit_field(_pt(0, 0), [_pt(1_000_000, 0)], random.Random(0)) is True


def test_admit_field_inside_keepout_is_mostly_dropped() -> None:
    front = _pt(0, 0)
    inside = _pt(KEEPOUT_M / 2, 0)
    drops = sum(
        0 if admit_field(inside, [front], random.Random(s)) else 1 for s in range(50)
    )
    assert drops > 40  # ~92% dropped given the 0.08 stray chance


def test_prune_drops_isolated_field_keeps_cluster() -> None:
    kept = prune_to_reachable(
        [_field("A", 0, 0), _field("B", 50_000, 0), _field("C", 5_000_000, 0)],
        HELO_MAXDIST_M,
    )
    assert {f.name for f in kept} == {"A", "B"}


def test_density_scales_and_clamps() -> None:
    assert density(0, 1, 3) == 1
    assert density(100, 1, 3) == 3
    assert density(20, 1, 3) == 3
    assert density(7, 1, 3) == 2


# --- airways, not milk runs ---------------------------------------------------


def test_airway_pairs_only_returns_genuine_transits() -> None:
    pool = [_field("A", 0, 0), _field("B", 20_000, 0), _field("C", 400_000, 0)]
    pairs = airway_pairs(pool, MIN_TRANSIT_M)
    named = {(pool[i].name, pool[j].name) for i, j in pairs}
    # A-B is a 20 km hop, not a transit.
    assert ("A", "B") not in named
    assert ("A", "C") in named and ("B", "C") in named


def test_a_fixed_wing_route_is_a_single_long_leg() -> None:
    """The milk-run rewrite: two endpoints, no meander."""
    routes = plan_airways(_spread(6), REGIONS["Caucasus"], (3, 3), random.Random(3))
    assert routes
    for route in routes:
        assert len(route.chain) == 2, "an airway is one leg, not a chain"
        a, b = route.chain
        dx, dy = a.point.x - b.point.x, a.point.y - b.point.y
        assert (dx * dx + dy * dy) >= MIN_TRANSIT_M * MIN_TRANSIT_M


def test_airways_are_flown_in_both_directions() -> None:
    """Traffic all pointing the same way reads as a conveyor belt, not an airway."""
    routes = plan_airways(_spread(6), REGIONS["Caucasus"], (3, 3), random.Random(11))
    headings = {route.chain[0].point.x < route.chain[1].point.x for route in routes}
    assert headings == {True, False}


def test_fixed_wing_traffic_cruises_high() -> None:
    routes = plan_airways(_spread(6), REGIONS["Caucasus"], (3, 3), random.Random(5))
    assert routes
    # Every fixed-wing type in a region fleet must cruise at a real flight level --
    # the old flat 5,000 m read as something military and interesting.
    assert all(r.altitude_m >= AIR_START_MIN_ALT_M for r in routes)


def test_most_airway_traffic_air_starts_so_the_sky_is_populated_at_once() -> None:
    routes = plan_airways(_spread(8), REGIONS["Caucasus"], (3, 3), random.Random(9))
    air = [r for r in routes if r.air_start]
    assert air, "airway traffic should mostly air-start at cruise"
    for route in air:
        assert route.air_start_point is not None
        assert route.start_time_s == 0
    # ...but not all of it, so departures are visible too.
    assert any(not r.air_start for r in routes)


def test_ground_started_traffic_is_staggered_across_the_window() -> None:
    routes = plan_airways(_spread(8), REGIONS["Caucasus"], (3, 3), random.Random(5))
    times = {r.start_time_s for r in routes if not r.air_start}
    assert all(0 <= t <= 6_600 for t in times)


def test_a_cramped_map_still_gets_traffic() -> None:
    """No pair clears the transit minimum -- fall back to the longest legs available
    rather than silently generating nothing."""
    cramped = _spread(4, spacing=20_000)
    routes = plan_airways(cramped, REGIONS["Caucasus"], (2, 2), random.Random(2))
    assert routes


def test_too_few_fields_yields_nothing() -> None:
    assert (
        plan_airways([_field("A", 0, 0)], REGIONS["Caucasus"], (1, 3), random.Random(0))
        == []
    )


# --- rotary stays local -------------------------------------------------------


def test_helicopters_do_not_fly_airways() -> None:
    """Deliberate asymmetry: local hops ARE what civil rotary traffic is."""
    pool = _spread(5, spacing=40_000)
    routes = plan_local_rotary(pool, REGIONS["Caucasus"], (1, 2), random.Random(1))
    assert routes
    cap2 = HELO_MAXDIST_M * HELO_MAXDIST_M
    for route in routes:
        assert route.is_helo is True
        assert route.air_start is False  # a helo popping in at altitude is absurd
        assert route.radio_alt is True  # low, on AGL, clear of terrain
        assert len(route.chain) >= 2
        for a, b in zip(route.chain, route.chain[1:]):
            dx, dy = a.point.x - b.point.x, a.point.y - b.point.y
            assert dx * dx + dy * dy <= cap2


# --- civil identity is a data table -------------------------------------------


def test_every_route_carries_an_operator_callsign() -> None:
    """`AEROFLOT 412` reads as an airliner where `CIV_An-26B_3` reads as a bug."""
    routes = plan_airways(_spread(6), REGIONS["Caucasus"], (2, 2), random.Random(4))
    assert routes
    for route in routes:
        operator, _, number = route.callsign.rpartition(" ")
        assert operator in REGIONS["Caucasus"].operators
        assert number.isdigit()


def test_western_theatres_do_not_fly_soviet_freighters() -> None:
    """The reported defect: the roster was applied globally."""
    for name in ("Nevada", "MarianaIslands", "Falklands"):
        fleet = REGIONS[name].fleet
        assert An_26B not in fleet, name
        assert IL_76MD not in fleet, name
        assert Yak_40 not in fleet, name
        assert Mi_8MT not in REGIONS[name].helos, name


def test_soviet_sphere_theatres_keep_the_antonovs() -> None:
    """The set was never wrong -- it was wrong *everywhere else*."""
    for name in ("Caucasus", "Kola"):
        assert An_26B in REGIONS[name].fleet, name
        assert IL_76MD in REGIONS[name].fleet, name


def test_western_theatres_fly_western_kit() -> None:
    assert C_130 in REGIONS["Nevada"].fleet
    assert UH_1H in REGIONS["Nevada"].helos


def test_wwii_theatres_field_no_civil_traffic_at_all() -> None:
    """A Yak-40 crossing the 1944 beachhead is an anachronism, not flavour."""
    for name in ("Normandy", "TheChannel"):
        assert REGIONS[name] is CIVIL_TRAFFIC_NONE, name
        assert REGIONS[name].fleet == ()
        assert REGIONS[name].helos == ()


def test_a_theatre_with_no_fleet_plans_nothing() -> None:
    assert plan_airways(_spread(6), CIVIL_TRAFFIC_NONE, (1, 3), random.Random(0)) == []
    assert (
        plan_local_rotary(
            _spread(4, 40_000), CIVIL_TRAFFIC_NONE, (1, 2), random.Random(0)
        )
        == []
    )


def test_an_unknown_map_falls_back_rather_than_generating_nothing() -> None:
    region = region_for("SomeFutureTerrain")
    assert region.fleet, "an unmapped terrain must still get traffic"


def test_every_region_key_is_a_real_terrain_name() -> None:
    """A typo'd key fails SILENTLY into the Soviet fallback -- the exact bug class the
    region table exists to fix.

    The trap is real and easy: the campaign yamls carry DISPLAY names ("Persian Gulf",
    "Sinai", "The Channel") while this table is keyed on ``Terrain.name``
    ("PersianGulf", "SinaiMap", "TheChannel"). Key it off the wrong one and Antonovs
    quietly reappear over the Gulf -- and over the 1944 Channel, which is worse.
    """
    import inspect

    import dcs.terrain as terrain_module
    from dcs.terrain.terrain import Terrain

    real = set()
    for _, obj in inspect.getmembers(terrain_module, inspect.isclass):
        if issubclass(obj, Terrain) and obj is not Terrain:
            try:
                real.add(obj().name)
            except Exception:  # pragma: no cover - a terrain that needs an install
                continue

    unknown = set(REGIONS) - real
    assert not unknown, f"not real Terrain.name values: {sorted(unknown)}"


def test_every_regional_airframe_has_a_cruise_profile() -> None:
    """A fleet entry with no profile is silently skipped at plan time -- catch it here
    instead of discovering an empty sky in-game."""
    for name, region in REGIONS.items():
        for aircraft in region.fleet + region.helos:
            assert aircraft in CRUISE_PROFILE, f"{name}: {aircraft.id} has no profile"
