"""Right-clicking an enemy supply route frags an interdiction package.

``interdiction_target_for_route_id`` is the resolution behind the
``/qt/create-package/supply-route/{route_id}`` endpoint: it parses the
``"<cp_a_id>:<cp_b_id>"`` route id back to its control points and returns the enemy end
(the contested one first) to frag the Armed Recon corridor against -- or ``None`` when
there is nothing to interdict.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

from game.server.supplyroutes.models import interdiction_target_for_route_id


def _cp(*, blue: bool, active_front: bool = False) -> Any:
    return SimpleNamespace(
        id=uuid4(),
        captured=SimpleNamespace(is_blue=blue),
        has_active_frontline=active_front,
    )


def _game(*cps: Any) -> Any:
    by_id = {cp.id: cp for cp in cps}

    def find(cp_id: Any) -> Any:
        return by_id[cp_id]  # raises KeyError when absent, like the real theater

    return cast(
        Any, SimpleNamespace(theater=SimpleNamespace(find_control_point_by_id=find))
    )


def _route(a: Any, b: Any) -> str:
    return f"{a.id}:{b.id}"


def test_contested_route_targets_the_red_end() -> None:
    blue = _cp(blue=True)
    red = _cp(blue=False, active_front=True)
    assert interdiction_target_for_route_id(_game(blue, red), _route(blue, red)) is red


def test_rear_road_prefers_the_contested_enemy_end() -> None:
    rear = _cp(blue=False, active_front=False)
    spearhead = _cp(blue=False, active_front=True)
    # red -> red road: pick the end feeding the active front (where the convoy runs).
    assert (
        interdiction_target_for_route_id(
            _game(rear, spearhead), _route(rear, spearhead)
        )
        is spearhead
    )


def test_friendly_route_yields_no_target() -> None:
    a = _cp(blue=True)
    b = _cp(blue=True)
    assert interdiction_target_for_route_id(_game(a, b), _route(a, b)) is None


def test_malformed_or_unknown_route_id_yields_no_target() -> None:
    red = _cp(blue=False)
    game = _game(red)
    assert interdiction_target_for_route_id(game, "not-a-route") is None  # no ":"
    assert interdiction_target_for_route_id(game, "not:uuids") is None  # bad UUIDs
    assert (
        interdiction_target_for_route_id(game, f"{uuid4()}:{red.id}") is None
    )  # unknown CP
