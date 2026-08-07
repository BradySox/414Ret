"""The C-130J "King" must never outrank a rescue helo for CSAR.

Upstream restricts CSAR capability to helicopters, because the DCS AI ``Land`` task is
helicopter-only and a fixed-wing rescuer just orbits the survivor. The 414th overrides
that for the C-130J so the King can be flown as the on-scene commander it always was
(``resources/units/aircraft/C-130J-30.yaml``).

The override has a sharp edge: the auto-planner picks a rescue airframe by task
priority, so if the King's number ever climbs above a helo's, the planner can frag a
King for a rescue **no AI can finish** — and the pickup silently never happens. That is
a quiet failure with no error anywhere, which is exactly the kind this pins.

Squadron call 2026-08-07: the King is the lowest CSAR number in the fleet.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from game import persistency
from game.ato.flighttype import FlightType
from game.dcs.aircrafttype import AircraftType

KING = "C-130J-30"


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    # AircraftType._load_all reads the user weapon-injection dir, which asserts on
    # an unset saved-games folder. Same fixture tests/test_csar.py uses.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16886)


def _csar_priorities() -> dict[str, int]:
    found: dict[str, int] = {}
    for aircraft in AircraftType.iter_all():
        priority = aircraft.task_priorities.get(FlightType.CSAR)
        if priority is not None:
            found[aircraft.dcs_unit_type.id] = priority
    return found


def test_the_king_is_csar_capable_at_all() -> None:
    """The override itself — if this fails, the explicit yaml entry stopped working."""
    assert KING in _csar_priorities(), (
        f"{KING} lost its explicit `CSAR:` task entry. Upstream's derivation is "
        "helicopters-only, so without that entry the King cannot be fragged for CSAR."
    )


def test_the_king_never_outranks_a_rescue_helo() -> None:
    priorities = _csar_priorities()
    king = priorities.get(KING)
    assert king is not None

    helos = {name: value for name, value in priorities.items() if name != KING}
    assert helos, "no other CSAR-capable airframe found — the fixture is wrong"

    outranked = {name: value for name, value in helos.items() if value <= king}
    assert not outranked, (
        f"{KING} is at CSAR {king}, which is not below every rescue helo: {outranked}. "
        "The auto-planner picks by priority, so it can now frag a King for a rescue no "
        "AI can complete (the DCS Land task is helicopter-only) and the pickup silently "
        "never happens. Lower the King, or raise the helo."
    )
