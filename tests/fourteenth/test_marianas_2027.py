"""CI lock on the "Marianas - Second Island Chain (2027)" campaign.

The modern-day China fight. Almost everything that makes it work degrades
*silently* at runtime -- a faction airframe that stops resolving substitutes, a mod
pack that is not preseeded drops the PLA kit back to Soviet legacy hardware, a
setting whose name drifts is simply ignored, and an airfield whose miz coalition is
reset to NEUTRAL stops being a control point at all (``Airport.is_neutral()``
returns False for NEUTRAL, so ``MizCampaignLoader.control_points`` skips it) -- so
the shipped definition is asserted here rather than trusted.

Sibling of tests/fourteenth/test_inherent_resolve.py and test_tanker_war.py.
"""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from dcs.mission import Mission
from dcs.vehicles import AirDefence, MissilesSS

from game import persistency
from game.campaignloader.mizcampaignloader import MizCampaignLoader

CAMPAIGN = Path("resources/campaigns/marianas_2027.yaml")
MIZ = CAMPAIGN.parent / "marianas_2027.miz"
FACTIONS = CAMPAIGN.parent.parent / "factions"


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    """AircraftType.named lazily loads unit data, which needs a save-dir root."""
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16885)


def _campaign() -> dict[str, Any]:
    return yaml.safe_load(CAMPAIGN.read_text(encoding="utf-8"))


def _mission() -> Mission:
    mission = Mission()
    mission.load_file(str(MIZ))
    return mission


def test_campaign_definition() -> None:
    data = _campaign()
    assert data["theater"] == "MarianaIslands"
    assert data["recommended_player_faction"] == "USA 2020"
    assert data["recommended_enemy_faction"] == "China 2027"
    assert str(data["recommended_start_date"]).startswith("2027")
    # The generated miz + the tool that generates it ship together. Never hand-edit
    # the miz -- re-run the tool.
    assert MIZ.exists()
    assert (FACTIONS.parent.parent / "tools/build_marianas_2027_miz.py").exists()


def test_mod_packs_are_preseeded() -> None:
    # Campaign settings re-seed the New Game "Mods" checkboxes. Without the China
    # pack the PLA ground/naval kit silently degrades to Soviet legacy hardware;
    # without the CJS pack the carrier loses its Growler det (§77) and its organic
    # tanker.
    settings = _campaign()["settings"]
    for mod in (
        "chinesemilitaryassetspack",
        "usamilitaryassetspack",
        # High Digit SAMs is a hard requirement: the enemy faction's long-range belt
        # (S-300PMU-1/PMU-2) exists only with it.
        "high_digit_sams",
        "fa_18efg",
        "fa18ef_tanker",
        "f22_raptor",
    ):
        assert settings[mod] is True, mod


def test_the_carrier_air_wing_is_period_correct() -> None:
    """No Prowler on a 2027 deck.

    The Navy retired the EA-6B in 2015 (USMC 2019), so a Prowler here is the same
    anachronism as red flying a J-7B. Electronic attack is the EA-18G, which also
    outranks every other airframe for the §77 Escort Jammer role (800 vs 790).
    """
    carrier = yaml.safe_dump(_campaign()["squadrons"]["Naval-1"])
    assert "EA-6B" not in carrier
    assert "EA-18G Growler" in carrier
    # The organic recovery tanker. Probe/drogue, like the air wing it feeds -- it
    # cannot service Andersen's boom receivers (see the tanker-compatibility test).
    assert "F/A-18E Tanker" in carrier
    assert "F/A-18F Super Hornet" in carrier


def test_the_carrier_keeps_a_mod_free_hornet_squadron() -> None:
    """The CJS pack is a mod, so the deck must not be entirely mod-gated.

    One legacy F/A-18C squadron is retained deliberately: a pilot who has not
    installed the Super Hornet mod still has a carrier jet to slot into. Removing it
    means also dropping the fa_18efg preseed.
    """
    blocks = _campaign()["squadrons"]["Naval-1"]
    legacy = [
        block
        for block in blocks
        if "F/A-18C Hornet (Lot 20)" in (block.get("aircraft") or [])
    ]
    assert legacy, "the carrier air wing has no un-modded Hornet squadron left"


