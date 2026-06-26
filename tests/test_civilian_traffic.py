"""Civilian background-traffic route planning (Python side).

The civilian layer is planned in ``game/missiongenerator/civiliantraffic.py`` and
spawned via pydcs (no MOOSE RAT). The geometry -- neutral pool, front keep-out,
reachable-neighbour pruning, multi-leg chaining, density, and the air-start/ground-
start split -- is plain Python, so unlike the old RAT plugin it is exercised here.
"""

from __future__ import annotations

import random

from dcs.helicopters import Mi_8MT
from dcs.mapping import Point
from dcs.planes import An_26B, C_130, Yak_52

from game.missiongenerator.civiliantraffic import (
    FW_MAXDIST_M,
    HELO_MAXDIST_M,
    KEEPOUT_M,
    _Field,
    admit_field,
    build_chain,
    density,
    plan_routes,
    prune_to_reachable,
)

_T = None  # terrain only passed through; never dereferenced in planning


def _pt(x: float, y: float) -> Point:
    return Point(x, y, _T)  # type: ignore[arg-type]  # terrain never dereferenced


def _field(name: str, x: float, y: float) -> _Field:
    return _Field(name=name, point=_pt(x, y))


def _grid(n: int, spacing: float = 40_000) -> list[_Field]:
    return [_field(chr(65 + i), i * spacing, 0) for i in range(n)]


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


def test_build_chain_stays_within_cap_and_never_doubles_back() -> None:
    pool = _grid(6)  # A..F, 40 km apart
    chain = build_chain(pool[0], pool, HELO_MAXDIST_M, n_legs=4, rng=random.Random(3))
    assert 2 <= len(chain) <= 5  # start + up to n_legs
    cap2 = HELO_MAXDIST_M * HELO_MAXDIST_M
    for a, b in zip(chain, chain[1:]):
        dx, dy = a.point.x - b.point.x, a.point.y - b.point.y
        assert dx * dx + dy * dy <= cap2  # every leg within the cap
    for a, b, c in zip(chain, chain[1:], chain[2:]):
        assert a is not c  # no immediate doubling back


def test_plan_routes_empty_when_fewer_than_two_reachable() -> None:
    lone = [_field("A", 0, 0), _field("B", 9_000_000, 0)]  # not reachable to each other
    assert (
        plan_routes(lone, FW_MAXDIST_M, (C_130,), (1, 3), 5, 1, random.Random(0)) == []
    )


def test_plan_routes_air_starts_only_high_cruisers_within_quota() -> None:
    pool = _grid(6)
    rng = random.Random(7)
    routes = plan_routes(pool, FW_MAXDIST_M, (C_130, Yak_52), (3, 3), 5, 1, rng)
    c130 = [r for r in routes if r.aircraft_type is C_130]
    yak = [r for r in routes if r.aircraft_type is Yak_52]
    # Exactly one C-130 (a high cruiser) air-starts at t=0; the rest ground-start.
    assert sum(1 for r in c130 if r.air_start) == 1
    assert all(r.start_time_s == 0 for r in c130 if r.air_start)
    assert all(r.air_start_point is not None for r in c130 if r.air_start)
    # The Yak-52 is a low flyer (RADIO alt) -> never air-starts, always ground.
    assert all(not r.air_start for r in yak)


def test_plan_routes_helos_never_air_start_and_use_radio_alt() -> None:
    pool = _grid(5, spacing=30_000)
    routes = plan_routes(
        pool, HELO_MAXDIST_M, (Mi_8MT,), (1, 2), 4, 0, random.Random(1)
    )
    assert routes
    for r in routes:
        assert r.is_helo is True
        assert r.air_start is False
        assert r.radio_alt is True
        assert 0 <= r.start_time_s <= 6_600
        assert len(r.chain) >= 2


def test_plan_routes_ground_starts_are_staggered_across_the_window() -> None:
    pool = _grid(8, spacing=30_000)
    routes = plan_routes(pool, FW_MAXDIST_M, (An_26B,), (3, 3), 5, 0, random.Random(5))
    times = {r.start_time_s for r in routes}
    assert len(times) > 1  # not all at the same instant
    assert all(0 <= t <= 6_600 for t in times)
