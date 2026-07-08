from __future__ import annotations

import json
import logging
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING, Any

from game.settings import Settings

if TYPE_CHECKING:
    from game.missiongenerator.luagenerator import LuaGenerator


class LuaPluginWorkOrder:
    def __init__(
        self, parent_mnemonic: str, filename: str, mnemonic: str, disable: bool
    ) -> None:
        self.parent_mnemonic = parent_mnemonic
        self.filename = filename
        self.mnemonic = mnemonic
        self.disable = disable

    def work(self, lua_generator: LuaGenerator, defer: bool = False) -> None:
        if self.disable:
            lua_generator.bypass_plugin_script(self.mnemonic)
        else:
            lua_generator.inject_plugin_script(
                self.parent_mnemonic, self.filename, self.mnemonic, defer=defer
            )


class PluginSettings:
    def __init__(self, identifier: str, value: Any) -> None:
        self.identifier = identifier
        self.value = value
        self.settings = Settings()
        self.initialize_settings()

    def set_settings(self, settings: Settings) -> None:
        self.settings = settings
        self.initialize_settings()

    def initialize_settings(self) -> None:
        # Plugin options are saved in the game's Settings, but it's possible for
        # plugins to change across loads. If new plugins are added or new
        # options added to those plugins, initialize the new settings.
        self.settings.initialize_plugin_option(self.identifier, self.value)

    @property
    def get_value(self) -> Any:
        return self.settings.plugin_option(self.identifier)

    def set_value(self, value: Any) -> None:
        self.settings.set_plugin_option(self.identifier, value)


class LuaPluginOption(PluginSettings):
    def __init__(
        self, identifier: str, name: str, min: Any, max: Any, value: Any
    ) -> None:
        super().__init__(identifier, value)
        self.name = name
        if type(value) == int or type(value) == float:
            self.min, self.max = min, max
        else:
            self.min, self.max = None, None


@dataclass(frozen=True)
class LuaPluginDefinition:
    identifier: str
    name: str
    description: str
    present_in_ui: bool
    enabled_by_default: bool
    options: List[LuaPluginOption]
    work_orders: List[LuaPluginWorkOrder]
    config_work_orders: List[LuaPluginWorkOrder]
    other_resource_files: List[str]

    @classmethod
    def from_json(cls, name: str, path: Path) -> LuaPluginDefinition:
        data = json.loads(path.read_text())

        options = []
        for option in data.get("specificOptions"):
            option_id = option["mnemonic"]
            options.append(
                LuaPluginOption(
                    identifier=f"{name}.{option_id}",
                    name=option.get("nameInUI", name),
                    min=option.get("minimumValue", 0),
                    max=option.get("maximumValue", 10000),
                    value=option.get("defaultValue"),
                )
            )

        work_orders = []
        for work_order in data.get("scriptsWorkOrders"):
            work_orders.append(
                LuaPluginWorkOrder(
                    name,
                    work_order.get("file"),
                    work_order["mnemonic"],
                    work_order.get("disable", False),
                )
            )
        config_work_orders = []
        for work_order in data.get("configurationWorkOrders"):
            config_work_orders.append(
                LuaPluginWorkOrder(
                    name,
                    work_order.get("file"),
                    work_order["mnemonic"],
                    work_order.get("disable", False),
                )
            )

        return cls(
            identifier=name,
            name=data["nameInUI"],
            description=data.get("descriptionInUI", ""),
            present_in_ui=not data.get("skipUI", False),
            enabled_by_default=data.get("defaultValue", False),
            options=options,
            work_orders=work_orders,
            config_work_orders=config_work_orders,
            other_resource_files=data.get("otherResourceFiles", []),
        )


