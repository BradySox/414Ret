"""Surface stranded-SOF CSAR rescues as first-class map objectives (SCAR 2c-3, C2).

Each ``PendingSofRescue`` on a coalition is rebuilt every turn into a "downed SOF
team" ``DownedSofGroundObject`` attached to a friendly control point's
``connected_objectives`` at the strand point, carrying the physical infantry team
the recovery helo extracts. The objects are *dynamic* (not authored in the
campaign .miz): they are torn down and rebuilt each turn so the set always matches
the live ``pending_csars``. Gated behind ``scar_command_post_intel``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from game.dcs.groundunittype import GroundUnitType
from game.missiongenerator.scarluadata import SCAR_SOF_UNIT_BLUE, SCAR_SOF_UNIT_RED
from game.point_with_heading import PointWithHeading
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import DownedSofGroundObject
from game.theater.theatergroup import TheaterGroup, TheaterUnit
from game.utils import Heading

if TYPE_CHECKING:
    from game.coalition import Coalition
    from game.game import Game
    from game.scar_rescue import PendingSofRescue
    from game.theater import ControlPoint

_OBJECTIVE_NAME = "Downed SOF Team"


def _sof_unit_for(coalition: Coalition) -> Optional[GroundUnitType]:
    name = SCAR_SOF_UNIT_BLUE if coalition.player.is_blue else SCAR_SOF_UNIT_RED
    try:
        return GroundUnitType.named(name)
    except KeyError:
        return None


def _clear_downed_sof_objectives(game: Game) -> None:
    """Remove every dynamically-created downed-SOF objective from the theater and
    the TGO registry, so the set can be rebuilt fresh. Idempotent and side-wide
    (also cleans up if the feature was just turned off)."""
    for cp in game.theater.controlpoints:
        kept = []
        for tgo in cp.connected_objectives:
            if isinstance(tgo, DownedSofGroundObject):
                if tgo.id in game.db.tgos.objects:
                    game.db.tgos.remove(tgo.id)
            else:
                kept.append(tgo)
        cp.connected_objectives = kept


def _anchor_for(
    game: Game, coalition: Coalition, rescue: PendingSofRescue
) -> Optional[ControlPoint]:
    """The friendly control point the objective hangs off. Reuses a still-friendly
    stored anchor; otherwise picks (and records) the nearest friendly control
    point. ``None`` if the side holds no base (nothing to anchor to)."""
    point = game.point_in_world(rescue.x, rescue.y)
    if rescue.anchor_cp_id is not None:
        try:
            stored = game.theater.find_control_point_by_id(rescue.anchor_cp_id)
        except KeyError:
            stored = None
        if stored is not None and stored.captured is coalition.player:
            return stored
    friendly = [
        cp for cp in game.theater.controlpoints if cp.captured is coalition.player
    ]
    if not friendly:
        return None
    nearest = min(friendly, key=lambda cp: point.distance_to_point(cp.position))
    rescue.anchor_cp_id = nearest.id
    return nearest


def _build_objective(
    game: Game,
    rescue: PendingSofRescue,
    anchor: ControlPoint,
    unit: GroundUnitType,
) -> None:
    point = game.point_in_world(rescue.x, rescue.y)
    location = PresetLocation(_OBJECTIVE_NAME, point)
    tgo = DownedSofGroundObject(_OBJECTIVE_NAME, location, anchor)
    position = PointWithHeading.from_point(point, Heading.from_degrees(0))
    group = TheaterGroup(game.next_group_id(), _OBJECTIVE_NAME, position, [], tgo)
    group.units.append(
        TheaterUnit(
            game.next_unit_id(),
            _OBJECTIVE_NAME,
            unit.dcs_unit_type,
            position,
            tgo,
        )
    )
    tgo.groups.append(group)
    anchor.connected_objectives.append(tgo)
    game.db.tgos.add(tgo.id, tgo)


def sync_downed_sof_objectives(game: Game) -> None:
    """Rebuild the downed-SOF objectives to match every coalition's
    ``pending_csars``. Run at turn initialization (idempotent, so re-running it
    within a turn -- e.g. after a cheat capture -- is safe)."""
    _clear_downed_sof_objectives(game)
    if not game.settings.scar_command_post_intel:
        return
    for coalition in game.coalitions:
        unit = _sof_unit_for(coalition)
        if unit is None:
            continue
        for rescue in coalition.pending_csars:
            anchor = _anchor_for(game, coalition, rescue)
            if anchor is None:
                continue
            _build_objective(game, rescue, anchor, unit)
