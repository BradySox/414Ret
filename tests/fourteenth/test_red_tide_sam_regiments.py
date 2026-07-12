"""Red Tide stands its three rear S-300 hubs up as regiments (SAM-belt STANDARD).

Sperenberg, Kastrup and Schoenefeld each field THREE clustered long-range (S-300)
fire units plus a shared EWR, so range-mode advanced-IADS nets them into a
regiment that degrades gracefully under SEAD instead of dying to one HARM/one
turn (the CLAUDE.md "SAM belts: strategic -> regiment-by-authoring" standard,
applied to Red Tide 2026-07-12 under the user's feature-lock override).

Marker-level lock (mirrors test_red_tide_motorpool): a future red_tide.miz
re-save that drops the clustered battalions or the hub EWRs fails here. The
end-to-end assignment (each hub CP gets 3 long_range_sams preset locations) was
headless-verified through Campaign.load_theater at build time.
"""

from pathlib import Path

import pytest
import yaml
from dcs.mission import Mission
from dcs.vehicles import AirDefence

from game import persistency
from game.campaignloader.mizcampaignloader import MizCampaignLoader
from game.layout import LAYOUTS

MIZ = Path("resources/campaigns/red_tide.miz")
YAML = Path("resources/campaigns/red_tide.yaml")

# The single-radar S-300/SA-5 variants Red Tide's fork faction uses so each
# regiment battalion fields ONE guidance radar (SAM-belt STANDARD: revert §60's
# doubling for a regiment-modeled strategic system, scoped to Red Tide).
SINGLE_RADAR_LAYOUTS = {
    "S-300 Site (Single Radar)": "S-300 Site TR",
    "SA-5 Legacy Site (Single Radar Circle)": "Track Radar",
    "SA-5 Legacy Site (Single Radar Semicircle)": "Track Radar",
}


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


# The three rear strategic hubs and the clustered battalion / EWR marker names.
REGIMENT_HUBS = ("Sperenberg", "Kastrup", "Schonefeld")


def _red_group_names(mission: Mission) -> set[str]:
    return {
        group.name
        for coalition in mission.coalition.values()
        for country in coalition.countries.values()
        for group in country.vehicle_group
    }


def _red_marker_types(mission: Mission) -> list[str]:
    return [
        group.units[0].type
        for coalition in mission.coalition.values()
        for country in coalition.countries.values()
        for group in country.vehicle_group
    ]


def test_each_rear_hub_fields_three_lorad_battalions() -> None:
    mission = Mission()
    mission.load_file(str(MIZ))
    names = _red_group_names(mission)

    for hub in REGIMENT_HUBS:
        # the original single battalion + the two clustered additions = 3 fire units
        for extra in ("LORAD 2", "LORAD 3"):
            marker = f"Red SAM {hub} ({extra})"
            assert marker in names, f"missing clustered battalion {marker!r}"


def test_kastrup_and_schoenefeld_gain_a_shared_ewr() -> None:
    # Sperenberg already carried an EWR; the two hubs that lacked one get their
    # own so the regiment has organic early warning even in range mode.
    mission = Mission()
    mission.load_file(str(MIZ))
    names = _red_group_names(mission)
    for hub in ("Kastrup", "Schonefeld"):
        assert f"414th Red EWR {hub}" in names, f"{hub} regiment has no EWR"


def test_added_battalions_are_long_range_sam_markers() -> None:
    # The clustered additions must be LORAD marker types or the loader won't
    # expand them into S-300 fire units.
    assert AirDefence.S_300PS_5P85C_ln.id in MizCampaignLoader.LONG_RANGE_SAM_UNIT_TYPES
    assert AirDefence.x_1L13_EWR.id == MizCampaignLoader.EWR_UNIT_TYPE

    mission = Mission()
    mission.load_file(str(MIZ))
    types = _red_marker_types(mission)
    # 5 original LORAD markers + 6 added (2 per hub x 3 hubs) = 11
    lorad = sum(1 for t in types if t in MizCampaignLoader.LONG_RANGE_SAM_UNIT_TYPES)
    assert lorad >= 11, f"expected >=11 LORAD markers after clustering, found {lorad}"


