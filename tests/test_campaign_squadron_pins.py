"""Campaign squadron pins that must stay fieldable by the faction they run against.

``DefaultSquadronAssigner`` resolves an ``aircraft:`` entry as a squadron-preset name
first, then as an ``AircraftType``. If the string names a real aircraft that the
coalition's faction does not roster, it returns **None with no log line**
(``defaultsquadronassigner.py``, the ``aircraft not in ... all_aircrafts`` branch) and
the authored det is quietly replaced by whatever generic airframe wins the task. The
campaign still loads, still plays, and the air wing the author wrote is simply not there.

Two batches of that shipped, both found by the 2026-08-08 audit:

* Four campaigns pinned ``A-6E Intruder`` against ``USA 2005`` / ``NATO OIF``. The
  Intruder left USN service in 1997, so those factions never rostered it -- the fork's
  #655 sweep (S-3B to sea control, the A-6 takes strike and carrier tanking) converted
  the campaigns without checking the modern rosters. Re-pointed to the Hornet those
  wings already fly, not back to upstream's S-3B, which is sea-control-only here and
  has no Strike/DEAD/BAI capability at all.
* Two campaigns pinned ``F-14A Tomcat (Block 135-GR Late)`` against ``Iran 2015``,
  which rosters only the Export block. Upstream #830 fixed both halves; a whole-file
  CRLF merge conflict took the campaign halves and kept the faction one.

This is deliberately a NARROW lock on the known cases rather than a sweep over every
campaign. A general rule was tried and rejected: many campaigns leave
``recommended_enemy_faction`` unset or are meant to be played against a faction the
player picks, so "pin must be in a recommended faction" produced 172 hits across 2149
pins, essentially all of them red aircraft in campaigns with no declared enemy. Judging
those needs per-control-point ownership, which the yaml alone does not carry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from game import persistency
from game.factions.faction import Faction

CAMPAIGNS = Path("resources/campaigns")
FACTIONS = Path("resources/factions")


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # Unit-type loading reads user overrides from the DCS saved-game folder, which is
    # only configured once the app boots. Point it at an empty temp dir so loading
    # falls back to the bundled resources/ data (same fixture as
    # tests/fourteenth/test_faction_mod_presets.py).
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


#: (campaign yaml, faction json, aircraft that must be pinned and rostered,
#:  aircraft that must NOT appear anywhere in the campaign's pins)
PINS: list[tuple[str, str, str, str]] = [
    # The #655 A-6E over-application. All four are modern carrier wings.
    (
        "IntotheHornetsNest.yaml",
        "usa_2005.json",
        "F/A-18C Hornet (Lot 20)",
        "A-6E Intruder",
    ),
    (
        "grabthars_hammer.yaml",
        "usa_2005.json",
        "F/A-18C Hornet (Lot 20)",
        "A-6E Intruder",
    ),
    (
        "operation_vectrons_claw.yaml",
        "usa_2005.json",
        "F/A-18C Hornet (Lot 20)",
        "A-6E Intruder",
    ),
    (
        "syria_TheLongRoadToH3.yaml",
        "NATO_OIF.json",
        "F/A-18C Hornet (Lot 20)",
        "A-6E Intruder",
    ),
    # Upstream #830, lost in a CRLF whole-file merge.
    (
        "scenic_route.yaml",
        "iran_2015.json",
        "F-14A Tomcat (Block 95-GR Export)",
        "F-14A Tomcat (Block 135-GR Late)",
    ),
    (
        "WRL_Operation_Noisy_Cricket_Redux.yaml",
        "iran_2015.json",
        "F-14A Tomcat (Block 95-GR Export)",
        "F-14A Tomcat (Block 135-GR Late)",
    ),
]


def _load_faction(filename: str) -> Faction:
    with (FACTIONS / filename).open(encoding="utf-8") as f:
        return Faction.from_dict(json.load(f))


def _pinned_aircraft(campaign: str) -> list[str]:
    """Every string in every squadron ``aircraft:`` list in the campaign."""
    data: Any = yaml.safe_load((CAMPAIGNS / campaign).read_text(encoding="utf-8"))
    found: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "aircraft" and isinstance(value, list):
                    found.extend(name for name in value if isinstance(name, str))
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data.get("squadrons") if isinstance(data, dict) else None)
    return found


@pytest.mark.parametrize(
    "campaign,faction_file,expected,forbidden",
    PINS,
    ids=[p[0].removesuffix(".yaml") for p in PINS],
)
def test_the_repointed_pin_is_present_and_rostered(
    campaign: str, faction_file: str, expected: str, forbidden: str
) -> None:
    pins = _pinned_aircraft(campaign)
    assert pins, f"{campaign} declares no squadron aircraft pins"

    # The airframe that replaced the broken pin is actually pinned...
    assert expected in pins, f"{campaign} no longer pins {expected!r}"

    # ...and the faction it runs against can actually field it. This is the assertion
    # that would have caught both batches: the pin resolves to a real AircraftType, so
    # the assigner reaches the roster check and silently returns None.
    rostered = {str(a) for a in _load_faction(faction_file).all_aircrafts}
    assert expected in rostered, (
        f"{campaign} pins {expected!r} but {faction_file} does not roster it -- "
        "the squadron will silently fall back to a generic airframe"
    )


@pytest.mark.parametrize(
    "campaign,faction_file,expected,forbidden",
    PINS,
    ids=[p[0].removesuffix(".yaml") for p in PINS],
)
def test_the_broken_pin_is_gone(
    campaign: str, faction_file: str, expected: str, forbidden: str
) -> None:
    pins = _pinned_aircraft(campaign)
    assert (
        forbidden not in pins
    ), f"{campaign} pins {forbidden!r} again, which {faction_file} does not roster"


def test_the_a6e_tanker_pins_are_left_alone() -> None:
    """Only the *Intruder* was unrosterable; the Tanker variant is real and stays.

    Two of these campaigns also pin ``A-6E Tanker`` for Refueling. It IS in both modern
    rosters, so the #655 carrier-tanking half of the change was correct and must not be
    swept up by a future pass at the Intruder.
    """
    for campaign, faction_file in (
        ("IntotheHornetsNest.yaml", "usa_2005.json"),
        ("syria_TheLongRoadToH3.yaml", "NATO_OIF.json"),
    ):
        assert "A-6E Tanker" in _pinned_aircraft(campaign), campaign
        rostered = {str(a) for a in _load_faction(faction_file).all_aircrafts}
        assert "A-6E Tanker" in rostered, faction_file


def test_iran_1988_keeps_the_late_block_tomcat() -> None:
    """The 135-GR Late is correct for 1988 -- do not sweep the rename fork-wide.

    ``tanker_war_1988.yaml`` pins it against Iran 1988, which rosters it. Only the two
    *Iran 2015* campaigns were wrong.
    """
    assert "F-14A Tomcat (Block 135-GR Late)" in _pinned_aircraft(
        "tanker_war_1988.yaml"
    )
    rostered = {str(a) for a in _load_faction("iran_1988.json").all_aircrafts}
    assert "F-14A Tomcat (Block 135-GR Late)" in rostered
