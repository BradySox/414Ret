"""The F-14 family must resolve armed loadouts for its fighter tasks.

Regression guard for the 2026-07-17 Scenic Route finding: PR #457 stripped the
F-14 payload files to the single "Retribution TARPS" preset on the assumption
that non-recon tasking "falls back to the pydcs default" -- but pydcs ships no
payloads at all, so every BARCAP/TARCAP/Escort-tasked Tomcat (both coalitions)
resolved Loadout.empty_loadout() and flew clean into fighter engagements
(four blue F-14Bs died on station without a shot in reply).

Also pins the F-14A-135-GR-Early unitType fix: upstream's payload file declares
unitType "F-14A-135-GR" (missing -Early), and pydcs binds payload files by that
field, so the Early variant resolved no payloads at all -- not even TARPS.

And pins the 2026-08-06 F-14B(U) pass. That variant arrived with upstream #904 and
never received the fork's F-14 data treatment, so it shipped a stock task table:
a SEAD entry on an airframe carrying no anti-radiation missile (which also opens the
derived SEAD Sweep lane), no TARPS despite being the most capable Tomcat in the tree,
and no air_refuel_type -- which reads as "compatible with any tanker", boom included.
"""

import re
from pathlib import Path

import pytest
from dcs.payloads import PayloadDirectories
from dcs.planes import (
    F_14A,
    F_14A_135_GR,
    F_14A_135_GR_Early,
    F_14A_95_GR,
    F_14B,
    F_14BU,
)
from dcs.unittype import FlyingType

from game.ato.flighttype import FlightType
from game import persistency
from game.ato.loadouts import Loadout
from game.dcs.aircrafttype import AircraftType

PAYLOADS_DIR = Path(__file__).parent.parent / "resources" / "customized_payloads"

# F-14A-95-GR is the Iranian "Block 95-GR Export" -- fielded by [CH] Iran 2020
# (Scenic Route Merged) with A-model Phoenix presets, so it must resolve armed too.
TOMCATS = [F_14B, F_14BU, F_14A_135_GR, F_14A_135_GR_Early, F_14A, F_14A_95_GR]

# The Export declares no TARPS task (its yaml carries no TARPS entry, so it is
# never tasked recon) -- only these variants need the "Retribution TARPS" preset.
TARPS_TOMCATS = [F_14B, F_14BU, F_14A_135_GR, F_14A_135_GR_Early, F_14A]

FIGHTER_TASKS = [
    FlightType.BARCAP,
    FlightType.TARCAP,
    FlightType.ESCORT,
    FlightType.SWEEP,
    FlightType.INTERCEPTION,
]


@pytest.fixture
def unit_data(tmp_path: Path) -> None:
    # AircraftType.named()/named_for_dcs_type() load the unit data + weapon DB, which
    # needs a Saved Games root. Not autouse: the loadout tests below read payload files
    # directly and must not pay for it.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16893)


@pytest.fixture(autouse=True)
def payload_dirs() -> None:
    # Force a rescan against the repo's payload dir regardless of what earlier
    # tests (or a developer's Saved Games) left in the class-level cache.
    PayloadDirectories.set_fallback(PAYLOADS_DIR)
    FlyingType._payload_cache = None  # type: ignore[assignment]


@pytest.mark.parametrize("aircraft", TOMCATS, ids=lambda a: a.id)
@pytest.mark.parametrize("task", FIGHTER_TASKS, ids=lambda t: t.value)
def test_tomcat_fighter_tasks_resolve_armed(
    aircraft: type[FlyingType], task: FlightType
) -> None:
    loadout = Loadout.default_for_task_and_aircraft(task, aircraft)
    assert loadout.pylons, f"{aircraft.id} {task.value} resolved an empty loadout"
    # Match on the weapon NAME, not the CLSID -- the AI F-14A's stores use
    # opaque GUID CLSIDs while the Heatblur jets use readable ones.
    a2a = [
        w
        for w in loadout.pylons.values()
        if w is not None and re.search(r"AIM-\d|AIM_\d", w.name)
    ]
    assert a2a, f"{aircraft.id} {task.value} loadout {loadout.name} has no A2A missile"


@pytest.mark.parametrize("aircraft", TARPS_TOMCATS, ids=lambda a: a.id)
def test_tomcat_tarps_preset_resolves(aircraft: type[FlyingType]) -> None:
    loadout = Loadout.default_for_task_and_aircraft(FlightType.TARPS, aircraft)
    assert loadout.name == "Retribution TARPS"
    assert any(
        w is not None and "TARPS" in (w.clsid or "") for w in loadout.pylons.values()
    )


def test_the_tomcat_is_never_tasked_as_a_weasel(unit_data: None) -> None:
    """No Tomcat carries an anti-radiation missile, so none may be tasked SEAD.

    The airframe data is the only gate: a SEAD entry makes the type auto-assignable to
    SEAD *and* to the derived SEAD Sweep lane, and the planner would frag it against a
    radar SAM armed with decoys and iron. (The Desert Storm pass hit the same class of
    bug through the `air-to-ground` secondary alias.)
    """
    weasel = {FlightType.SEAD, FlightType.SEAD_SWEEP, FlightType.SEAD_ESCORT}
    for aircraft in TOMCATS:
        for variant in AircraftType.for_dcs_type(aircraft):
            offenders = sorted(t.value for t in variant.task_priorities if t in weasel)
            assert (
                not offenders
            ), f"{variant.variant_id} is tasked {offenders} with no ARM"


def test_the_upgraded_tomcat_outranks_the_b_it_upgrades(unit_data: None) -> None:
    """The B(U) is the later, more capable jet -- its combat weights must reflect that.

    Guards against a future upstream sync restoring the stock table, where every
    air-to-air task sat at a flat 530 and the B(U) *lost* BARCAP to the older F-14B
    (585) while beating it at Escort.
    """
    b = AircraftType.named("F-14B Tomcat")
    bu = AircraftType.named("F-14B(U) Tomcat")
    assert bu.air_refuel_type is not None, "B(U) must declare a refuelling method"
    assert bu.air_refuel_type == b.air_refuel_type
    shared = set(b.task_priorities) & set(bu.task_priorities) - {FlightType.TARPS}
    assert shared, "expected the two Tomcats to share combat tasks"
    for task in shared:
        assert bu.task_priorities[task] > b.task_priorities[task], (
            f"F-14B(U) should outrank the F-14B at {task.value} "
            f"({bu.task_priorities[task]} vs {b.task_priorities[task]})"
        )


def test_early_tomcat_payload_file_binds_to_its_own_type() -> None:
    # pydcs keys payload files by the unitType FIELD, not the filename; upstream
    # declares "F-14A-135-GR" here, which silently unbinds the whole file.
    text = (PAYLOADS_DIR / "F-14A-135-GR-Early.lua").read_text()
    match = re.search(r'\["unitType"\]\s*=\s*"([^"]*)"', text)
    assert match is not None
    assert match.group(1) == "F-14A-135-GR-Early"
