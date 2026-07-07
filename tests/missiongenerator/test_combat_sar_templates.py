"""On-demand Combat SAR rescue templates (§21 rework).

``AircraftGenerator.spawn_combat_sar_templates`` drops a cold late-activation
rescue-helo template the combatsar runtime clones when a pilot goes down and no
player CSAR package is up (replacing the retired standing orbit). These pin the
guard logic -- the actual template group creation mirrors the proven QRA
``spawn_intercept_templates`` path and rides the in-game pass.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.ato.flighttype import FlightType
from game.missiongenerator.aircraft.aircraftgenerator import AircraftGenerator


def _generator(settings: Any, blue: Any = None) -> AircraftGenerator:
    gen = AircraftGenerator.__new__(AircraftGenerator)
    gen.game = SimpleNamespace(settings=settings, blue=blue)  # type: ignore[assignment]
    gen.mission_data = SimpleNamespace(combat_sar_templates=None)  # type: ignore[assignment]
    return gen


def _squadron(*, helicopter: bool, csar_capable: bool) -> Any:
    return SimpleNamespace(
        aircraft=SimpleNamespace(
            helicopter=helicopter,
            capable_of=lambda task: csar_capable and task is FlightType.COMBAT_SAR,
        ),
        location=SimpleNamespace(name="Balad"),
    )


def _blue(squadrons: list[Any]) -> Any:
    return SimpleNamespace(
        air_wing=SimpleNamespace(iter_squadrons=lambda: iter(squadrons))
    )


def test_noop_when_auto_combat_sar_off() -> None:
    gen = _generator(SimpleNamespace(auto_combat_sar=False))
    gen.spawn_combat_sar_templates()
    assert gen.mission_data.combat_sar_templates is None


def test_noop_when_no_csar_capable_helo_owned() -> None:
    # A fixed-wing CSAR airframe (a King C-130) is not a rescue helo; an unarmed
    # transport helo without the COMBAT_SAR task is not CSAR-capable. Neither yields
    # an on-demand rescue template.
    squadrons = [
        _squadron(helicopter=False, csar_capable=True),  # King, not a helo
        _squadron(helicopter=True, csar_capable=False),  # helo, not CSAR-tasked
    ]
    gen = _generator(SimpleNamespace(auto_combat_sar=True), _blue(squadrons))
    gen.spawn_combat_sar_templates()
    assert gen.mission_data.combat_sar_templates is None
