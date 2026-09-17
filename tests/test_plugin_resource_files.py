"""Every file a plugin promises to ship must actually be on disk.

``otherResourceFiles`` in a plugin's ``plugin.json`` is what puts a file into the
generated ``.miz`` under ``l10n/DEFAULT/``. A plugin that *references* an asset without
*declaring* it produces a mission where the Lua asks DCS for a filename the mission does
not contain — and DCS answers with silence, not an error. Nothing in the tree catches
that: the Lua syntax gate passes, every Python test passes, the mission generates, and
the feature is simply mute in the cockpit.

That is not hypothetical. Upstream's Ops.CSAR shipped exactly this way: MOOSE hardcodes
``radioSound = "beacon.ogg"`` and transmits ``l10n/DEFAULT/beacon.ogg``, no such file
exists anywhere in this repo, and ``opscsar/plugin.json`` declared no
``otherResourceFiles`` at all — so every downed pilot's ADF homing beacon keyed a file
that was not there, while the kneeboard briefed the crew a frequency to tune. Found
2026-08-07 while writing the CSAR in-game-pass rows, after the adoption had merged.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PLUGINS = Path("resources/plugins")


def _plugin_manifests() -> list[Path]:
    return sorted(PLUGINS.glob("*/plugin.json"))


def test_there_are_plugins_to_check() -> None:
    """Guard the guard: a bad glob would make every test below vacuously pass."""
    assert len(_plugin_manifests()) > 5


@pytest.mark.parametrize("manifest", _plugin_manifests(), ids=lambda p: p.parent.name)
def test_declared_resource_files_exist(manifest: Path) -> None:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    missing = [
        name
        for name in data.get("otherResourceFiles", [])
        if not (manifest.parent / name).is_file()
    ]
    assert not missing, (
        f"{manifest.parent.name}/plugin.json declares otherResourceFiles that are not "
        f"on disk: {missing}. The generator copies these into the mission's "
        "l10n/DEFAULT/, so a missing one means the plugin asks DCS for a file the .miz "
        "does not contain — silently, with no error anywhere."
    )


@pytest.mark.parametrize("manifest", _plugin_manifests(), ids=lambda p: p.parent.name)
def test_shipped_audio_is_declared(manifest: Path) -> None:
    """The inverse: an audio file sitting in a plugin dir but never declared is dead
    weight, and usually means someone added the asset and forgot the manifest half."""
    declared = set(
        json.loads(manifest.read_text(encoding="utf-8")).get("otherResourceFiles", [])
    )
    on_disk = {
        path.name
        for path in manifest.parent.iterdir()
        if path.suffix.lower() in {".wav", ".ogg", ".mp3"}
    }
    undeclared = sorted(on_disk - declared)
    assert not undeclared, (
        f"{manifest.parent.name} carries audio that plugin.json never declares: "
        f"{undeclared}. Without an otherResourceFiles entry it is never packed into "
        "the mission, so the plugin cannot play it."
    )


def test_the_csar_survivor_beacon_ships_its_tone() -> None:
    """The specific regression: see the module docstring.

    MOOSE's default ``beacon.ogg`` is absent from this repo, so ``OpsCSAR.lua`` must
    override ``radioSound`` to something the plugin actually ships, and the manifest
    must carry it.
    """
    manifest = PLUGINS / "opscsar" / "plugin.json"
    script = PLUGINS / "opscsar" / "OpsCSAR.lua"
    declared = json.loads(manifest.read_text(encoding="utf-8")).get(
        "otherResourceFiles", []
    )
    assert declared, "opscsar declares no otherResourceFiles, so no beacon tone ships"

    lua = script.read_text(encoding="utf-8")
    assert "radioSound" in lua, (
        "OpsCSAR.lua no longer overrides radioSound, so it falls back to MOOSE's "
        "hardcoded beacon.ogg, which does not exist in this repo."
    )
    for name in declared:
        assert name in lua, (
            f"{name} is shipped but OpsCSAR.lua never names it — the override and the "
            "manifest have drifted apart."
        )
    # Match a live assignment, not a mention. The override's own comment quotes
    # `radioSound = "beacon.ogg"` to explain what upstream did and why it is wrong,
    # and that explanation is the most useful thing in the file — so skip comments.
    code = [line for line in lua.splitlines() if not line.lstrip().startswith("--")]
    reverted = [
        line.strip()
        for line in code
        if re.search(r"""radioSound\s*=\s*["']beacon\.ogg["']""", line)
    ]
    assert not reverted, (
        f"OpsCSAR.lua assigns radioSound = beacon.ogg ({reverted}), which ships with "
        "nothing in this tree, so the survivor beacon would be silent."
    )


def test_the_csar_beacon_pin_reaches_in_mission_ejections() -> None:
    """A pilot who ejects during the mission is registered by MOOSE's own
    ``CSAR:_AddCsar``, which draws the channel from its random pool and never sees
    ``beaconHz``. Test 33 put its two blue survivors on 620 and 820 kHz while the
    kneeboard briefed 260. The plugin must override the instance's draw so every
    survivor keys the pinned channel, not only the ones placed at mission start.
    """
    lua = (PLUGINS / "opscsar" / "OpsCSAR.lua").read_text(encoding="utf-8")
    code = [line for line in lua.splitlines() if not line.lstrip().startswith("--")]
    assert any(
        re.search(r"\._GenerateADFFrequency\s*=\s*function", line) for line in code
    ), (
        "OpsCSAR.lua no longer overrides _GenerateADFFrequency on the Ops.CSAR "
        "instance, so an in-mission ejection keys a random channel instead of the "
        "briefed 260 kHz."
    )
