"""Terrain-binding glue for the blank-canvas campaign maker.

Turns the map-agnostic policy decisions in :mod:`game.campaignloader.blanktheater`
into a real :class:`ConflictTheater`. Supports the **neutral-paint** flow the
campaign maker uses:

1. **Setup** — ``generate_blank_theater(terrain, all_neutral=True)`` builds a
   theater of *every* airfield on the map, all neutral (gray), no fronts, no
   units. The player paints ownership on the live map.
2. **Finalize** — ``generate_blank_theater(terrain, ownership=…)`` rebuilds from
   only the painted bases (gray ones are dropped, so they can't be captured or
   rendered), assigns each its chosen coalition, and derives ground fronts from
   nearest-neighbor adjacency among the kept bases.

A legacy auto-split mode (no ``all_neutral`` / ``ownership``) remains for tests
and as a fallback: it assigns sides via the geographic split in
:func:`assign_coalitions`.

Why neutral bases must be pruned at finalize: each side's planner only sees its
own bases, but ``ObjectiveFinder`` pulls ``control_points_for(NEUTRAL)`` as
**capture/expansion targets** — so an unpainted gray base would be something the
AI tries to seize. Dropping unpainted bases entirely removes that path and keeps
them off the map.

This module loads a (heavy) DCS terrain, so it is not unit-tested in CI;
correctness past theater construction is verified headlessly and in-game. See
``docs/dev/design/414th-campaign-maker-notes.md``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from game.data.groups import GroupTask
from game.theater.controlpoint import Airfield
from game.theater.iadsnetwork.iadsnetwork import IadsNetwork
from game.theater.player import Player
from game.theater.theaterloader import TheaterLoader

from .blanktheater import AirfieldSite, assign_coalitions, nearest_neighbor_links

if TYPE_CHECKING:
    from dcs.mapping import Point

    from game import Game
    from game.theater import ConflictTheater

logger = logging.getLogger(__name__)

# Support buildings synthesized at each owned base on finalize. A blank canvas is
# pure airfields (income_per_turn == 0) with no .miz-provided structures, so a
# finalized campaign would otherwise generate +0 budget. A factory gives income;
# the ammo/fuel dumps add a little income plus a visible, strikeable ground layer
# so the theater isn't barren. (Increment C — minimal pass; see the design notes.)
_BLANK_CANVAS_BUILDINGS = (
    GroupTask.FACTORY,
    GroupTask.AMMO,
    GroupTask.FUEL,
)


def ownership_from_theater(theater: ConflictTheater) -> dict[str, Player]:
    """Read painted (non-neutral) airfield ownership off a setup theater.

    Maps ``airport.name -> Player`` for every non-neutral ``Airfield``. The
    server builds the finalize ``ownership`` argument from this after the player
    paints on the live map.
    """
    owners: dict[str, Player] = {}
    for cp in theater.controlpoints:
        if not isinstance(cp, Airfield):
            continue
        if cp.starting_coalition.is_neutral:
            continue
        owners[cp.airport.name] = cp.starting_coalition
    return owners


def finalize_blank_canvas(setup_game: Game) -> Game:
    """Turn a painted all-neutral setup game into the real campaign.

    Reads the ownership the player painted onto *setup_game* (via
    :func:`ownership_from_theater`), rebuilds the theater keeping only the painted
    bases with their sides + derived fronts, and regenerates a fresh game using the
    setup game's own factions / settings / budgets / date — no separate param
    stash needed. The returned game is **pre-``begin_turn_0``**: the caller staffs
    airwings (the air-wing dialog) and then calls ``begin_turn_0`` + loads it, the
    same tail the new-game wizard runs.

    Raises ``RuntimeError`` if no base was painted.
    """
    from datetime import datetime, time

    from game.campaignloader.campaigncarrierconfig import CampaignCarrierConfig
    from game.campaignloader.campaigngroundconfig import TgoConfig
    from game.theater.start_generator import (
        GameGenerator,
        GeneratorSettings,
        ModSettings,
    )

    from .campaignairwingconfig import CampaignAirWingConfig

    ownership = ownership_from_theater(setup_game.theater)
    if not ownership:
        raise RuntimeError(
            "Cannot finalize a blank canvas with no painted bases — "
            "paint at least one blue and one red base first."
        )

    terrain_name = setup_game.theater.terrain.name
    advanced_iads = setup_game.theater.iads_network.advanced_iads
    theater = generate_blank_theater(
        terrain_name, ownership=ownership, advanced_iads=advanced_iads
    )

    generator_settings = GeneratorSettings(
        start_date=datetime(
            setup_game.date.year, setup_game.date.month, setup_game.date.day
        ),
        start_time=time(12, 0),
        player_budget=int(setup_game.blue.budget),
        enemy_budget=int(setup_game.red.budget),
        inverted=False,
        advanced_iads=advanced_iads,
        no_carrier=False,
        no_lha=False,
        no_player_navy=False,
        no_enemy_navy=False,
        tgo_config=TgoConfig({}),
        carrier_config=CampaignCarrierConfig({}),
        squadrons_start_full=True,
    )

    game = GameGenerator(
        setup_game.blue.faction,
        setup_game.red.faction,
        theater,
        CampaignAirWingConfig.empty(),
        setup_game.settings,
        generator_settings,
        ModSettings(),
        campaign_name=f"Blank canvas — {terrain_name}",
    ).generate()

    _synthesize_support_buildings(game)
    return game


def _nearby_land_point(game: Game, origin: Point, index: int) -> Optional[Point]:
    """A land point a few km from *origin*, fanned out by *index* so successive
    buildings at the same base don't stack. Returns None if every candidate falls
    in the sea (e.g. a base hemmed in by water)."""
    for radius in (4000, 6000, 8000):
        for step in range(6):
            heading = (index * 60 + step * 40) % 360
            candidate = origin.point_from_heading(heading, radius)
            if game.theater.is_on_land(candidate):
                return candidate
    return None


def _synthesize_support_buildings(game: Game) -> None:
    """Give each owned base a small economy so a finalized blank canvas has income.

    A blank canvas is pure airfields with no preset structures, so without this a
    finalized campaign generates +0 budget and a barren ground layer. For every
    owned control point we synthesize the ``_BLANK_CANVAS_BUILDINGS`` (a factory
    plus an ammo and fuel dump) from the coalition's building force groups -- the
    same templates the drop-spawn tool and campaign generator use -- placed on land
    near the base. Neutral (unpainted, soon-pruned) bases are skipped.

    Minimal Increment-C pass: enough to be functional (income) and pretty (visible,
    strikeable structures); richer economy laydown is deferred.
    """
    import random

    from game.naming import namegen
    from game.theater.presetlocation import PresetLocation
    from game.utils import Heading

    placed = 0
    for cp in game.theater.controlpoints:
        if cp.captured.is_neutral:
            continue
        coalition = game.coalition_for(cp.captured)
        for index, task in enumerate(_BLANK_CANVAS_BUILDINGS):
            force_groups = list(coalition.armed_forces.groups_for_task(task))
            if not force_groups:
                continue
            point = _nearby_land_point(game, cp.position, index)
            if point is None:
                continue
            heading = game.theater.heading_to_conflict_from(
                point
            ) or Heading.from_degrees(0)
            location = PresetLocation(namegen.random_objective_name(), point, heading)
            tgo = random.choice(force_groups).generate(
                location.original_name, location, cp, game, task
            )
            cp.connected_objectives.append(tgo)
            placed += 1

    logger.info("Blank canvas: synthesized %d support buildings.", placed)


def generate_blank_theater(
    terrain_name: str,
    *,
    all_neutral: bool = False,
    ownership: Optional[dict[str, Player]] = None,
    inverted: bool = False,
    with_fronts: bool = True,
    advanced_iads: bool = False,
) -> ConflictTheater:
    """Build a blank-canvas theater on *terrain_name*.

    Modes (checked in order):

    * ``all_neutral=True`` — every airfield as a NEUTRAL control point, no fronts.
      The paintable setup state.
    * ``ownership`` given — only airfields present in the mapping become control
      points, each with its mapped coalition; unpainted airfields are dropped.
      Fronts are derived among the kept bases (unless ``with_fronts=False``).
    * otherwise — legacy auto-split: every airfield, sides chosen by the
      geographic split in :func:`assign_coalitions`.

    Raises ``RuntimeError`` if the terrain exposes no airfields, or if
    ``ownership`` selects none of them.
    """
    theater = TheaterLoader(terrain_name.lower()).load()

    airports = list(theater.terrain.airport_list())
    if not airports:
        raise RuntimeError(
            f"Terrain '{terrain_name}' exposes no airfields to seed a blank campaign."
        )

    # Decide each airfield's starting coalition.
    if all_neutral:
        coalition_for = {a.name: Player.NEUTRAL for a in airports}
        kept = airports
    elif ownership is not None:
        kept = [a for a in airports if a.name in ownership]
        if not kept:
            raise RuntimeError(
                "Blank-canvas finalize: ownership selected none of the terrain's airfields."
            )
        coalition_for = {a.name: ownership[a.name] for a in kept}
    else:
        sites = [AirfieldSite(a.name, a.position.x, a.position.y) for a in airports]
        owners = assign_coalitions(sites, inverted=inverted)
        coalition_for = {
            a.name: (Player.BLUE if owners[a.name] else Player.RED) for a in airports
        }
        kept = airports

    cps_by_name: dict[str, Airfield] = {}
    for airport in kept:
        cp = Airfield(airport, theater, coalition_for[airport.name])
        theater.add_controlpoint(cp)
        cps_by_name[airport.name] = cp

    # Fronts: nearest-neighbor convoy routes among the kept bases. Skipped for the
    # all-neutral setup state (nothing is owned yet) and when explicitly disabled.
    if with_fronts and not all_neutral and len(cps_by_name) > 1:
        sites = [AirfieldSite(a.name, a.position.x, a.position.y) for a in kept]
        for pair in nearest_neighbor_links(sites):
            a_name, b_name = tuple(pair)
            cp_a = cps_by_name[a_name]
            cp_b = cps_by_name[b_name]
            cp_a.create_convoy_route(cp_b, [cp_a.position, cp_b.position], [])
            cp_b.create_convoy_route(cp_a, [cp_b.position, cp_a.position], [])

    theater.iads_network = IadsNetwork(advanced_iads, [])

    blue = sum(1 for c in coalition_for.values() if c.is_blue)
    red = sum(1 for c in coalition_for.values() if c.is_red)
    logger.info(
        "Blank theater '%s': %d airfields kept (%d blue / %d red / %d neutral), fronts=%s",
        terrain_name,
        len(kept),
        blue,
        red,
        len(kept) - blue - red,
        with_fronts and not all_neutral,
    )
    return theater
