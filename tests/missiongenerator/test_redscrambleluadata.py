"""Host red-scramble emitter (dcsRetribution.redScramble) -- §61.

Locks the emit contract the ``redscramble`` plugin depends on: gated by
``host_red_scramble``; no templates or no red airfield emits no node (plugin
no-ops); only red-held Airfield control points are listed, nearest active front
first (the Lua side keeps the first nine, so ordering decides what a big theater
keeps); templates pass through in the order the generator built them (best
interceptor first -- the EMERGENCY command launches templates[1]).
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any, Optional

from game.missiongenerator.luagenerator import LuaData
from game.missiongenerator.redscrambleluadata import (
    RedScrambleTemplate,
    populate_red_scramble_lua,
)
from game.theater import Airfield
from game.theater.player import Player


def _pos(x: float, y: float) -> Any:
    return SimpleNamespace(
        x=x,
        y=y,
        distance_to_point=lambda p, _x=x, _y=y: math.hypot(_x - p.x, _y - p.y),
    )


def _airfield(name: str, x: float, y: float, player: Player = Player.RED) -> Any:
    """A real Airfield (isinstance-true) without the heavyweight __init__.

    ``captured`` is a property over ``self.coalition.player``, and ``coalition``
    itself a property over ``_coalition`` -- so the fake seeds ``_coalition``.
    """
    airfield = Airfield.__new__(Airfield)
    airfield.name = name
    airfield.position = _pos(x, y)
    airfield._coalition = SimpleNamespace(player=player)  # type: ignore[assignment]
    return airfield


def _game(
    controlpoints: list[Any],
    fronts: list[Any] | None = None,
    *,
    on: bool = True,
) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(host_red_scramble=on),
        theater=SimpleNamespace(
            controlpoints=controlpoints,
            conflicts=lambda: [SimpleNamespace(position=p) for p in fronts or []],
        ),
    )


def _mission_data(templates: list[RedScrambleTemplate]) -> Any:
    return SimpleNamespace(red_scramble_templates=templates)


_TEMPLATES = [
    RedScrambleTemplate(group_name="RedScramble|MiG-29S", label="MiG-29S"),
    RedScrambleTemplate(group_name="RedScramble|Su-27", label="Su-27"),
]


def _emit(game: Any, mission_data: Any) -> Optional[Any]:
    root = LuaData("dcsRetribution")
    populate_red_scramble_lua(root, game, mission_data)
    return root.get_item("redScramble")


def _records(node: Any, item: str) -> list[dict[str, Any]]:
    child = node.get_item(item)
    assert child is not None
    return [{v.key: v.value for v in record.value} for record in child.objects]


def test_emits_templates_in_order_and_bases_front_first() -> None:
    front = _pos(0, 0)
    near = _airfield("Haina", 10_000, 0)
    far = _airfield("Wittstock", 200_000, 0)
    blue = _airfield("Fulda", 5_000, 0, player=Player.BLUE)
    not_airfield = SimpleNamespace(
        name="FARP", position=_pos(1, 1), coalition=SimpleNamespace(player=Player.RED)
    )

    node = _emit(
        _game([far, blue, near, not_airfield], fronts=[front]),
        _mission_data(_TEMPLATES),
    )
    assert node is not None
    assert _records(node, "templates") == [
        {"group": "RedScramble|MiG-29S", "label": "MiG-29S"},
        {"group": "RedScramble|Su-27", "label": "Su-27"},
    ]
    assert [r["name"] for r in _records(node, "bases")] == ["Haina", "Wittstock"]


def test_frontless_theater_lists_red_airfields_alphabetically() -> None:
    a = _airfield("Erfurt", 50_000, 0)
    b = _airfield("Dresden", 10_000, 0)
    node = _emit(_game([a, b]), _mission_data(_TEMPLATES))
    assert node is not None
    assert [r["name"] for r in _records(node, "bases")] == ["Dresden", "Erfurt"]


def test_neutral_airfields_are_never_listed() -> None:
    neutral = _airfield("Templin", 10_000, 0, player=Player.NEUTRAL)
    red = _airfield("Haina", 20_000, 0)
    node = _emit(_game([neutral, red]), _mission_data(_TEMPLATES))
    assert node is not None
    assert [r["name"] for r in _records(node, "bases")] == ["Haina"]


def test_gated_off_by_the_setting() -> None:
    red = _airfield("Haina", 10_000, 0)
    assert _emit(_game([red], on=False), _mission_data(_TEMPLATES)) is None


def test_no_templates_emits_no_node() -> None:
    red = _airfield("Haina", 10_000, 0)
    assert _emit(_game([red]), _mission_data([])) is None
    assert _emit(_game([red]), None) is None


def test_no_red_airfield_emits_no_node() -> None:
    blue = _airfield("Fulda", 10_000, 0, player=Player.BLUE)
    assert _emit(_game([blue]), _mission_data(_TEMPLATES)) is None
