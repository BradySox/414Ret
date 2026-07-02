"""Surface captured-pilot POWs as first-class recovery objectives (SCAR rescue
rework, Phase 3).

Each ``PendingPowRecovery`` on a coalition is rebuilt every turn into a
``CapturedPilotGroundObject`` positioned just outside the nearest ENEMY control
point (the "airfield" holding the POW), offset ``_MARKER_OFFSET_M`` toward the
friendly anchor so the map marker clears the airfield's own icon, and anchored
to the nearest friendly control point's ``connected_objectives`` so it renders
as a friendly recovery objective. The objects are *dynamic* (not authored in the
campaign .miz): torn down and rebuilt each turn so the set always matches the
live ``pending_pow_recoveries``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from game.dcs.groundunittype import GroundUnitType
from game.point_with_heading import PointWithHeading
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import CapturedPilotGroundObject
from game.theater.theatergroup import TheaterGroup, TheaterUnit
from game.utils import Heading

if TYPE_CHECKING:
    from game.coalition import Coalition
    from game.game import Game
    from game.pow_recovery import PendingPowRecovery
    from game.theater import ControlPoint

_OBJECTIVE_NAME = "Captured Pilot"

# DCS unit-type names (variant ids) for the per-side special-forces infantry that
# stands in for the captured pilot. (Relocated here from the retired SOF
# capture-economy module ``game/scar_rescue.py`` when that loop's dead code was
# removed 2026-07-01 -- the POW body is now these variants' only consumer; the
# unit YAML variants are kept for it.)
_POW_UNIT_BLUE = "SOF Team (BLUFOR)"
_POW_UNIT_RED = "SOF Team (OPFOR)"

# The objective is deliberately positioned near the holding airfield rather than
# exactly on it -- the map marker sat on top of the airbase's own icon, making it
# unclickable (2026-06-30 in-game report). Recovery is matched by airframe name,
# not exact position (see commit_pow_recoveries), so this offset is cosmetic-only.
_MARKER_OFFSET_M = 900


def _pow_unit(coalition: Coalition) -> Optional[GroundUnitType]:
    # A single soldier stands in for the captured pilot (a known-valid vanilla
    # unit variant per side).
    name = _POW_UNIT_BLUE if coalition.player.is_blue else _POW_UNIT_RED
    try:
        return GroundUnitType.named(name)
    except KeyError:
        return None


def _clear_pow_objectives(game: Game) -> None:
    """Remove every dynamically-created captured-pilot objective from the theater
    and the TGO registry so the set can be rebuilt fresh. Idempotent and side-wide
    (also cleans up if the feature produced none this turn)."""
    for cp in game.theater.controlpoints:
        kept = []
        for tgo in cp.connected_objectives:
            if isinstance(tgo, CapturedPilotGroundObject):
                if tgo.id in game.db.tgos.objects:
                    game.db.tgos.remove(tgo.id)
            else:
                kept.append(tgo)
        cp.connected_objectives = kept


def _holding_airfield(
    game: Game, coalition: Coalition, pow_entry: PendingPowRecovery
) -> Optional[ControlPoint]:
    """The nearest enemy control point holding the POW (its "airfield"). Reuses a
    still-enemy stored holding; otherwise picks (and records) the nearest enemy
    control point. ``None`` if the enemy holds no base."""
    point = game.point_in_world(pow_entry.x, pow_entry.y)
    if pow_entry.holding_cp_id is not None:
        try:
            stored = game.theater.find_control_point_by_id(pow_entry.holding_cp_id)
        except KeyError:
            stored = None
        if stored is not None and stored.captured is not coalition.player:
            return stored
    enemy = [
        cp for cp in game.theater.controlpoints if cp.captured is not coalition.player
    ]
    if not enemy:
        return None
    nearest = min(enemy, key=lambda cp: point.distance_to_point(cp.position))
    pow_entry.holding_cp_id = nearest.id
    return nearest


def _friendly_anchor(
    game: Game, coalition: Coalition, holding_cp: ControlPoint
) -> Optional[ControlPoint]:
    """The friendly control point the (blue) recovery objective hangs off for
    ownership/rendering: the nearest friendly control point to the holding
    airfield. ``None`` if the side holds no base."""
    friendly = [
        cp for cp in game.theater.controlpoints if cp.captured is coalition.player
    ]
    if not friendly:
        return None
    return min(
        friendly, key=lambda cp: holding_cp.position.distance_to_point(cp.position)
    )


def _build_pow_objective(
    game: Game,
    pow_entry: PendingPowRecovery,
    holding_cp: ControlPoint,
    anchor: ControlPoint,
    unit: GroundUnitType,
) -> None:
    # Offset toward the friendly anchor so the marker clears the airfield's own
    # icon on the map (still reads as "held at this airfield").
    heading = holding_cp.position.heading_between_point(anchor.position)
    point = holding_cp.position.point_from_heading(heading, _MARKER_OFFSET_M)
    location = PresetLocation(_OBJECTIVE_NAME, point)
    tgo = CapturedPilotGroundObject(
        _OBJECTIVE_NAME, location, anchor, pow_entry.airframe_unit_name
    )
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


def sync_pow_objectives(game: Game) -> None:
    """Rebuild the captured-pilot POW objectives to match every coalition's
    ``pending_pow_recoveries``. Run at turn initialization (idempotent, so
    re-running it within a turn is safe)."""
    _clear_pow_objectives(game)
    for coalition in game.coalitions:
        unit = _pow_unit(coalition)
        if unit is None:
            continue
        for pow_entry in coalition.pending_pow_recoveries:
            holding = _holding_airfield(game, coalition, pow_entry)
            if holding is None:
                continue
            anchor = _friendly_anchor(game, coalition, holding)
            if anchor is None:
                continue
            _build_pow_objective(game, pow_entry, holding, anchor, unit)
