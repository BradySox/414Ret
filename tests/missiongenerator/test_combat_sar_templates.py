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
from unittest.mock import patch

from game.ato.flighttype import FlightType
from game.missiongenerator.aircraft.aircraftgenerator import AircraftGenerator

_AG = "game.missiongenerator.aircraft.aircraftgenerator"


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


def _template_generator() -> AircraftGenerator:
    gen = AircraftGenerator.__new__(AircraftGenerator)
    gen.country_assigner = SimpleNamespace(  # type: ignore[assignment]
        for_squadron=lambda squadron: SimpleNamespace(id=1)
    )
    gen.game = SimpleNamespace(  # type: ignore[assignment]
        db=SimpleNamespace(flights=object()), settings=SimpleNamespace()
    )
    gen.mission = object()  # type: ignore[assignment]
    gen.helipads = {}
    gen.ground_spawns_roadbase = {}
    gen.ground_spawns_large = {}
    gen.ground_spawns = {}
    gen.mission_data = SimpleNamespace(  # type: ignore[assignment]
        combat_sar_templates=None, parked_rescue_helos=[]
    )
    return gen


def _fake_flight(*_args: Any, **_kwargs: Any) -> Any:
    return SimpleNamespace(state=None, roster=SimpleNamespace(clear=lambda: None))


def test_template_flight_is_barcap_not_the_jolly_callsign_type() -> None:
    # A COMBAT_SAR flight carries the 'Jolly' callsign, which pydcs cannot resolve on
    # the airfield-spawn fallback a helo hits when its helipads are full -> an in-game
    # ValueError. The template flight must be BARCAP (airfield-valid callsign), exactly
    # like the untasked-aircraft / QRA templates it mirrors.
    captured: dict[str, Any] = {}

    def capturing_flight(*args: Any, **_kwargs: Any) -> Any:
        captured["flight_type"] = args[3]
        return _fake_flight()

    spawner = SimpleNamespace(create_combat_sar_template=lambda name: SimpleNamespace())
    with patch(f"{_AG}.Flight", capturing_flight), patch(
        f"{_AG}.Package", lambda *a, **k: object()
    ), patch(f"{_AG}.Completed", lambda *a, **k: object()), patch(
        f"{_AG}.FlightGroupSpawner", lambda *a, **k: spawner
    ):
        gen = _template_generator()
        squadron = SimpleNamespace(location=SimpleNamespace(name="Balad"))
        result = gen._create_combat_sar_template(
            squadron, "CombatSAR On-Demand Rescue"  # type: ignore[arg-type]
        )

    assert result == "CombatSAR On-Demand Rescue"
    assert captured["flight_type"] is FlightType.BARCAP


def test_template_creation_failure_degrades_to_none_not_a_crash() -> None:
    # The exact in-game failure: helipads full -> airfield fallback -> pydcs
    # `_assign_callsign` raises "'Jolly' is not in list". An optional rescue template
    # must NEVER break mission generation -- it degrades to None (the parked ramp helos
    # still cover the rescue).
    def raise_jolly(name: str) -> Any:
        raise ValueError("'Jolly' is not in list")

    spawner = SimpleNamespace(create_combat_sar_template=raise_jolly)
    with patch(f"{_AG}.Flight", _fake_flight), patch(
        f"{_AG}.Package", lambda *a, **k: object()
    ), patch(f"{_AG}.Completed", lambda *a, **k: object()), patch(
        f"{_AG}.FlightGroupSpawner", lambda *a, **k: spawner
    ):
        gen = _template_generator()
        squadron = SimpleNamespace(location=SimpleNamespace(name="Balad"))
        result = gen._create_combat_sar_template(squadron, "X")  # type: ignore[arg-type]

    assert result is None