def test_naval_and_missile_features_are_preseeded() -> None:
    settings = _campaign()["settings"]
    # The PLARF hunt is the campaign's signature: scooting launchers you can only
    # find by flying recon at them.
    assert settings["mobile_missile_relocation"] is True
    assert settings["concealed_enemy_forces"] is True
    # The missile exchange at sea, and island logistics under coastal fire.
    for key in (
        "cruise_missile_strikes",
        "cruise_missile_auto_raids",
        "cargo_ship_convoys",
        "coastal_batteries_engage_ships",
    ):
        assert settings[key] is True, key


def test_runtime_plugins_are_preseeded() -> None:
    # A saved plugin default of "off" silently kills the runtime half of a feature
    # even with its setting on (the §36 lesson), so every plugin the settings above
    # depend on is preseeded.
    campaign = _campaign()
    # The map has to be nested under `settings:` to reach Campaign.settings at all.
    # It sat at the document root from 2026-06 until 2026-08-08, where the loader
    # never looked -- so assert the location, not just the values.
    assert "plugins" not in campaign, "a root-level `plugins:` block is discarded"
    plugins = campaign["settings"]["plugins"]
    for plugin in (
        "gpsjamming",
        "mobilemissiles",
        "cruisemissiles",
        "aisleep",
        "rednet",
    ):
        assert plugins[plugin] is True, plugin
    # §50 needs no plugin -- its ambush spring is authored as native DCS triggers.
    assert "convoyambush" not in plugins


def test_guam_is_blue_and_the_chain_is_red() -> None:
    """Ownership is the whole premise: Guam holds, the chain is occupied."""
    airports = _mission().terrain.airports
    for name in ("Andersen AFB", "Antonio B. Won Pat Intl", "Olf Orote"):
        assert airports[name].is_blue(), f"{name} must be blue"
    for name in ("Rota Intl", "Tinian Intl", "Saipan Intl", "Pagan Airstrip"):
        assert airports[name].is_red(), f"{name} must be red"


def test_every_based_airfield_is_actually_a_control_point() -> None:
    """A NEUTRAL airfield is dropped entirely by the loader.

    ``MizCampaignLoader.control_points`` gates on
    ``is_blue() or is_red() or is_neutral()``, and pydcs's ``is_neutral()`` returns
    False for a NEUTRAL coalition -- so a field reset to NEUTRAL silently stops
    existing, taking every squadron the yaml based there with it.
    """
    airports = _mission().terrain.airports
    based = {
        name
        for name in _campaign()["squadrons"]
        if name in airports  # carriers/LHAs/FOBs are group names, not airfields
    }
    assert based, "no airfield-based squadrons found -- key format changed?"
    for name in based:
        airport = airports[name]
        assert (
            airport.is_blue() or airport.is_red()
        ), f"{name} bases squadrons but is NEUTRAL, so it is not a control point"


def test_north_west_field_stays_out() -> None:
    # pydcs reports it with zero runways: it can host no fixed wing, so it is
    # deliberately left NEUTRAL (and therefore not a control point).
    airport = _mission().terrain.airports["North West Field"]
    assert not airport.is_blue() and not airport.is_red()
    assert not airport.runways


def test_red_fields_fit_their_parking() -> None:
    """Squadrons must not out-number the ramp they are based on.

    Rota (9 slots), Tinian (4) and Pagan Airstrip (3) are tiny; Olf Orote has 4.
    A campaign edit that oversubscribes one of them spawns aircraft into each other.
    """
    mission = _mission()
    airports = mission.terrain.airports
    squadrons = _campaign()["squadrons"]
    for name, blocks in squadrons.items():
        airport = airports.get(name)
        if airport is None:
            continue
        based = sum(block.get("size", 12) for block in blocks)
        slots = len(airport.parking_slots)
        assert based <= slots, f"{name}: {based} airframes based on {slots} slots"


