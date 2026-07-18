"""§70 COMINT (C0) — tiering, collector record, leak determinism, reveal rules.

Locks the contracts from the design note: sources are the prerequisite for every
tier (a dead net yields nothing), OFF is an exact no-op, the collector must
survive to bank a take, the tasking leak is deterministic (no reroll across
regeneration), the reveal snaps the nearest concealed site inside source range,
``map_hidden`` (§50 ambush teams) is never revealed, and the reveal is
idempotent under initialize_turn's re-init cases.
"""

from __future__ import annotations

import datetime
import math
from types import SimpleNamespace
from typing import Any, cast

from game.ato.flighttype import FlightType
from game.fourteenth.comint import (
    COMINT_REVEAL_RANGE_M,
    apply_comint_reveal,
    collection_tier,
    comint_kneeboard_lines,
    comint_leak_line,
    comint_sources,
    gated_posture_detail,
    record_comint_collection,
)
from game.theater import Player


class _Pos:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def distance_to_point(self, other: "_Pos") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


def _tgo(
    category: str,
    *,
    alive: bool = True,
    x: float = 0.0,
    y: float = 0.0,
    name: str = "site",
    concealed: bool = False,
    map_hidden: bool = False,
    coin_spawned: bool = False,
    known: bool = False,
    task: Any = None,
) -> Any:
    tgo = SimpleNamespace(
        category=category,
        groups=[SimpleNamespace(units=[SimpleNamespace(alive=alive)])],
        position=_Pos(x, y),
        name=name,
        concealed=concealed,
        map_hidden=map_hidden,
        coin_spawned=coin_spawned,
        discovered_by_player=known,
        task=task,
        control_point=SimpleNamespace(name="Haina"),
    )
    tgo.known_for = lambda viewer, _t=tgo: _t.discovered_by_player
    return tgo


def _flight(
    flight_type: FlightType = FlightType.BARCAP,
    dcs_id: str = "F-16C_50",
    count: int = 2,
) -> Any:
    return SimpleNamespace(
        flight_type=flight_type,
        unit_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(id=dcs_id)),
        count=count,
    )


def _package(
    task: FlightType,
    target_name: str,
    *flights: Any,
    tot: datetime.datetime = datetime.datetime.min,
) -> Any:
    return SimpleNamespace(
        primary_task=task,
        target=SimpleNamespace(name=target_name),
        flights=list(flights),
        time_over_target=tot,
    )


def _game(
    red_tgos: list[Any],
    *,
    on: bool = True,
    turn: int = 5,
    collected_turn: Any = None,
    red_packages: list[Any] | None = None,
    blue_packages: list[Any] | None = None,
    concealed_enemy_forces: bool = False,
) -> Any:
    messages: list[tuple[str, str]] = []
    game = SimpleNamespace(
        settings=SimpleNamespace(
            comint_collection=on,
            concealed_enemy_forces=concealed_enemy_forces,
        ),
        theater=SimpleNamespace(
            controlpoints=[
                SimpleNamespace(captured=Player.RED, ground_objects=red_tgos),
                # A blue CP full of red-looking objects must never count.
                SimpleNamespace(captured=Player.BLUE, ground_objects=[_tgo("comms")]),
            ]
        ),
        red=SimpleNamespace(
            player=Player.RED,
            ato=SimpleNamespace(packages=red_packages or []),
        ),
        blue=SimpleNamespace(
            player=Player.BLUE,
            ato=SimpleNamespace(packages=blue_packages or []),
        ),
        turn=turn,
        comint_collected_turn=collected_turn,
        comint_reveal_turn=None,
        comint_reveal_note=None,
        messages=messages,
    )
    game.message = lambda title, text="": messages.append((title, text))
    return game


def _events() -> Any:
    updated: list[Any] = []
    return SimpleNamespace(update_tgo=lambda tgo: updated.append(tgo), updated=updated)


