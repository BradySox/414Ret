"""Terrain elevation at the positions campaigns author ground objects on.

A ground-marked steerpoint (target areas, CAS FLOT boundaries, flyovers) is
written at 0 for client flights, and that 0 reaches the jet as sea level rather
than as ground level -- so a target on high terrain gets a steerpoint under the
map. These pin the lookup that lets the same waypoint carry a real MSL number.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from game.theater import terrainelevation
from game.theater.terrainelevation import TerrainElevations, elevation_at


@pytest.fixture(autouse=True)
def _clear_cache() -> Any:
    terrainelevation._cache.clear()
    yield
    terrainelevation._cache.clear()


def _table() -> TerrainElevations:
    return TerrainElevations(100, {(0, 0): 43.0, (50, 50): 1200.0})


def test_an_exact_cell_answers_directly() -> None:
    assert _table().elevation_at(10.0, -20.0) == 43.0


def test_a_nearby_position_takes_the_nearest_sample() -> None:
    # The campaign marker is a point; the layout spreads its units around it, so
    # the waypoint rarely lands in the sampled cell itself.
    assert _table().elevation_at(400.0, 0.0) == 43.0


def test_a_position_past_the_search_radius_is_unknown() -> None:
    # Better no answer than a mountain's height applied to a valley.
    assert _table().elevation_at(40_000.0, 40_000.0) is None


def test_an_unsampled_terrain_is_unknown_not_an_error() -> None:
    terrain = SimpleNamespace(name="NoSuchTerrain")
    position = SimpleNamespace(x=0.0, y=0.0)
    assert elevation_at(terrain, position) is None  # type: ignore[arg-type]


def test_the_persian_gulf_table_ships_and_reads() -> None:
    # The reported case's map. Regenerate with
    # scripts/derive_terrain_elevations.py --terrain PersianGulf.
    table = terrainelevation._for_terrain("PersianGulf")
    assert table is not None
    assert len(table.points) > 500
    # The Gulf floor is at sea level and the Zagros/Hajar rim is thousands of
    # metres up; a table that lost its scale would fail both.
    elevations = list(table.points.values())
    assert min(elevations) < 10
    assert max(elevations) > 1000
