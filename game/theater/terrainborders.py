"""Shipped per-terrain border geometry (§96) — the automagic half.

A campaign should not have to author the shape of its neighbours: the borders of
a real-world map are a property of the *terrain*, identical for every campaign on
it. ``resources/borders/<terrain>.yaml`` carries them, and a campaign that says
nothing gets them for free.

**This is what makes the feature work on existing campaigns** (DM call,
2026-08-25): 52 of the 54 campaigns on real-world maps author no borders at all,
and hand-editing every one of them was never the plan.

Precedence is simple and total: **a campaign that declares
``neutral_border_defense:`` owns its borders completely** and this file is not
consulted. Mixing the two would make it impossible to tell where a zone came
from.

Each terrain entry carries geometry and an origin, nothing else. What a
country's airspace means — whose it is, and whether it lets you through — is
derived at run time from the airbases inside its border, so one file is correct
on every campaign that map carries. Only the airframe it scrambles comes from
the dated table (``nationalpostures``), which is the one fact no campaign can
supply for a country that holds nothing.

**Every country on the map is here, the map's own nation included.** It was
excluded until 2026-08-26 on the theory that a border round the battlefield is
noise; that deleted Russia from Kola and Iran from the Persian Gulf and left
the war itself as the one region with no line on it.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

#: Relative to the install root, like every other resource read.
BORDERS_DIR = Path("resources/borders")

_cache: dict[str, list[dict[str, Any]]] = {}


def _terrain_key(terrain_name: str) -> str:
    return terrain_name.strip().lower().replace(" ", "")


def load_terrain_borders(
    terrain_name: str, directory: Optional[Path] = None
) -> list[dict[str, Any]]:
    """Raw zone dicts shipped for this terrain, ready for ``from_yaml``.

    Empty for a terrain with no file (fictional maps, Nevada, the Marianas —
    anywhere there is no foreign border to draw). Never raises: a bad file costs
    the feature, never the campaign.
    """
    key = _terrain_key(terrain_name)
    if directory is None and key in _cache:
        return _cache[key]
    path = (directory or BORDERS_DIR) / f"{key}.yaml"
    zones: list[dict[str, Any]] = []
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("zones"), list):
            zones = [z for z in raw["zones"] if isinstance(z, dict)]
        elif raw is not None:
            logging.warning("Terrain borders: %s has no zones list.", path)
    except FileNotFoundError:
        pass  # A terrain with no foreign borders is normal, not an error.
    except Exception:
        logging.warning("Terrain borders: %s unreadable.", path, exc_info=True)
    if directory is None:
        _cache[key] = zones
    return zones