def _debriefing(survivors: dict[int, int]) -> Any:
    # Keyed by id() -- SimpleNamespace fakes aren't hashable.
    return SimpleNamespace(
        air_losses=SimpleNamespace(
            surviving_flight_members=lambda flight: survivors.get(id(flight), 0)
        )
    )


def test_no_alive_sources_is_tier_zero() -> None:
    game = _game([_tgo("comms", alive=False), _tgo("aa")], collected_turn=4)
    assert collection_tier(cast(Any, game)) == 0
    assert comint_kneeboard_lines(cast(Any, game)) == [
        "Enemy C2 net silent — no COMINT take."
    ]


def test_off_is_an_exact_noop() -> None:
    game = _game([_tgo("comms")], on=False, collected_turn=4)
    assert collection_tier(cast(Any, game)) == 0
    assert comint_kneeboard_lines(cast(Any, game)) == []
    assert gated_posture_detail(cast(Any, game), "Surging") == "Surging"

    flight = _flight(FlightType.JAMMING)
    game.blue.ato.packages = [_package(FlightType.BARCAP, "x", flight)]
    record_comint_collection(cast(Any, game), _debriefing({id(flight): 2}))
    # Unchanged from construction -- the record hook never ran.
    assert game.comint_collected_turn == 4

    events = _events()
    apply_comint_reveal(cast(Any, game), events)
    assert game.comint_reveal_turn is None
    assert events.updated == []


def test_alive_net_is_the_ambient_tier() -> None:
    game = _game([_tgo("comms"), _tgo("commandcenter")])
    assert collection_tier(cast(Any, game)) == 1
    lines = comint_kneeboard_lines(cast(Any, game))
    assert lines[0] == "Enemy net active: 2 emitter(s) up."
    assert "Ambient take only" in lines[1]


def test_concealed_coin_spawns_are_sources() -> None:
    cell = _tgo("armor", concealed=True, coin_spawned=True)
    game = _game([cell])
    assert comint_sources(cast(Any, game)) == [cell]
    assert collection_tier(cast(Any, game)) == 1


def test_collector_record_requires_a_survivor() -> None:
    jammer = _flight(FlightType.JAMMING, dcs_id="C-130J-30")
    game = _game([_tgo("comms")], turn=7)
    game.blue.ato.packages = [_package(FlightType.JAMMING, "orbit", jammer)]

    record_comint_collection(cast(Any, game), _debriefing({id(jammer): 0}))
    assert game.comint_collected_turn is None

    record_comint_collection(cast(Any, game), _debriefing({id(jammer): 1}))
    assert game.comint_collected_turn == 7


def test_a_drone_is_always_listening() -> None:
    drone = _flight(FlightType.BAI, dcs_id="MQ-9 Reaper", count=1)
    game = _game([_tgo("comms")], turn=3)
    game.blue.ato.packages = [_package(FlightType.BAI, "cells", drone)]
    record_comint_collection(cast(Any, game), _debriefing({id(drone): 1}))
    assert game.comint_collected_turn == 3


def test_tier_two_needs_both_collection_and_sources() -> None:
    collected = _game([_tgo("comms")], turn=5, collected_turn=4)
    assert collection_tier(cast(Any, collected)) == 2
    stale = _game([_tgo("comms")], turn=5, collected_turn=3)
    assert collection_tier(cast(Any, stale)) == 1
    silent = _game([_tgo("comms", alive=False)], turn=5, collected_turn=4)
    assert collection_tier(cast(Any, silent)) == 0


