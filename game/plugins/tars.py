from __future__ import annotations

from typing import List

from game.plugins.luaplugin import LuaPlugin


class TarsPlugin(LuaPlugin):
    """Ops.TARS player recon / TARPS film (vendored class + the 414th init).

    Loaded late (after all plugin config) because tars_414_init.lua calls
    TARS:New() and applies the 414th config at file scope, after which it needs
    dcsRetribution.plugins.tars and MOOSE present. No mission-data gate beyond
    the plugin being enabled, so the default should_late_init applies.
    """

    def late_init_files(self) -> List[str]:
        return ["TARS.lua", "tars_414_init.lua"]

    def late_init_comment(self) -> str:
        return "Load Ops.TARS (player recon / TARPS film)"
