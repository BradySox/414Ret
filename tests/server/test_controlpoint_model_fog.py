"""ControlPointJs must apply the same recon intel-fog to CP-attached ship
groups (carrier/LHA escorts) that TgoJs applies to standalone TGOs -- they are
the only channel for carrier groups and previously shipped ground truth."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.server.controlpoints.models import ControlPointJs
from game.theater import Player


class _Latlng:
    lat = 1.0
    lng = 2.0


def _distance(m: float) -> Any:
    return SimpleNamespace(meters=m)


def _ship_tgo(*, known: bool) -> Any:
    unit = SimpleNamespace(
        display_name_for=lambda viewer=None: f"ship [{'seen' if viewer else 'truth'}]"
    )
    group = SimpleNamespace(
        max_threat_range=lambda viewer=None: _distance(100.0),
        max_detection_range=lambda viewer=None: _distance(200.0),
    )
    return SimpleNamespace(
        is_control_point=True,
        known_for=lambda viewer=None: known,
        units=[unit],
        groups=[group],
    )


def _cp(tgo: Any, blue: bool = False) -> Any:
    player = Player.BLUE if blue else Player.RED
    return SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        name="CVBG",
        captured=player,
        target_position=None,
        position=SimpleNamespace(latlng=lambda: _Latlng()),
        moveable=True,
        sidc=lambda: "10063000001202000000",
        ground_objects=[tgo],
    )


def test_unscouted_enemy_carrier_group_is_fogged() -> None:
    js = ControlPointJs.for_control_point(_cp(_ship_tgo(known=False)))
    assert js.units == []
    assert js.threat_ranges == []
    assert js.detection_ranges == []


def test_scouted_enemy_carrier_group_lists_viewer_aware_units() -> None:
    js = ControlPointJs.for_control_point(_cp(_ship_tgo(known=True)))
    assert js.units == ["ship [seen]"]  # display_name_for(Player.BLUE), not truth
    assert js.threat_ranges == [100.0]
    assert js.detection_ranges == [200.0]
