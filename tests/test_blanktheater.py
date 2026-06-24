"""Unit tests for the blank-canvas policy core (game/campaignloader/blanktheater.py).

Pure-Python; no terrain/pydcs needed. Covers the two map-agnostic decisions the
blank-start glue relies on: the geographic coalition split and the nearest-neighbor
connectivity proposal.
"""

from __future__ import annotations

import pytest

from game.campaignloader.blanktheater import (
    AirfieldSite,
    assign_coalitions,
    nearest_neighbor_links,
)


def _sites(*coords: tuple[float, float]) -> list[AirfieldSite]:
    return [AirfieldSite(name=f"AF{i}", x=x, y=y) for i, (x, y) in enumerate(coords)]


def test_split_on_widest_axis_x() -> None:
    # spread is along x; west half blue, east half red
    sites = _sites((0, 0), (10, 1), (20, 0), (30, 1))
    owners = assign_coalitions(sites)
    assert owners["AF0"] is True and owners["AF1"] is True
    assert owners["AF2"] is False and owners["AF3"] is False


def test_split_on_widest_axis_y() -> None:
    # spread is along y; the split axis follows the data, not always x
    sites = _sites((0, 0), (1, 10), (0, 20), (1, 30))
    owners = assign_coalitions(sites)
    assert owners["AF0"] is True and owners["AF1"] is True
    assert owners["AF2"] is False and owners["AF3"] is False


def test_inverted_swaps_sides() -> None:
    sites = _sites((0, 0), (10, 0), (20, 0), (30, 0))
    base = assign_coalitions(sites)
    inv = assign_coalitions(sites, inverted=True)
    assert all(inv[name] is not base[name] for name in base)


def test_both_coalitions_present() -> None:
    sites = _sites((0, 0), (10, 0), (20, 0), (30, 0), (40, 0))
    owners = assign_coalitions(sites)
    assert True in owners.values()
    assert False in owners.values()


def test_degenerate_all_same_coordinate_still_splits() -> None:
    # every airfield at the same point: the guard must still hand one to red
    sites = _sites((5, 5), (5, 5), (5, 5))
    owners = assign_coalitions(sites)
    assert True in owners.values()
    assert False in owners.values()


def test_single_site() -> None:
    assert assign_coalitions(_sites((0, 0))) == {"AF0": True}
    assert assign_coalitions(_sites((0, 0)), inverted=True) == {"AF0": False}


def test_empty_raises() -> None:
    with pytest.raises(ValueError):
        assign_coalitions([])


def test_links_are_undirected_and_deduped() -> None:
    sites = _sites((0, 0), (1, 0), (100, 0))
    links = nearest_neighbor_links(sites, k=1)
    # AF0<->AF1 are mutual nearest; that pair appears once, not twice
    assert frozenset(("AF0", "AF1")) in links
    assert all(len(pair) == 2 for pair in links)
    # no self-links
    assert all("AF0" not in pair or "AF0" != next(iter(pair)) for pair in links)


def test_links_respect_k() -> None:
    sites = _sites((0, 0), (1, 0), (2, 0), (3, 0), (4, 0))
    k1 = nearest_neighbor_links(sites, k=1)
    k3 = nearest_neighbor_links(sites, k=3)
    assert len(k3) >= len(k1)
    # with k>=1 over 5 colinear sites the graph is connected (every node appears)
    named = {n for pair in k3 for n in pair}
    assert named == {s.name for s in sites}