def test_theatre_missile_sites_exist_on_the_contested_islands() -> None:
    """The PLARF hunt needs missile-category markers; Repartee shipped none."""
    mission = _mission()
    sites = [
        group
        for coalition in mission.coalition.values()
        for country in coalition.countries.values()
        for group in country.vehicle_group
        if group.units[0].type == MizCampaignLoader.MISSILE_SITE_UNIT_TYPE
    ]
    assert MizCampaignLoader.MISSILE_SITE_UNIT_TYPE == MissilesSS.Scud_B.id
    assert len(sites) == 3, f"expected 3 PLARF sites, found {len(sites)}"
    assert {g.name for g in sites} == {
        "Rota PLARF Site",
        "Tinian PLARF Site",
        "Saipan PLARF Site",
    }


def test_rota_has_a_point_defence_battery() -> None:
    """Rota was NEUTRAL upstream and carries no authored garrison of its own.

    The band is deliberate and it is a SHORT one: Rota sits **75 km from Andersen**, so
    a long-range battery here covers the airfield the player has to fly out of (an
    HQ-22 reaches 170 km). The marker band and the HQ-7 pin have to agree, because
    ``get_unit_group_for_task`` silently discards an override whose task does not match
    the band.
    """
    mission = _mission()
    names = {
        group.name
        for coalition in mission.coalition.values()
        for country in coalition.countries.values()
        for group in country.vehicle_group
        if group.units[0].type in MizCampaignLoader.SHORT_RANGE_SAM_UNIT_TYPES
    }
    assert "Rota SAM Site" in names
    assert _campaign()["ground_forces"]["Rota SAM Site"] == "HQ-7"
    assert AirDefence.Strela_1_9P31.id in MizCampaignLoader.SHORT_RANGE_SAM_UNIT_TYPES


def test_red_air_is_period_correct() -> None:
    """No J-7B. Repartee's 2010 OOB still flew a 1960s MiG-21 copy in a modern war."""
    squadrons = yaml.safe_dump(_campaign()["squadrons"])
    assert "J-7B" not in squadrons
    # The pieces that make red a modern opponent rather than a legacy one.
    for airframe in ("Su-30MKK Flanker-G", "J-11A Flanker-L", "KJ-2000", "H-6J Badger"):
        assert airframe in squadrons, airframe


def test_blue_outnumbers_red_in_the_air() -> None:
    """Blue is the side on the offensive here, and the OOB has to say so.

    Repartee shipped the ratio backwards (165 red vs 62 blue) because six carrier
    squadrons omitted ``size`` and silently defaulted to 12 each.
    """
    squadrons = _campaign()["squadrons"]
    blue_bases = {
        "Andersen AFB",
        "Antonio B. Won Pat Intl",
        "Olf Orote",
        "Naval-1",
        "Naval-2",
        "Naval-30",  # second US carrier
        "Naval-31",  # RN amphibious group
    }
    blue = red = 0
    for base, blocks in squadrons.items():
        for block in blocks:
            # Every block states its size explicitly -- an omitted size is the bug.
            assert "size" in block, f"{base}: squadron block omits an explicit size"
            if base in blue_bases:
                blue += block["size"]
            else:
                red += block["size"]
    assert blue > red, f"blue {blue} must out-mass red {red}"


BLUE_BASES = {
    "Andersen AFB",
    "Antonio B. Won Pat Intl",
    "Olf Orote",
    "Naval-1",
    "Naval-2",
}


def _blue_aircraft_types(tankers: bool) -> list[Any]:
    """Resolve blue's authored airframes -- the tankers, or everything else.

    A squadron `aircraft:` entry may name either an airframe or a squadron preset;
    only the former resolves, and this campaign authors airframes throughout, so a
    KeyError means "preset" and anything else is a real failure worth surfacing.
    """
    from game.dcs.aircrafttype import AircraftType

    out = []
    for base, blocks in _campaign()["squadrons"].items():
        if base not in BLUE_BASES:
            continue
        for block in blocks:
            if (block.get("primary") == "Refueling") is not tankers:
                continue
            for name in block.get("aircraft") or []:
                try:
                    out.append(AircraftType.named(name))
                except KeyError:  # a squadron preset, not an airframe
                    continue
    return out


