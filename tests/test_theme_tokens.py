"""Guards for the generated Qt stylesheet (qt_ui/theme).

The stylesheet is now built from design tokens instead of being hand-maintained.
The risk that introduces is a *silent* one: a widget that sets a style hook the
generated sheet has no rule for renders unthemed, and nothing fails. These tests
close that gap by reading the hooks the application actually sets and asserting
the sheet styles every one of them.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Set

from game.ato.flighttype import FlightType
from qt_ui import liberation_theme
from qt_ui.theme import (
    RETRIBUTION_DARK,
    build_stylesheet,
    task_chip_colors,
    to_css_variables,
)

QT_UI_ROOT = Path(__file__).resolve().parents[1] / "qt_ui"

# Hooks whose value is computed at runtime, so a source scan cannot see them.
# QFlightTypeTaskInfo passes the FlightType name; QFinancesMenu passes these.
_DYNAMIC_HOOKS: Set[str] = {
    "green",
    "expense",
    "muted",
    "balance",
    "net",
    "net-neg",
    "pill-on",
    "pill-off",
}


def _hooks_used_in_source() -> Set[str]:
    """Every literal ``setProperty("style"|"class", "...")`` value in qt_ui.

    Parsed rather than pattern-matched so that commented-out code cannot
    contribute a hook the app never actually sets.
    """
    hooks: Set[str] = set()
    for path in QT_UI_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr != "setProperty":
                continue
            if len(node.args) != 2:
                continue
            name, value = node.args
            if not isinstance(name, ast.Constant) or name.value not in (
                "style",
                "class",
            ):
                continue
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                continue
            # A class property may name several classes: "btn-danger comms".
            hooks.update(value.value.split())
    return hooks


def _sheet_styles(hook: str, sheet: str) -> bool:
    """True if the sheet has a rule selecting this hook, either form."""
    return f'[style="{hook}"]' in sheet or f".{hook}" in sheet


def test_every_style_hook_in_the_app_is_styled() -> None:
    sheet = build_stylesheet()
    hooks = _hooks_used_in_source() | _DYNAMIC_HOOKS
    # Sanity: the scan must actually find the hooks, or this test proves nothing.
    assert "btn-primary" in hooks
    assert len(hooks) > 20

    unstyled = sorted(hook for hook in hooks if not _sheet_styles(hook, sheet))
    assert not unstyled, (
        "These style hooks are set by the UI but have no rule in the generated "
        f"stylesheet, so they render unthemed: {unstyled}"
    )


def test_every_flight_type_has_a_task_chip() -> None:
    # QFlightTypeTaskInfo styles its label with the FlightType's name. The sheet
    # this replaced covered only 10 of these, so the rest drew with no chip.
    colors = task_chip_colors()
    missing = sorted(t.name for t in FlightType if t.name not in colors)
    assert not missing, f"FlightType members with no task-chip colour: {missing}"

    sheet = build_stylesheet()
    unstyled = sorted(t.name for t in FlightType if not _sheet_styles(t.name, sheet))
    assert not unstyled, f"FlightType members with no chip rule: {unstyled}"


def test_stylesheet_has_no_unresolved_template_markers() -> None:
    # A mistyped f-string would leave the token expression in the output rather
    # than its value, which Qt silently ignores along with the whole rule.
    sheet = build_stylesheet()
    for marker in ("{p.", "{s.", "None", "{}"):
        assert marker not in sheet, f"Unresolved marker {marker!r} in the stylesheet"


def test_stylesheet_braces_are_balanced() -> None:
    sheet = build_stylesheet()
    assert sheet.count("{") == sheet.count("}")


def test_css_variables_cover_the_palette() -> None:
    css = to_css_variables()
    for color in (
        RETRIBUTION_DARK.ground,
        RETRIBUTION_DARK.panel,
        RETRIBUTION_DARK.accent,
        RETRIBUTION_DARK.danger,
        RETRIBUTION_DARK.success,
    ):
        assert color in css, f"{color} missing from the exported CSS variables"


def test_accent_stays_out_of_the_maps_semantic_hues() -> None:
    # The campaign map uses amber/orange for suspected activity, the FLOT and
    # MIA pilots. Chrome must not compete with map meaning, which is why the
    # accent is cyan-teal. Guard the intent, not the exact hex.
    red, green, blue = (int(RETRIBUTION_DARK.accent[i : i + 2], 16) for i in (1, 3, 5))
    assert blue > red, "The accent must not drift warm — the map owns amber/orange"
    assert green > red, "The accent must not drift warm — the map owns amber/orange"


def test_default_theme_is_the_generated_one() -> None:
    liberation_theme.set_theme_index(liberation_theme.DEFAULT_THEME_INDEX)
    assert liberation_theme.theme_is_generated()
    assert liberation_theme.get_theme_name() == "Retribution"


def test_every_theme_entry_declares_its_source() -> None:
    for index, theme in liberation_theme.THEMES.items():
        assert theme["themeSource"] in {"file", "generated"}, index
        if theme["themeSource"] == "file":
            assert theme["themeFile"], f"Theme {index} is file-backed but names no file"


def test_legacy_stylesheet_is_still_selectable() -> None:
    # The hand-written sheet stays available so a bad look is one dropdown away
    # from being reverted rather than a rebuild.
    names = {theme["themeName"] for theme in liberation_theme.THEMES.values()}
    assert "DCS World (legacy)" in names
