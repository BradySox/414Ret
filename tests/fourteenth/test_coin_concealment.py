"""COIN concealment: un-reconned hidden insurgent TGOs render as uncertainty areas.

Locks the server-side jitter contract (deterministic, bounded, true position inside
the circle, never applied once discovered) and the spawn-side flag plumbing.
"""

from __future__ import annotations

import math
import uuid
from types import SimpleNamespace
from typing import Any, Optional

import game.fourteenth.coin as coin
from game.server.tgos.models import (
    CONCEALED_RADIUS_M,
    _CONCEALED_MAX_OFFSET,
    _CONCEALED_MIN_OFFSET,
    concealed_uncertainty,
)


class _Point:
    def __init__(self, x: float, y: float, terrain: Any = None) -> None:
        self.x = x
        self.y = y
        self._terrain = terrain


class _Tgo:
    def __init__(self, concealed: bool, known: bool) -> None:
        self.id = uuid.UUID(int=0x414)
        self.concealed = concealed
        self._known = known
        self.position = _Point(100_000.0, -50_000.0)

    def known_for(self, viewer: Optional[Any] = None) -> bool:
        return self._known


def test_unconcealed_or_known_tgos_have_no_uncertainty() -> None:
    assert concealed_uncertainty(_Tgo(concealed=False, known=False)) is None  # type: ignore[arg-type]
    # Discovered (TARPS/attack, fog off, or the fog-overview reveal): exact marker.
    assert concealed_uncertainty(_Tgo(concealed=True, known=True)) is None  # type: ignore[arg-type]


def test_concealed_tgo_gets_a_bounded_deterministic_jitter() -> None:
    tgo = _Tgo(concealed=True, known=False)
    result = concealed_uncertainty(tgo)  # type: ignore[arg-type]
    assert result is not None
    centre, radius = result
    assert radius == CONCEALED_RADIUS_M
    offset = math.hypot(centre.x - tgo.position.x, centre.y - tgo.position.y)
    # Bounded: never dead-on the target, and the true position always inside the
    # circle (max offset < radius).
    assert _CONCEALED_MIN_OFFSET * radius <= offset <= _CONCEALED_MAX_OFFSET * radius
    # Deterministic: the circle must not wander between refreshes/reloads, or the
    # player could triangulate the true position.
    again = concealed_uncertainty(tgo)  # type: ignore[arg-type]
    assert again is not None
    assert (again[0].x, again[0].y) == (centre.x, centre.y)


def test_different_tgos_jitter_differently() -> None:
    a = _Tgo(concealed=True, known=False)
    b = _Tgo(concealed=True, known=False)
    b.id = uuid.UUID(int=0x415)
    ra = concealed_uncertainty(a)  # type: ignore[arg-type]
    rb = concealed_uncertainty(b)  # type: ignore[arg-type]
    assert ra is not None and rb is not None
    assert (ra[0].x, ra[0].y) != (rb[0].x, rb[0].y)


def _spawn_game() -> Any:
    """The minimum spawn_red_ground_at needs: a red force group whose generate()
    returns a bare TGO stand-in, plus theater/db stubs."""

    class _Group:
        def generate(
            self, name: str, location: Any, cp: Any, game: Any, task: Any
        ) -> Any:
            return SimpleNamespace(id=uuid.uuid4(), sidc_entity_override=None)

    return SimpleNamespace(
        red=SimpleNamespace(
            armed_forces=SimpleNamespace(random_group_for_task=lambda task: _Group())
        ),
        theater=SimpleNamespace(heading_to_conflict_from=lambda point: None),
        db=SimpleNamespace(tgos=SimpleNamespace(add=lambda tgo_id, tgo: None)),
    )


def test_spawn_sets_the_concealed_flag() -> None:
    game = _spawn_game()
    cp = SimpleNamespace(connected_objectives=[])
    point = _Point(0.0, 0.0)
    exact = coin.spawn_red_ground_at(
        game, cp, point, task=None, events=None  # type: ignore[arg-type]
    )
    assert exact.concealed is False
    hidden = coin.spawn_red_ground_at(
        game, cp, point, task=None, events=None, concealed=True  # type: ignore[arg-type]
    )
    assert hidden.concealed is True
