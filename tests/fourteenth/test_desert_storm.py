"""CI lock on the Iraq "Umm al-Ma'arik (Desert Storm 1991)" campaign definition.

The will profile / phase arc degrade silently at runtime (by design), the squadron
airframes substitute silently if a faction unit goes missing, the supply routes bind by
closest-CP so a laydown edit can silently re-pair them, the KARI IADS is authored as
.miz statics, and DCS parking is dimension-resolved so an over-wide airframe at a
small-stand field silently fails to ground-spawn -- so the shipped campaign + the
faction adds it depends on are asserted here. Sibling of
tests/fourteenth/test_tanker_war.py.

Laydown v2 (the western desert war): BLUE holds only the seized H-3 complex + the
off-map Saudi rear (the Iraq map has no 60x60 heavy stands west of Baghdad, so the
E-3/KC-135 wing flies from over the border -- historically where it always was);
Al-Asad reverts to Iraq as Qadessiya AB and the campaign climbs the pipeline-road
ladder H-3 -> H-2 -> Al-Asad.
"""

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from game import persistency
from game.fourteenth.phases import parse_phases
from game.fourteenth.political_will import parse_will_profile

CAMPAIGN = Path("resources/campaigns/iraq_desert_storm.yaml")
FACTIONS = CAMPAIGN.parent.parent / "factions"

OFFMAP_KEY = "Coalition Rear (Saudi Arabia)"

#: yaml squadron key -> Iraq terrain airport name (int keys are airport ids).
AIRPORT_NAMES = {
    1: "Al-Asad Airbase",
    2: "Baghdad International Airport",
    3: "Mosul International Airport",
    4: "Erbil International Airport",
    6: "Qayyarah Airfield West",
    7: "Sulaimaniyah International Airport",
    8: "Balad Airbase",
    10: "Kirkuk International Airport",
    12: "Al-Sahra Airport",
    14: "Al-Salam Airbase",
    15: "H-2 Airbase",
    16: "H-3 Main Airbase",
    17: "H-3 Southwest Airbase",
    18: "H-3 Northwest Airbase",
}


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    """AircraftType.named lazily loads unit data, which needs a save-dir root."""
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16884)


def _campaign() -> dict[str, Any]:
    return yaml.safe_load(CAMPAIGN.read_text(encoding="utf-8"))


def test_desert_storm_campaign_definition() -> None:
    data = _campaign()
    assert data["theater"] == "Iraq"
    assert data["recommended_player_faction"] == "NATO Desert Storm"
    assert data["recommended_enemy_faction"] == "Iraq 1991"
    # The air campaign opened 17 January 1991 (datetime form seeds the 0300 clock).
    assert str(data["recommended_start_date"]).startswith("1991-01-17")
    # KARI is a networked IADS -- the whole premise.
    assert data["advanced_iads"] is True
    assert (CAMPAIGN.parent / data["miz"]).exists()

    # The 414th feature preseeds this campaign is built around.
    for key in (
        "restrict_weapons_by_date",
        "restrict_props_by_date",
        "campaign_phases",
        "vietnam_political_will",
        "c2_decapitation_effects",
        "auto_repair_air_defenses",
        "comint_collection",
        "red_comms_net",
        "convoy_ambush",
        "host_red_scramble",
    ):
        assert data["settings"][key] is True, key
    # The s36 lesson: every preseeded feature's plugin is preseeded with it.
    plugins = data["settings"]["plugins"]
    for plugin in ("convoyambush", "mobilemissiles", "rednet", "redscramble"):
        assert plugins[plugin] is True, plugin
    assert plugins["redscramble.hostPlayers"] == "Flash"


