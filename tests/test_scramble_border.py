"""Tests for the reactive-scramble RED airspace border emitted to Lua."""

from __future__ import annotations

from game.missiongenerator.luagenerator import LuaGenerator
from game.theater import Player


class _Pos:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class _CP:
    def __init__(self, x: float, y: float) -> None:
        self.position = _Pos(x, y)


class _Theater:
    def __init__(self, red_cps: list[_CP]) -> None:
        self._red_cps = red_cps

    def control_points_for(self, player: Player, **_kwargs: object) -> list[_CP]:
        return self._red_cps if player == Player.RED else []


class _Game:
    def __init__(self, red_cps: list[_CP]) -> None:
        self.theater = _Theater(red_cps)


def _generator(red_cps: list[_CP]) -> LuaGenerator:
    return LuaGenerator(_Game(red_cps), None, None)  # type: ignore[arg-type]


def test_border_is_a_closed_ring_buffered_forward() -> None:
    cps = [_CP(0, 0), _CP(100_000, 0), _CP(100_000, 100_000), _CP(0, 100_000)]
    border = _generator(cps)._scramble_border_points()
    assert border is not None
    # Closed polygon ring.
    assert border[0] == border[-1]
    xs = [x for x, _ in border]
    zs = [z for _, z in border]
    # The forward buffer pushes the ring outside the raw hull on every side.
    assert min(xs) < 0 and max(xs) > 100_000
    assert min(zs) < 0 and max(zs) > 100_000


def test_border_none_without_red_control_points() -> None:
    assert _generator([])._scramble_border_points() is None
