"""Briefing emitter (dcsRetribution.briefing) -- the mission-start popup's config.

Locks the shape the ``briefing`` plugin consumes: a shared header
(campaign/mission/date/time) plus one record per **player-crewed** flight
(callsign/aircraft/task/field). AI-only flights are excluded; the node is absent
when the setting is off or the mission has no player flight, so the plugin no-ops.
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Any

from game.missiongenerator.briefingluadata import populate_briefing_lua
from game.missiongenerator.luagenerator import LuaData, LuaValue


def _kv(item: Any) -> dict[str, Any]:
    vals = item.value
    if isinstance(vals, LuaValue):
        vals = [vals]
    return {v.key: v.value for v in vals}


def _flight(
    group: str,
    callsign: str,
    *,
    player: bool = True,
    aircraft: str = "F/A-18C",
    task: str = "BARCAP",
    airfield: str = "Kutaisi",
) -> Any:
    return SimpleNamespace(
        client_units=["human"] if player else [],
        group_name=group,
        callsign=callsign,
        aircraft_type=SimpleNamespace(display_name=aircraft),
        task_display_name=task,
        departure=SimpleNamespace(airfield_name=airfield),
    )


def _game(*, on: bool = True, turn: int = 0, campaign: str = "Red Tide") -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(mission_briefing_popup=on),
        campaign_name=campaign,
        turn=turn,
        current_day=datetime.date(1968, 6, 12),
        conditions=SimpleNamespace(start_time=datetime.datetime(1968, 6, 12, 14, 30)),
    )


def _briefing(game: Any, flights: list[Any]) -> LuaData | None:
    root = LuaData("dcsRetribution")
    md = SimpleNamespace(flights=flights)
    populate_briefing_lua(root, game, md)  # type: ignore[arg-type]
    node = root.get_item("briefing")
    assert node is None or isinstance(node, LuaData)
    return node


def test_emits_header_and_one_record_per_player_flight() -> None:
    node = _briefing(
        _game(turn=2),
        [_flight("Enfield 1-1", "Enfield11", aircraft="F/A-18C", task="BARCAP")],
    )
    assert node is not None

    header = node.get_item("header")
    assert isinstance(header, LuaData)
    hk = _kv(header)
    assert hk["campaign"] == "Red Tide"
    assert hk["mission"] == "2"  # raw game.turn (matches the kneeboard's "Turn N")
    assert hk["date"] == "Wednesday 12 June 1968"
    assert hk["time"] == "14:30L"

    flights = node.get_item("flights")
    assert isinstance(flights, LuaData)
    recs = [_kv(r) for r in flights.objects]
    assert len(recs) == 1
    assert recs[0] == {
        "group": "Enfield 1-1",
        "callsign": "Enfield11",
        "aircraft": "F/A-18C",
        "task": "BARCAP",
        "airfield": "Kutaisi",
    }


def test_excludes_ai_only_flights() -> None:
    node = _briefing(
        _game(),
        [
            _flight("Enfield 1-1", "Enfield11", player=True),
            _flight("Dodge 2-1", "Dodge21", player=False),
        ],
    )
    assert node is not None
    flights = node.get_item("flights")
    assert isinstance(flights, LuaData)
    recs = [_kv(r) for r in flights.objects]
    assert [r["group"] for r in recs] == ["Enfield 1-1"]


def test_no_node_when_no_player_flight() -> None:
    node = _briefing(_game(), [_flight("Dodge 2-1", "Dodge21", player=False)])
    assert node is None


def test_gated_off_by_the_setting() -> None:
    node = _briefing(_game(on=False), [_flight("Enfield 1-1", "Enfield11")])
    assert node is None
