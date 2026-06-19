"""Tests for the native DCS DTC cartridge export (builder + injector).

These cover the pure, game-independent layers: building the F/A-18C cartridge from SA data
(CAP/tanker tracks) and injecting it into a ``.miz`` archive. The game-state extraction in
``sadata.py`` needs a full ``Game`` and is exercised in-game.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import dcs.lua
import pytest

from game.missiongenerator.dtc.cartridge import (
    F18_TYPE,
    build_cartridge,
    cartridge_archive_names,
    cartridge_display_name,
)
from game.missiongenerator.dtc.injector import inject_cartridges
from game.missiongenerator.dtc.sadata import OrbitTrack, SaData
from game.settings import Settings

F16_TYPE = "F-16C_50"  # not a DTC airframe anymore; used to assert it is skipped.


def test_dtc_generation_defaults_off() -> None:
    assert Settings().generate_dtc is False


def _sample_sa() -> SaData:
    return SaData(
        orbits=[
            OrbitTrack(
                x=5000.0,
                y=6000.0,
                course_deg=90,
                length_m=18520,
                width_m=9260.0,
                name="Colt 1-1",
            ),
            OrbitTrack(
                x=7000.0,
                y=8000.0,
                course_deg=270,
                length_m=27780,
                width_m=9260.0,
                name="Texaco 1-1",
            ),
        ],
    )


def test_f18_cartridge_carries_cap_tracks() -> None:
    cartridge = build_cartridge(F18_TYPE, _sample_sa(), "Syria")

    assert cartridge["type"] == F18_TYPE
    assert cartridge["name"] == "Retribution Syria DTC_1"
    assert cartridge["data"]["terrain"] == "Syria"

    cap = cartridge["data"]["SA"]["CAP_PTS"]
    assert len(cap) == 2
    assert cap[0]["course"] == 90 and cap[0]["length"] == 18520
    assert cap[1]["x"] == 7000.0 and cap[1]["y"] == 8000.0


def test_cartridge_carries_no_threats_or_flot() -> None:
    # Threat rings draw themselves from DCS intel; the cartridge must stay CAP/tanker only.
    sa = build_cartridge(F18_TYPE, _sample_sa(), "Syria")["data"]["SA"]
    assert sa["MEZ_THRTS"] == []
    assert sa["FAOR_FLOT"]["FLOT"] == []


def test_template_partitions_preserved() -> None:
    cartridge = build_cartridge(F18_TYPE, _sample_sa(), "Syria")
    # The non-generated partitions from the ME template must survive untouched so the
    # cartridge stays structurally complete and loadable.
    assert "COMM" in cartridge["data"]
    assert "ALR67" in cartridge["data"]
    assert cartridge["data"]["WYPT"]["terrain"] == "Syria"


def test_inject_cartridges_adds_dtc_member(tmp_path: Path) -> None:
    miz = tmp_path / "test.miz"
    with zipfile.ZipFile(miz, "w") as z:
        z.writestr("mission", "mission = {}")

    cartridges = {F18_TYPE: build_cartridge(F18_TYPE, _sample_sa(), "Syria")}
    inject_cartridges(miz, cartridges)

    with zipfile.ZipFile(miz) as z:
        names = z.namelist()
        assert "mission" in names
        for filename in cartridge_archive_names(F18_TYPE):
            arcname = f"DTC/{filename}.dtc"
            assert arcname in names
            loaded = json.loads(z.read(arcname))
            assert loaded["type"] == F18_TYPE


def test_inject_cartridges_noop_when_empty(tmp_path: Path) -> None:
    miz = tmp_path / "test.miz"
    with zipfile.ZipFile(miz, "w") as z:
        z.writestr("mission", "mission = {}")
    inject_cartridges(miz, {})
    with zipfile.ZipFile(miz) as z:
        assert z.namelist() == ["mission"]


@pytest.mark.parametrize("terrain", ["Iraq", "Syria", "PersianGulf"])
def test_display_name_is_neutral_and_terrain_tagged(terrain: str) -> None:
    name = cartridge_display_name(terrain)
    assert name == f"Retribution {terrain} DTC_1"
    assert name.endswith(" DTC_1")
    # Must NOT reuse ED's default airframe-variant names: a player's personal library
    # cartridge of the same name shadows the mission cartridge and -- across maps --
    # silently fails to apply on a terrain mismatch.
    assert "FA-18C" not in name


def test_archive_name_is_canonical_type_id() -> None:
    # DCS's canonical cartridge filename is the type id.
    assert cartridge_archive_names(F18_TYPE) == ("FA-18C_hornet",)


def test_saved_games_library_file_named_after_cartridge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # DCS resolves the per-unit AutoLoad reference (the cartridge *name*) to a
    # <name>.dtc file. Writing under the aircraft-type filename left it invisible to the
    # name-keyed auto-load, so the file must be named after the cartridge.
    from game.missiongenerator.dtc import generator as gen_mod

    monkeypatch.setattr(gen_mod, "base_path", lambda: tmp_path)
    cartridge = build_cartridge(F18_TYPE, _sample_sa(), "Iraq")
    gen_mod.DtcGenerator._write_saved_games_library({F18_TYPE: cartridge})

    written = tmp_path / "DTC" / "Retribution Iraq DTC_1.dtc"
    assert written.exists()
    loaded = json.loads(written.read_text(encoding="utf-8"))
    assert loaded["name"] == "Retribution Iraq DTC_1"
    assert len(loaded["data"]["SA"]["CAP_PTS"]) == 2


def test_inject_cartridges_patches_only_hornet_units_for_autoload(
    tmp_path: Path,
) -> None:
    miz = tmp_path / "autoload.miz"
    mission = """
mission = {
  ["coalition"] = {
    ["blue"] = {
      ["country"] = {
        [1] = {
          ["plane"] = {
            ["group"] = {
              [1] = {
                ["units"] = {
                  [1] = {["type"] = "FA-18C_hornet", ["skill"] = "Client"},
                  [2] = {["type"] = "FA-18C_hornet", ["skill"] = "Client"}
                }
              },
              [2] = {
                ["units"] = {
                  [1] = {["type"] = "F-16C_50", ["skill"] = "Player"}
                }
              }
            }
          }
        }
      }
    }
  }
}
"""
    with zipfile.ZipFile(miz, "w") as z:
        z.writestr("mission", mission)

    inject_cartridges(miz, {F18_TYPE: build_cartridge(F18_TYPE, _sample_sa(), "Syria")})

    with zipfile.ZipFile(miz) as z:
        loaded = dcs.lua.loads(z.read("mission").decode("utf-8"))["mission"]

    blue = loaded["coalition"]["blue"]["country"][1]["plane"]["group"]
    hornet_units = blue[1]["units"]
    viper_unit = blue[2]["units"][1]

    expected_name = cartridge_display_name("Syria")
    for unit in hornet_units.values():
        assert unit["DTC"]["AutoLoad"] is True
        assert unit["DTC"]["Cartridges"] == {
            1: {"name": expected_name, "default": True}
        }
    # The F-16 no longer gets a DTC cartridge, so its unit must be untouched.
    assert "DTC" not in viper_unit
