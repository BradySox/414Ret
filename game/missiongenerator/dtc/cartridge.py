"""Build the F/A-18C DTC cartridge by overlaying SA data onto the template.

The template (``resources/dtc/templates/FA-18C_hornet.dtc``) is a real ME-authored
cartridge with the generated arrays emptied but every other partition (COMM, ALR67, CMDS)
left at the ME defaults, so the result is always structurally complete and loadable.

Scope (per the 414th): the cartridge carries only the Hornet SA-page **CAP/tanker
tracks** (``SA.CAP_PTS``). Threat rings draw themselves from DCS intel, and COMM/waypoints
load from the mission independently of DTC, so we deliberately do not touch those
partitions. DTC is F/A-18C only (the F-16 has no equivalent racetrack partition).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from game.missiongenerator.dtc.sadata import OrbitTrack, SaData

TEMPLATE_DIR = Path("resources/dtc/templates")

F18_TYPE = "FA-18C_hornet"

#: DCS types that get a DTC cartridge. Used to gate which player flights get one.
DTC_AIRCRAFT_TYPES = frozenset({F18_TYPE})

# Neutral, Retribution-branded cartridge name. DCS auto-loads a mission cartridge by its
# in-sim *name* (the unit's DTC.Cartridges[].name reference), resolved against BOTH the
# mission-embedded files and the player's personal Saved Games\DCS\DTC library. The old
# names copied ED's default airframe-variant convention ("FA-18C Lot 20 DTC_1"), so a
# player's personal cartridge of the same name shadowed ours and -- if it was authored on
# a different map -- silently failed to apply on a terrain mismatch. A neutral name no
# player library will contain, tagged with the terrain so it can never be shadowed by a
# stale cartridge from another map, fixes both.
_NEUTRAL_NAME_PREFIX = "Retribution"


def cartridge_display_name(terrain_name: str) -> str:
    """Neutral, terrain-tagged cartridge name, e.g. ``"Retribution Iraq DTC_1"``.

    The ``DTC_1`` suffix is the cartridge slot.
    """
    return f"{_NEUTRAL_NAME_PREFIX} {terrain_name} DTC_1"


def cartridge_archive_names(dcs_type: str) -> tuple[str, ...]:
    """The ``DTC/<stem>.dtc`` member name(s) for a cartridge of this type.

    DCS's canonical cartridge filename is the aircraft type id (e.g.
    ``FA-18C_hornet.dtc``). Auto-load identity is the JSON ``name``, not the filename.
    """
    return (dcs_type,)


def _load_template(dcs_type: str) -> dict[str, Any]:
    path = TEMPLATE_DIR / f"{dcs_type}.dtc"
    return json.loads(path.read_text(encoding="utf-8"))


def _f18_cap_pts(orbits: list[OrbitTrack]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, o in enumerate(orbits):
        out.append(
            {
                "id": f"CAP_PTS_{i + 1}",
                "num": i + 1,
                "note": "",
                "course": o.course_deg,
                "diameter": o.width_m,
                "length": o.length_m,
                "turn_direction": "Left",
                "x": o.x,
                "y": o.y,
            }
        )
    return out


def _build_f18(template: dict[str, Any], sa: SaData, terrain_name: str) -> None:
    sa_part = template["data"]["SA"]
    sa_part["CAP_PTS"] = _f18_cap_pts(sa.orbits)
    # The WYPT partition carries its own terrain field (current DCS SA-partition
    # build); a mismatch with data.terrain makes the cartridge fail to load.
    if "WYPT" in template["data"]:
        template["data"]["WYPT"]["terrain"] = terrain_name


def build_cartridge(dcs_type: str, sa: SaData, terrain_name: str) -> dict[str, Any]:
    """Return a complete F/A-18C cartridge dict with the CAP/tanker tracks overlaid."""
    cartridge = _load_template(dcs_type)

    cartridge["name"] = cartridge_display_name(terrain_name)
    cartridge["type"] = dcs_type
    cartridge["data"]["name"] = ""
    cartridge["data"]["type"] = dcs_type
    cartridge["data"]["terrain"] = terrain_name

    _build_f18(cartridge, sa, terrain_name)
    return cartridge