class LuaPlugin(PluginSettings):
    def __init__(self, definition: LuaPluginDefinition) -> None:
        self.definition = definition
        super().__init__(self.definition.identifier, self.definition.enabled_by_default)

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def description(self) -> str:
        return self.definition.description

    @property
    def show_in_ui(self) -> bool:
        return self.definition.present_in_ui

    @property
    def options(self) -> List[LuaPluginOption]:
        return self.definition.options

    @property
    def enabled(self) -> bool:
        return type(self.get_value) == bool and self.get_value

    @classmethod
    def from_json(cls, name: str, path: Path) -> Optional[LuaPlugin]:
        try:
            definition = LuaPluginDefinition.from_json(name, path)
        except KeyError:
            logging.exception("Required plugin configuration value missing")
            return None

        return cls(definition)

    def set_settings(self, settings: Settings) -> None:
        super().set_settings(settings)
        for option in self.definition.options:
            option.set_settings(self.settings)

    def inject_scripts(self, lua_generator: LuaGenerator) -> None:
        for work_order in self.definition.work_orders:
            work_order.work(lua_generator)

    @staticmethod
    def _lua_literal(value: Any) -> str:
        """Render a plugin-option value as a Lua literal.

        ``bool`` -> ``true``/``false``; ``int``/``float`` -> the number; anything
        else -> a quoted, escaped Lua string. ``bool`` is checked first because it
        subclasses ``int``. (Previously every value was ``str(...).lower()`` emitted
        bare -- fine for bools/numbers, but a *string* option such as the Vietnam
        convoy ``convoyTruckType: "Ural-375"`` became the bare token ``ural-375``,
        which Lua parsed as ``ural - 375`` -> "arithmetic on global 'ural'".)
        """
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    def inject_configuration(self, lua_generator: LuaGenerator) -> None:
        # inject the plugin options
        if self.options:
            option_decls = []
            for option in self.options:
                value = self._lua_literal(option.get_value)
                name = option.identifier
                option_decls.append(f"    dcsRetribution.plugins.{name} = {value}")

            joined_options = "\n".join(option_decls)

            lua = textwrap.dedent(f"""\
                -- {self.identifier} plugin configuration.

                if dcsRetribution then
                    if not dcsRetribution.plugins then
                        dcsRetribution.plugins = {{}}
                    end
                    dcsRetribution.plugins.{self.identifier} = {{}}
                    {joined_options}
                end

            """)

            lua_generator.inject_lua_trigger(
                lua, f"{self.identifier} plugin configuration"
            )

        # Config scripts are deferred so LuaGenerator can bundle every plugin's
        # config load into a single mission-start trigger -- DCS silently drops
        # some of many separate DoScriptFile triggers on a heavy mission.
        for work_order in self.definition.config_work_orders:
            work_order.work(lua_generator, defer=True)

    def inject_other_resource_files(self, lua_generator: LuaGenerator) -> None:
        for resource_file in self.definition.other_resource_files:
            # TODO: should probably deconflict names of resources
            lua_generator.inject_other_plugin_resources(
                self.definition.identifier, resource_file
            )

    # --- Late-init lifecycle (the "after everything else is configured" pass) ---
    #
    # A few plugins (TIC, TARS, SCAR) must load their main script AFTER every
    # plugin's configuration has been injected, because their init reads
    # dcsRetribution.plugins.<id> / MOOSE at file scope. The base LuaPluginWorkOrder
    # path can't express that ordering (a plugin's scripts load before its own
    # config), so those features were previously hand-injected in LuaGenerator.
    # These hooks let such a plugin declare what to load late instead. The defaults
    # are no-ops, so the other plugins are unaffected.

    def late_init_files(self) -> List[str]:
        """Resource-relative .lua files to load AFTER all plugin config.

        Empty (the default) means this plugin has no late-init pass.
        """
        return []

    def late_init_comment(self) -> str:
        """Comment for the late-init TriggerStart (shown in the .miz triggers)."""
        return self.name

    def late_init_preamble(self, lua_generator: LuaGenerator) -> Optional[str]:
        """Optional inline Lua emitted (DoScript) right before the files load."""
        return None

    def should_late_init(self, lua_generator: LuaGenerator) -> bool:
        """Whether the late-init pass should fire for this mission.

        Default: fire when the plugin is enabled and actually declares files.
        Subclasses override to add mission-data gates (e.g. only when frontline
        groups were handed to TIC, or a SCAR tasking was planned).
        """
        return self.enabled and bool(self.late_init_files())

    def inject_late_init(self, lua_generator: LuaGenerator) -> None:
        lua_generator.inject_late_plugin_scripts(
            self.identifier,
            self.late_init_files(),
            self.late_init_comment(),
            self.late_init_preamble(lua_generator),
        )
