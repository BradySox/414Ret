"""The [CH] MiG-29MU2 must resolve armed loadouts for its planned tasks.

Regression guard: the customized_payloads file shipped (PR #481) with filename
"MiG-29MU2.lua" and unitType "MiG-29MU2", but the CH pack update renamed the
pydcs id to "CH_MiG-29MU2" (the yaml was renamed to match, this file was missed).
pydcs binds payload files by the unitType FIELD, so the whole preset set silently
unbound -- every planned Fulcrum resolved Loadout.empty_loadout() and flew clean.
"""

import re
from pathlib import Path

import pytest
from dcs.payloads import PayloadDirectories
from dcs.unittype import FlyingType

from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from pydcs_extensions.ukrainemilitaryassetspack.ukrainemilitaryassetspack import (
    MiG_29MU2,
)

PAYLOADS_DIR = Path(__file__).parents[2] / "resources" / "customized_payloads"

# The tasks the CH_MiG-29MU2.yaml declares -- each must resolve a non-empty,
# task-appropriate preset from the payload file.
A2A_TASKS = [
    FlightType.BARCAP,
    FlightType.TARCAP,
    FlightType.ESCORT,
    FlightType.SWEEP,
]
A2G_TASKS = [
    FlightType.CAS,
    FlightType.BAI,
    FlightType.STRIKE,
    FlightType.SEAD,
    FlightType.DEAD,
    FlightType.OCA_AIRCRAFT,
    FlightType.OCA_RUNWAY,
]


@pytest.fixture(autouse=True)
def payload_dirs() -> None:
    PayloadDirectories.set_fallback(PAYLOADS_DIR)
    FlyingType._payload_cache = None  # type: ignore[assignment]


def test_payload_file_binds_to_the_pydcs_id() -> None:
    # pydcs keys payload files by the unitType FIELD; the CH pack id is
    # "CH_MiG-29MU2", so a bare "MiG-29MU2" silently unbinds the whole file.
    text = (PAYLOADS_DIR / "CH_MiG-29MU2.lua").read_text()
    match = re.search(r'\["unitType"\]\s*=\s*"([^"]*)"', text)
    assert match is not None
    assert match.group(1) == MiG_29MU2.id == "CH_MiG-29MU2"


@pytest.mark.parametrize("task", A2A_TASKS, ids=lambda t: t.value)
def test_a2a_tasks_resolve_armed(task: FlightType) -> None:
    loadout = Loadout.default_for_task_and_aircraft(task, MiG_29MU2)
    assert loadout.pylons, f"{task.value} resolved an empty loadout"
    a2a = [
        w
        for w in loadout.pylons.values()
        if w is not None and re.search(r"AIM-\d|R-\d|AIM_\d", w.name)
    ]
    assert a2a, f"{task.value} loadout {loadout.name} has no A2A missile"


@pytest.mark.parametrize("task", A2G_TASKS, ids=lambda t: t.value)
def test_a2g_tasks_resolve_nonempty(task: FlightType) -> None:
    loadout = Loadout.default_for_task_and_aircraft(task, MiG_29MU2)
    assert loadout.pylons, f"{task.value} resolved an empty loadout"
