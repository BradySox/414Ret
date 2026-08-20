"""String plugin options: the value the user can actually reach from the UI.

The settings page picked its widget from the option's default type and handled
bool and int/float only, so a string option rendered a label beside an empty
cell -- visible, and uneditable. The fork ships seven of them (a taxi-card
frequency, four comma-separated weapon-pattern lists, the FAC(A) aircraft type
and the red-scramble spawn mode). Two of the seven name one exact thing and are
dropdowns; the pattern lists stay free text because they are plural by design.

`choices` is what separates the two shapes: a closed set becomes a dropdown, and
everything else stays free text, because a pattern list has no enumerable values.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from game.plugins.luaplugin import LuaPluginDefinition, PluginOptionDependencyError

PLUGINS = Path("resources/plugins")


def _write(tmp_path: Path, options: list[dict[str, object]]) -> Path:
    path = tmp_path / "plugin.json"
    path.write_text(
        json.dumps(
            {
                "nameInUI": "Test",
                "specificOptions": options,
                "scriptsWorkOrders": [],
                "configurationWorkOrders": [],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_a_string_option_without_choices_stays_free_text(tmp_path: Path) -> None:
    definition = LuaPluginDefinition.from_json(
        "test", _write(tmp_path, [{"mnemonic": "patterns", "defaultValue": "A,B,C"}])
    )
    assert definition.options[0].choices is None


def test_choices_are_carried_off_the_json(tmp_path: Path) -> None:
    definition = LuaPluginDefinition.from_json(
        "test",
        _write(
            tmp_path,
            [
                {
                    "mnemonic": "takeoff",
                    "defaultValue": "air",
                    "choices": ["air", "hot", "runway"],
                }
            ],
        ),
    )
    assert definition.options[0].choices == ["air", "hot", "runway"]


def test_a_default_outside_its_own_choices_is_rejected_at_load(tmp_path: Path) -> None:
    # Otherwise the dropdown opens on a value it cannot offer, and the moment the
    # user touches it the original is unreachable.
    path = _write(
        tmp_path,
        [
            {
                "mnemonic": "takeoff",
                "defaultValue": "vertical",
                "choices": ["air", "hot"],
            }
        ],
    )
    with pytest.raises(PluginOptionDependencyError, match="not one of its choices"):
        LuaPluginDefinition.from_json("test", path)


def test_every_shipped_choices_list_contains_its_own_default() -> None:
    # The guard above only fires for a plugin someone loads. Sweep the tree so a
    # bad pair cannot ship in the first place.
    checked = 0
    for path in sorted(PLUGINS.glob("**/plugin.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        for option in data.get("specificOptions") or []:
            choices = option.get("choices")
            if choices:
                assert option.get("defaultValue") in choices, path
                checked += 1
    assert (
        checked
    ), "no shipped option declares choices -- did the sweep find the files?"


def test_the_red_scramble_spawn_mode_offers_the_three_modes_its_lua_reads() -> None:
    # redscramble-config.lua branches on "hot" and "runway" and treats anything else
    # as the air spawn. Those three are the whole set; a typo in this field silently
    # became an air spawn.
    data = json.loads(
        (PLUGINS / "redscramble" / "plugin.json").read_text(encoding="utf-8-sig")
    )
    takeoff = next(o for o in data["specificOptions"] if o["mnemonic"] == "takeoff")
    assert takeoff["choices"] == ["air", "hot", "runway"]


def test_the_fac_aircraft_choices_are_types_dcs_actually_has() -> None:
    # facType is compared against u:getTypeName() in vietnamops.lua, so a mod that
    # renames its id leaves the dropdown offering an aircraft that can never be
    # found -- and nothing errors. The LvS-103 layouts lost their launchers this way.
    import game  # noqa: F401  -- the pack registration order the app uses
    import pydcs_extensions  # noqa: F401
    from dcs.planes import plane_map

    data = json.loads(
        (PLUGINS / "vietnamops" / "plugin.json").read_text(encoding="utf-8-sig")
    )
    fac = next(o for o in data["specificOptions"] if o["mnemonic"] == "facType")
    assert fac["choices"], "the FAC aircraft must stay a dropdown, not free text"
    for choice in fac["choices"]:
        assert choice in plane_map, choice
