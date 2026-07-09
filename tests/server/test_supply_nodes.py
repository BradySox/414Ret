"""§53 P4b -- the supply-flow overlay emit (SupplyNodeJs.all_in_game).

Guards the selection contract: off => empty (hides the layer); on => only BLUE
fronts + producers, with the right readiness/production, and quiet rear CPs and the
enemy coalition excluded.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from dcs.mapping import LatLng

from game.server.game.models import SupplyNodeJs
from game.theater import Player


def _tgo(category: str, *alive: bool) -> Any:
    return SimpleNamespace(
        category=category, statics=[SimpleNamespace(alive=a) for a in alive]
    )


def _cp(
    name: str,
    owner: Player = Player.BLUE,
    *,
    front: bool = False,
    units: int = 0,
    tgos: list[Any] | None = None,
    supply: float = 0.0,
) -> Any:
    return SimpleNamespace(
        name=name,
        captured=owner,
        position=SimpleNamespace(latlng=lambda: LatLng(lat=1.0, lng=2.0)),
        has_active_frontline=front,
        ground_objects=list(tgos or []),
        base=SimpleNamespace(supply=supply, total_frontline_units=units),
    )


def _game(cps: list[Any], *, on: bool = True) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(war_economy=on),
        blue=SimpleNamespace(player=Player.BLUE),
        theater=SimpleNamespace(
            control_points_for=lambda player: [c for c in cps if c.captured == player],
        ),
    )


def test_off_emits_nothing() -> None:
    cps = [_cp("Kutaisi", front=True, units=5, supply=5.0)]
    assert SupplyNodeJs.all_in_game(_game(cps, on=False)) == []


def test_on_emits_fronts_and_producers_only() -> None:
    cps = [
        _cp("Kutaisi", front=True, units=5, supply=5.0),  # demand 10 -> 50%
        _cp("Batumi", tgos=[_tgo("factory", True)]),  # producer, no front
        _cp("Vaziani"),  # quiet rear -- neither -> excluded
        _cp("Mozdok", Player.RED, front=True, units=5, supply=0.0),  # enemy -> excluded
    ]
    nodes = {n.name: n for n in SupplyNodeJs.all_in_game(_game(cps))}

    assert set(nodes) == {"Kutaisi", "Batumi"}

    front = nodes["Kutaisi"]
    assert front.is_front is True
    assert front.production == 0.0
    assert abs(front.supply - 0.5) < 1e-9

    producer = nodes["Batumi"]
    assert producer.is_front is False
    assert producer.production == 8.0
    assert producer.supply == 1.0  # no front to starve
