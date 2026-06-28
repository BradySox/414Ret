"""Save a hand-built blank-canvas theater as a reusable campaign, and rebuild one
from that descriptor — the ``.miz``-less save-as-campaign path (campaign-maker
Increment D).

A blank canvas is built **without** a ``.miz`` (``generate_blank_theater`` + the
§C.2 default laydown + drop-spawn §20). So rather than author a ``.miz``, we
serialize the *inputs* — terrain + ownership + the per-site **laydown intent** (a
``GroupTask`` at a position, per side) — into the campaign YAML's ``blank_canvas``
block, and rebuild by re-populating each control point's ``preset_locations`` so
the **normal** ``GameGenerator`` fills them (the exact path §C.2 and a real ``.miz``
campaign use). ``Campaign.load_theater`` branches on the ``blank_canvas`` key.

Storing the laydown *intent* (task + position), not exact units, keeps the saved
campaign **cross-faction-safe**: re-rolling with a different faction generates
faction-appropriate units, and there is no fragile unit-by-unit reconstruction of
the ~17 ``TheaterGroundObject`` subclasses. The militarily-meaningful laydown
round-trips (SAMs, EWR, armor, factory, ammo, IADS buildings, missile / coastal /
strike sites). Flavour buildings the generator does not place from presets
(FUEL / OIL) and dynamic / naval objects are intentionally **not** captured in v1.

This module loads a (heavy) DCS terrain on rebuild, so the full round-trip is
verified headlessly + in-game, not in CI; the serializer and the site→preset
routing are pure and unit-tested. See
``docs/dev/design/414th-campaign-maker-notes.md`` (Increment D).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from game.data.groups import GroupTask
from game.theater.controlpoint import Airfield, ControlPoint
from game.theater.player import Player
from game.version import CAMPAIGN_FORMAT_VERSION

from .blanktheatergen import generate_blank_theater

if TYPE_CHECKING:
    from game import Game
    from game.theater import ConflictTheater

logger = logging.getLogger(__name__)

#: Schema version of the ``blank_canvas`` descriptor body (independent of the
#: campaign-format version stamped on the YAML).
BLANK_CAMPAIGN_SCHEMA = 1

#: ``GroupTask`` → the ``PresetLocations`` list the generator reads it from. A
#: serialized site's task routes its rebuilt ``PresetLocation`` into the matching
#: list, so ``GameGenerator.generate()`` places it natively. Tasks absent here
#: (FUEL / OIL flavour buildings, naval, dynamic objects) are not round-tripped.
_TASK_TO_PRESET: dict[GroupTask, str] = {
    GroupTask.AAA: "aaa",
    GroupTask.SHORAD: "short_range_sams",
    GroupTask.MERAD: "medium_range_sams",
    GroupTask.LORAD: "long_range_sams",
    GroupTask.EARLY_WARNING_RADAR: "ewrs",
    GroupTask.BASE_DEFENSE: "armor_groups",
    GroupTask.FACTORY: "factories",
    GroupTask.AMMO: "ammunition_depots",
    GroupTask.MISSILE: "missile_sites",
    GroupTask.COASTAL: "coastal_defenses",
    GroupTask.STRIKE_TARGET: "strike_locations",
    GroupTask.COMMAND_CENTER: "iads_command_center",
    GroupTask.COMMS: "iads_connection_node",
    GroupTask.POWER: "iads_power_source",
}


def _cp_name(cp: ControlPoint) -> str:
    return cp.airport.name if isinstance(cp, Airfield) else cp.name


def _side_str(player: Player) -> str:
    return "blue" if player.is_blue else "red"


def serialize_blank_campaign(game: Game) -> dict[str, Any]:
    """Capture a built blank-canvas game's terrain ownership + laydown intent as the
    ``blank_canvas`` descriptor body (``{version, ownership, sites}``).

    Ownership is the **current** side of each non-neutral airfield. Each ground
    object whose ``GroupTask`` the generator places from a preset becomes a *site*
    (anchor CP + side + task + position); everything else (flavour buildings with no
    preset generator, naval, dynamic SOF/POW objects) is skipped.
    """
    theater = game.theater

    ownership: dict[str, str] = {}
    for cp in theater.controlpoints:
        if isinstance(cp, Airfield) and not cp.captured.is_neutral:
            ownership[cp.airport.name] = _side_str(cp.captured)

    sites: list[dict[str, Any]] = []
    for tgo in theater.ground_objects:
        task = tgo.task
        if task not in _TASK_TO_PRESET:
            continue
        cp = tgo.control_point
        if cp.captured.is_neutral:
            continue
        sites.append(
            {
                "anchor": _cp_name(cp),
                "side": _side_str(cp.captured),
                "task": task.name,
                "x": round(tgo.position.x, 1),
                "y": round(tgo.position.y, 1),
            }
        )

    return {"version": BLANK_CAMPAIGN_SCHEMA, "ownership": ownership, "sites": sites}


def blank_campaign_document(
    game: Game,
    *,
    name: str,
    authors: str = "Campaign Maker",
    description: str = "Hand-built blank-canvas campaign.",
) -> dict[str, Any]:
    """The full campaign-YAML document for a saved blank canvas: the standard
    campaign header (stamped with the current ``CAMPAIGN_FORMAT_VERSION`` so the
    New-Game list does not hide it — see the version-gate gotcha) plus the
    ``blank_canvas`` descriptor in place of a ``miz``.
    """
    major, minor = CAMPAIGN_FORMAT_VERSION
    return {
        "name": name,
        "theater": game.theater.terrain.name,
        "authors": authors,
        "description": description,
        "version": f"{major}.{minor}",
        "recommended_player_faction": game.blue.faction.name,
        "recommended_enemy_faction": game.red.faction.name,
        "recommended_player_money": int(game.blue.budget),
        "recommended_enemy_money": int(game.red.budget),
        "advanced_iads": game.theater.iads_network.advanced_iads,
        "blank_canvas": serialize_blank_campaign(game),
    }


def _apply_sites(theater: ConflictTheater, sites: list[dict[str, Any]]) -> int:
    """Re-seed each serialized site as a ``PresetLocation`` on its anchor control
    point, so ``GameGenerator.generate()`` later places it. Returns the count
    seeded. Pure given a theater — unit-tested with a fake theater."""
    from game.naming import namegen
    from game.theater.presetlocation import PresetLocation
    from dcs.mapping import Point

    cps_by_name = {
        _cp_name(cp): cp for cp in theater.controlpoints if isinstance(cp, Airfield)
    }

    placed = 0
    for site in sites:
        anchor = site.get("anchor")
        cp = cps_by_name.get(anchor) if isinstance(anchor, str) else None
        if cp is None:
            continue
        task = _task_by_name(site.get("task"))
        field = _TASK_TO_PRESET.get(task) if task is not None else None
        if field is None:
            continue
        point = Point(float(site["x"]), float(site["y"]), theater.terrain)
        getattr(cp.preset_locations, field).append(
            PresetLocation(namegen.random_objective_name(), point)
        )
        placed += 1
    return placed


def _task_by_name(name: Optional[str]) -> Optional[GroupTask]:
    if name is None:
        return None
    try:
        return GroupTask[name]
    except KeyError:
        logger.warning("Blank campaign: unknown GroupTask %r in descriptor.", name)
        return None


def build_blank_theater_from_descriptor(
    terrain_name: str, descriptor: dict[str, Any], advanced_iads: bool
) -> ConflictTheater:
    """Rebuild a blank-canvas theater from a ``blank_canvas`` descriptor: ownership
    → ``generate_blank_theater`` (control points + derived fronts), then re-seed each
    site's ``PresetLocation`` so the normal generator fills the laydown. Returns the
    theater pre-generation, exactly like ``Campaign.load_theater``'s ``.miz`` path.
    """
    ownership = {
        airfield: (Player.BLUE if side == "blue" else Player.RED)
        for airfield, side in descriptor.get("ownership", {}).items()
    }
    theater = generate_blank_theater(
        terrain_name, ownership=ownership, advanced_iads=advanced_iads
    )
    placed = _apply_sites(theater, descriptor.get("sites", []))
    logger.info("Blank campaign: rebuilt %d laydown sites from descriptor.", placed)
    return theater
