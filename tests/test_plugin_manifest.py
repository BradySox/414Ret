"""Guard the Lua plugin manifest (``resources/plugins/plugins.json``).

The manifest is a hand-maintained list and plugins only load if they're in it,
so two silent failures are possible and have both bitten this fork:

* a plugin **listed** with no matching ``<name>/plugin.json`` -> load breaks;
* a plugin **dir with a plugin.json that is NOT listed** -> it never loads. This
  is exactly how **BigEye** and **LotATC** were silently dropped (#262).

Plus a denylist: plugins the 414th deliberately **retired** must not creep back
(into the manifest *or* as a loadable dir) on an upstream-``dev`` merge.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_PLUGINS = _REPO / "resources" / "plugins"
_MANIFEST = _PLUGINS / "plugins.json"

# Deliberately retired in the 414th fork (most still ship upstream, so a merge
# could re-add them). See the changelog / feature list for the why of each.
RETIRED_PLUGINS = {
    "arty",  # CG ArtySpotter fire-support script
    "artymbot",  # Mbot Call-Artillery fire-support script
    "civilian_traffic",  # MOOSE RAT -> rebuilt as Python pydcs spawns (#206)
    "dismounts",  # MIST-only infantry-dismount script
    "ewrj",  # generic fighter-pod EW jammer -> replaced by the c130j platform
    "ewrs",  # legacy MIST EWR callouts -> superseded by bigeye
    "flightcontrol",  # half-baked MOOSE FLIGHTCONTROL ATC (§13, retired)
    "scar",  # in-mission armor-hunt SCAR scenario (#266, rescue rework)
    "scramble",  # old ramp-scramble QRA -> replaced by the intercept reserve
    "skynetiads",  # Skynet IADS engine -> MANTIS is the sole engine (#246)
    "splashdamage",  # superseded by the tuned splashdamage3 build
    "splashdamage2",  # superseded by the tuned splashdamage3 build
}

# Dirs that legitimately have a plugin.json but are intentionally not loaded.
# None today; add here (with a reason) if that ever becomes deliberate.
INTENTIONALLY_UNLISTED: set[str] = set()


def _manifest() -> list[str]:
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))


def _dirs_with_plugin_json() -> set[str]:
    return {p.parent.name for p in _PLUGINS.glob("*/plugin.json")}


def test_manifest_is_a_unique_string_list() -> None:
    names = _manifest()
    assert isinstance(names, list) and all(isinstance(n, str) for n in names)
    assert len(names) == len(set(names)), "duplicate entries in plugins.json"


def test_every_listed_plugin_has_a_dir() -> None:
    dirs = _dirs_with_plugin_json()
    missing = [n for n in _manifest() if n not in dirs]
    assert (
        not missing
    ), f"plugins.json lists plugins with no <name>/plugin.json: {missing}"


def test_no_plugin_dir_is_silently_unlisted() -> None:
    orphans = sorted(
        _dirs_with_plugin_json() - set(_manifest()) - INTENTIONALLY_UNLISTED
    )
    assert not orphans, (
        "plugin dir(s) have a plugin.json but are NOT in plugins.json, so they "
        f"never load (this is how BigEye/LotATC were silently dropped): {orphans}"
    )


@pytest.mark.parametrize("retired", sorted(RETIRED_PLUGINS))
def test_retired_plugin_stays_gone(retired: str) -> None:
    assert (
        retired not in _manifest()
    ), f"retired plugin {retired!r} re-added to plugins.json"
    assert not (
        _PLUGINS / retired / "plugin.json"
    ).exists(), f"retired plugin dir {retired!r} reappeared"