def test_every_blue_receiver_has_a_compatible_blue_tanker() -> None:
    """Boom jets need a boom tanker; probe jets need a drogue.

    The KC-135 **MPRS** is `tanker_refuel_types: probe` — a *drogue* tanker, not a
    boom one. Basing only an MPRS at Andersen left the entire land wing (F-15C/E,
    F-16CM, B-1B — all `air_refuel_type: boom`) with nothing it could tank from,
    which no other test noticed because both entries are simply "a tanker".
    """
    tankers = _blue_aircraft_types(tankers=True)
    assert tankers, "blue fields no tankers at all"
    for receiver in _blue_aircraft_types(tankers=False):
        if receiver.air_refuel_type is None:
            continue  # untagged receivers are permissive by design
        assert any(
            receiver.can_refuel_from(tanker) for tanker in tankers
        ), f"{receiver} ({receiver.air_refuel_type}) has no compatible blue tanker"


def test_guam_keeps_two_blue_supply_roads() -> None:
    """§50 ambient convoys + the ambush roll need same-side road corridors."""
    routes = _campaign()["supply_routes"]
    assert len(routes) == 2
    for route in routes:
        waypoints = route["waypoints"]
        # Both roads start at Won Pat; each traces a real Guam highway, so an
        # intermediate corridor is mandatory (never a straight line).
        assert waypoints[0] == [-24, -78]
        assert len(waypoints) >= 4, "supply route must follow the driveable corridor"


def test_china_2027_faction_is_a_modern_pla() -> None:
    """The enemy is a fork faction, and both edits to it are load-bearing.

    `China 2020` cannot field a long-range SAM at all; `Redfor (China) 2020` can, but
    is a CJTF-Red faction that also rolls SA-2/SA-6 and loses the Chinese country
    identity. `China 2027` is China 2020 with the obsolete HQ-2 dropped and the
    S-300PMU family added -- modern, era-clean, and still natively Chinese.
    """
    import json

    data = json.loads((FACTIONS / "china_2027.json").read_text(encoding="utf-8"))
    assert data["name"] == "China 2027"
    assert data["country"] == "China"  # keeps §23 voices + zh_CN pilot names
    presets = data["preset_groups"]
    # The HQ-2 is a 1960s S-75 derivative; leaving it in lets base defences roll it.
    assert "HQ-2" not in presets
    for era_wrong in ("SA-2/S-75", "SA-6"):
        assert era_wrong not in presets, era_wrong
    for modern in ("SA-20/S-300PMU-1", "SA-20B/S-300PMU-2", "HQ-22", "HQ-7"):
        assert modern in presets, modern


def test_ground_forces_pins_match_their_marker_band() -> None:
    """A pin whose task does not match its marker's band is SILENTLY discarded.

    ``StartGenerator.get_unit_group_for_task`` only honours a ``ground_forces``
    override when ``task in fg.tasks``. Pinning the HQ-22 (which declares LORAD) onto
    a medium marker therefore did nothing at all and the site rolled an SA-11 instead
    -- with no warning anywhere. Every pin is checked against its marker here.
    """
    from game.campaignloader.campaign import Campaign
    from game.data.groups import GroupTask

    band_for_task = {
        GroupTask.LORAD: MizCampaignLoader.LONG_RANGE_SAM_UNIT_TYPES,
        GroupTask.MERAD: MizCampaignLoader.MEDIUM_RANGE_SAM_UNIT_TYPES,
        GroupTask.SHORAD: MizCampaignLoader.SHORT_RANGE_SAM_UNIT_TYPES,
        GroupTask.AAA: MizCampaignLoader.AAA_UNIT_TYPES,
        # Naval markers have no SAM band -- the ship marker type IS the band.
        GroupTask.NAVY: {MizCampaignLoader.SHIP_UNIT_TYPE},
        # §86 jamming sites are EWR-tasked, so they pin onto EWR-band markers.
        GroupTask.EARLY_WARNING_RADAR: {MizCampaignLoader.EWR_UNIT_TYPE},
    }
    markers = {
        group.name: group.units[0].type
        for coalition in _mission().coalition.values()
        for country in coalition.countries.values()
        for attr in ("vehicle_group", "ship_group")
        for group in getattr(country, attr)
    }
    config = Campaign.from_file(CAMPAIGN).load_ground_forces_config()
    pinned = list(config)
    assert pinned, "no ground_forces pins found -- block removed?"
    for name in pinned:
        assert name in markers, f"{name} is pinned but is not a marker in the miz"
        force_group = config[name]
        assert force_group is not None
        unit_type = markers[name]
        ok = any(
            task in force_group.tasks and unit_type in types
            for task, types in band_for_task.items()
        )
        assert ok, (
            f"{name}: marker type {unit_type} does not match any task of "
            f"{force_group.name} ({[t.name for t in force_group.tasks]}) -- "
            "the override would be silently discarded"
        )


