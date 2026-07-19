"""CI lock on the S-3B / A-6 role split (2026-07-19 faction audit).

The Viking used to out-weight the A-6E Intruder on every land-attack task
(BAI 690 vs 675, Strike 480 vs 440, OCA/Aircraft 510 vs 480), so any carrier air
wing fielding both sent the S-3 on the Intruder's missions. The Viking is now
sea-control only, the A-6 took over strike *and* carrier tanking, and the S-3B
survives as a small anti-ship contingent.

Each of those is a data decision spread over ~23 factions / ~39 campaigns that
nothing else would catch if it silently regressed -- in particular the carrier
tanker, where the obvious replacement (F/A-18E Tanker) is mod-gated and vanishes
from a default game.
"""

import json
from pathlib import Path

import pytest
import yaml

from game import persistency
from game.ato.flighttype import FlightType
from game.dcs.aircrafttype import AircraftType
from game.factions.faction import Faction
from game.theater.start_generator import ModSettings

FACTIONS = Path("resources/factions")
CAMPAIGNS = Path("resources/campaigns")


@pytest.fixture(autouse=True, scope="module")
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    # Resolving an AircraftType reads the DCS saved-game folder (weapon
    # injections), which is only configured once the app boots. Point it at an
    # empty temp dir so it falls back to the bundled resources/ data.
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


# Tasks the Viking must never be auto-assigned again.
LAND_ATTACK = [
    FlightType.STRIKE,
    FlightType.BAI,
    FlightType.CAS,
    FlightType.OCA_AIRCRAFT,
    FlightType.OCA_RUNWAY,
    FlightType.ARMED_RECON,
    FlightType.DEAD,
]


def _faction_files() -> list[Path]:
    return sorted(FACTIONS.glob("*.json"))


def test_viking_is_sea_control_only() -> None:
    viking = AircraftType.named("S-3B Viking")
    assert viking.capable_of(FlightType.ANTISHIP)
    for task in LAND_ATTACK:
        assert not viking.capable_of(task), f"Viking regained {task.value}"


def test_viking_outranks_the_carrier_fast_jets_for_anti_ship() -> None:
    """The dedicated sea-control platform must win the anti-ship pick.

    `priority_list_for_task` sorts descending, so a higher weight is preferred.
    """
    viking = AircraftType.named("S-3B Viking").task_priority(FlightType.ANTISHIP)
    for other in ("A-6E Intruder", "F/A-18C Hornet (Lot 20)"):
        assert viking > AircraftType.named(other).task_priority(
            FlightType.ANTISHIP
        ), f"{other} out-ranks the Viking for anti-ship"


def test_the_intruder_kept_the_strike_role() -> None:
    intruder = AircraftType.named("A-6E Intruder")
    for task in (FlightType.STRIKE, FlightType.BAI, FlightType.CAS):
        assert intruder.capable_of(task)


def test_the_a6e_tanker_is_a_pure_tanker() -> None:
    tanker = AircraftType.named("A-6E Tanker")
    assert tanker.capable_of(FlightType.REFUELING)
    assert tanker.carrier_capable
    for task in LAND_ATTACK:
        assert not tanker.capable_of(task), "the tanker variant took on attack tasks"


@pytest.mark.parametrize("path", _faction_files(), ids=lambda p: p.name)
def test_no_faction_still_fields_the_s3b_tanker(path: Path) -> None:
    """Carrier tanking moved to the A-6; the S-3B Tanker is no longer rostered.

    The type and its VS squadron presets deliberately stay on disk so a custom
    faction can still opt back in -- this only pins the shipped rosters.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "S-3B Tanker" not in (data.get("tankers") or [])
    assert "S-3B Tanker" not in (data.get("aircrafts") or [])


# The carrier wings whose tanking this audit moved off the S-3B. Pinned explicitly
# rather than inferred: "has carrier-capable aircraft" is a bad proxy for "operates a
# carrier" (plenty of land factions roster an A-4E), so an inferred check fires on
# ~140 factions that never had a deck.
A6E_TANKER_FACTIONS = [
    "NATO_Desert_Storm.json",
    "NATO_OIF.json",
    "SW_Rebel_Alliance.json",
    "USA 1970 Vietnam War.json",
    "US_UK_Falklands.json",
    "bluefor_modern.json",
    "blufor_current.json",
    "blufor_late_coldwar.json",
    "cjtf_oir_2016.json",
    "final_countdown_2.json",
    "israel_2011_ODS.json",
    "oef_coalition_2006.json",
    "us_aggressors.json",
    "usa_1990.json",
    "usa_2005.json",
    "usa_2020.json",
    "usn_1985.json",
    "usn_2005.json",
    "usn_2009.json",
    "wrl_taskforceblue.json",
]


@pytest.mark.parametrize("name", A6E_TANKER_FACTIONS)
def test_carrier_factions_keep_a_vanilla_carrier_tanker(name: str) -> None:
    """These wings must still have organic carrier gas WITHOUT any mod enabled.

    This is the guard the audit actually needed. The obvious modern replacement,
    `F/A-18E Tanker`, is gated behind `ModSettings.fa18ef_tanker` (default False), so
    five factions briefly ended up with no carrier tanker at all in a default game.
    `GameGenerator` applies ModSettings, so the check must run against the post-mod
    roster -- reading the raw JSON hides exactly this bug.
    """
    faction = Faction.from_dict(
        json.loads((FACTIONS / name).read_text(encoding="utf-8"))
    )
    faction.apply_mod_settings(ModSettings())

    # `all_aircrafts` is declared list[UnitType[Any]] upstream; narrow it so the
    # AircraftType-only accessors below type-check.
    tankers = [
        a
        for a in faction.all_aircrafts
        if isinstance(a, AircraftType)
        and a.carrier_capable
        and a.capable_of(FlightType.REFUELING)
    ]
    assert tankers, (
        f"{faction.name} has no vanilla carrier tanker once mods are off "
        "(a mod-gated tanker does not count)"
    )


@pytest.mark.parametrize("path", sorted(CAMPAIGNS.glob("*.yaml")), ids=lambda p: p.name)
def test_no_campaign_tasks_the_viking_with_land_attack(path: Path) -> None:
    """A squadron whose airframe cannot fly its primary is silently dead.

    `Squadron.set_auto_assignable_mission_types` filters by capability, so naming
    the Viking on a strike primary yields an empty task set rather than an error --
    the failure mode this pins (it caught 16 Vikings sitting on DEAD).
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    land_attack = {t.value for t in LAND_ATTACK}
    for base, entries in (data.get("squadrons") or {}).items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            aircraft = entry.get("aircraft") or []
            if isinstance(aircraft, str):
                aircraft = [aircraft]
            if "S-3B Viking" not in aircraft:
                continue
            assert entry.get("primary") not in land_attack, (
                f"{path.name}: {base} tasks the Viking with "
                f"{entry.get('primary')} -- it can only fly Anti-ship"
            )
