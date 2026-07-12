"""The Red Tide fork faction stays honest to its July 1988 date.

Two locks from the 2026-07-12 roster audit (user request, feature-lock
override):

* **Era ceiling** — no unit in ``Russia 1980 (Red Tide)`` may carry an
  ``introduced`` year after the campaign date. The audit found the shipped
  roster clean; this keeps a future edit from slipping a 1990s system into
  a Cold-War-hot campaign. Units whose yamls carry no date are skipped (they
  were hand-audited era-safe: A-50 '84, IL-78M '87, SA-8 '71, ...).

* **The ARM-intercept point defense exists** — the SA-15 Tor (and the SA-19
  Tunguska) were added so the S-300 regiments' point-defense escorts can
  actually engage an inbound HARM (the MANTIS SHORAD link, checklist G30).
  Without the Tor, red's SHORAD roster is IR-only (SA-9/13) + the Osa, none
  of which DCS tasks against missiles -- the G30 mechanic would be a no-op
  for red. A roster edit that drops the Tor fails here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

FACTION = Path("resources/factions/russia_1980_red_tide.json")
UNITS_DIR = Path("resources/units")
CAMPAIGN_YEAR = 1988

UNIT_LISTS = (
    "aircrafts",
    "awacs",
    "tankers",
    "frontline_units",
    "artillery_units",
    "logistics_units",
    "infantry_units",
    "naval_units",
    "air_defense_units",
    "missiles",
)


def _variant_intro_years() -> dict[str, int]:
    years: dict[str, int] = {}
    for yml in UNITS_DIR.rglob("*.yaml"):
        try:
            data = yaml.safe_load(yml.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue
        intro = data.get("introduced")
        if not isinstance(intro, int):
            continue
        for variant in data.get("variants") or {}:
            years[variant] = intro
    return years


def _faction() -> dict[str, Any]:
    return json.loads(FACTION.read_text(encoding="utf-8"))


def test_no_red_tide_unit_postdates_the_campaign() -> None:
    years = _variant_intro_years()
    faction = _faction()
    violations = [
        f"{lst}: {name} (introduced {years[name]})"
        for lst in UNIT_LISTS
        for name in faction.get(lst, [])
        if name in years and years[name] > CAMPAIGN_YEAR
    ]
    assert (
        not violations
    ), f"Red Tide is July {CAMPAIGN_YEAR}; era-violating units: {violations}"


def test_red_tide_fields_the_arm_intercept_point_defense() -> None:
    air_defense = _faction()["air_defense_units"]
    assert "SA-15 Tor" in air_defense, (
        "the Tor is red's only SHORAD DCS tasks against missiles - without it "
        "the MANTIS SHORAD link (G30) cannot intercept HARMs on Red Tide"
    )
    assert "SA-19 Grison (2K22 Tunguska)" in air_defense