def test_no_blue_base_sits_behind_the_red_chain() -> None:
    """Blue holds the southern end; red holds everything north of it.

    The first cut inverted Guam to blue but left Fuzzle's carrier group at the far
    NORTH of the chain (his premise was a lone CSG fighting south), and left FOB
    Uracus blue 780 km behind red lines -- so blue held both ends with red sandwiched
    between. The map has to read as one axis.
    """
    from game.campaignloader.campaign import Campaign

    theater = Campaign.from_file(CAMPAIGN).load_theater(advanced_iads=False)
    blue: list[tuple[float, str]] = []
    red: list[tuple[float, str]] = []
    for cp in theater.controlpoints:
        (blue if cp.starting_coalition.is_blue else red).append(
            (cp.position.x, cp.name)
        )
    assert blue and red
    northernmost_blue = max(blue)
    southernmost_red = min(red)
    assert northernmost_blue[0] < southernmost_red[0], (
        f"{northernmost_blue[1]} (blue) sits north of {southernmost_red[1]} (red) -- "
        "the laydown is sandwiched again"
    )


def test_andersen_fields_raptors_without_losing_its_mod_free_fighter() -> None:
    """The F-22A det, and the Eagle squadron that must survive alongside it.

    Guam is the real-world Raptor rotation base and the F-22A is the one blue airframe
    that beats a J-11A/J-15 on merit rather than on numbers -- but it is a mod. The
    F-15C squadron is kept deliberately so a host without the mod still has an
    air-superiority arm, exactly as the carrier keeps a legacy Hornet squadron.
    """
    blocks = _campaign()["squadrons"]["Andersen AFB"]
    by_airframe = {
        airframe: block
        for block in blocks
        for airframe in (block.get("aircraft") or [])
    }
    assert "F-22A Raptor" in by_airframe
    assert "F-15C Eagle" in by_airframe, (
        "the mod-free air-superiority squadron was removed; if that is intended, the "
        "f22_raptor preseed has to go with it"
    )


def test_the_raptor_has_an_authored_max_range() -> None:
    """An airframe with no ``max_range`` silently falls back to 150 NM.

    That is less than half the F-15C's authored 400 NM, so an un-authored Raptor is
    range-gated out of the deep half of this campaign -- it could not reach the PLAN
    carrier groups (108-157 NM) or anything north of Saipan -- while the older Eagle
    could. The fallback is a warning at load and nothing else, so it is pinned here.
    """
    from game.dcs.aircrafttype import AircraftType

    raptor = AircraftType.named("F-22A Raptor")
    eagle = AircraftType.named("F-15C Eagle")
    default_fallback_m = 277_800  # 150 NM
    assert (
        raptor.max_mission_range.meters > default_fallback_m
    ), "F-22A.yaml lost its max_range and fell back to the 150 NM default"
    assert raptor.max_mission_range >= eagle.max_mission_range


