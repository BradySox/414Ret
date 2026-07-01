"""Sandy (FlightType.SCAR) group names feed into dcsRetribution.CombatSAR.sandys.

Sandy previously wasn't part of the CombatSAR data table at all -- the runtime had
no way to know which groups were the rescue-escort flights, so it could never
dynamically retask one toward a live ejection (see 414th-features.md §15 gotcha
and docs/dev/design/414th-scar-rescue-rework-notes.md). This locks the bucketing
(a SCAR flight lands in blue_sandys/red_sandys, never in the rescue/king buckets)
and the emission (the side's node carries a "sandys" list of group names).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.ato.flighttype import FlightType
from game.missiongenerator.luagenerator import LuaData, LuaItem, LuaValue, LuaGenerator


def _string_list(item: LuaItem | None) -> list[str]:
    assert item is not None
    value = item.value
    assert isinstance(value, LuaValue)
    assert isinstance(value.value, list)
    return value.value


def _key_values(item: LuaItem) -> list[LuaValue]:
    value = item.value
    assert isinstance(value, list)
    return value


def _fd(
    group_name: str, flight_type: FlightType, *, is_blue: bool, helo: bool = False
) -> Any:
    return SimpleNamespace(
        group_name=group_name,
        flight_type=flight_type,
        friendly=SimpleNamespace(is_blue=is_blue),
        aircraft_type=SimpleNamespace(helicopter=helo),
        combat_sar_king=None,
        departure=SimpleNamespace(airfield_name="Kutaisi"),
    )


def _coalition(country_id: int) -> Any:
    return SimpleNamespace(
        opponent=SimpleNamespace(
            faction=SimpleNamespace(country=SimpleNamespace(id=country_id))
        ),
        pending_csars=[],
    )


def _generator(flights: list[Any], *, auto_combat_sar: bool = False) -> LuaGenerator:
    gen = LuaGenerator.__new__(LuaGenerator)
    gen.mission_data = SimpleNamespace(flights=flights)  # type: ignore[assignment]
    gen.game = SimpleNamespace(  # type: ignore[assignment]
        settings=SimpleNamespace(
            auto_combat_sar=auto_combat_sar, scar_command_post_intel=False
        ),
        blue=_coalition(49),
        red=_coalition(2),
    )
    # Bypass pilot-template generation (needs a real Mission/theater) -- it's
    # separate, pre-existing logic unrelated to this Sandy-bucketing change.
    gen._generate_combat_sar_pilot_template = lambda coalition: "Combat SAR Downed Pilot"  # type: ignore[method-assign]
    return gen


def test_sandy_flight_lands_in_the_sandys_list_not_rescue_or_kings() -> None:
    flights = [
        _fd("Jolly-1", FlightType.COMBAT_SAR, is_blue=True, helo=True),
        _fd("King-1", FlightType.COMBAT_SAR, is_blue=True, helo=False),
        _fd("Sandy-1", FlightType.SCAR, is_blue=True),
        _fd("Sandy-2", FlightType.SCAR, is_blue=True),
    ]
    gen = _generator(flights)
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    combat_sar = lua_data.get_item("CombatSAR")
    assert combat_sar is not None
    assert _string_list(combat_sar.get_item("sandys")) == ["Sandy-1", "Sandy-2"]
    # Sandy never leaks into the rescueHelos or kings lists.
    assert _string_list(combat_sar.get_item("rescueHelos")) == ["Jolly-1"]
    kings_item = combat_sar.get_item("kings")
    assert isinstance(kings_item, LuaData)
    kings_objects = kings_item.objects
    assert len(kings_objects) == 1
    assert any(
        v.key == "group" and v.value == "King-1" for v in _key_values(kings_objects[0])
    )


def test_no_sandy_flights_emits_an_empty_list() -> None:
    flights = [_fd("Jolly-1", FlightType.COMBAT_SAR, is_blue=True, helo=True)]
    gen = _generator(flights)
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    combat_sar = lua_data.get_item("CombatSAR")
    assert combat_sar is not None
    assert _string_list(combat_sar.get_item("sandys")) == []


def test_red_sandy_lands_on_the_red_node() -> None:
    flights = [
        _fd("RedJolly-1", FlightType.COMBAT_SAR, is_blue=False, helo=True),
        _fd("RedSandy-1", FlightType.SCAR, is_blue=False),
        _fd("BlueJolly-1", FlightType.COMBAT_SAR, is_blue=True, helo=True),
    ]
    gen = _generator(flights)
    lua_data = LuaData("dcsRetribution")

    gen._generate_combat_sar(lua_data)

    combat_sar = lua_data.get_item("CombatSAR")
    assert combat_sar is not None
    assert _string_list(combat_sar.get_item("sandys")) == []
    red_node = combat_sar.get_item("red")
    assert red_node is not None
    assert _string_list(red_node.get_item("sandys")) == ["RedSandy-1"]
