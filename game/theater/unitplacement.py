from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from dcs import Point
from dcs.mapping import LatLng
from dcs.unittype import UnitType as DcsUnitType

from game.data.groups import GroupTask
from game.layout.layout import TgoLayout, TgoLayoutUnitGroup
from game.naming import namegen
from game.theater.presetlocation import PresetLocation
from game.utils import Heading

if TYPE_CHECKING:
    from game.armedforces.forcegroup import ForceGroup
    from game.coalition import Coalition
    from game.game import Game
    from game.theater.controlpoint import ControlPoint
    from game.theater.theatergroundobject import TheaterGroundObject

logger = logging.getLogger(__name__)

# Non-cheat max distance from a friendly CP for a user-placed TGO (200 km).
_MAX_PLACEMENT_RANGE_M = 200_000


@dataclass
class PlacementSelection:
    """One unit-group row from the placement dialog."""

    unit_group: TgoLayoutUnitGroup
    dcs_group_name: str  # e.g. "SA-10 Site (Control)"
    unit_type: type[DcsUnitType]
    count: int


@dataclass
class PendingUnitPlacement:
    """A TGO queued for next-turn materialisation ("Deploy Next Turn")."""

    id: UUID = field(default_factory=uuid4)
    lat: float = 0.0
    lng: float = 0.0
    coalition_player_is_blue: bool = True
    force_group: Optional[ForceGroup] = None
    layout: Optional[TgoLayout] = None
    selections: list[PlacementSelection] = field(default_factory=list)
    free: bool = False
    respawn: bool = False
    #: Budget charged at queue time (0.0 for a free/cheat placement). Refunded if
    #: the placement is later discarded (CP lost, terrain changed) so the player
    #: isn't billed for a TGO that never appeared.
    cost: float = 0.0


def _nearest_coalition_cp(
    game: Game, coalition: Coalition, point: Point, allow_naval: bool = False
) -> Optional[ControlPoint]:
    """Return the nearest CP owned by *coalition*, or None if there are none."""
    best: Optional[ControlPoint] = None
    best_dist = float("inf")
    for cp in game.theater.control_points_for(coalition.player):
        if cp.is_fleet and not allow_naval:
            continue
        d = point.distance_to_point(cp.position)
        if d < best_dist:
            best = cp
            best_dist = d
    return best


def _is_sea_layout(layout: TgoLayout) -> bool:
    naval_tasks = {
        GroupTask.NAVY,
        GroupTask.AIRCRAFT_CARRIER,
        GroupTask.HELICOPTER_CARRIER,
    }
    return bool(naval_tasks.intersection(layout.tasks))


def place_unit_group(
    game: Game,
    coalition: Coalition,
    lat: float,
    lng: float,
    force_group: ForceGroup,
    layout: TgoLayout,
    selections: list[PlacementSelection],
    free: bool = False,
    deploy_next_turn: bool = False,
    respawn: bool = False,
    cost: float = 0.0,
) -> TheaterGroundObject | PendingUnitPlacement:
    """Create a user-placed TGO at (lat, lng) belonging to *coalition*.

    If *deploy_next_turn* is True, queues a :class:`PendingUnitPlacement` on
    ``game.pending_unit_placements`` and returns it immediately without touching
    the theater. The placement is materialised at the start of the coalition's
    next turn by :func:`process_pending_placements`.

    Raises ``ValueError`` if:
    - The position is on the wrong terrain (land vs sea).
    - No friendly CP exists within the range limit (non-free/non-cheat mode).
    """
    point = Point.from_latlng(LatLng(lat, lng), game.theater.terrain)
    sea_layout = _is_sea_layout(layout)

    # Terrain validation
    if sea_layout and not game.theater.is_in_sea(point):
        raise ValueError("Naval units must be placed in sea territory.")
    if not sea_layout and not game.theater.is_on_land(point):
        raise ValueError("Land units must be placed on land territory.")

    # Find nearest friendly CP
    cp = _nearest_coalition_cp(game, coalition, point, allow_naval=sea_layout)
    if cp is None:
        raise ValueError(
            f"{coalition.player} has no control points to attach the unit to."
        )

    # Range enforcement in non-cheat mode
    if not free and not game.settings.enable_free_unit_placement:
        dist = point.distance_to_point(cp.position)
        if dist > _MAX_PLACEMENT_RANGE_M:
            dist_km = dist / 1000
            raise ValueError(
                f"Position is {dist_km:.0f} km from nearest friendly base"
                f" (max {_MAX_PLACEMENT_RANGE_M // 1000} km)."
                " Enable Free Placement to bypass."
            )

    if deploy_next_turn:
        pending = PendingUnitPlacement(
            lat=lat,
            lng=lng,
            coalition_player_is_blue=coalition.player.is_blue,
            force_group=force_group,
            layout=layout,
            selections=selections,
            free=free,
            respawn=respawn,
            cost=cost,
        )
        game.pending_unit_placements.append(pending)
        return pending

    return _materialise(
        game, coalition, point, cp, force_group, layout, selections, free, respawn
    )


