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
from game.ato.flighttype import FlightType
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
    "steel_tiger.yaml",
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


def test_matches_era_drives_the_vietnam_card_filter() -> None:
    # The New Game "Vietnam" card lists only era: vietnam campaigns; the default front
    # door (era=None) lists everything. This predicate is what QCampaignList filters on.
    khe = Campaign.from_file(_CAMPAIGNS / "khe_sanh_niagara.yaml")
    assert khe.matches_era("vietnam")  # shown by the Vietnam card
    assert khe.matches_era(None)  # and by the default (no filter)
    assert not khe.matches_era("ww2")  # but not by some other era shell

    # A non-Vietnam campaign is hidden by the Vietnam card, shown by the default.
    non_vietnam = next((c for c in Campaign.load_each() if c.era != "vietnam"), None)
    assert non_vietnam is not None, "expected at least one non-Vietnam campaign"
    assert not non_vietnam.matches_era("vietnam")
    assert non_vietnam.matches_era(None)


# P2 era pre-seed: the campaign settings: block that auto-applies (on campaign-select,
# via QNewGameSettings._load_campaign_settings -> Settings.deserialize_state_dict) to turn
# the Vietnam Ops mechanics + era weapon gating on. Per-campaign because they differ
# (Khe Sanh is inland -> no naval gunfire; Yankee Station is coastal -> yes).
_ERA_PRESEED: dict[str, dict[str, bool]] = {
    "khe_sanh_niagara.yaml": {
        "vietnam_arc_light": True,
        "vietnam_flak_gauntlet": True,
        "vietnam_naval_gunfire": False,  # inland
        "vietnam_convoy_interdiction": True,
        "vietnam_airbase_harassment": True,  # the besieged-strip story
        "vietnam_super_gaggle": True,  # the cut-off-garrison resupply story
        "vietnam_fac_marking": True,  # the whole battlefield suite is on
        "vietnam_snake_and_nape": True,
        "vietnam_political_will": True,
        "vietnam_static_front": True,
        "restrict_weapons_by_date": True,
    },
    "1968_Yankee_Station.yaml": {
        "vietnam_arc_light": True,
        "vietnam_flak_gauntlet": True,
        "vietnam_naval_gunfire": True,  # coastal
        "vietnam_convoy_interdiction": True,  # the campaign's own Ho Chi Minh Trail
        "vietnam_airbase_harassment": True,
        "vietnam_super_gaggle": True,
        "vietnam_fac_marking": True,
        "vietnam_snake_and_nape": True,
        "vietnam_political_will": True,
        "vietnam_static_front": True,
        "restrict_weapons_by_date": True,
    },
    "operation_velvet_thunder.yaml": {
        "vietnam_arc_light": True,
        "vietnam_flak_gauntlet": True,
        "vietnam_naval_gunfire": False,
        "vietnam_convoy_interdiction": True,
        "vietnam_airbase_harassment": True,
        "vietnam_super_gaggle": True,
        "vietnam_fac_marking": True,
        "vietnam_snake_and_nape": True,
        "vietnam_political_will": True,
        "vietnam_static_front": True,
        "restrict_weapons_by_date": True,
    },
    "steel_tiger.yaml": {
        "vietnam_arc_light": True,
        "vietnam_flak_gauntlet": True,
        "vietnam_naval_gunfire": True,  # shares the coastal Yankee Station laydown
        "vietnam_convoy_interdiction": True,  # the campaign's centrepiece
        "vietnam_airbase_harassment": True,
        "vietnam_super_gaggle": True,
        "vietnam_fac_marking": True,
        "vietnam_snake_and_nape": True,
        "vietnam_political_will": True,
        "vietnam_static_front": True,
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


# The Vietnam theaters are geometrically compressed, so the upstream 80/70 NM AEW&C/
# tanker standoff overshoots: on a small map it stands the orbits ~150 km behind the
# front, sprawling support (and its escorts) toward the map edge. These campaigns pin a
# tighter buffer (orbits ~75-90 km back, still clear of the threat). Per-campaign by
# design -- large maps keep the wide defaults -- so guard both ends.
_COMPRESSED_SUPPORT_BUFFERS = [
    "khe_sanh_niagara.yaml",
    "1968_Yankee_Station.yaml",
    "operation_velvet_thunder.yaml",
    "steel_tiger.yaml",
]


@pytest.mark.parametrize("campaign_file", _COMPRESSED_SUPPORT_BUFFERS)
def test_vietnam_campaign_tightens_support_orbits(campaign_file: str) -> None:
    from game.settings import Settings

    campaign = Campaign.from_file(_CAMPAIGNS / campaign_file)
    settings = Settings()
    settings.__dict__.update(Settings.deserialize_state_dict(campaign.settings))
    assert settings.aewc_threat_buffer_min_distance == 25, (
        f"{campaign_file}: AEW&C buffer should be 25 NM so the orbit hugs the "
        "compressed front instead of sprawling to the map edge."
    )
    assert (
        settings.tanker_threat_buffer_min_distance == 20
    ), f"{campaign_file}: tanker buffer should be 20 NM for the compressed front."
    # Large/other campaigns are untouched: the defaults stay wide.
    assert Settings().aewc_threat_buffer_min_distance == 80
    assert Settings().tanker_threat_buffer_min_distance == 70


# The Vietnam air war is a GCI-ambush war: Hanoi's air arm (VIETNAM_AIR_DEFENSE_DOCTRINE)
# intercepts, it does not fly fast-mover interdiction/strike. A 2026-07-02 played Yankee
# Station turn 1 showed red flying BAI/Strike/Armed-Recon/Air-Assault packages because
# several red MiG squadrons were authored with a BAI (or air-to-ground-secondary) role,
# which auto-assigned them to the offensive task set. These two guards lock the fix:
#   1. red fighter squadrons carry NO air-to-ground auto-assignment (defensive only), and
#   2. the campaigns hold more MiGs on QRA hot-alert (opfor reserve 4, not the global 2)
#      so they scramble reactively instead of standing forward BARCAP orbits.
# operation_velvet_thunder is included -- it carried the same anachronism (a primary-BAI
# MiG-21 at Saipan + air-to-ground MiG escorts).
_GCI_AMBUSH_CAMPAIGNS = [
    "1968_Yankee_Station.yaml",
    "steel_tiger.yaml",
    "khe_sanh_niagara.yaml",
    "red_flag_81_2.yaml",
    "operation_velvet_thunder.yaml",
]

# The auto-assignable tasks that mean "this squadron flies offense" -- exactly what a
# GCI-only ambush force must never be handed.
_OFFENSIVE_TASKS = {
    FlightType.BAI,
    FlightType.STRIKE,
    FlightType.ARMED_RECON,
    FlightType.CAS,
    FlightType.OCA_RUNWAY,
    FlightType.OCA_AIRCRAFT,
    FlightType.AIR_ASSAULT,
    FlightType.SCAR,
}

# Fighter airframes that make a red squadron an interceptor (not a helo/transport).
_RED_FIGHTER_MARKERS = ("MiG", "F-5", "Su-")


@pytest.mark.parametrize("campaign_file", _GCI_AMBUSH_CAMPAIGNS)
def test_vietnam_red_fighters_are_defensively_tasked(campaign_file: str) -> None:
    from game.theater.player import Player

    campaign = Campaign.from_file(_CAMPAIGNS / campaign_file)
    theater = campaign.load_theater(campaign.advanced_iads)
    red_cps = {
        cp for cp in theater.controlpoints if cp.starting_coalition == Player.RED
    }
    air_wing = campaign.load_air_wing_config(theater)

    checked = 0
    offenders: list[str] = []
    for control_point, squadron_configs in air_wing.by_location.items():
        if control_point not in red_cps:
            continue  # BLUE is the offensive side -- only Hanoi must be GCI-only.
        for squadron_config in squadron_configs:
            aircraft = list(squadron_config.aircraft)
            if not any(
                marker in a for a in aircraft for marker in _RED_FIGHTER_MARKERS
            ):
                continue  # helos/transports aren't the ambush force.
            checked += 1
            bad = squadron_config.auto_assignable & _OFFENSIVE_TASKS
            if bad:
                offenders.append(
                    f"{control_point.name} {aircraft}: {sorted(t.value for t in bad)}"
                )
    assert checked, (
        f"{campaign_file}: no red fighter squadrons found -- the red OOB or the "
        "control-point keys regressed."
    )
    assert not offenders, (
        f"{campaign_file}: red MiG/aggressor squadrons are auto-assignable to offensive "
        f"tasks -- Hanoi flies GCI-ambush (MiGCAP), not interdiction. Give them a BARCAP "
        f"primary + air-to-air secondary. Offenders: {offenders}"
    )


@pytest.mark.parametrize("campaign_file", _GCI_AMBUSH_CAMPAIGNS)
def test_vietnam_campaign_seeds_opfor_qra_reserve(campaign_file: str) -> None:
    from game.settings import Settings

    campaign = Campaign.from_file(_CAMPAIGNS / campaign_file)
    settings = Settings()
    settings.__dict__.update(Settings.deserialize_state_dict(campaign.settings))
    assert settings.opfor_default_qra_reserve == 4, (
        f"{campaign_file}: OPFOR should seed 4 QRA airframes per BARCAP-capable squadron "
        "so red holds MiGs on reactive hot-alert instead of standing forward BARCAP orbits."
    )
    # OWNFOR is deliberately left on the global default (0) -- this posture is red-only.
    assert settings.ownfor_default_qra_reserve == 0, (
        f"{campaign_file}: OWNFOR QRA reserve should stay at the default; the GCI-ambush "
        "posture is red-only."
    )


@pytest.mark.parametrize(
    ("faction_file", "doctrine_name"),
    [
        # BLUE flies the offensive doctrine; Hanoi's factions fly the air-defense
        # split (no Alpha Strike fan / escort reserve / forced strike escorts).
        ("USA 1970 Vietnam War.json", "vietnam"),
        ("usa_1965.json", "vietnam"),
        ("vietnam_1970.json", "vietnam_air_defense"),
        ("nva_1970.json", "vietnam_air_defense"),
    ],
)
def test_vietnam_factions_load_vietnam_doctrine(
    faction_file: str, doctrine_name: str
) -> None:
    # End-to-end: the faction loader maps the JSON doctrine string to the right
    # Vietnam doctrine (P1 + the red split), not the COLDWAR/MODERN default.
    from game.data.doctrine import VIETNAM_AIR_DEFENSE_DOCTRINE, VIETNAM_DOCTRINE

    expected = {
        "vietnam": VIETNAM_DOCTRINE,
        "vietnam_air_defense": VIETNAM_AIR_DEFENSE_DOCTRINE,
    }[doctrine_name]
    data = json.loads((_FACTIONS / faction_file).read_text(encoding="utf-8"))
    faction = Faction.from_dict(data)
    assert faction.doctrine is expected


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


@pytest.fixture(scope="module")
def steel_tiger() -> tuple[Campaign, ConflictTheater, CampaignAirWingConfig]:
    """The Steel Tiger campaign loaded through the real new-game path, once.

    Steel Tiger reuses the 1968 Yankee Station .miz with an interdiction-tilted OOB, so
    this is the guard that its hand-authored squadron block actually resolves against that
    theater (every airframe loads, every control-point key exists).
    """
    campaign = Campaign.from_file(_CAMPAIGNS / "steel_tiger.yaml")
    theater = campaign.load_theater(campaign.advanced_iads)
    air_wing = campaign.load_air_wing_config(theater)
    return campaign, theater, air_wing


def test_steel_tiger_loads_and_populates_bases(
    steel_tiger: tuple[Campaign, ConflictTheater, CampaignAirWingConfig],
) -> None:
    # The real regression guard: the campaign loads through the new-game path without
    # raising (a bad .miz reference or an invalid task string in SquadronConfig.from_data
    # would raise on the fixture's load), and the interdiction OOB lands squadrons across
    # many bases. Note a campaign squadron's `aircraft` entry may be a *squadron-name* alias
    # (e.g. "VAW-122", "43d Strategic Wing"), resolved by name against the squadron-def DB
    # rather than AircraftType.named -- and an unresolved entry only warns + falls back -- so
    # this asserts breadth of population, not per-string aircraft resolution.
    _campaign, _theater, air_wing = steel_tiger
    total = sum(len(sqs) for sqs in air_wing.by_location.values())
    assert total > 0, "Steel Tiger produced no squadrons -- a CP key regressed."
    # 19 control-point keys are configured; if the keys wholesale failed to resolve against
    # the theater they would be logged-and-skipped and this would collapse. Require most.
    assert (
        len(air_wing.by_location) >= 12
    ), f"Only {len(air_wing.by_location)} bases populated -- control-point keys regressed."


def test_steel_tiger_carrier_squadrons_carrier_capable(
    steel_tiger: tuple[Campaign, ConflictTheater, CampaignAirWingConfig],
) -> None:
    # Same rule as Khe Sanh: the reused Yankee Station carriers must fly carrier-capable
    # airframes (never the land-based F-4E). Some carrier entries are squadron-name aliases
    # (VAW-122 E-2, VS-28 (Tanker) S-3) that AircraftType.named can't resolve -- those carrier
    # types are all deck aircraft anyway -- so skip a name that isn't a bare airframe and
    # check the ones that are (A-6E/F-8E/CH-53E here), which is where an errant F-4E would show.
    _campaign, theater, air_wing = steel_tiger
    carriers = set(theater.find_carriers()) | set(theater.find_lhas())
    checked = 0
    offenders: list[str] = []
    for control_point, squadrons in air_wing.by_location.items():
        if control_point not in carriers:
            continue
        for squadron in squadrons:
            for aircraft_name in squadron.aircraft:
                try:
                    aircraft = AircraftType.named(aircraft_name)
                except KeyError:
                    continue  # a squadron-name alias, resolved via the squadron-def DB
                checked += 1
                if not control_point.can_operate(aircraft):
                    offenders.append(f"{control_point.name}: {aircraft_name}")
    assert (
        checked
    ), "No Steel Tiger carrier airframes were checked -- carrier topology regressed."
    assert not offenders, (
        f"Steel Tiger carrier squadrons fly airframes that cannot operate from the "
        f"carrier: {offenders}."
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


# W4: every Vietnam campaign carries the authored Rolling Thunder -> Linebacker II
# ROE arc (campaign phases P2). Guard the structure so an edit can't silently drop
# a campaign's arc or break its parse (a bad block degrades to Tier-0 at runtime,
# which would quietly lose the whole ROE layer).
_ROE_ARC_KEYS = ["rolling_thunder", "bombing_halt", "linebacker", "linebacker_ii"]


@pytest.mark.parametrize("campaign_file", list(_ERA_PRESEED))
def test_vietnam_campaign_authored_roe_arc(campaign_file: str) -> None:
    import yaml

    from game.fourteenth.phases import parse_phases

    with (_CAMPAIGNS / campaign_file).open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    arc = parse_phases(data.get("phases"))
    assert [p.key for p in arc] == _ROE_ARC_KEYS, campaign_file
    # Rolling Thunder binds: a sanctuary zone + locked deep-target classes.
    assert arc[0].restricted_zones and arc[0].locked_target_classes, campaign_file
    # Escalation is will-coupled from the first phase.
    assert arc[0].advance_when is not None, campaign_file
    assert arc[0].advance_when.blue_will_below is not None, campaign_file
    # Linebacker II: nothing locked, and no sanctuary except the permanent
    # "PRC border" ring (the Yankee Station / Steel Tiger coastal-ladder laydown
    # keeps it in every phase -- MiGs across the border stayed safe in the real
    # war too; Khe Sanh / Velvet Thunder release everything).
    assert not arc[3].locked_target_classes, campaign_file
    for zone in arc[3].restricted_zones:
        assert "PRC border" in zone.name, campaign_file
    # The scheduled escalation dates are strictly increasing.
    pins = [p.min_turn for p in arc[1:]]
    assert pins == sorted(pins) and all(p > 0 for p in pins), campaign_file
