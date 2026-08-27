"""Syria - Anatolian Reach laydown guards.

Israel + a US carrier and tanker hub against a Turkey-Russia bloc in 2004. The
campaign's whole shape is a 250-400 nm penetration, and three of its decisions
are load-bearing in ways nothing else in the tree would catch:

* **Akrotiri is support-only.** It is the closest blue base to seven of the nine
  Turkish fields (Incirlik 188 nm against Ramat David's 260), so a single strike
  or fighter squadron based there wins every auto-planner comparison and the
  Israeli squadrons stop flying. The long-range campaign then quietly stops
  happening with nothing in the log to say why. Verified in the first flown turn:
  Akrotiri put up one E-3A and two KC-135s and no combat aircraft.
* **The enemy faction is inline, not a name.** Retribution allows one faction per
  coalition, so the alliance is written into the yaml (the shape Fuzzle's shipped
  Operation Allied Sword uses). If it silently degrades to a named faction the
  Russian half -- and with it every long-range SAM -- disappears, because
  Turkey 2005 rosters no LORAD at all.
* **The SAM belt is period-gated by hand.** ``restrict_weapons_by_date`` gates
  weapons but never preset groups, so nothing except this test stops an S-400
  (2007) or a Buk-M2 (2008) being added to a 2004 campaign.

Validated at ``load_theater`` depth, the fork's campaign-test convention.
"""

from pathlib import Path
from typing import Any

import yaml

from game import persistency
from game.campaignloader.campaign import Campaign
from game.theater import ConflictTheater

YAML = Path("resources/campaigns/anatolian_reach.yaml")

BLUE_FIELDS = {"Hatzerim", "Ramat David", "Akrotiri"}
RED_FIELDS = {
    # the nine Turkish fields, fixed by the campaign author
    "Gulechoba",
    "Konya",
    "Diyarbakir",
    "Adiyaman",
    "Kahramanmaras",
    "Sanliurfa",
    "Incirlik",
    "Chukurova",
    "Gazipasa",
    # the two Syrian corridor gates
    "Aleppo",
    "Bassel Al-Assad",
}

#: Systems that postdate 2004 and must never appear in this campaign's presets.
ANACHRONISTIC_PRESETS = {
    "SA-21/S-400",  # service 2007
    "SA-17",  # Buk-M2, service 2008
    "SA-20B/S-300PMU-2",  # 1997 but paired with post-2004 kit; excluded by choice
    "SA-23/S-300VM",
}

#: Aircraft that must not be based at Akrotiri. Anything not in this set is a
#: combat type for the purposes of the guard below.
AKROTIRI_SUPPORT_ONLY = {
    "KC-135 Stratotanker",
    "KC-135 Stratotanker MPRS",
    "KC-130",
    "E-3A",
    "E-2C Hawkeye",
    "C-130J-30",
    "C-130J-30 Super Hercules",
}

AKROTIRI_AIRFIELD_ID = 44


def _data() -> dict[str, Any]:
    with YAML.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
        return data


def _theater(tmp_path: Path) -> tuple[Campaign, ConflictTheater]:
    persistency.setup(str(tmp_path), False, 0)
    campaign = Campaign.from_file(YAML)
    return campaign, campaign.load_theater(campaign.advanced_iads)


def test_campaign_loads_with_expected_control_points(tmp_path: Path) -> None:
    _, theater = _theater(tmp_path)
    names = {cp.name for cp in theater.controlpoints}
    assert BLUE_FIELDS | RED_FIELDS <= names


def test_ownership(tmp_path: Path) -> None:
    """Read ``starting_coalition``, never ``captured``.

    ``captured`` resolves through ``self.coalition``, which is only wired inside
    ``Game.__init__``; at ``load_theater`` depth it raises "ControlPoint not
    fully initialized".
    """
    _, theater = _theater(tmp_path)
    by_name = {cp.name: cp for cp in theater.controlpoints}
    for name in BLUE_FIELDS:
        assert by_name[name].starting_coalition.is_blue, f"{name} must start BLUE"
    for name in RED_FIELDS:
        assert by_name[name].starting_coalition.is_red, f"{name} must start RED"


def test_akrotiri_flies_no_combat_aircraft() -> None:
    """The one constraint the whole long-range design rests on.

    See the module docstring: a combat squadron here silently benches Israel.
    """
    squadrons = _data()["squadrons"][AKROTIRI_AIRFIELD_ID]
    offenders = [
        aircraft
        for entry in squadrons
        for aircraft in entry["aircraft"]
        if aircraft not in AKROTIRI_SUPPORT_ONLY
    ]
    assert not offenders, (
        "Akrotiri must stay tankers/AEW&C/lift only; found combat aircraft: %s"
        % ", ".join(sorted(set(offenders)))
    )


def test_enemy_faction_is_inline_and_carries_both_halves() -> None:
    """A named faction here would drop the Russian half and every LORAD."""
    faction = _data()["recommended_enemy_faction"]
    assert isinstance(faction, dict), (
        "the enemy faction must stay an inline definition: Retribution allows one "
        "faction per coalition, so a name cannot express the alliance"
    )
    aircraft = set(faction["aircrafts"])
    turkish = {"F-16CM Fighting Falcon (Block 50)", "F-4E Phantom II"}
    russian = {"MiG-31 Foxhound", "Su-27 Flanker-B", "Su-24M Fencer-D"}
    assert turkish <= aircraft, "the Turkish half of the alliance is missing"
    assert russian <= aircraft, "the Russian half of the alliance is missing"


def test_red_has_a_long_range_sam() -> None:
    """Turkey 2005 rosters no LORAD; without the Russian presets the deep strike
    flies through undefended airspace and the campaign has no subject."""
    presets = set(_data()["recommended_enemy_faction"]["preset_groups"])
    assert presets & {"SA-10/S-300PS", "SA-20/S-300PMU-1"}, (
        "red must field an S-300 family system, or a 250-400 nm penetration is "
        "unopposed"
    )


def test_sam_presets_are_period_correct_for_2004() -> None:
    presets = set(_data()["recommended_enemy_faction"]["preset_groups"])
    late = presets & ANACHRONISTIC_PRESETS
    assert not late, (
        "restrict_weapons_by_date does not gate SAM presets, so this is the only "
        "guard: %s postdate the 2004 setting" % ", ".join(sorted(late))
    )


def test_tanker_autoplanning_is_preseeded() -> None:
    """A host's saved settings layer UNDER campaign preseeds, so a Default.zip
    with these off would strip the tankers the whole campaign is built around."""
    settings = _data()["settings"]
    for key in (
        "autoplan_tankers_for_strike",
        "autoplan_tankers_for_oca",
        "autoplan_tankers_for_dead",
    ):
        assert settings.get(key) is True, "%s must be preseeded true" % key


def test_carrier_override_targets_the_miz_group() -> None:
    """The .miz group must stay a Stennis hull -- the loader recognises no other
    as a carrier -- while this block paints it back to a Roosevelt in game."""
    carriers = _data()["carriers"]
    assert "Naval-1" in carriers, "the carrier override must key the .miz group name"
    assert carriers["Naval-1"]["preferred_type"] == "CVN-71 Theodore Roosevelt"


def test_carrier_is_a_control_point(tmp_path: Path) -> None:
    _, theater = _theater(tmp_path)
    assert any(
        cp.name == "Naval-1" for cp in theater.controlpoints
    ), "the carrier did not register; check the .miz hull is a Stennis under CJTF Blue"
