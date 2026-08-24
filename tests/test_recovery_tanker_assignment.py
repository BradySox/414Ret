"""RECOVERY is offered to the squadrons capable of it.

A squadron's auto-assignable set is `secondary | {primary}` from the campaign's
air-wing config, and no campaign in the tree lists Recovery as either. The
carrier tanker squadron a campaign authored was therefore capable of recovery
tanking, sat on the boat while dozens of aircraft recovered, and was never
offered the tasking -- which left the whole recovery-tanker path unreachable:
`RecoverySupport`, `PlanRecovery`, `RecoveryTankerFlightPlan`, the carrier-ETA
queue at the end of `schedule_missions`, and both of its settings.

Measured 2026-08-24 on three saves with carriers: the tanker squadron was
present and on the boat in each (A-6E Tanker x4 on CVN-71, S-3B Tanker x2 on
CVN-75), its auto-assignable set was `['Refueling']` in every case, and zero
RECOVERY packages were planned on any save or turn.

Same hole CSAR fell into, and fixed the same way.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from game import persistency
from game.ato.flighttype import FlightType
from game.campaignloader.campaignairwingconfig import SquadronConfig
from game.dcs.aircrafttype import AircraftType
from game.squadrons.squadron import Squadron


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16886)


def _aircraft_named(display_name: str) -> Any:
    for aircraft in AircraftType.iter_all():
        if aircraft.display_name == display_name:
            return aircraft
    raise AssertionError(f"aircraft {display_name} not found")


def _squadron_flying(display_name: str, tasks: set[FlightType]) -> Squadron:
    squadron = Squadron.__new__(Squadron)
    squadron.aircraft = _aircraft_named(display_name)
    squadron.auto_assignable_mission_types = set(tasks)
    return squadron


def test_no_campaign_lists_recovery_as_a_squadron_task() -> None:
    """The premise. If a campaign ever does, this fix is no longer the whole story."""
    campaigns = Path("resources/campaigns")
    listing = [
        p for p in campaigns.glob("*.yaml") if "Recovery" in p.read_text("utf-8")
    ]
    assert not listing, f"campaigns now list Recovery: {[p.name for p in listing]}"


def test_a_carrier_tanker_is_offered_recovery() -> None:
    squadron = _squadron_flying("A-6E Tanker", {FlightType.REFUELING})
    squadron.enable_recovery_if_capable()
    assert FlightType.RECOVERY in squadron.auto_assignable_mission_types


def test_the_viking_tanker_is_offered_recovery() -> None:
    squadron = _squadron_flying("S-3B Tanker", {FlightType.REFUELING})
    squadron.enable_recovery_if_capable()
    assert FlightType.RECOVERY in squadron.auto_assignable_mission_types


def test_a_land_tanker_is_not_offered_recovery() -> None:
    """The capability filter is what keeps this from touching every tanker."""
    squadron = _squadron_flying("KC-135 Stratotanker", {FlightType.REFUELING})
    squadron.enable_recovery_if_capable()
    assert FlightType.RECOVERY not in squadron.auto_assignable_mission_types


def test_a_fighter_is_not_offered_recovery() -> None:
    squadron = _squadron_flying("F/A-18C Hornet (Lot 20)", {FlightType.CAS})
    squadron.enable_recovery_if_capable()
    assert FlightType.RECOVERY not in squadron.auto_assignable_mission_types


def test_set_auto_assignable_does_not_force_recovery_on() -> None:
    """The Air Wing dialog applies the player's choices through this call.

    Seeding RECOVERY inside it would make the tasking impossible to turn off,
    which is exactly why CSAR is seeded by its own method instead.
    """
    squadron = _squadron_flying("A-6E Tanker", {FlightType.REFUELING})
    squadron.enable_recovery_if_capable()
    squadron.set_auto_assignable_mission_types({FlightType.REFUELING})
    assert FlightType.RECOVERY not in squadron.auto_assignable_mission_types


def test_a_faction_fields_a_recovery_capable_tanker() -> None:
    """Without one in the tankers pool no wing can raise the squadron at all."""
    capable = {"A-6E Tanker", "S-3B Tanker"}
    factions = Path("resources/factions")
    fielding = [
        p.name
        for p in factions.glob("*.json")
        if capable & set(json.loads(p.read_text("utf-8")).get("tankers") or [])
    ]
    assert fielding, "no faction fields a recovery-capable tanker"


def test_the_campaign_config_still_does_not_claim_recovery() -> None:
    """RECOVERY is seeded by its own method, not folded into the config set.

    The config set is what the campaign asked for; keeping RECOVERY out of it is
    what lets the migrator's one-shot latch and the dialog's off-switch both
    behave.
    """
    config = SquadronConfig.from_data({"primary": "Refueling"})
    assert FlightType.RECOVERY not in config.auto_assignable
