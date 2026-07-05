"""Concealment: un-reconned hidden TGOs render as uncertainty areas.

Locks the server-side jitter contract (deterministic, bounded, true position inside
the circle, never applied once discovered), the COIN spawn-side flag plumbing, and
the generalized `concealed_enemy_forces` qualifier (mobile SAMs / vehicle groups /
missile sites conceal; LORAD / EWRs / buildings / user-placed stay exact).
"""

from __future__ import annotations

import math
import uuid
from types import SimpleNamespace
from typing import Any, Optional

import game.fourteenth.coin as coin
from game.data.groups import GroupTask
from game.server.tgos.models import (
    CONCEALED_RADIUS_M,
    FIELD_FORCE_RADIUS_M,
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
    def __init__(
        self,
        concealed: bool = False,
        known: bool = False,
        category: str = "armor",
        task: Optional[GroupTask] = None,
        setting_on: bool = False,
        user_placed: bool = False,
    ) -> None:
        self.id = uuid.UUID(int=0x414)
        self.concealed = concealed
        self._known = known
        self.category = category
        self.task = task
        self.user_placed = user_placed
        self.position = _Point(100_000.0, -50_000.0)
        self.control_point = SimpleNamespace(
            coalition=SimpleNamespace(
                game=SimpleNamespace(
                    settings=SimpleNamespace(concealed_enemy_forces=setting_on)
                )
            )
        )

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


def _radius_for(tgo: _Tgo) -> Optional[float]:
    result = concealed_uncertainty(tgo)  # type: ignore[arg-type]
    return None if result is None else result[1]


def test_field_forces_conceal_when_the_setting_is_on() -> None:
    # Deployed vehicle groups: the tighter field-force circle.
    assert _radius_for(_Tgo(category="armor", setting_on=True)) == FIELD_FORCE_RADIUS_M
    # Missile sites (the SCUD hunt) and the mobile SAM belt: the full circle.
    assert _radius_for(_Tgo(category="missile", setting_on=True)) == CONCEALED_RADIUS_M
    for task in (GroupTask.MERAD, GroupTask.SHORAD, GroupTask.AAA):
        assert (
            _radius_for(_Tgo(category="aa", task=task, setting_on=True))
            == CONCEALED_RADIUS_M
        )


def test_fixed_sites_and_infrastructure_stay_exact() -> None:
    # LORAD strategic sites and EWRs (they emit) keep exact markers.
    assert (
        _radius_for(_Tgo(category="aa", task=GroupTask.LORAD, setting_on=True)) is None
    )
    assert (
        _radius_for(
            _Tgo(category="ewr", task=GroupTask.EARLY_WARNING_RADAR, setting_on=True)
        )
        is None
    )
    # Buildings/ships/etc. never qualify.
    assert _radius_for(_Tgo(category="factory", setting_on=True)) is None
    assert _radius_for(_Tgo(category="ship", setting_on=True)) is None
    # The player placed it — they know where it is.
    assert (
        _radius_for(_Tgo(category="armor", setting_on=True, user_placed=True)) is None
    )


def test_setting_off_leaves_field_forces_exact_but_coin_concealed() -> None:
    assert _radius_for(_Tgo(category="armor", setting_on=False)) is None
    # The COIN intrinsic flag conceals regardless of the setting.
    assert (
        _radius_for(_Tgo(concealed=True, category="armor", setting_on=False))
        == CONCEALED_RADIUS_M
    )


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