def test_single_radar_variants_field_one_guidance_radar() -> None:
    # The regiment battalions must be single-radar (redundancy comes from having
    # three fire units, not doubled radars).
    for layout_name, slot in SINGLE_RADAR_LAYOUTS.items():
        layout = LAYOUTS.by_name(layout_name)
        (guid,) = [ug for ug in layout.all_unit_groups if ug.name == slot]
        assert guid.unit_count == [1], (
            f"{layout_name} '{slot}' must field ONE guidance radar, "
            f"got {guid.unit_count}"
        )


def test_single_radar_battalions_are_lean_fire_units() -> None:
    # A regiment battalion is a *fire unit*, not a stacked full site (the flown
    # 2026-07-12 finding: "all long range sams still generated full sites"):
    # ONE search radar and 4 TELs for the S-300; Tin Shield + Square Pair + 6
    # launchers for the SA-5, with no battalion-level P-19/P-14 — acquisition
    # and early warning serve the regiment via the hub's shared EWR site.
    s300 = LAYOUTS.by_name("S-300 Site (Single Radar)")
    slot_names = {ug.name for ug in s300.all_unit_groups}
    assert "S-300 Site SR2" not in slot_names, "battalion regained a second SR"
    (sr1,) = [ug for ug in s300.all_unit_groups if ug.name == "S-300 Site SR1"]
    assert sr1.unit_count == [1]
    for ln_slot in ("S-300 Site LN1", "S-300 Site LN2"):
        (ln,) = [ug for ug in s300.all_unit_groups if ug.name == ln_slot]
        assert ln.unit_count == [2], f"battalion fields 4 TELs, {ln_slot} grew"

    for variant in (
        "SA-5 Legacy Site (Single Radar Circle)",
        "SA-5 Legacy Site (Single Radar Semicircle)",
    ):
        sa5 = LAYOUTS.by_name(variant)
        sa5_slots = {ug.name for ug in sa5.all_unit_groups}
        assert "Command Post" not in sa5_slots, f"{variant} regained the P-19"
        assert "EW Radar" not in sa5_slots, f"{variant} regained a battalion P-14"
        (ln,) = [ug for ug in sa5.all_unit_groups if ug.name == "Launcher"]
        assert ln.unit_count == [6], f"{variant} launcher count drifted"


def test_base_s300_layout_keeps_its_60_doubling() -> None:
    # The scoping guardrail: reverting §60 for Red Tide must NOT touch the shared
    # S-300 Site layout, or every other campaign's lone S-300 loses its redundancy.
    base = LAYOUTS.by_name("S-300 Site")
    (tr,) = [ug for ug in base.all_unit_groups if ug.name == "S-300 Site TR"]
    assert tr.unit_count == [2], "base S-300 Site lost its §60 second radar"


def test_red_tide_recommends_the_single_radar_fork_faction() -> None:
    data = yaml.safe_load(YAML.read_text(encoding="utf-8"))
    assert data["recommended_enemy_faction"] == "Russia 1980 (Red Tide)"


# Red airfields the EWR-net markers must anchor to (nearest-CP binding).
RED_EWR_ANCHOR_FIELDS = ("Wittstock", "Haina", "Schonefeld", "Kastrup", "Sperenberg")


def test_red_ewr_net_markers_sit_in_red_territory() -> None:
    # "414th Red EWR 1" shipped planted 28 km from BLUE Frankfurt (200 km from
    # the nearest red field). The campaign loader binds a marker to the NEAREST
    # CP coalition-blind, so blue swallowed red's radar -- and since the blue
    # faction fields no EWR ForceGroup it silently never generated (the
    # repeated retribution.log "Blufor ... has no ForceGroup for EWR").
    # Relocated to Wittstock 2026-07-12; lock every red EWR marker within
    # 25 km of a red airfield so a miz edit can't strand one across the FLOT.
    mission = Mission()
    mission.load_file(str(MIZ))
    anchors = {
        a.name: a.position
        for a in mission.terrain.airport_list()
        if a.name in RED_EWR_ANCHOR_FIELDS
    }
    assert len(anchors) == len(RED_EWR_ANCHOR_FIELDS)
    for coalition in mission.coalition.values():
        for country in coalition.countries.values():
            for group in country.vehicle_group:
                if not group.name.startswith("414th Red EWR"):
                    continue
                dist_km = (
                    min(
                        group.units[0].position.distance_to_point(p)
                        for p in anchors.values()
                    )
                    / 1000
                )
                assert dist_km <= 25, (
                    f"{group.name} is {dist_km:.0f} km from the nearest red EWR "
                    "anchor field -- it will bind to the wrong (blue) CP"
                )
