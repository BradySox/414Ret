from typing import Any, cast

from game.theater.frontline import FrontLine


def test_equal_front_lines_have_equal_hashes() -> None:
    blue = object()
    red = object()
    first = object.__new__(FrontLine)
    second = object.__new__(FrontLine)
    first.blue_cp = cast(Any, blue)
    first.red_cp = cast(Any, red)
    second.blue_cp = cast(Any, blue)
    second.red_cp = cast(Any, red)

    assert first == second
    assert hash(first) == hash(second)
    assert len({first, second}) == 1
