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
"""

import re
from pathlib import Path

import pytest
from dcs.payloads import PayloadDirectories
from dcs.planes import F_14A, F_14A_135_GR, F_14A_135_GR_Early, F_14B
from dcs.unittype import FlyingType

from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout

PAYLOADS_DIR = Path(__file__).parent.parent / "resources" / "customized_payloads"

TOMCATS = [F_14B, F_14A_135_GR, F_14A_135_GR_Early, F_14A]

FIGHTER_TASKS = [
    FlightType.BARCAP,
    FlightType.TARCAP,
    FlightType.ESCORT,
    FlightType.SWEEP,
    FlightType.INTERCEPTION,
]


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


@pytest.mark.parametrize("aircraft", TOMCATS, ids=lambda a: a.id)
def test_tomcat_tarps_preset_resolves(aircraft: type[FlyingType]) -> None:
    loadout = Loadout.default_for_task_and_aircraft(FlightType.TARPS, aircraft)
    assert loadout.name == "Retribution TARPS"
    assert any(
        w is not None and "TARPS" in (w.clsid or "") for w in loadout.pylons.values()
    )


def test_early_tomcat_payload_file_binds_to_its_own_type() -> None:
    # pydcs keys payload files by the unitType FIELD, not the filename; upstream
    # declares "F-14A-135-GR" here, which silently unbinds the whole file.
    text = (PAYLOADS_DIR / "F-14A-135-GR-Early.lua").read_text()
    match = re.search(r'\["unitType"\]\s*=\s*"([^"]*)"', text)
    assert match is not None
    assert match.group(1) == "F-14A-135-GR-Early"
