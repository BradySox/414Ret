"""Pure policy core for the blank-canvas campaign generator.

The "campaign maker" lets a player start from an empty theater (every airfield on
the map, assignable ownership, no preset SAMs/armor/objectives) and build a
campaign by hand. This module owns the **map-agnostic decisions** that part needs:

* :func:`assign_coalitions` — give every airfield a starting side via a
  deterministic geographic split, so a fresh map isn't all one colour;
* :func:`nearest_neighbor_links` — propose a ground-connectivity graph (which
  airfields share a supply route / can form a front) when the player wants ground
  fronts rather than a pure air war.

Kept deliberately free of pydcs / Retribution imports so it is unit-testable
without loading a DCS terrain (full terrains are too heavy for CI) — same split
that worked for ``scenerycatalog``. The terrain-binding glue (loading the terrain,
creating ``Airfield`` control points, wiring ``create_convoy_route``, the new-game
wizard page) lives elsewhere and is verified in-game; see
``docs/dev/design/414th-campaign-maker-notes.md``.

Coordinate convention: ``AirfieldSite.x``/``.y`` are pydcs ``Point`` coords
(``x`` = north, ``y`` = east) — whatever ``airport.position`` yields.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass


@dataclass(frozen=True)
class AirfieldSite:
    """A candidate control point: a name + its 2-D map position."""

    name: str
    x: float
    y: float


def assign_coalitions(
    sites: list[AirfieldSite], inverted: bool = False
) -> dict[str, bool]:
    """Map each airfield name -> ``True`` (blue) / ``False`` (red).

    Splits the field along its axis of greatest spread at the median coordinate:
    the lower half goes blue, the upper half red (``inverted`` swaps). Deterministic
    and roughly balanced. Guarantees at least one airfield per side when two or more
    sites exist; with a single site it returns just that one (blue, or red if
    ``inverted``).

    Raises ``ValueError`` on an empty input.
    """
    if not sites:
        raise ValueError("assign_coalitions requires at least one airfield site.")

    if len(sites) == 1:
        return {sites[0].name: not inverted}

    xs = [s.x for s in sites]
    ys = [s.y for s in sites]
    # split on whichever axis the airfields are more spread along
    use_x = (max(xs) - min(xs)) >= (max(ys) - min(ys))
    coord = (lambda s: s.x) if use_x else (lambda s: s.y)
    median = statistics.median(coord(s) for s in sites)

    result: dict[str, bool] = {}
    for s in sites:
        blue = coord(s) <= median
        result[s.name] = (not blue) if inverted else blue

    # Degenerate guard: if every site landed on one side (e.g. many ties at the
    # median), flip the single most-extreme site so both coalitions are present.
    if len(set(result.values())) == 1:
        all_blue = next(iter(result.values()))
        # the extreme on the opposite end of the split axis becomes the other side
        extreme = (max if all_blue else min)(sites, key=coord)
        result[extreme.name] = not all_blue

    return result


def nearest_neighbor_links(
    sites: list[AirfieldSite], k: int = 3
) -> set[frozenset[str]]:
    """Propose undirected ground links: connect each airfield to its *k* nearest.

    Returned as a set of two-name :class:`frozenset` pairs (de-duplicated across
    directions). The glue layer turns each pair into a bidirectional
    ``create_convoy_route`` so fronts can form where blue meets red. ``k`` bounds
    fan-out; a pair counts once even if both endpoints select each other.
    """
    links: set[frozenset[str]] = set()
    for a in sites:
        others = [o for o in sites if o.name != a.name]
        others.sort(key=lambda o: (o.x - a.x) ** 2 + (o.y - a.y) ** 2)
        for b in others[:k]:
            links.add(frozenset((a.name, b.name)))
    return links
