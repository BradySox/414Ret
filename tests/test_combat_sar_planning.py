"""AI Combat SAR auto-package composition (SCAR rescue rework, Phase 5).

The standing rescue alert (``auto_combat_sar``) fields the rescue helo + a Sandy
(SCAR) escort, and a dedicated C-130 "King" on-scene commander when the coalition
owns one. These lock the proposed-flight composition.
"""

from __future__ import annotations

from typing import Any, cast

from game.ato.flighttype import FlightType
from game.commander.tasks.primitive.combatsar import PlanCombatSar


def test_combat_sar_alert_proposes_rescue_then_sandy() -> None:
    task = PlanCombatSar(cast(Any, object()))
    task.propose_flights()
    assert [f.task for f in task.flights] == [
        FlightType.COMBAT_SAR,  # rescue helo (or AICSAR)
        FlightType.SCAR,  # Sandy escort
    ]


def test_combat_sar_alert_fields_a_king_when_a_c130_is_owned() -> None:
    king = object()  # stands in for the owned C-130 AircraftType
    task = PlanCombatSar(cast(Any, object()), king_aircraft=cast(Any, king))
    task.propose_flights()
    assert [f.task for f in task.flights] == [
        FlightType.COMBAT_SAR,  # rescue helo / AICSAR
        FlightType.COMBAT_SAR,  # the C-130 King
        FlightType.SCAR,  # Sandy escort
    ]
    # The King flight is pinned to that specific airframe so it can't collapse
    # into a second rescue helo.
    king_flights = [f for f in task.flights if f.preferred_type is king]
    assert len(king_flights) == 1
