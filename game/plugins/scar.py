from __future__ import annotations

from typing import List, TYPE_CHECKING

from game.plugins.luaplugin import LuaPlugin

if TYPE_CHECKING:
    from game.missiongenerator.luagenerator import LuaGenerator


class ScarPlugin(LuaPlugin):
    """SCAR scenario/results bridge (scar_414_init.lua).

    Loaded late (after all plugin config), gated on a SCAR tasking having been
    planned (mission_data.scar_taskings non-empty). The scenario is currently
    dormant — generate_plugin_data() clears scar_taskings for the rescue rework —
    so this gate evaluates False and nothing is injected, matching the previous
    behavior exactly.
    """

    def late_init_files(self) -> List[str]:
        return ["scar_414_init.lua"]

    def late_init_comment(self) -> str:
        return "Load SCAR scenario bridge"

    def should_late_init(self, lua_generator: LuaGenerator) -> bool:
        return self.enabled and bool(lua_generator.mission_data.scar_taskings)
