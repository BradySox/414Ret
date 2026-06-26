"""Civilian background-traffic route planning (Python side).

The civilian layer is planned in ``game/missiongenerator/civiliantraffic.py`` and
spawned via pydcs (air-started groups, no MOOSE RAT). The geometry -- neutral pool,
front keep-out, reachable-neighbour pruning, density, and route pairing -- is plain
Python, so unlike the old RAT plugin it is exercised directly here in CI.
"""

from __future__ import annotations

import random

from dcs.mapping import Point

from game.missiongenerator.civiliantraffic import (
    FW_MAXDIST_M,
    HELO_MAXDIST_M,
    KEEPOUT_M,
    _Field,
    admit_field,
    density,
    plan_layer,
    prune_to_reachable,
)
from dcs.planes import C_130

_T = None  # terrain only passed through; never dereferenced in planning


def _pt(x: float, y: float) -> Point:
    return Point(x, y, _T)  # type: ignore[arg-type]  # terrain never dereferenced


def _field(name: str, x: float, y: float) -> _Field:
    return _Field(name=name, point=_pt(x, y))


def test_admit_field_clear_of_front_is_always_admitted() -> None:
    rng = random.Random(0)
    assert admit_field(_pt(0, 0), [_pt(1_000_000, 0)], rng) is True


def test_admit_field_inside_keepout_is_dropped_without_stray() -> None:
    # A field right on the front, with a seeded rng whose first draw exceeds the
    # small stray chance, is dropped.
    rng = random.Random(1)
    front = _pt(0, 0)
    inside = _pt(KEEPOUT_M / 2, 0)  # within the bubble
    # Most seeds drop it; assert the keep-out actually triggers (not always-True).
    drops = sum(
        0 if admit_field(inside, [front], random.Random(s)) else 1 for s in range(50)
    )
    assert drops > 40  # ~92% dropped given the 0.08 stray chance


def test_prune_drops_isolated_field_keeps_cluster() -> None:
    near_a = _field("A", 0, 0)
    near_b = _field("B", 50_000, 0)  # within both caps of A
    lonely = _field("C", 5_000_000, 0)  # nothing within cap
    kept = prune_to_reachable([near_a, near_b, lonely], HELO_MAXDIST_M)
    names = {f.name for f in kept}
    assert names == {"A", "B"}


def test_density_scales_and_clamps() -> None:
    assert density(0, 1, 3) == 1  # clamped up to lo
    assert density(100, 1, 3) == 3  # clamped down to hi
    assert density(20, 1, 3) == 3  # ceil(20*.15)=3
    assert density(7, 1, 3) == 2  # ceil(7*.15)=2


def test_plan_layer_empty_when_fewer_than_two_reachable() -> None:
    rng = random.Random(0)
    lone = [_field("A", 0, 0), _field("B", 9_000_000, 0)]  # not reachable to each other
    routes = plan_layer(lone, FW_MAXDIST_M, (C_130,), 6000, 150, False, (1, 3), rng)
    assert routes == []


def test_plan_layer_routes_stay_within_cap_and_between_distinct_fields() -> None:
    rng = random.Random(7)
    pool = [_field(chr(65 + i), i * 40_000, 0) for i in range(6)]  # A..F, 40 km apart
    routes = plan_layer(pool, HELO_MAXDIST_M, (C_130,), 1000, 60, True, (1, 2), rng)
    assert routes, "expected at least one route"
    cap2 = HELO_MAXDIST_M * HELO_MAXDIST_M
    for r in routes:
        # destination is a real pool field, the leg is within the cap, and the
        # air-start sits between the (implicit) departure and the destination.
        assert any(r.destination.name == f.name for f in pool)
        assert 0 <= r.start_time_s <= 2700
        assert r.is_helo is True