def test_every_naval_marker_is_pinned_inshore() -> None:
    """One Navy preset, and every ship marker pinned to it.

    The HHQ-9 reaches **250 km** while Guam-to-Saipan is only 205 km, so a single heavy
    surface group covers a third of the theatre. Giving the scattered markers the heavy
    preset produced **13 of 30 rings at 250 km** -- which does not make the campaign
    harder, it makes the map unreadable. The area-defence destroyers stay concentrated
    with the carrier and LHA groups, which draw them from ``naval_units``.

    Two invariants, both learned the hard way:
      * exactly ONE Navy preset may be registered -- an unpinned marker rolls at random
        among them (``generate_ships`` -> ``random_group_for_task``), so a second preset
        is a live hazard even if nothing references it today;
      * EVERY ship marker is pinned explicitly, so composition never depends on a roll.
    """
    import json

    data = json.loads((FACTIONS / "china_2027.json").read_text(encoding="utf-8"))
    navy_presets = [p for p in data["preset_groups"] if "Navy" in p]
    assert navy_presets == ["Chinese Navy 2027 Escort"], navy_presets

    pins = _campaign()["ground_forces"]
    naval_pins = {n for n, g in pins.items() if g == "Chinese Navy 2027 Escort"}
    markers = {
        group.name
        for coalition in _mission().coalition.values()
        for country in coalition.countries.values()
        for group in country.ship_group
        if group.units[0].type == MizCampaignLoader.SHIP_UNIT_TYPE
    }
    # These three sit next to Guam and bind BLUE (a ship marker prefers a blue control
    # point), so they generate the carrier group's own screen from USA 2020. Pinning them
    # to a Chinese preset would hand the US fleet PLA frigates.
    blue_screen = {"Naval-17", "Naval-18", "Naval-27"}
    unpinned = markers - naval_pins - blue_screen
    assert not unpinned, f"red ship markers left to a random roll: {sorted(unpinned)}"

    escort = yaml.safe_load(
        (FACTIONS.parent / "groups/Chinese-Navy-2027-Escort.yaml").read_text(
            encoding="utf-8"
        )
    )
    # The Destroyer slot must be filled by the preset: an empty slot is filled from the
    # roster, whose destroyers are the 250 km hulls.
    assert "Type 052B Destroyer" in escort["units"]
    for hull in ("[CH] Type 052D Destroyer", "[CH] Type 054B Frigate"):
        assert hull not in escort["units"], hull
        assert hull in data["naval_units"], f"{hull} must stay available to the fleet"

    # The Type 055 is the ONLY hull carrying the YJ-21 anti-ship ballistic missile, which
    # cannot realistically be intercepted. A flown mission put ten of them in the air
    # inside 99 seconds and killed the carrier before the player got airborne. The 052D
    # keeps the fleet's reach with the YJ-18, which Standard missiles do defeat.
    assert "[CH] Type 055 Destroyer" not in data["naval_units"]


def test_no_land_sam_site_covers_guam() -> None:
    """Rota is 75 km from Andersen; Tinian is 175 km.

    Any long-range battery on Rota puts the airfield the player flies out of inside a
    SAM envelope on turn 1 (an HQ-22 reaches 170 km). Rota therefore gets point defence
    only, and the long-range anchor starts at Tinian where the HQ-22's ring stops just
    short of Guam. The S-300PMU-2 (200 km) is deliberately not authored anywhere in the
    corridor -- there is no site in it from which that ring misses Andersen.
    """
    pins = _campaign()["ground_forces"]
    assert pins["Rota SAM Site"] == "HQ-7"
    assert pins["Ground-1"] == "HQ-22"
    assert "SA-20B/S-300PMU-2" not in pins.values()


def test_a_culled_ship_marker_is_never_also_pinned() -> None:
    """A marker cannot be both deleted from the miz and pinned in the campaign.

    Black reformatted the cull tuple one-entry-per-line, an edit missed it, and two
    markers ended up in CULLED_SHIP_MARKERS *and* in ground_forces -- deleted from the
    miz while the campaign still claimed to place them. Silent, because a pin for a
    marker that does not exist simply never fires.
    """
    tool = Path("tools/build_marianas_2027_miz.py").read_text(encoding="utf-8")
    culled = set(
        re.findall(r'"(Naval-\d+)"', tool[tool.index("CULLED_SHIP_MARKERS") :][:400])
    )
    pinned = {n for n in _campaign()["ground_forces"] if n.startswith("Naval-")}
    assert culled, "cull list not found -- did the tool rename it?"
    assert not (culled & pinned), sorted(culled & pinned)
