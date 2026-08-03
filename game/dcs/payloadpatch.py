"""Make pydcs's payload loader survive mod payload files it cannot parse.

pydcs's ``FlyingType.load_payloads`` catches ``SyntaxError`` but not
``ValueError``. Some mod payload Lua files index their pylon tables with named
constants::

    local WTL = 1   --[[ LEFT WINGTIP ]]
    ...
    ["pylons"] = { [WTL] = { ["CLSID"] = "...", ["num"] = WTL }, ... }

pydcs's Lua parser accepts only a string or a number where a table key belongs,
so it raises ``ValueError`` and the exception escapes into whatever asked for the
loadout. That is not hypothetical: it aborts a turn's planning pass outright when
the first caller happens to be inside ``Coalition.plan_missions`` (the CJS Super
Hornet v2.4 files hit this), and it is worse than a plain failure because
``load_payloads`` assigns ``cls.payloads = {}`` *before* the loop -- so the next
call returns the half-filled dict without raising, and the airframe silently ends
up with a partial payload set instead of an error anyone would notice.

This module installs a replacement that skips an unparseable file with a warning
and keeps going, so one bad mod file costs that file's fits and nothing else.

``patch_pydcs_payload_loader`` is idempotent and is called from
``persistency.setup`` (which every entry point -- the app, tools, and tests --
goes through) as well as ``qt_ui.main``.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any, Optional

from dcs.unittype import FlyingType

_PATCHED = False


def _uses_unsupported_lua_table_indices(lua_text: str) -> bool:
    """True if the file keys a table with a local variable, e.g. ``[WTL] =``."""
    local_names = set(re.findall(r"^\s*local\s+([A-Za-z_]\w*)\s*=", lua_text, re.M))
    return any(
        re.search(rf"\[\s*{re.escape(name)}\s*\]\s*=", lua_text) for name in local_names
    )


def _payload_unit_type_from_text(lua_text: str) -> Optional[str]:
    match = re.search(r'(?:\["unitType"\]|unitType)\s*=\s*"([^"]+)"', lua_text)
    return match.group(1) if match else None


def patch_pydcs_payload_loader() -> None:
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    import dcs.lua as lua

    @classmethod  # type: ignore[misc]
    def _patched_load_payloads(cls: Any) -> Any:
        from dcs.payloads import PayloadDirectories

        if FlyingType._UnitPayloadGlobals is None:
            from dcs import task

            FlyingType._UnitPayloadGlobals = {
                v.internal_name: v.id for k, v in task.MainTask.map.items()
            }

        FlyingType.scan_payload_dir()
        if cls.payloads is not None:
            return cls.payloads
        cls.payloads = {}

        for payload_dir in PayloadDirectories.payload_dirs():
            if not payload_dir.exists():
                continue
            for payload_path in payload_dir.glob("*.lua"):
                lua_text: Optional[str] = None
                try:
                    FlyingType._payload_cache[payload_path]
                except KeyError:
                    lua_text = payload_path.read_text(
                        encoding="utf-8", errors="replace"
                    )
                    payload_unit_type = _payload_unit_type_from_text(lua_text)
                    if payload_unit_type is None:
                        continue
                    FlyingType._payload_cache[payload_path] = payload_unit_type
                if (
                    FlyingType._payload_cache[payload_path] != cls.id
                    or not payload_path.exists()
                ):
                    continue
                if lua_text is None:
                    lua_text = payload_path.read_text(
                        encoding="utf-8", errors="replace"
                    )
                if _uses_unsupported_lua_table_indices(lua_text):
                    _warn_skipped(payload_path)
                    continue
                try:
                    payload_main = lua.loads(
                        lua_text,
                        _globals=FlyingType._UnitPayloadGlobals,  # type: ignore[arg-type]
                    )
                except SyntaxError:
                    print(
                        f"Error parsing lua file '{payload_path}'",
                        file=sys.stderr,
                    )
                    raise
                except ValueError:
                    _warn_skipped(payload_path)
                    continue
                pays = payload_main["unitPayloads"]
                if pays["unitType"] == cls.id:
                    for load in pays["payloads"].values():
                        # Payload directories are iterated in decreasing order of
                        # preference, so keep the first fit seen under a name.
                        if load["name"] not in cls.payloads:
                            cls.payloads[load["name"]] = load

        return cls.payloads

    FlyingType.load_payloads = _patched_load_payloads  # type: ignore[method-assign,assignment]


def _warn_skipped(payload_path: Path) -> None:
    logging.getLogger("pydcs").warning(
        "Skipping payload file with unsupported Lua syntax "
        "(local variable table indices): %s",
        payload_path,
    )