def _materialise(
    game: Game,
    coalition: Coalition,
    point: Point,
    cp: ControlPoint,
    force_group: ForceGroup,
    layout: TgoLayout,
    selections: list[PlacementSelection],
    free: bool,
    respawn: bool,
) -> TheaterGroundObject:
    heading = game.theater.heading_to_conflict_from(point) or Heading.from_degrees(0)
    location = PresetLocation(namegen.random_objective_name(), point, heading)
    task: Optional[GroupTask] = force_group.tasks[0] if force_group.tasks else None
    tgo = layout.create_ground_object(location.original_name, location, cp, task)
    tgo.user_placed = True
    tgo.respawn_enabled = respawn
    tgo.heading = heading

    for sel in selections:
        force_group.create_theater_group_for_tgo(
            tgo,
            sel.unit_group,
            sel.dcs_group_name,
            game,
            sel.unit_type,
            sel.count,
        )

    cp.connected_objectives.append(tgo)
    game.db.tgos.add(tgo.id, tgo)
    logger.info(
        "Drop-spawn: placed %s '%s' for %s at (%s)",
        type(tgo).__name__,
        tgo.name,
        coalition.player,
        point,
    )
    return tgo


def process_pending_placements(game: Game, coalition: Coalition) -> None:
    """Materialise all pending placements queued for *coalition* this turn.

    Called at the start of the coalition's turn (same timing as procurement).
    Placements that can no longer be satisfied (CP lost, no valid terrain) are
    discarded with a warning.
    """

    def _refund(pending: PendingUnitPlacement) -> None:
        # The cost was charged at queue time; a placement that can't be
        # satisfied never delivered a TGO, so give the money back.
        if pending.cost and not pending.free:
            coalition.budget += pending.cost

    remaining: list[PendingUnitPlacement] = []
    for pending in game.pending_unit_placements:
        if pending.coalition_player_is_blue != coalition.player.is_blue:
            remaining.append(pending)
            continue

        if pending.force_group is None or pending.layout is None:
            logger.warning("Pending placement has no force_group/layout — discarded.")
            _refund(pending)
            continue

        point = Point.from_latlng(
            LatLng(pending.lat, pending.lng), game.theater.terrain
        )
        sea = _is_sea_layout(pending.layout)
        cp = _nearest_coalition_cp(game, coalition, point, allow_naval=sea)
        if cp is None:
            logger.warning(
                "Pending placement: no CP available for %s — discarded.",
                coalition.player,
            )
            _refund(pending)
            continue

        # Terrain check again in case conditions changed since queueing.
        if sea and not game.theater.is_in_sea(point):
            logger.warning("Pending placement terrain mismatch (sea) — discarded.")
            _refund(pending)
            continue
        if not sea and not game.theater.is_on_land(point):
            logger.warning("Pending placement terrain mismatch (land) — discarded.")
            _refund(pending)
            continue

        try:
            _materialise(
                game,
                coalition,
                point,
                cp,
                pending.force_group,
                pending.layout,
                pending.selections,
                pending.free,
                pending.respawn,
            )
        except Exception as exc:
            logger.warning(
                "Pending placement materialisation failed: %s — discarded.", exc
            )
            _refund(pending)

    game.pending_unit_placements = remaining


def process_respawns(game: Game, coalition: Coalition) -> None:
    """Auto-recreate destroyed user-placed TGOs flagged for respawn.

    Called after combat resolution for the coalition whose turn it is.
    """
    for cp in game.theater.control_points_for(coalition.player):
        for tgo in cp.connected_objectives:
            if not (tgo.user_placed and tgo.respawn_enabled):
                continue
            if not tgo.is_dead():
                continue
            for group in tgo.groups:
                for unit in group.units:
                    unit.alive = True
            logger.info(
                "Drop-spawn respawn: revived '%s' for %s.", tgo.name, coalition.player
            )
