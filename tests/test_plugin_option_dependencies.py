"""Plugin-option ``enabledWhen``: dependencies between a plugin's own options.

``Settings`` fields have had ``enabled_when`` for a while, so a child setting
greys out when its master is off. The 207 options plugins expose had no such
mechanism, which is the same trap in a different box: a spinbox that reads as
live while the script that consumes it never runs.

These pin the parsing, the load-time validation (a typo'd mnemonic must fail
loudly rather than grey an option out forever), and -- the part most likely to
rot -- that every dependency declared in a shipped plugin.json is one the Lua
actually honours.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from game.plugins.luaplugin import (
    LuaPluginDefinition,
    LuaPluginOption,
    PluginOptionDependencyError,
    normalize_plugin_enabled_when,
    plugin_option_is_enabled,
)
from game.settings import Settings

PLUGIN_JSONS = sorted(Path("resources/plugins").glob("*/plugin.json"))


def _write_plugin(tmp_path: Path, options: list[dict[str, Any]]) -> Path:
    path = tmp_path / "plugin.json"
    path.write_text(
        json.dumps(
            {
                "nameInUI": "Test",
                "defaultValue": True,
                "specificOptions": options,
                "scriptsWorkOrders": [],
                "configurationWorkOrders": [],
            }
        )
    )
    return path


def _option(mnemonic: str, **extra: Any) -> dict[str, Any]:
    return {"nameInUI": mnemonic, "mnemonic": mnemonic, "defaultValue": True, **extra}


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def test_shorthand_means_enabled_when_master_is_truthy() -> None:
    assert normalize_plugin_enabled_when("p", "master") == ("p.master", True)


def test_explicit_pair_carries_the_expected_value() -> None:
    assert normalize_plugin_enabled_when("p", ["master", False]) == ("p.master", False)


def test_absent_dependency_is_none() -> None:
    assert normalize_plugin_enabled_when("p", None) is None


def test_master_is_qualified_with_the_plugin_id(tmp_path: Path) -> None:
    """Options are stored under 'plugin.mnemonic', so the master must match."""
    path = _write_plugin(
        tmp_path, [_option("master"), _option("child", enabledWhen="master")]
    )
    definition = LuaPluginDefinition.from_json("myplugin", path)
    child = next(o for o in definition.options if o.identifier.endswith("child"))
    assert child.enabled_when == ("myplugin.master", True)


def test_options_without_a_dependency_are_unaffected(tmp_path: Path) -> None:
    path = _write_plugin(tmp_path, [_option("plain")])
    definition = LuaPluginDefinition.from_json("myplugin", path)
    assert definition.options[0].enabled_when is None


# --------------------------------------------------------------------------
# Load-time validation
# --------------------------------------------------------------------------


def test_unknown_master_raises_at_load(tmp_path: Path) -> None:
    """A typo would otherwise grey the option out forever, silently."""
    path = _write_plugin(tmp_path, [_option("child", enabledWhen="nosuchoption")])
    with pytest.raises(PluginOptionDependencyError, match="nosuchoption"):
        LuaPluginDefinition.from_json("myplugin", path)


def test_self_dependency_raises_at_load(tmp_path: Path) -> None:
    path = _write_plugin(tmp_path, [_option("child", enabledWhen="child")])
    with pytest.raises(PluginOptionDependencyError, match="on itself"):
        LuaPluginDefinition.from_json("myplugin", path)


def test_forward_reference_to_a_later_option_is_allowed(tmp_path: Path) -> None:
    """Declaration order must not matter -- validation runs over the whole set."""
    path = _write_plugin(
        tmp_path, [_option("child", enabledWhen="master"), _option("master")]
    )
    definition = LuaPluginDefinition.from_json("myplugin", path)
    child = next(o for o in definition.options if o.identifier.endswith("child"))
    assert child.enabled_when == ("myplugin.master", True)


# --------------------------------------------------------------------------
# The greying rule
#
# Pure on purpose: the options page only passes this answer to setEnabled, so
# the rule is covered here instead of behind a Qt widget that CI's headless
# runner has to stand up.
# --------------------------------------------------------------------------


def _settings(**options: Any) -> Settings:
    settings = Settings()
    for identifier, value in options.items():
        settings.set_plugin_option(identifier.replace("__", "."), value)
    return settings


def _dependent(master: str = "p.master", expected: Any = True) -> LuaPluginOption:
    return LuaPluginOption(
        identifier="p.child",
        name="child",
        min=0,
        max=1,
        value=True,
        enabled_when=(master, expected),
    )


def test_dependant_is_live_when_the_master_matches() -> None:
    assert plugin_option_is_enabled(_dependent(), _settings(p__master=True))


def test_dependant_is_dead_when_the_master_does_not_match() -> None:
    assert not plugin_option_is_enabled(_dependent(), _settings(p__master=False))


def test_an_inverse_dependency_greys_when_the_master_is_on() -> None:
    option = _dependent(expected=False)
    assert plugin_option_is_enabled(option, _settings(p__master=False))
    assert not plugin_option_is_enabled(option, _settings(p__master=True))


def test_an_option_with_no_dependency_is_always_live() -> None:
    option = LuaPluginOption("p.plain", "plain", 0, 1, True)
    assert plugin_option_is_enabled(option, _settings())


def test_a_master_missing_from_an_old_save_leaves_the_dependant_live() -> None:
    """Degrade toward usable, not toward a control the user cannot explain."""
    assert plugin_option_is_enabled(_dependent(), _settings())


# --------------------------------------------------------------------------
# The shipped plugins
# --------------------------------------------------------------------------


@pytest.mark.parametrize("path", PLUGIN_JSONS, ids=lambda p: p.parent.name)
def test_every_shipped_plugin_loads(path: Path) -> None:
    """Covers the validation above across the real tree, not just fixtures."""
    LuaPluginDefinition.from_json(path.parent.name, path)


def _declared_dependencies() -> list[tuple[str, str, Any]]:
    found = []
    for path in PLUGIN_JSONS:
        definition = LuaPluginDefinition.from_json(path.parent.name, path)
        for option in definition.options:
            if option.enabled_when is not None:
                found.append(
                    (option.identifier, option.enabled_when[0], option.enabled_when[1])
                )
    return found


def test_the_tree_actually_declares_dependencies() -> None:
    """Guards against the feature being wired up but never used."""
    assert len(_declared_dependencies()) >= 13


def test_a_master_is_never_itself_a_dependant() -> None:
    """One level only.

    The options page refreshes every row from stored values on any change, so a
    chain would render correctly -- but a two-level dependency is a sign the
    plugin's options want restructuring, and nothing in the tree needs one.
    """
    deps = _declared_dependencies()
    dependants = {identifier for identifier, _master, _value in deps}
    masters = {master for _identifier, master, _value in deps}
    assert not (dependants & masters)


def test_declared_masters_are_boolean_options() -> None:
    """A greyed row is read as "the master is off", so the master must be a toggle."""
    for path in PLUGIN_JSONS:
        data = json.loads(path.read_text())
        options = data.get("specificOptions") or []
        by_mnemonic = {o["mnemonic"]: o for o in options}
        for option in options:
            when = option.get("enabledWhen")
            if when is None:
                continue
            master = when if isinstance(when, str) else when[0]
            assert isinstance(by_mnemonic[master]["defaultValue"], bool), (
                f"{path}: '{option['mnemonic']}' depends on '{master}', which is "
                "not a boolean option"
            )
