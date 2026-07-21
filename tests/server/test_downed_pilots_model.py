"""§21 downed-aviator map overlay emit (DownedPilotJs.all_in_game).

Guards the contract: nobody down => empty (hides the layer); MIA evaders emit
at their last known position with the turns-down detail; POWs emit at their
holding field with the SITREP-matched turn-countdown clock ("N turns left");
missing pilot/holding-field data degrades, never raises.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from dcs.mapping import LatLng

from game.server.game.models import DownedPilotJs


def _latlng_point(lat: float, lng: float) -> Any:
    return SimpleNamespace(latlng=lambda: LatLng(lat=lat, lng=lng))


def _mia(name: Optional[str] = "Capt Mitchell", *, turn_downed: int = 3) -> Any:
    return SimpleNamespace(
        unit_name="jet 1-1",
        x=100.0,
        y=200.0,
        pilot=None if name is None else SimpleNamespace(name=name),
        turn_downed=turn_downed,
    )


def _pow(
    name: Optional[str] = "Lt Wells",
    *,
    holding_cp_id: Any = "cp-1",
    turns_remaining: int = 2,
) -> Any:
    return SimpleNamespace(
        airframe_unit_name="jet 2-1",
        x=300.0,
        y=400.0,
        pilot=None if name is None else SimpleNamespace(name=name),
        holding_cp_id=holding_cp_id,
        turns_remaining=turns_remaining,
    )


def _game(
    *,
    mia: list[Any] | None = None,
    pows: list[Any] | None = None,
    turn: int = 5,
    holding_cp: Any = None,
) -> Any:
    def find_cp(cp_id: Any) -> Any:
        if holding_cp is None:
            raise KeyError(cp_id)
        return holding_cp

    return SimpleNamespace(
        turn=turn,
        downed_pilots=list(mia or []),
        blue=SimpleNamespace(pending_pow_recoveries=list(pows or [])),
        theater=SimpleNamespace(find_control_point_by_id=find_cp),
        point_in_world=lambda x, y: _latlng_point(x / 100.0, y / 100.0),
    )


def test_nobody_down_emits_nothing() -> None:
    assert DownedPilotJs.all_in_game(_game()) == []


def test_mia_emits_at_last_known_position() -> None:
    pilots = DownedPilotJs.all_in_game(_game(mia=[_mia(turn_downed=3)], turn=5))
    assert len(pilots) == 1
    entry = pilots[0]
    assert entry.status == "mia"
    assert entry.name == "Capt Mitchell"
    assert entry.detail == "evading (2 turns down)"
    assert entry.position.lat == 1.0 and entry.position.lng == 2.0


def test_pow_emits_at_the_holding_field_with_the_clock() -> None:
    holding = SimpleNamespace(name="Mozdok", position=_latlng_point(9.0, 9.0))
    pilots = DownedPilotJs.all_in_game(
        _game(pows=[_pow(turns_remaining=2)], holding_cp=holding)
    )
    assert len(pilots) == 1
    entry = pilots[0]
    assert entry.status == "pow"
    assert entry.name == "Lt Wells"
    assert entry.detail == "held at Mozdok (2 turns left)"
    assert entry.position.lat == 9.0  # the holding field, not the capture spot


def test_missing_data_degrades_never_raises() -> None:
    # No pilot object -> generic name; unknown holding cp -> capture position +
    # "an unknown location"; single-turn singulars read right.
    pilots = DownedPilotJs.all_in_game(
        _game(
            mia=[_mia(name=None, turn_downed=4)],
            pows=[_pow(name=None, holding_cp_id="gone", turns_remaining=1)],
            turn=5,
        )
    )
    assert [p.status for p in pilots] == ["mia", "pow"]
    assert pilots[0].name == "Downed aviator"
    assert pilots[0].detail == "evading (1 turn down)"
    assert pilots[1].name == "Downed aviator"
    assert pilots[1].detail == "held at an unknown location (1 turn left)"
    assert pilots[1].position.lat == 3.0  # fell back to the capture position