def test_desert_storm_blue_holds_only_the_h3_complex() -> None:
    """The v2 historical laydown: blue's flying wing lives on the three seized H-3
    strips; the heavies fly from the off-map Saudi rear; Al-Asad (key 1) is RED."""
    squadrons = _campaign()["squadrons"]
    blue_keys = {OFFMAP_KEY, 16, 17, 18}
    assert blue_keys <= set(squadrons)

    # The off-map rear: the big-wing support set (no 60x60 stands exist west of
    # Baghdad for them to park on) plus the coalition allies flying from where
    # they really flew -- the RAF and Daguet entries reference nation-countried
    # squadron PRESETS by name (the s23 layer), not airframe strings.
    rear = {cfg["aircraft"][0] for cfg in squadrons[OFFMAP_KEY]}
    assert rear == {
        "E-3A",
        "KC-135 Stratotanker",
        "KC-135 Stratotanker MPRS",
        "No. 31 Squadron",
        "Escadron de chasse 2/5",
        "Escadron de Chasse 3/33 Lorraine",
    }
    # Daguet's recon det flies the photo war: TARPS primary on the F1CR stand-in.
    belfort = [c for c in squadrons[OFFMAP_KEY] if c["name"] == "ER 1/33 Belfort"]
    assert belfort and belfort[0]["primary"] == "TARPS"

    # The escort-starvation fix survives the move: the F-15C wall stands BARCAP at
    # H-3 Main with the air-to-air secondary that feeds every package escort.
    eagles = [c for c in squadrons[16] if c["aircraft"] == ["F-15C Eagle"]]
    assert eagles and eagles[0]["primary"] == "BARCAP"
    assert eagles[0]["secondary"] == "air-to-air"
    assert eagles[0]["size"] == 12  # trimmed to fit the complex

    # The Bombcat strikes but never hunts SAMs: an air-to-GROUND secondary expands
    # to DEAD/SEAD, and KARI's SAM demand had the planner fragging Tomcats at SA-2
    # rings (first flown new-game finding). Era truth: DS Tomcats flew escort/CAP.
    tomcats = [c for c in squadrons[16] if c["aircraft"] == ["F-14B Tomcat"]]
    assert tomcats and tomcats[0]["primary"] == "Strike"
    assert tomcats[0]["secondary"] == "air-to-air"

    # The flyable modules the faction was extended for.
    faction = json.loads(
        (FACTIONS / "NATO_Desert_Storm.json").read_text(encoding="utf-8")
    )
    for airframe in ("A-10C Thunderbolt II (Suite 7)", "CH-47F Block I"):
        assert airframe in faction["aircrafts"], airframe
    # The Hog flies from the Northwest strip (Southwest has only two stands wide
    # enough); the helo det owns the Southwest strip.
    assert any(
        c["aircraft"] == ["A-10C Thunderbolt II (Suite 7)"] for c in squadrons[18]
    )
    assert any(c["aircraft"] == ["CH-47F Block I"] for c in squadrons[17])

    # Qadessiya flies its real tenants: the Foxbat wing at RED Al-Asad.
    assert any(c["aircraft"] == ["MiG-25PD Foxbat-E"] for c in squadrons[1])


def test_desert_storm_red_fighters_are_defensively_tasked() -> None:
    """The Red Tide red-posture lesson: interceptors fly BARCAP/TARCAP primaries (the
    GCI alert force the QRA reserve staffs), never offensive fighter taskings."""
    data = _campaign()
    assert data["settings"]["opfor_default_qra_reserve"] == 4
    fighters = {
        "MiG-25PD Foxbat-E",
        "MiG-23ML Flogger-G",
        "MiG-29A Fulcrum-A",
        "MiG-21bis Fishbed-N",
        "Mirage-F1EQ",
    }
    for base_id, configs in data["squadrons"].items():
        for cfg in configs:
            aircraft = cfg.get("aircraft") or []
            if not isinstance(aircraft, list) or not aircraft:
                continue
            if aircraft[0] in fighters and cfg["primary"] != "Escort":
                assert cfg["primary"] in ("BARCAP", "TARCAP"), (base_id, aircraft)


def test_desert_storm_every_squadron_fits_its_parking() -> None:
    """DCS Iraq resolves parking by slot dimensions (slot_version 2), and the map
    has NO oversized stands at most fields -- the original DS91 had the E-3/KC-135
    wing at H-3 Main (zero fitting stands) and the 24-Fulcrum reserve at Al-Kut
    (six plane stands + 58 helipads). Assert every based squadron's airframe has at
    least as many dimensionally-fitting slots as airframes, so a re-basing can
    never silently strand a wing again. The off-map rear is exempt (air-spawn)."""
    from dcs.terrain.iraq import Iraq

    from game.dcs.aircrafttype import AircraftType

    terrain = Iraq()
    airports = {a.name: a for a in terrain.airports.values()}
    for base_id, configs in _campaign()["squadrons"].items():
        if base_id == OFFMAP_KEY:
            continue
        airport = airports[AIRPORT_NAMES[base_id]]
        for cfg in configs:
            unit_type = AircraftType.named(cfg["aircraft"][0]).dcs_unit_type
            if unit_type.helicopter:
                fitting = [
                    s
                    for s in airport.parking_slots
                    if s.helicopter
                    and unit_type.width < s.width
                    and unit_type.length < s.length
                    and unit_type.height < (s.height or 1000)
                ]
            else:
                fitting = [
                    s
                    for s in airport.parking_slots
                    if (s.airplanes or s.large)
                    and unit_type.width < s.width
                    and unit_type.length < s.length
                    and unit_type.height < (s.height or 1000)
                ]
            assert len(fitting) >= cfg["size"], (
                base_id,
                airport.name,
                cfg["aircraft"][0],
                f"{len(fitting)} fitting slots < {cfg['size']} airframes",
            )


