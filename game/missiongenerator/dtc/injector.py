"""Inject cartridge JSON into the saved ``.miz`` archive.

Current DCS also stores per-unit DTC linkage in the mission table itself: player/client
units get a ``DTC`` block with a cartridge name list and ``AutoLoad`` state. So mission
injection has two parts:

* write the cartridge JSON members under ``DTC/*.dtc``
* patch the ``mission`` Lua so supported player/client units reference those cartridges
"""

from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import dcs.lua

from game.missiongenerator.dtc.cartridge import cartridge_archive_names


def inject_cartridges(miz_path: Path, cartridges: dict[str, dict[str, Any]]) -> None:
    """Append native ``DTC/*.dtc`` members for each cartridge to the ``.miz``.

    ``cartridges`` maps DCS aircraft type id -> cartridge dict.
    """
    if not cartridges:
        return

    with zipfile.ZipFile(miz_path) as miz:
        members = {
            info.filename: miz.read(info.filename)
            for info in miz.infolist()
            if not _is_generated_dtc_member(info.filename, cartridges)
        }
        mission_text = members["mission"].decode("utf-8", errors="strict")
        members["mission"] = _patch_mission_unit_dtc(mission_text, cartridges).encode(
            "utf-8"
        )

    for dcs_type, cartridge in cartridges.items():
        payload = json.dumps(cartridge, indent=2).encode("utf-8")
        for filename in cartridge_archive_names(dcs_type):
            members[f"DTC/{filename}.dtc"] = payload

    _rewrite_archive(miz_path, members)


def _rewrite_archive(miz_path: Path, members: dict[str, bytes]) -> None:
    fd, tmp_name = tempfile.mkstemp(
        dir=str(miz_path.parent), suffix=".miz", prefix=f"{miz_path.stem}_dtc_"
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as out:
            for name, payload in members.items():
                out.writestr(name, payload)
        tmp_path.replace(miz_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _patch_mission_unit_dtc(
    mission_text: str, cartridges: dict[str, dict[str, Any]]
) -> str:
    mission_dict = dcs.lua.loads(mission_text)
    mission = mission_dict["mission"]
    for coalition in mission.get("coalition", {}).values():
        for country in coalition.get("country", {}).values():
            for category in ("plane", "helicopter"):
                groups = country.get(category, {}).get("group", {})
                for group in _table_values(groups):
                    units = list(_table_values(group.get("units", {})))
                    if not units:
                        continue
                    supported_units = [
                        unit for unit in units if unit.get("type") in cartridges
                    ]
                    if not supported_units:
                        continue
                    if not any(
                        unit.get("skill") in ("Client", "Player") for unit in units
                    ):
                        continue
                    for unit in supported_units:
                        cartridge_name = cartridges[unit["type"]]["name"]
                        _assign_unit_dtc(unit, cartridge_name)
    return "mission = " + dcs.lua.dumps(mission)


def _assign_unit_dtc(unit: dict[str, Any], cartridge_name: str) -> None:
    dtc = unit.setdefault("DTC", {})
    cartridges = dtc.get("Cartridges")
    if not isinstance(cartridges, list):
        cartridges = []
        dtc["Cartridges"] = cartridges

    existing = next((c for c in cartridges if c.get("name") == cartridge_name), None)
    if existing is None:
        cartridges.append({"name": cartridge_name, "default": len(cartridges) == 0})
    elif "default" not in existing:
        existing["default"] = len(cartridges) == 1

    if not any(bool(c.get("default")) for c in cartridges):
        cartridges[0]["default"] = True

    dtc["AutoLoad"] = True


def _table_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, list):
        return value
    return []


def _is_generated_dtc_member(
    filename: str, cartridges: dict[str, dict[str, Any]]
) -> bool:
    for dcs_type in cartridges:
        for alias in cartridge_archive_names(dcs_type):
            if filename == f"DTC/{alias}.dtc":
                return True
    return False
