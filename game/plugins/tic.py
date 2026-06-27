from __future__ import annotations

import textwrap
from typing import List, Optional, TYPE_CHECKING

from game.plugins.luaplugin import LuaPlugin

if TYPE_CHECKING:
    from game.missiongenerator.luagenerator import LuaGenerator


class TicPlugin(LuaPlugin):
    """Troops In Contact frontline battle sim (TIC_v1.1 + the 414th init).

    Loaded late (after all plugin config) because the preamble seeds the GLSCO
    config table from dcsRetribution.plugins.tic, which is only set once the
    normal plugin-config pass has run. The gate is the FLOT generator handing
    frontline groups to TIC (mission_data.tic_groups non-empty); that population
    is itself enable-gated (flotgenerator.tic_enabled), so a non-empty list
    already implies the TIC plugin is on.
    """

    def late_init_files(self) -> List[str]:
        return ["TIC_v1.1.lua", "tic_414_init.lua"]

    def late_init_comment(self) -> str:
        return "Load TIC_v1.1 (frontline battle sim)"

    def should_late_init(self, lua_generator: LuaGenerator) -> bool:
        return bool(lua_generator.mission_data.tic_groups)

    def late_init_preamble(self, lua_generator: LuaGenerator) -> Optional[str]:
        # Pre-seed TIC (GLSCO) configuration from the plugin options before the
        # script's file-scope auto-initialization runs. AutoInitialize/AutoStart
        # are disabled because tic_414_init.lua (loaded right after the main
        # script) installs the 414th's ambient-fire extension and then owns
        # Initialize/Activate.
        return textwrap.dedent("""\
            -- Pre-seed TIC (GLSCO) configuration from Retribution plugin
            -- options. TIC respects values that exist before it loads.
            -- AutoInitialize/AutoStart are disabled because tic_414_init.lua
            -- (loaded right after the main script) installs the 414th's
            -- ambient-fire extension and then owns Initialize/Activate.
            GLSCO = GLSCO or {}
            GLSCO.AutoInitialize = false
            GLSCO.AutoStart = false
            if dcsRetribution and dcsRetribution.plugins
                    and dcsRetribution.plugins.tic then
                GLSCO.StormTrooperAI =
                    dcsRetribution.plugins.tic.stormtrooper == true
                GLSCO.CreateMenus =
                    dcsRetribution.plugins.tic.createMenus == true
            end
            """)