def test_desert_storm_squadrons_carry_historical_identities() -> None:
    """Every squadron is named for its real (or best-match) January 1991 unit, per
    the published orbats. Era discipline rides along: female_pilot_percentage is 0
    everywhere (US combat squadrons were closed to women until 1993), and the Iraqi
    squadrons carry an explicit EMPTY nickname -- the campaign-authored way of
    suppressing the def generator's random nickname roll (IrAF units used none)."""
    squadrons = _campaign()["squadrons"]
    for base_id, configs in squadrons.items():
        for cfg in configs:
            assert cfg.get("name"), (base_id, cfg["aircraft"])
            assert cfg.get("female_pilot_percentage") == 0, (base_id, cfg["name"])
            assert "nickname" in cfg, (base_id, cfg["name"])

    by_name = {cfg["name"]: cfg for cfgs in squadrons.values() for cfg in cfgs}
    # The marquee identities.
    assert by_name["VF-103"]["nickname"] == "Sluggers"  # the real DS F-14B unit
    assert by_name["58th TFS"]["nickname"] == "Gorillas"  # 16 kills, most of the war
    assert by_name["1-101st Aviation"]["nickname"] == "Expect No Mercy"  # TF Normandy
    # Night one's only Iraqi air-to-air kill came from the Qadessiya Foxbats --
    # and Iraqi squadrons carry no nickname.
    assert by_name["No. 84 Squadron"]["aircraft"] == ["MiG-25PD Foxbat-E"]
    assert by_name["No. 84 Squadron"]["nickname"] == ""


