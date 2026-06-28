"""Guards for the Vietnam faction + Khe Sanh campaign content pass (#281).

Three invariants that nothing in CI checked before -- each was only hand-validated
when the content landed, exactly the kind of thing the next cold pass re-derives:

1. **Every unit string in a Vietnam-era faction resolves.** The faction loader
   *silently drops* an unresolved name (see ``Faction._resolve_named_set`` and
   ``test_unknown_aircraft_name_skipped_not_whole_faction``), so a typo'd VWV /
   ``[CH]`` unit vanishes at runtime with only a log line -- JSON parsing alone
   won't catch it. This walks every roster the loader resolves and fails on the
   first drop.

2. **Every carrier-based Khe Sanh squadron flies a carrier-capable airframe.** The
   current DCS F-4 module is land-based only, so the campaign deliberately flies
   the F-8E Crusader off the carrier. This loads the real ``Campaign.from_file``
   new-game path (``MizCampaignLoader`` builds the theater) and asserts the
   engine's own ``ControlPoint.can_operate`` for each carrier squadron's aircraft.

3. **Campaigns whose factions field ``[CH]`` Russian-pack armor enable
   ``russianmilitaryassetspack``.** Without it, ``apply_mod_settings`` strips the
   armor and the siege loses its tanks -- again silently. The dependency is proven
   by diffing the faction with vs. without the pack, so there is no hardcoded id
   list to drift from ``Faction.apply_mod_settings``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional

import pytest
import yaml

from game import persistency
from game.campaignloader.campaign import Campaign
from game.campaignloader.campaignairwingconfig import CampaignAirWingConfig
from game.dcs.aircrafttype import AircraftType
from game.dcs.groundunittype import GroundUnitType
from game.dcs.shipunittype import ShipUnitType
from game.factions.faction import Faction
from game.theater import ConflictTheater
from game.theater.start_generator import ModSettings

_REPO = Path(__file__).resolve().parents[1]
_FACTIONS = _REPO / "resources" / "factions"
_CAMPAIGNS = _REPO / "resources" / "campaigns"

# Faction-roster keys -> the resolver ``Faction.from_dict`` uses for each. These
# are exactly the rosters that go through the silent-drop path.
_ROSTER_RESOLVERS: dict[str, Callable[[str], Any]] = {
    "aircrafts": AircraftType.named,
    "awacs": AircraftType.named,
    "tankers": AircraftType.named,
    "frontline_units": GroundUnitType.named,
    "artillery_units": GroundUnitType.named,
    "infantry_units": GroundUnitType.named,
    "logistics_units": GroundUnitType.named,
    "air_defense_units": GroundUnitType.named,
    "missiles": GroundUnitType.named,
    "naval_units": ShipUnitType.named,
}

# A faction file is "Vietnam-era content" if its name carries one of these tags;
# this is the set the #281 content pass touched.
_VIETNAM_TAGS = ("vietnam", "vietcong", "nva")
_VIETNAM_FACTION_FILES = [
    path
    for path in sorted(_FACTIONS.glob("*.json"))
    if any(tag in path.name.lower() for tag in _VIETNAM_TAGS)
]

# Campaigns that field ``[CH]`` Russian-pack armor and so must enable the pack.
_CH_ARMOR_CAMPAIGNS = [
    "khe_sanh_niagara.yaml",
    "1968_Yankee_Station.yaml",
    "operation_velvet_thunder.yaml",
]


@pytest.fixture(scope="session", autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # Unit-type loading reads the DCS saved-game folder; point it at an empty temp
    # dir so the resolvers work headless (mirrors tests/test_factions.py).
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


@pytest.fixture(scope="module")
def khe_sanh() -> tuple[Campaign, ConflictTheater, CampaignAirWingConfig]:
    """The Khe Sanh campaign loaded through the real new-game path, once."""
    campaign = Campaign.from_file(_CAMPAIGNS / "khe_sanh_niagara.yaml")
    theater = campaign.load_theater(campaign.advanced_iads)
    air_wing = campaign.load_air_wing_config(theater)
    return campaign, theater, air_wing


def _faction_json_by_name(name: str) -> Optional[dict[str, Any]]:
    for path in sorted(_FACTIONS.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("name") == name:
            return data
    return None


def _unit_ids(faction: Faction) -> set[str]:
    ids = {unit.dcs_unit_type.id for unit in faction.accessible_units}
    ids |= {aircraft.dcs_unit_type.id for aircraft in faction.all_aircrafts}
    return ids


def _russian_pack_dependent_ids(faction_data: dict[str, Any]) -> set[str]:
    """Unit ids the faction fields only when the Russian assets pack is enabled.

    Computed by diffing the faction with the pack on vs. off. Only that one mod
    flag differs between the two, so the diff is exactly the pack-gated units --
    no hardcoded id list to drift from ``Faction.apply_mod_settings``. (The default
    ``ModSettings()`` state is restored, so this leaves no session-wide pydcs
    mutation behind.)
    """
    with_pack = Faction.from_dict(faction_data)
    with_pack.apply_mod_settings(ModSettings(russianmilitaryassetspack=True))
    without_pack = Faction.from_dict(faction_data)
    without_pack.apply_mod_settings(ModSettings(russianmilitaryassetspack=False))
    return _unit_ids(with_pack) - _unit_ids(without_pack)


def test_vietnam_faction_file_set_is_non_empty() -> None:
    # If the glob/tag filter ever stops matching, the per-file parametrization
    # below would silently collect zero cases and vacuously pass.
    assert (
        _VIETNAM_FACTION_FILES
    ), "No Vietnam faction files matched; the guard is dead."


@pytest.mark.parametrize("faction_file", _VIETNAM_FACTION_FILES, ids=lambda p: p.name)
def test_vietnam_faction_units_all_resolve(faction_file: Path) -> None:
    data = json.loads(faction_file.read_text(encoding="utf-8"))
    dropped: list[str] = []
    for key, resolver in _ROSTER_RESOLVERS.items():
        for name in data.get(key, []):
            try:
                resolver(name)
            except KeyError:
                dropped.append(f"{key}: {name!r}")
    assert not dropped, (
        f"{faction_file.name} declares unit strings the loader can't resolve, so "
        f"they are silently dropped at runtime: {dropped}. Fix the name or re-ship "
        "the mod that provides the unit."
    )


@pytest.mark.parametrize("campaign_file", _CH_ARMOR_CAMPAIGNS)
def test_vietnam_campaigns_tagged_era_vietnam(campaign_file: str) -> None:
    # The New Game "Vietnam" shell filters the campaign list by this tag; an untagged
    # Vietnam campaign would silently vanish from the shell (P0 of the Vietnam mode).
    campaign = Campaign.from_file(_CAMPAIGNS / campaign_file)
    assert campaign.era == "vietnam", (
        f"{campaign_file} must declare 'era: vietnam' so the New Game Vietnam shell "
        "lists it. See docs/dev/design/414th-vietnam-retribution-notes.md."
    )


# P2 era pre-seed: the campaign settings: block that auto-applies (on campaign-select,
# via QNewGameSettings._load_campaign_settings -> Settings.deserialize_state_dict) to turn
# the Vietnam Ops mechanics + era weapon gating on. Per-campaign because they differ
# (Khe Sanh is inland -> no naval gunfire; Yankee Station is coastal -> yes).
_ERA_PRESEED: dict[str, dict[str, bool]] = {
    "khe_sanh_niagara.yaml": {
        "vietnam_arc_light": True,
        "vietnam_flak_gauntlet": True,
        "vietnam_naval_gunfire": False,  # inland
        "restrict_weapons_by_date": True,
    },
    "1968_Yankee_Station.yaml": {
        "vietnam_arc_light": True,
        "vietnam_flak_gauntlet": True,
        "vietnam_naval_gunfire": True,  # coastal
        "restrict_weapons_by_date": True,
    },
    "operation_velvet_thunder.yaml": {
        "vietnam_arc_light": True,
        "vietnam_flak_gauntlet": True,
        "vietnam_naval_gunfire": False,
        "restrict_weapons_by_date": True,
    },
}


@pytest.mark.parametrize("campaign_file", list(_ERA_PRESEED))
def test_vietnam_campaign_era_preseed_applies(campaign_file: str) -> None:
    from game.settings import Settings

    campaign = Campaign.from_file(_CAMPAIGNS / campaign_file)
    # Mirror the wizard: deserialize the campaign settings: block onto a default Settings.
    settings = Settings()
    settings.__dict__.update(Settings.deserialize_state_dict(campaign.settings))
    for field, expected in _ERA_PRESEED[campaign_file].items():
        assert getattr(settings, field) == expected, (
            f"{campaign_file}: era pre-seed '{field}' should be {expected} after the "
            "campaign settings: block is applied in the New Game wizard."
        )


@pytest.mark.parametrize(
    "faction_file",
    [
        "USA 1970 Vietnam War.json",
        "vietnam_1970.json",
        "nva_1970.json",
        "usa_1965.json",
    ],
)
def test_vietnam_factions_load_vietnam_doctrine(faction_file: str) -> None:
    # End-to-end: the faction loader maps the JSON "vietnam" string to VIETNAM_DOCTRINE
    # (P1 of the Vietnam Retribution mode), not the COLDWAR default.
    from game.data.doctrine import VIETNAM_DOCTRINE

    data = json.loads((_FACTIONS / faction_file).read_text(encoding="utf-8"))
    faction = Faction.from_dict(data)
    assert faction.doctrine is VIETNAM_DOCTRINE


def test_khe_sanh_carrier_squadrons_carrier_capable(
    khe_sanh: tuple[Campaign, ConflictTheater, CampaignAirWingConfig],
) -> None:
    _campaign, theater, air_wing = khe_sanh
    carriers = set(theater.find_carriers()) | set(theater.find_lhas())

    checked = 0
    offenders: list[str] = []
    for control_point, squadrons in air_wing.by_location.items():
        if control_point not in carriers:
            continue
        for squadron in squadrons:
            for aircraft_name in squadron.aircraft:
                aircraft = AircraftType.named(aircraft_name)
                checked += 1
                # can_operate is the engine's own rule (carrier_capable, or
                # lha_capable for an Essex-class deck).
                if not control_point.can_operate(aircraft):
                    offenders.append(f"{control_point.name}: {aircraft_name}")

    assert checked, (
        "No carrier squadrons were checked -- the carrier topology or air-wing "
        "config regressed (expected a Naval carrier with squadrons)."
    )
    assert not offenders, (
        f"Carrier squadrons fly airframes that cannot operate from the carrier: "
        f"{offenders}. The current DCS F-4 is land-based only -- use a "
        "carrier-capable type (e.g. F-8E Crusader)."
    )


def test_khe_sanh_control_point_strengths_applied(
    khe_sanh: tuple[Campaign, ConflictTheater, CampaignAirWingConfig],
) -> None:
    """``control_point_strengths`` from the campaign YAML override each named CP's starting
    ground strength on the new-game path. Khe Sanh sets a depleted Kutaisi so the siege fronts
    start near the perimeter -- the front between two enemy CPs sits at
    ``strength_pct * route_length`` from the blue CP, so without this Kutaisi would start at
    full strength and the fronts would sit at the route midpoint (far out)."""
    _campaign, theater, _air_wing = khe_sanh
    data = yaml.safe_load(
        (_CAMPAIGNS / "khe_sanh_niagara.yaml").read_text(encoding="utf-8")
    )
    strengths = data.get("control_point_strengths", {})
    assert strengths, "Khe Sanh should set control_point_strengths (besieged Kutaisi)."

    by_name = {cp.name: cp for cp in theater.controlpoints}
    for name, value in strengths.items():
        assert name in by_name, f"control_point_strengths names unknown CP {name!r}"
        assert by_name[name].base.strength == pytest.approx(float(value))
    # The whole point: Kutaisi is depleted (< full strength) so the fronts pull in close.
    assert by_name["Kutaisi"].base.strength < 1.0


@pytest.mark.parametrize("campaign_file", _CH_ARMOR_CAMPAIGNS)
def test_ch_armor_campaigns_enable_russian_pack(campaign_file: str) -> None:
    campaign = Campaign.from_file(_CAMPAIGNS / campaign_file)
    faction_names = [
        campaign.recommended_player_faction,
        campaign.recommended_enemy_faction,
    ]

    dependent: dict[str, list[str]] = {}
    for faction_name in faction_names:
        data = _faction_json_by_name(faction_name)
        if data is None:
            continue
        pack_units = _russian_pack_dependent_ids(data)
        if pack_units:
            dependent[faction_name] = sorted(pack_units)

    if not dependent:
        pytest.skip(
            f"{campaign_file} fields no Russian-pack units; the setting is moot."
        )

    assert campaign.settings.get("russianmilitaryassetspack") is True, (
        f"{campaign_file} fields [CH] Russian-pack units {dependent} but does not "
        "enable 'russianmilitaryassetspack' in settings -- apply_mod_settings will "
        "silently strip that armor. Add 'russianmilitaryassetspack: true'."
    )
