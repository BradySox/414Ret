from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from game.missiongenerator.luagenerator import LuaGenerator
from game.plugins.luaplugin import LuaPlugin
from game.plugins.tars import TarsPlugin
from game.plugins.tic import TicPlugin


def _enabled_plugin(cls: type[LuaPlugin], identifier: str, enabled: bool) -> LuaPlugin:
    """Build a plugin instance without the Settings-loading __init__."""
    plugin = cls.__new__(cls)
    plugin.identifier = identifier
    plugin.settings = MagicMock()
    plugin.settings.plugin_option.return_value = enabled
    return plugin


def _gen(**mission_data: object) -> MagicMock:
    gen = MagicMock()
    for key, value in mission_data.items():
        setattr(gen.mission_data, key, value)
    return gen


# --- Gate logic (reproduces each old _inject_*_script gate exactly) ------------


def test_tic_gates_on_frontline_groups_only() -> None:
    tic = TicPlugin.__new__(TicPlugin)
    # TIC's gate ignores `enabled` by design: tic_groups is only populated when
    # the TIC plugin is on (flotgenerator.tic_enabled), so non-empty implies on.
    assert tic.should_late_init(_gen(tic_groups=["TIC:a"])) is True
    assert tic.should_late_init(_gen(tic_groups=[])) is False


def test_tars_gates_on_enabled() -> None:
    assert _enabled_plugin(TarsPlugin, "tars", True).should_late_init(_gen()) is True
    assert _enabled_plugin(TarsPlugin, "tars", False).should_late_init(_gen()) is False


def test_plain_plugin_has_no_late_init() -> None:
    plain = _enabled_plugin(LuaPlugin, "ctld", True)
    assert plain.late_init_files() == []
    assert plain.should_late_init(_gen()) is False


# --- Declared files must exist on disk (the fail-loud-at-CI guard) -------------


def test_declared_late_init_files_exist() -> None:
    root = Path("resources/plugins")
    for identifier, cls in (
        ("tic", TicPlugin),
        ("tars", TarsPlugin),
    ):
        plugin = cls.__new__(cls)
        for filename in plugin.late_init_files():
            assert (
                root / identifier / filename
            ).is_file(), (
                f"{identifier}/{filename} declared by {cls.__name__} is missing"
            )


# --- inject_late_init plumbing + the generator helper -------------------------


def test_inject_late_init_passes_files_comment_and_preamble() -> None:
    tic = TicPlugin.__new__(TicPlugin)
    tic.identifier = "tic"
    gen = MagicMock()
    tic.inject_late_init(gen)
    gen.inject_late_plugin_scripts.assert_called_once()
    ident, files, comment, preamble = gen.inject_late_plugin_scripts.call_args.args
    assert ident == "tic"
    assert files == ["TIC_v1.1.lua", "tic_414_init.lua"]
    assert comment == "Load TIC_v1.1 (frontline battle sim)"
    assert preamble is not None and "GLSCO.AutoInitialize = false" in preamble


def test_tars_late_init_has_no_preamble() -> None:
    tars = TarsPlugin.__new__(TarsPlugin)
    tars.identifier = "tars"
    gen = MagicMock()
    tars.inject_late_init(gen)
    _, _, _, preamble = gen.inject_late_plugin_scripts.call_args.args
    assert preamble is None


def test_helper_emits_one_trigger_with_all_files() -> None:
    gen = LuaGenerator.__new__(LuaGenerator)
    gen.mission = MagicMock()
    gen.inject_late_plugin_scripts(
        "tic", ["TIC_v1.1.lua", "tic_414_init.lua"], "comment", preamble="-- pre"
    )
    assert gen.mission.map_resource.add_resource_file.call_count == 2
    gen.mission.triggerrules.triggers.append.assert_called_once()


def test_helper_skips_when_a_file_is_missing() -> None:
    gen = LuaGenerator.__new__(LuaGenerator)
    gen.mission = MagicMock()
    gen.inject_late_plugin_scripts("tic", ["does_not_exist.lua"], "comment")
    gen.mission.map_resource.add_resource_file.assert_not_called()
    gen.mission.triggerrules.triggers.append.assert_not_called()


def test_helper_noop_on_empty_file_list() -> None:
    gen = LuaGenerator.__new__(LuaGenerator)
    gen.mission = MagicMock()
    gen.inject_late_plugin_scripts("tic", [], "comment")
    gen.mission.triggerrules.triggers.append.assert_not_called()
