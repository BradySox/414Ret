"""Headless Lua plugin harness: runs resources/plugins scripts under lupa.

Loads tests/lua/dcs_stubs.lua (a fake of the vanilla-DCS mission scripting
sandbox) into a real Lua 5.1 interpreter -- the dialect DCS runs -- then loads a
plugin script against a dcsRetribution config table built from plain Python
dicts. Tests drive the virtual clock and assert on the recorded trigger/timer
activity.

This complements, never replaces, the in-game pass checklist: it catches the
"script errors and the feature silently never starts" class of bug that the
luac -p CI gate cannot, but it models no DCS AI, physics, or weapons flight.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import lupa.lua51

REPO_ROOT = Path(__file__).resolve().parents[2]
STUBS = Path(__file__).resolve().parent / "dcs_stubs.lua"


class DcsPluginHarness:
    def __init__(self) -> None:
        self.lua = lupa.lua51.LuaRuntime(unpack_returned_tuples=False)
        self.lua.execute(STUBS.read_text(encoding="utf-8"))
        self.harness = self.lua.globals().DcsHarness

    # -- config ---------------------------------------------------------------

    def to_lua(self, value: Any) -> Any:
        """Recursively convert Python dicts/lists/scalars to Lua tables."""
        if isinstance(value, dict):
            table = self.lua.table()
            for key, item in value.items():
                table[key] = self.to_lua(item)
            return table
        if isinstance(value, (list, tuple)):
            table = self.lua.table()
            for index, item in enumerate(value, start=1):
                table[index] = self.to_lua(item)
            return table
        return value

    def set_retribution_config(
        self,
        vietnam_ops: dict[str, Any] | None = None,
        plugin_options: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Build the dcsRetribution global the generator would have emitted."""
        config: dict[str, Any] = {"plugins": plugin_options or {}}
        if vietnam_ops is not None:
            config["VietnamOps"] = vietnam_ops
        self.lua.globals().dcsRetribution = self.to_lua(config)

    # -- plugin loading / time ------------------------------------------------

    def load_plugin_script(self, relative_path: str) -> None:
        """Execute a plugin script exactly as the mission would at load."""
        script = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        self.lua.execute(script)

    def advance_to(self, mission_time: float) -> None:
        """Run all scheduled functions due up to mission_time (virtual clock)."""
        self.harness.advanceTo(mission_time)

    def add_group(self, spec: dict[str, Any]) -> None:
        self.harness.addGroup(self.to_lua(spec))

    def fire_event(self, event: dict[str, Any]) -> None:
        self.harness.fireEvent(self.to_lua(event))

    def pending_scheduled(self) -> int:
        return int(self.harness.pendingCount())

    # -- recorded activity ----------------------------------------------------

    def to_python(self, value: Any) -> Any:
        """Recursively convert Lua tables back to Python lists/dicts."""
        if lupa.lua51.lua_type(value) != "table":
            return value
        keys = list(value.keys())
        if keys and all(isinstance(k, (int, float)) for k in keys):
            return [self.to_python(value[k]) for k in sorted(keys)]
        return {k: self.to_python(value[k]) for k in keys}

    def records(self, name: str) -> list[Any]:
        recorded = self.to_python(self.harness.records[name])
        if recorded is None or recorded == {}:
            return []
        assert isinstance(recorded, list)
        return recorded

    @property
    def side(self) -> Any:
        return self.lua.globals().coalition.side

    @property
    def category(self) -> Any:
        return self.lua.globals().Group.Category

    def assert_no_lua_errors(self) -> None:
        errors = self.records("errors")
        assert not errors, f"Lua errors escaped the plugin: {errors}"