def test_desert_storm_allied_squadrons_carry_their_nations() -> None:
    """The RAF and Daguet entries bind nation-countried squadron presets (the s23
    per-squadron-country layer: national comms identity + pilot names). Pin the
    preset files' countries and the faction's Tornado add so a preset rename or
    faction scrub can't silently anglicize them back to the CJTF default."""
    raf = yaml.safe_load(
        Path("resources/squadrons/Tornado/No 31 Squadron RAF.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert raf["name"] == "No. 31 Squadron"
    assert raf["country"] == "UK"
    assert raf["aircraft"] == "Tornado GR4"

    ada = yaml.safe_load(
        Path(
            "resources/squadrons/m2000c/ADA_EscadronDeChasse_2-5_IleDeFrance.yaml"
        ).read_text(encoding="utf-8")
    )
    assert ada["name"] == "Escadron de chasse 2/5"
    assert ada["country"] == "France"

    # Daguet's recon det: the F1CT (standing in for the F1CR, whose camera nose it
    # kept) must be recon-capable and long-legged enough to fly from the rear.
    lorraine = yaml.safe_load(
        Path("resources/squadrons/Mirage-F1/AAE Squadron 3-33 Lorraine.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert lorraine["name"] == "Escadron de Chasse 3/33 Lorraine"
    assert lorraine["country"] == "France"
    assert lorraine["aircraft"] == "Mirage-F1CT"

    faction = json.loads(
        (FACTIONS / "NATO_Desert_Storm.json").read_text(encoding="utf-8")
    )
    assert "Tornado GR4" in faction["aircrafts"]
    assert "Mirage-F1CT" in faction["aircrafts"]
    # The off-map basing depends on honest strike radii (the unset default of
    # 150 NM -- or the F1's old 200 -- grounds a rear-based jet).
    gr4 = yaml.safe_load(
        Path("resources/units/aircraft/Tornado GR4.yaml").read_text(encoding="utf-8")
    )
    assert gr4["max_range"] >= 400
    f1ct = yaml.safe_load(
        Path("resources/units/aircraft/Mirage-F1CT.yaml").read_text(encoding="utf-8")
    )
    assert f1ct["max_range"] >= 400
    assert f1ct["tasks"]["TARPS"] == 700


def test_desert_storm_will_profile_is_the_coalition_story() -> None:
    profile = parse_will_profile(_campaign()["will"])
    assert profile.blue.label == "Coalition cohesion"
    assert profile.red.label == "the regime's resolve"
    # One Al-Firdos is survivable, a habit is not.
    assert profile.weights.blue_roe_violation == 3.0


def test_desert_storm_phase_arc() -> None:
    arc = parse_phases(_campaign()["phases"])
    assert [p.key for p in arc] == ["instant_thunder", "scud_hunt", "umm_al_maarik"]
    # Every phase keeps the Baghdad no-strike circle (the CDE bill, never a hard block).
    for phase in arc:
        assert any("Baghdad" in zone.name for zone in phase.restricted_zones), phase.key
    # Instant Thunder advances on IADS attrition -- the rollback coupling.
    assert arc[0].advance_when is not None
    assert arc[0].advance_when.enemy_iads_below == 0.55
    # The Scud hunt surges the red convoys it hunts, and seizes the first rung;
    # the ground offensive takes Qadessiya.
    assert arc[1].trail_surge == 1.5
    capture_objectives = {
        objective.done_when.capture_cp
        for phase in arc
        for objective in phase.objectives
        if objective.done_when is not None
        and objective.done_when.capture_cp is not None
    }
    assert capture_objectives == {"H-2 Airbase", "Al-Asad Airbase"}


def test_desert_storm_supply_graph_is_the_red_interior() -> None:
    """12 authored routes -- the red highway net (the interdiction target set).
    Endpoints are exact CP XY (closest-CP binding reads first/last waypoint only),
    so pin the corridor spine: a laydown edit that moves a base silently re-pairs
    the route. The blue H-3 -> H-2 -> Al-Asad ladder legs are .miz path groups
    (they carry the front line up the ladder), not yaml routes."""
    routes = _campaign()["supply_routes"]
    assert len(routes) == 12
    endpoints = {(tuple(r["waypoints"][0]), tuple(r["waypoints"][-1])) for r in routes}
    # Highway 1 north: Baghdad -> Balad (al-Bakr) -> Tikrit -> Qayyarah -> Mosul.
    assert ((-142, 160), (75938, 13806)) in endpoints
    assert ((75938, 13806), (157133, -61805)) in endpoints
    assert ((157133, -61805), (279544, -97450)) in endpoints
    assert ((279544, -97450), (339469, -94071)) in endpoints
    # The Mosul-Erbil arc ties the north together.
    assert ((339469, -94071), (330838, -22360)) in endpoints


def test_desert_storm_miz_authors_the_kari_network() -> None:
    """The KARI C2: an ADOC + 3 sector operations centers, comms/power relays at
    every red base (the four v2 fields included), a 5-station EWR chain with the
    forward Qadessiya set, and the front-ladder path groups."""
    miz = CAMPAIGN.parent / "iraq_desert_storm.miz"
    mission_lua = zipfile.ZipFile(miz).read("mission").decode("utf-8", "replace")
    assert mission_lua.count('".Command Center"') >= 4
    assert mission_lua.count('"Comms tower M"') >= 13
    assert mission_lua.count('"GeneratorF"') >= 13
    assert mission_lua.count('"1L13 EWR"') >= 5
    # The Scud batteries the s49 hunt needs -- incl. the two western baskets.
    assert mission_lua.count('"Scud_B"') >= 9
    # The v2 laydown structures: the off-map rear and the pipeline-road ladder.
    assert OFFMAP_KEY in mission_lua
    assert "Front H-3 to H-2" in mission_lua
    assert "Corridor H-2 to Al-Asad" in mission_lua
    # The Dictator-universe inheritance is gone (zones renamed to the 1991 target set).
    for legacy in ("Wadiya", "Aladeen", "Tamir Mafraad", "Allison Burgers"):
        assert legacy not in mission_lua, legacy
    for renamed in ("Saad 16", "Baba Gurgur", "Daura Oil Refinery"):
        assert renamed in mission_lua, renamed
