"""The authored §82 arrival schedules must stay doctrinally coherent.

Two campaigns carry a schedule, and they are deliberately different shapes:

* **Baltic Fury** opens *offensively* (a NATO counter-offensive into a dense
  S-400/S-300 belt), so its arc is **SEAD/DEAD before strike** — you roll the
  belt back first and the deep-strike arm is worth having only once it can
  survive over the target.
* **Red Tide** opens *defensively* (holding the Fulda Gap). There is no door to
  kick on turn 1, so its arc is **hold -> stabilise -> counter-attack**, and
  what arrives later is the counter-offensive capability. A defensive battle
  cannot defer its CAS.

These tests pin the *rules*, not just the turn numbers, so a later laydown edit
that quietly defers the wrong thing (the enablers, the air-superiority backbone,
the Gap's CAS) fails CI instead of shipping a campaign whose opening cannot be
flown.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

import pytest
import yaml

from game.campaignloader.campaign import Campaign
from game.campaignloader.campaignairwingconfig import (
    CampaignAirWingConfig,
    SquadronConfig,
)

BALTIC_FURY = Path("resources/campaigns/operation_baltic_fury.yaml")
RED_TIDE = Path("resources/campaigns/red_tide.yaml")


class Scheduled(NamedTuple):
    turn: Optional[int]
    base: str
    primary: str
    aircraft: str
    note: Optional[str]


def squadrons(campaign: Path) -> List[Scheduled]:
    data: Dict[str, Any] = yaml.safe_load(campaign.read_text(encoding="utf-8"))
    out: List[Scheduled] = []
    for base, blocks in (data.get("squadrons") or {}).items():
        for block in blocks:
            config = SquadronConfig.from_data(block)
            aircraft = block.get("aircraft_type") or (block.get("aircraft") or [""])[0]
            out.append(
                Scheduled(
                    turn=config.available_from_turn,
                    base=str(base),
                    primary=config.primary.value,
                    aircraft=str(aircraft),
                    note=config.arrival_note,
                )
            )
    return out


def arrival_turns(campaign: Path, primary: str) -> List[int]:
    """Arrival turns for one primary task -- already narrowed to int."""
    return [a.turn for a in arrivals(campaign) if a.primary == primary and a.turn]


def arrivals(campaign: Path) -> List[Scheduled]:
    return [s for s in squadrons(campaign) if s.turn]


def schedule_of(campaign: Path) -> List[tuple[int, str]]:
    """(turn, aircraft) for every arrival, sorted -- the authored schedule."""
    out: List[tuple[int, str]] = []
    for a in arrivals(campaign):
        assert a.turn is not None
        out.append((a.turn, a.aircraft))
    return sorted(out)


def turn_one(campaign: Path) -> List[Scheduled]:
    return [s for s in squadrons(campaign) if not s.turn]


ALL_CAMPAIGNS = [BALTIC_FURY, RED_TIDE]

#: Tasks that make the rest of the wing work. Deferring one strands every
#: package that needs it, so an enabler must never be scheduled.
ENABLER_TASKS = {"AEW&C", "Refueling"}

#: Tasks that hold the air. At least one must be on the ramp from turn 1 or the
#: opening turn is unflyable regardless of what arrives later.
AIR_SUPERIORITY_TASKS = {"TARCAP", "BARCAP", "Escort"}


@pytest.mark.parametrize("campaign", ALL_CAMPAIGNS, ids=lambda p: p.stem)
def test_every_campaign_squadron_parses(campaign: Path) -> None:
    """A malformed available_from_turn raises, so parsing is the first guard."""
    assert squadrons(campaign), f"{campaign} authored no squadrons"


@pytest.mark.parametrize("campaign", ALL_CAMPAIGNS, ids=lambda p: p.stem)
def test_every_arrival_announces_itself(campaign: Path) -> None:
    """An arrival the player cannot see coming is the feature failing silently."""
    for arrival in arrivals(campaign):
        assert (
            arrival.note
        ), f"{arrival.aircraft} arrives on turn {arrival.turn} unannounced"


@pytest.mark.parametrize("campaign", ALL_CAMPAIGNS, ids=lambda p: p.stem)
def test_enablers_are_never_deferred(campaign: Path) -> None:
    """AEW&C and tankers make everything else work; they fly from turn 1."""
    for arrival in arrivals(campaign):
        assert arrival.primary not in ENABLER_TASKS, (
            f"{campaign.stem} defers an enabler ({arrival.primary} "
            f"{arrival.aircraft}) to turn {arrival.turn}"
        )


@pytest.mark.parametrize("campaign", ALL_CAMPAIGNS, ids=lambda p: p.stem)
def test_air_superiority_is_on_the_ramp_from_turn_one(campaign: Path) -> None:
    """Withholding the whole air-superiority arm is not a slope, it is a
    different campaign."""
    present = {s.primary for s in turn_one(campaign)}
    assert (
        present & AIR_SUPERIORITY_TASKS
    ), f"{campaign.stem} has no air-superiority squadron on turn 1"


@pytest.mark.parametrize("campaign", ALL_CAMPAIGNS, ids=lambda p: p.stem)
def test_arrival_turns_are_sane(campaign: Path) -> None:
    for arrival in arrivals(campaign):
        turn = arrival.turn
        assert turn is not None
        assert 1 <= turn <= 20, (
            f"{arrival.aircraft} arrives on turn {turn}, which is not a "
            f"turn a campaign realistically reaches"
        )


# ------------------------------------------------------- Baltic Fury (offense)


def test_baltic_fury_schedules_exactly_the_authored_arrivals() -> None:
    assert schedule_of(BALTIC_FURY) == [
        (3, "F/A-18C Hornet (Lot 20)"),
        (5, "[CH] JAS 39C Gripen"),
        (7, "F-15E Strike Eagle (Suite 4+)"),
        (7, "F/A-18F Super Hornet"),
        (9, "B-1B Lancer"),
    ]


def test_baltic_fury_rolls_the_belt_back_before_it_strikes() -> None:
    """The ordering principle: SEAD/DEAD before strike. The deep-strike arm must
    not arrive before the unit that makes its target survivable."""
    dead = arrival_turns(BALTIC_FURY, "DEAD")
    strike = arrival_turns(BALTIC_FURY, "Strike")
    assert (
        dead and strike
    ), "the campaign should schedule both a DEAD and a strike arrival"
    assert max(dead) < min(strike), "strike arrives before the DEAD rollback opens"


def test_baltic_fury_closes_its_barcap_hole_before_the_rollback() -> None:
    """Defensive counter-air precedes offensive DEAD -- which also matches the
    real accession order (Finland April 2023, Sweden March 2024)."""
    barcap = arrival_turns(BALTIC_FURY, "BARCAP")
    dead = arrival_turns(BALTIC_FURY, "DEAD")
    assert barcap and dead
    assert max(barcap) < min(dead)


def test_baltic_fury_keeps_a_growler_from_turn_one() -> None:
    """Turns 1-4 are deliberately Growler-thin, not SEAD-less: something must be
    able to service the belt while the Gripens are still in Sweden."""
    sead = [
        s
        for s in turn_one(BALTIC_FURY)
        if s.primary in {"SEAD", "SEAD Escort"} or "Growler" in s.aircraft
    ]
    assert sead, "no SEAD capability at all on turn 1"


def test_baltic_fury_keeps_the_raptors_from_turn_one() -> None:
    assert any("F-22A" in s.aircraft for s in turn_one(BALTIC_FURY))


def test_baltic_fury_keeps_ground_support_from_turn_one() -> None:
    """The land battle runs from turn 1 regardless of the air campaign's phase."""
    assert any(s.primary == "CAS" for s in turn_one(BALTIC_FURY))


