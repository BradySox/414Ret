"""§57 -- the friendly minefield overlay emit (MinefieldJs.all_in_game).

off => empty (hides the layer); on => only live (charges > 0) fields, with their radius +
charges. BLUE-only by construction (game.minefields are all friendly in v1).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from dcs.mapping import LatLng

from game.server.game.models import MinefieldJs


def _mf(lat: float, lng: float, radius: float, charges: int) -> Any:
    return SimpleNamespace(
        position=SimpleNamespace(latlng=lambda la=lat, ln=lng: LatLng(lat=la, lng=ln)),
        radius_m=radius,
        charges=charges,
    )


def _game(fields: list[Any], *, on: bool = True) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(air_droppable_minefields=on),
        minefields=list(fields),
    )


def test_off_emits_nothing() -> None:
    assert MinefieldJs.all_in_game(_game([_mf(1.0, 2.0, 200.0, 4)], on=False)) == []


def test_on_emits_only_live_fields() -> None:
    fields = [_mf(1.0, 2.0, 250.0, 4), _mf(3.0, 4.0, 200.0, 0)]  # second exhausted
    out = MinefieldJs.all_in_game(_game(fields))
    assert len(out) == 1  # the 0-charge field is filtered out
    assert out[0].radius_m == 250.0
    assert out[0].charges == 4


def test_no_fields_is_empty() -> None:
    assert MinefieldJs.all_in_game(_game([])) == []
