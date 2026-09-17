"""The [CH] Su-24MU must resolve non-empty loadouts for its planned tasks.

Regression guard, sibling of test_mig29mu2_loadouts.py: the customized_payloads
file shipped (PR #481) with filename "Su-24MU.lua" and unitType "Su-24MU", but
the CH pack update renamed the pydcs id to "CH_Su-24MU" (the unit yaml was
renamed to match, this file was missed). pydcs binds payload files by the
unitType FIELD, so the whole strike-preset set silently unbound and every
planned Fencer flew a clean airframe.
"""

import re
from pathlib import Path

import pytest
from dcs.payloads import PayloadDirectories
from dcs.unittype import FlyingType

from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from pydcs_extensions.ukrainemilitaryassetspack.ukrainemilitaryassetspack import (
    Su_24MU,
)

PAYLOADS_DIR = Path(__file__).parents[2] / "resources" / "customized_payloads"

# The Su-24MU is a strike platform -- CH_Su-24MU.yaml declares only A2G tasks.
A2G_TASKS = [
    FlightType.CAS,
    FlightType.BAI,
    FlightType.STRIKE,
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
    # "CH_Su-24MU", so a bare "Su-24MU" silently unbinds the whole file.
    text = (PAYLOADS_DIR / "CH_Su-24MU.lua").read_text()
    match = re.search(r'\["unitType"\]\s*=\s*"([^"]*)"', text)
    assert match is not None
    assert match.group(1) == Su_24MU.id == "CH_Su-24MU"


@pytest.mark.parametrize("task", A2G_TASKS, ids=lambda t: t.value)
def test_a2g_tasks_resolve_nonempty(task: FlightType) -> None:
    loadout = Loadout.default_for_task_and_aircraft(task, Su_24MU)
    assert loadout.pylons, f"{task.value} resolved an empty loadout"
