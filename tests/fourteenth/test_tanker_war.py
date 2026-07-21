"""CI lock on the Persian Gulf "The Tanker War (1988)" campaign definition.

The will profile / phase arc degrade silently at runtime (by design), the period air OOB
substitutes silently if a mod airframe or a faction unit goes missing, and the IADS is a
YAML `ground_forces` map -- so the shipped campaign + the faction adds it depends on are
asserted here. Sibling of tests/fourteenth/test_inherent_resolve.py.
"""

import json
from pathlib import Path
from typing import Any

import yaml

CAMPAIGN = Path("resources/campaigns/tanker_war_1988.yaml")
FACTIONS = CAMPAIGN.parent.parent / "factions"


def _campaign() -> dict[str, Any]:
    return yaml.safe_load(CAMPAIGN.read_text(encoding="utf-8"))


def test_tanker_war_campaign_definition() -> None:
    data = _campaign()
    assert data["theater"] == "Persian Gulf"
    assert data["recommended_player_faction"] == "US Navy 1985"
    assert data["recommended_enemy_faction"] == "Iran 1988"
    # 1988 -- the Praying Mantis year (YAML parses the date to a date object).
    assert str(data["recommended_start_date"]).startswith("1988")

    # The naval-war identity layer + the Phase 3 coastal hunt preseed on.
    for key in (
        "mobile_missile_relocation",
        "coastal_missile_relocation",
    ):
        assert data["settings"][key] is True, key

    # The strike arm is the free Heatblur A-6E (not the A-6A/A-7E mods), which stay off.
    # The one AI-mod exception is VAQ-135's EA-6B Prowler EW det, preseeded on.
    for mod in ("a6a_intruder", "a7e_corsair2"):
        assert not data["settings"].get(mod, False), mod
    assert data["settings"]["ea6b_prowler"] is True

    # The generated gun-fort miz + its build tool ship next to the yaml.
    assert (CAMPAIGN.parent / data["miz"]).exists()
    assert (FACTIONS.parent.parent / "tools/build_tanker_war_miz.py").exists()


def test_tanker_war_period_iads_is_a_hawk_belt_plus_rapier() -> None:
    gf = _campaign()["ground_forces"]
    # Iran '88 fielded no long-range SAM, so the long+medium markers are HAWK batteries and
    # the short markers are Rapier -- the real Shah-era Iranian IADS.
    assert gf["RED L-LONG 1"] == "Hawk"
    assert gf["RED L-MED 1"] == "Hawk"
    assert gf["RED L-SHORT BANDAR 1"] == "Rapier"


def test_tanker_war_air_oob_is_period_with_the_prowler_det() -> None:
    squadrons = yaml.safe_dump(_campaign()["squadrons"])
    assert "A-6E Intruder" in squadrons  # the free Heatblur strike arm
    assert "A-6A Intruder" not in squadrons  # not the mod
    assert "A-7E Corsair II" not in squadrons  # not the mod
    assert "EA-6B Prowler" in squadrons  # VAQ-135's EW det -- the one AI mod (VSN)
    assert "Mirage-F1EQ" in squadrons  # the Iraqi Exocet-raider flavor
    # Blue's land Phantoms are the player-flyable Heatblur F-4E-45MC.
    assert "F-4E-45MC Phantom II" in squadrons


def test_tanker_war_faction_additions() -> None:
    iran = json.loads((FACTIONS / "iran_1988.json").read_text(encoding="utf-8"))
    assert "Mirage-F1EQ" in iran["aircrafts"]
    assert "Rapier" in iran["air_defense_units"]
    assert "EWR 1L13" in iran["air_defense_units"]  # P-37 forms no EWR group; 1L13 does
    usn = json.loads((FACTIONS / "usn_1985.json").read_text(encoding="utf-8"))
    assert "A-6E Intruder" in usn["aircrafts"]
    assert "KC-130" in usn["tankers"]
