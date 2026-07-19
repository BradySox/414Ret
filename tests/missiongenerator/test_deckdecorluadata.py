"""Launch-phase deck dressing emitter (``dcsRetribution.deckDecor``, §72).

Locks the config contract the ``deckdecor`` plugin consumes: one record per
carrier that received launch-phase statics -- ship group name, flagship unit
name, coalition side id, the generation-time BRC, and the static unit names to
strike below -- and no node at all when nothing launch-phase was placed.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.missiongenerator.deckdecorluadata import populate_deck_decor_lua
from game.missiongenerator.luagenerator import LuaData, LuaValue
from game.missiongenerator.missiondata import DeckDecorInfo


def _kv(item: Any) -> dict[str, Any]:
    vals = item.value
    if isinstance(vals, LuaValue):
        vals = [vals]
    return {v.key: v.value for v in vals}


def _emit(deck_decor: list[DeckDecorInfo]) -> LuaData | None:
    root = LuaData("dcsRetribution")
    md = SimpleNamespace(deck_decor=deck_decor)
    populate_deck_decor_lua(root, SimpleNamespace(), md)  # type: ignore[arg-type]
    node = root.get_item("deckDecor")
    assert node is None or isinstance(node, LuaData)
    return node


def test_emits_one_record_per_boat() -> None:
    node = _emit(
        [
            DeckDecorInfo(
                ship_group_name="CSG 1",
                carrier_unit_name="CVN-71 Theodore Roosevelt",
                blue=True,
                brc_degrees=87.35,
                clear_names=["CSG 1 deck decor 17 object"],
            ),
            DeckDecorInfo(
                ship_group_name="Red CSG",
                carrier_unit_name="Kuz",
                blue=False,
                brc_degrees=270.0,
                clear_names=[
                    "Red CSG deck decor 05 object",
                    "Red CSG deck decor 06 object",
                ],
            ),
        ]
    )
    assert node is not None
    boats = node.get_item("boats")
    assert isinstance(boats, LuaData)
    recs = [_kv(r) for r in boats.objects]
    assert recs[0] == {
        "group": "CSG 1",
        "unit": "CVN-71 Theodore Roosevelt",
        "side": "2",
        "brc": "87.3",
        "clearNames": ["CSG 1 deck decor 17 object"],
    }
    assert recs[1]["side"] == "1"
    assert recs[1]["clearNames"] == [
        "Red CSG deck decor 05 object",
        "Red CSG deck decor 06 object",
    ]


def test_no_node_when_nothing_launch_phase() -> None:
    assert _emit([]) is None
