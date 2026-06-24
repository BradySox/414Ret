"""Terrain-binding glue for the blank-canvas campaign maker (Increment 2).

Turns the map-agnostic policy decisions in :mod:`game.campaignloader.blanktheater`
into a real :class:`ConflictTheater`: load the terrain, create an ``Airfield``
control point for every airfield on the map, assign each a starting coalition, and
(optionally) wire a ground-connectivity graph so fronts can form.

This is the no-`.miz` path — it produces the same ``ConflictTheater`` shape that
``Campaign.load_theater`` would, so the existing ``GameGenerator`` /
``begin_turn_0`` pipeline consumes it unchanged.

Unlike the policy core, this module loads a (heavy) DCS terrain, so it is not
unit-tested in CI; correctness past theater construction is an in-game pass. See
``docs/dev/design/414th-campaign-maker-notes.md`` (Increment 2 + the no-fronts
runnability gate).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from game.theater.controlpoint import Airfield
from game.theater.iadsnetwork.iadsnetwork import IadsNetwork
from game.theater.player import Player
from game.theater.theaterloader import TheaterLoader

from .blanktheater import AirfieldSite, assign_coalitions, nearest_neighbor_links

if TYPE_CHECKING:
    from game.theater import ConflictTheater

logger = logging.getLogger(__name__)


def generate_blank_theater(
    terrain_name: str,
    *,
    inverted: bool = False,
    with_fronts: bool = True,
    advanced_iads: bool = False,
) -> ConflictTheater:
    """Build an empty, playable theater of every airfield on *terrain_name*.

    Each airfield becomes an ``Airfield`` control point with a coalition from the
    geographic split in :func:`assign_coalitions`. No SAMs / armor / objectives are
    placed — the player fills those in via drop-spawn after the campaign starts.

    If *with_fronts* (default), a nearest-neighbor convoy-route graph is added so
    ground fronts can form where blue meets red; set it ``False`` for a pure air war
    (see the runnability gate in the design note before relying on that path).

    Raises ``RuntimeError`` if the terrain exposes no airfields.
    """
    theater = TheaterLoader(terrain_name.lower()).load()

    airports = list(theater.terrain.airport_list())
    if not airports:
        raise RuntimeError(
            f"Terrain '{terrain_name}' exposes no airfields to seed a blank campaign."
        )

    sites = [AirfieldSite(a.name, a.position.x, a.position.y) for a in airports]
    owners = assign_coalitions(sites, inverted=inverted)

    cps_by_name: dict[str, Airfield] = {}
    for airport in airports:
        coalition = Player.BLUE if owners[airport.name] else Player.RED
        cp = Airfield(airport, theater, coalition)
        theater.add_controlpoint(cp)
        cps_by_name[airport.name] = cp

    if with_fronts:
        for pair in nearest_neighbor_links(sites):
            a_name, b_name = tuple(pair)
            cp_a = cps_by_name[a_name]
            cp_b = cps_by_name[b_name]
            # straight-line convoy route between the two bases, both directions
            cp_a.create_convoy_route(cp_b, [cp_a.position, cp_b.position], [])
            cp_b.create_convoy_route(cp_a, [cp_b.position, cp_a.position], [])

    # Mirror the tail of Campaign.load_theater: a blank (basic) IADS network.
    theater.iads_network = IadsNetwork(advanced_iads, [])

    blue = sum(1 for is_blue in owners.values() if is_blue)
    logger.info(
        "Blank theater '%s': %d airfields (%d blue / %d red), fronts=%s",
        terrain_name,
        len(airports),
        blue,
        len(airports) - blue,
        with_fronts,
    )
    return theater
