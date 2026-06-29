from __future__ import annotations

from game.plugins.luaplugin import LuaPlugin


def test_bool_renders_lua_keyword() -> None:
    assert LuaPlugin._lua_literal(True) == "true"
    assert LuaPlugin._lua_literal(False) == "false"


def test_numbers_render_bare() -> None:
    assert LuaPlugin._lua_literal(8) == "8"
    assert LuaPlugin._lua_literal(0) == "0"
    assert LuaPlugin._lua_literal(2.5) == "2.5"


def test_string_renders_quoted_and_unchanged() -> None:
    # The Vietnam convoy bug: a string option (convoyTruckType) was emitted bare
    # and lowercased -> `= Ural-375` -> Lua parsed `ural - 375`. It must be a
    # quoted Lua string with the original casing preserved.
    assert LuaPlugin._lua_literal("Ural-375") == '"Ural-375"'


def test_string_escapes_quotes_and_backslashes() -> None:
    assert LuaPlugin._lua_literal('a"b') == '"a\\"b"'
    assert LuaPlugin._lua_literal("a\\b") == '"a\\\\b"'