def test_reveal_snaps_the_nearest_eligible_concealed_site() -> None:
    near = _tgo("armor", concealed=True, x=10_000, name="near cell")
    far = _tgo("armor", concealed=True, x=30_000, name="far cell")
    beyond = _tgo("armor", concealed=True, x=COMINT_REVEAL_RANGE_M + 1, name="beyond")
    hidden = _tgo("armor", concealed=True, map_hidden=True, x=5_000, name="ambush")
    known = _tgo("armor", concealed=True, known=True, x=1_000, name="known")
    game = _game(
        [_tgo("comms"), near, far, beyond, hidden, known], turn=5, collected_turn=4
    )
    events = _events()

    apply_comint_reveal(cast(Any, game), events)

    assert near.discovered_by_player is True
    assert far.discovered_by_player is False
    assert beyond.discovered_by_player is False
    assert hidden.discovered_by_player is False
    assert events.updated == [near]
    assert game.comint_reveal_turn == 5
    assert game.comint_reveal_note == "near cell (Haina area)"
    assert game.messages and "localized" in game.messages[0][0]


def test_reveal_is_idempotent_across_reinit() -> None:
    first = _tgo("armor", concealed=True, x=10_000, name="a")
    second = _tgo("armor", concealed=True, x=20_000, name="b")
    game = _game([_tgo("comms"), first, second], turn=5, collected_turn=4)
    events = _events()

    apply_comint_reveal(cast(Any, game), events)
    apply_comint_reveal(cast(Any, game), events)

    assert first.discovered_by_player is True
    assert second.discovered_by_player is False
    assert events.updated == [first]


def test_map_hidden_is_never_revealed_even_alone() -> None:
    ambush = _tgo("armor", concealed=True, map_hidden=True, x=5_000)
    game = _game([_tgo("comms"), ambush], turn=5, collected_turn=4)
    events = _events()
    apply_comint_reveal(cast(Any, game), events)
    assert ambush.discovered_by_player is False
    assert events.updated == []
    # The evaluation still stamps the turn so a re-init can't try again.
    assert game.comint_reveal_turn == 5


def test_category_concealment_needs_the_setting() -> None:
    field_sam = _tgo("aa", x=10_000, name="sam")
    field_sam.task = None
    game = _game([_tgo("comms"), field_sam], turn=5, collected_turn=4)
    events = _events()
    apply_comint_reveal(cast(Any, game), events)
    assert field_sam.discovered_by_player is False


def test_leak_picks_the_most_threatening_package_deterministically() -> None:
    tot = datetime.datetime(2026, 7, 18, 14, 0)
    red_packages = [
        _package(FlightType.BAI, "convoy", _flight(count=4)),
        _package(FlightType.STRIKE, "Fulda", _flight(count=2), tot=tot),
        _package(FlightType.BARCAP, "cap", _flight(count=2)),
    ]
    game = _game([_tgo("comms")], red_packages=red_packages)
    line = comint_leak_line(cast(Any, game))
    assert line is not None
    assert "Strike" in line
    assert "Fulda" in line
    assert "13:30–14:30" in line
    # Deterministic: the same state leaks the same package every call.
    assert comint_leak_line(cast(Any, game)) == line


def test_kneeboard_block_at_tier_two_carries_leak_and_reveal() -> None:
    game = _game(
        [_tgo("comms")],
        turn=5,
        collected_turn=4,
        red_packages=[_package(FlightType.STRIKE, "Fulda", _flight(count=2))],
    )
    game.comint_reveal_note = "near cell (Haina area)"
    lines = comint_kneeboard_lines(cast(Any, game))
    assert lines[0] == "Enemy net active: 1 emitter(s) up."
    assert lines[1] == "Collection sortie banked a full take last mission:"
    assert any("Intercepted tasking traffic" in line for line in lines)
    assert any("Transmissions localized: near cell" in line for line in lines)


def test_posture_detail_is_earned_by_an_emitting_net() -> None:
    live = _game([_tgo("comms")])
    assert gated_posture_detail(cast(Any, live), "Surging (all-in)") == (
        "Surging (all-in)"
    )
    silent = _game([_tgo("comms", alive=False)])
    assert gated_posture_detail(cast(Any, silent), "Surging (all-in)") is None
    assert gated_posture_detail(cast(Any, silent), None) is None
