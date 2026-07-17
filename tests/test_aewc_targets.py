"""AEW&C target selection (theaterstate._aewc_targets).

With a front the land anchor stays the stock rear-safe farthest-from-threats CP;
with NO front the support orbit holds AT its target (no FLOT to march against), so
the anchor must be the friendly CP nearest the enemy — the flown Scenic Route
Merged A-50 orbited its rearmost home base 424 NM from the enemy fleet before this.
Carrier targets are unaffected either way.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.commander.theaterstate import _aewc_targets


def _cp(name: str, carrier: bool = False) -> Any:
    return SimpleNamespace(name=name, is_carrier=carrier)


def _finder(*, fronts: list[Any], cps: list[Any], farthest: Any, closest: Any) -> Any:
    return SimpleNamespace(
        friendly_control_points=lambda: iter(cps),
        front_lines=lambda: iter(fronts),
        farthest_friendly_control_point=lambda: farthest,
        closest_friendly_control_point=lambda: closest,
    )


def test_fronted_theater_keeps_the_rear_anchor() -> None:
    boat, rear, forward = _cp("CVN", carrier=True), _cp("Rear"), _cp("Forward")
    finder = _finder(
        fronts=[object()], cps=[boat, rear, forward], farthest=rear, closest=forward
    )
    assert _aewc_targets(finder) == [boat, rear]


def test_frontless_theater_anchors_on_the_forward_field() -> None:
    boat, rear, forward = _cp("CVN", carrier=True), _cp("Rear"), _cp("Forward")
    finder = _finder(
        fronts=[], cps=[boat, rear, forward], farthest=rear, closest=forward
    )
    assert _aewc_targets(finder) == [boat, forward]