# ----------------------------------------------------------- Red Tide (defense)


def test_red_tide_schedules_exactly_the_authored_arrivals() -> None:
    assert schedule_of(RED_TIDE) == [
        (4, "Mirage-F1EE"),
        (6, "F-15E Strike Eagle (Suite 4+)"),
        (8, "B-52H Stratofortress"),
    ]


def test_red_tide_never_defers_its_cas() -> None:
    """A defensive battle cannot defer the arm holding the ground. This is the
    single rule that distinguishes Red Tide's arc from Baltic Fury's."""
    for arrival in arrivals(RED_TIDE):
        assert arrival.primary not in {"CAS", "Armed Recon", "Air Assault"}, (
            f"Red Tide defers {arrival.primary} ({arrival.aircraft}) to turn "
            f"{arrival.turn}, but the Gap fight needs it from turn 1"
        )


def test_red_tide_keeps_its_sead_and_dead_from_turn_one() -> None:
    """Holding the Gap means keeping the SAM belt honest from the first mission."""
    tasks = {s.primary for s in turn_one(RED_TIDE)}
    assert "SEAD" in tasks and "DEAD" in tasks


def test_red_tide_counter_offensive_arrives_in_order() -> None:
    """hold -> stabilise -> counter-attack: escort depth, then deep interdiction,
    then the heavy stick."""
    escort = arrival_turns(RED_TIDE, "Escort")
    bai = arrival_turns(RED_TIDE, "BAI")
    strike = arrival_turns(RED_TIDE, "Strike")
    assert escort and bai and strike
    assert max(escort) < min(bai) and max(bai) < min(strike)


# ------------------------------------------------- the real loader binds them

#: The base each scheduled squadron must actually land on. A yaml-level check
#: cannot catch a base-id typo, because
#: ``CampaignAirWingConfig.from_campaign_data`` *logs a warning and skips* a
#: squadron whose base it cannot resolve -- so a bad id silently deletes the
#: arrival instead of failing. These pin the resolved ControlPoint names.
EXPECTED_BINDINGS = {
    BALTIC_FURY: {
        (3, "Hamburg", "F/A-18C Hornet (Lot 20)"),
        (5, "Nordholz", "[CH] JAS 39C Gripen"),
        (7, "Nordholz", "F-15E Strike Eagle (Suite 4+)"),
        (7, "CVN-75 Harry S. Truman", "F/A-18F Super Hornet"),
        (9, "Bremen", "B-1B Lancer"),
    },
    RED_TIDE: {
        (4, "Frankfurt", "Mirage-F1EE"),
        (6, "Frankfurt", "F-15E Strike Eagle (Suite 4+)"),
        (8, "Ramstein", "B-52H Stratofortress"),
    },
}


@pytest.mark.parametrize("campaign", ALL_CAMPAIGNS, ids=lambda p: p.stem)
def test_every_scheduled_squadron_binds_to_its_real_control_point(
    campaign: Path,
) -> None:
    loaded = Campaign.from_file(campaign)
    theater = loaded.load_theater(loaded.advanced_iads)
    config = CampaignAirWingConfig.from_campaign_data(
        loaded.data.get("squadrons", {}), theater
    )

    bound = set()
    for control_point, squadron_configs in config.by_location.items():
        for squadron_config in squadron_configs:
            if not squadron_config.available_from_turn:
                continue
            aircraft = (
                squadron_config.aircraft_type or (squadron_config.aircraft or [""])[0]
            )
            bound.add(
                (
                    squadron_config.available_from_turn,
                    control_point.name,
                    str(aircraft),
                )
            )

    assert bound == EXPECTED_BINDINGS[campaign]
