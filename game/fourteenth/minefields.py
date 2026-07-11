"""Air-droppable minefields — cross-turn persistence (§57 Phase 2).

Phase 1 makes a dropped CBU-99 lay a scripted proximity minefield that works the *same*
mission. This module carries a field that was left undisturbed across the turn boundary.

At mission end the ``minefields`` runtime plugin writes back the current state of every field
it managed — persisted fields (by their Python ``id``) and newly-laid fields (``id`` 0), each
with its remaining ``charges`` — through the ``minefields_state`` named-global channel.
:func:`reconcile_minefields` then:

* updates a known persisted field's charges (removing it once exhausted),
* creates a record for each newly-laid field that still has charges, and
* leaves a persisted field the plugin did *not* report unchanged (a field nobody drove over
  does not decay — "left undisturbed → re-laid next turn").

The emitter (:mod:`game.missiongenerator.minefieldluadata`) re-emits the survivors into the
next mission for the plugin to re-arm. Coordinates round-trip as ``x`` = north (``Point.x``) /
``z`` = east (``Point.y``) — the DCS ``getPoint`` frame the plugin works in.

Blue-only v1. Gated by the ``air_droppable_minefields`` setting (persistence + emit); the
runtime plugin is separately gated by its Plugin Options toggle, so the same-turn tactical
mining of Phase 1 still works with just the plugin on and this setting off.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from dcs.mapping import Point

if TYPE_CHECKING:
    from game import Game
    from game.debriefing import Debriefing


@dataclass
class Minefield:
    """One persisted air-dropped minefield (a scripted area, not any DCS unit)."""

    id: int
    position: Point
    radius_m: float
    charges: int
    laid_turn: int = 0


def active_minefields(game: "Game") -> list[Minefield]:
    """The live fields (charges remaining) — what the emitter re-arms and the map shows."""
    return [m for m in getattr(game, "minefields", []) or [] if m.charges > 0]


def reconcile_minefields(game: "Game", debriefing: "Debriefing") -> None:
    """Fold the plugin's end-of-mission field report into ``game.minefields``.

    A no-op when the feature is off or the plugin reported nothing (so a persisted field is
    never silently dropped just because the plugin did not run).
    """
    if not getattr(game.settings, "air_droppable_minefields", False):
        return
    reports = getattr(debriefing.state_data, "minefields_state", None)
    if not reports:
        return

    fields = list(getattr(game, "minefields", []) or [])
    by_id = {m.id: m for m in fields}
    next_id = (max(by_id) + 1) if by_id else 1
    terrain = game.theater.terrain

    for rid, x, z, radius, charges in reports:
        charges = int(charges)
        if rid and rid in by_id:
            # A known persisted field: the plugin's count is authoritative for this mission.
            existing = by_id[rid]
            existing.charges = charges
            if charges <= 0:
                fields.remove(existing)
                del by_id[rid]
        elif not rid and charges > 0:
            # A field laid this mission (id 0) that survived it: promote to a persisted record.
            radius = float(radius) if float(radius) > 0 else 0.0
            new = Minefield(
                id=next_id,
                position=Point(float(x), float(z), terrain),
                radius_m=radius,
                charges=charges,
                laid_turn=game.turn,
            )
            fields.append(new)
            by_id[next_id] = new
            next_id += 1
        # rid given but unknown (stale save / removed field) → ignore.

    game.minefields = fields
