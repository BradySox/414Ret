"""Caucasus - Iron Gate laydown guards.

The 414th's fork of Plob's *Northern Russia*: June 2018 against Russia 2020,
blue flying from Kutaisi and Kobuleti with its tankers and AWACS on an off-map
air spawn. Plob's campaign still ships unchanged beside it, so the first thing
these pins protect is that the two stay separate.

The rest guard the parking arithmetic, which is the part that fails silently.
DCS stands are NESTED -- one that takes a Hind also takes a Huey, not the
reverse -- so a base's slot count is not the binding constraint, and sizing
against it overfills the big stands with no error anywhere. It bit three times
during the build: 28 helicopters into Kutaisi's 25 helicopter-capable spots,
Beslan asking ten aircraft to share five large stands, and Tbilisi-Lochini
holding 74 when its jets fit 70.

Validated at ``load_theater`` depth, the fork's campaign-test convention.
"""

from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

from game import persistency
from game.campaignloader.campaign import Campaign
from game.dcs.aircrafttype import AircraftType
from game.theater import ConflictTheater, ParkingType
from game.theater.controlpoint import OffMapSpawn

YAML = Path("resources/campaigns/caucasus_iron_gate.yaml")
PLOBS = Path("resources/campaigns/northern_russia.yaml")

BLUE_FIELDS = {"Kutaisi", "Kobuleti"}
AIR_SPAWN = "Turkey"
RED_FIELDS = {"Beslan", "Mineralnye Vody", "Mozdok", "Nalchik", "Tbilisi-Lochini"}
#: Kutaisi is the A-10 and helicopter base; the fast jets are pushed back to Batumi.
KUTAISI_TYPES = {
    "A-10C Thunderbolt II (Suite 7)",
    "UH-1H Iroquois",
    "OH-58D(R) Kiowa Warrior",
    "C-130J-30",
}


@pytest.fixture(scope="module")
def loaded(tmp_path_factory: Any) -> tuple[Campaign, ConflictTheater]:
    persistency.setup(str(tmp_path_factory.mktemp("iron-gate")), False, 0)
    campaign = Campaign.from_file(YAML)
    return campaign, campaign.load_theater(campaign.advanced_iads)


def test_it_is_its_own_campaign_and_plobs_is_untouched(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    # The whole point of the fork: Northern Russia keeps its own date, faction
    # and unsized squadrons. If a future edit "helpfully" syncs them, say so here.
    campaign, _ = loaded
    assert campaign.name == "Caucasus - Iron Gate"
    plobs = Campaign.from_file(PLOBS)
    assert plobs.name == "Caucasus - Northern Russia"
    assert plobs.recommended_start_date != campaign.recommended_start_date
    assert plobs.recommended_enemy_faction != campaign.recommended_enemy_faction


def test_the_era_and_the_enemy_match(loaded: tuple[Campaign, ConflictTheater]) -> None:
    campaign, _ = loaded
    start = campaign.recommended_start_date
    assert start is not None
    assert start.year == 2018
    # Russia 2020 is vanilla DCS; a mod-gated faction here would silently strip
    # red's best SAMs for anyone without the mod.
    assert campaign.recommended_enemy_faction == "Russia 2020"


def test_blue_flies_from_two_fields_and_an_air_spawn(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    blue = {cp.name for cp in theater.controlpoints if cp.starting_coalition.is_blue}
    assert BLUE_FIELDS <= blue
    assert AIR_SPAWN in blue
    # Batumi and Gudauta were both tried and dropped: Batumi has ten stands,
    # Gudauta thirty-one against Kobuleti's forty-two and a longer transit.
    names = {cp.name for cp in theater.controlpoints}
    assert "Gudauta" not in names and "Batumi" not in names
    spawn = theater.control_point_named(AIR_SPAWN)
    assert isinstance(spawn, OffMapSpawn)


def test_the_support_aircraft_spawn_airborne(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    campaign, theater = loaded
    config = campaign.load_air_wing_config(theater)
    spawn = theater.control_point_named(AIR_SPAWN)
    tasks = {str(s.primary) for s in config.by_location[spawn]}
    assert tasks == {"Refueling", "AEW&C"}, tasks


def test_kutaisi_keeps_the_a10s_and_the_helicopters(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    campaign, theater = loaded
    config = campaign.load_air_wing_config(theater)
    kutaisi = theater.control_point_named("Kutaisi")
    flown = {s.aircraft_type or s.aircraft[0] for s in config.by_location[kutaisi]}
    assert flown == KUTAISI_TYPES, flown


def test_red_still_holds_its_five_fields(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    _, theater = loaded
    red = {cp.name for cp in theater.controlpoints if not cp.starting_coalition.is_blue}
    assert RED_FIELDS <= red


def test_no_base_oversubscribes_a_stand_class(
    loaded: tuple[Campaign, ConflictTheater],
) -> None:
    """Hall's condition over the nested stand classes.

    For every capacity k, the aircraft needing a stand of that class or smaller
    must total <= k. Checking only the base's grand total passes while the big
    stands are overfilled, which is exactly how three overfills got authored.
    """
    campaign, theater = loaded
    config = campaign.load_air_wing_config(theater)
    for cp, squadrons in config.by_location.items():
        airport = getattr(cp, "airport", None)
        if airport is None:  # carrier, LHA, FOB, air spawn: one flat pool
            pool = cp.total_aircraft_parking(
                ParkingType(fixed_wing=True, fixed_wing_stol=True, rotary_wing=True)
            )
            assert sum(s.max_size for s in squadrons) <= pool, cp.name
            continue
        wanted: dict[int, int] = defaultdict(int)
        for squadron in squadrons:
            aircraft = AircraftType.named(
                squadron.aircraft_type or squadron.aircraft[0]
            )
            fits = len(airport.free_parking_slots(aircraft.dcs_unit_type))
            wanted[fits] += squadron.max_size
        assert sum(wanted.values()) <= len(airport.parking_slots), cp.name
        for capacity in sorted(wanted):
            needed = sum(n for fits, n in wanted.items() if fits <= capacity)
            assert needed <= capacity, (
                f"{cp.name}: {needed} aircraft need a stand of class {capacity} "
                f"or smaller, but only {capacity} such stands exist"
            )
