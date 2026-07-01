"""Captured-pilot POW objective surfacing (SCAR rescue rework, Phase 3).

Each ``PendingPowRecovery`` is rebuilt every turn into a ``CapturedPilotGroundObject``
positioned at the nearest ENEMY control point (the holding "airfield") and anchored
to the nearest friendly control point so it renders as a friendly recovery
objective. These pin the surfacing (holding/anchor selection, idempotent rebuild,
teardown) and the recovery-only offering. Mirrors ``test_scar_objectives``.
"""

from __future__ import annotations

import itertools
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

from dcs.mapping import Point

from game.ato.flighttype import FlightType
from game.db.database import Database
from game.pow_objectives import sync_pow_objectives
from game.pow_recovery import PendingPowRecovery
from game.theater import Player
from game.theater.theatergroundobject import CapturedPilotGroundObject


def _cp(captured: Player, x: float, y: float) -> Any:
    return SimpleNamespace(
        id=uuid4(),
        captured=captured,
        position=Point(x, y, None),  # type: ignore[arg-type]
        connected_objectives=[],
    )


def _game(*, blue_pows: list[PendingPowRecovery], cps: list[Any]) -> Any:
    ids = itertools.count(1)

    def find(cp_id: Any) -> Any:
        for cp in cps:
            if cp.id == cp_id:
                return cp
        raise KeyError(cp_id)

    blue = SimpleNamespace(player=Player.BLUE, pending_pow_recoveries=blue_pows)
    red = SimpleNamespace(player=Player.RED, pending_pow_recoveries=[])
    return SimpleNamespace(
        coalitions=[blue, red],
        db=SimpleNamespace(tgos=Database()),
        theater=SimpleNamespace(controlpoints=cps, find_control_point_by_id=find),
        point_in_world=lambda x, y: Point(x, y, None),  # type: ignore[arg-type]
        next_group_id=lambda: next(ids),
        next_unit_id=lambda: next(ids),
    )


def _pows(cps: list[Any]) -> list[CapturedPilotGroundObject]:
    return [
        tgo
        for cp in cps
        for tgo in cp.connected_objectives
        if isinstance(tgo, CapturedPilotGroundObject)
    ]


def test_capture_is_surfaced_at_the_enemy_airfield() -> None:
    friendly = _cp(Player.BLUE, 0.0, 0.0)
    enemy = _cp(Player.RED, 1000.0, 2000.0)
    pow_entry = PendingPowRecovery("Enfield11", 1001.0, 2001.0)
    game = _game(blue_pows=[pow_entry], cps=[friendly, enemy])

    sync_pow_objectives(cast(Any, game))

    held = _pows([friendly, enemy])
    assert len(held) == 1
    tgo = held[0]
    # Positioned near the enemy airfield (offset toward the friendly anchor so the
    # marker clears the airbase's own icon -- not exactly on top of it), anchored
    # to the friendly CP, carries the POW.
    offset = tgo.position.distance_to_point(enemy.position)
    assert 0 < offset < enemy.position.distance_to_point(friendly.position)
    assert tgo.control_point is friendly
    assert tgo.unit_count == 1
    # The holding enemy field is recorded, and the TGO is registered for fragging.
    assert pow_entry.holding_cp_id == enemy.id
    assert game.db.tgos.get(tgo.id) is tgo
    # Carries the airframe key so a recovery raid maps back to this POW.
    assert tgo.airframe_unit_name == "Enfield11"


def test_holding_field_is_the_nearest_enemy_control_point() -> None:
    friendly = _cp(Player.BLUE, 0.0, 0.0)
    near_enemy = _cp(Player.RED, 1010.0, 2010.0)
    far_enemy = _cp(Player.RED, 9000.0, 9000.0)
    pow_entry = PendingPowRecovery("A", 1000.0, 2000.0)
    game = _game(blue_pows=[pow_entry], cps=[friendly, near_enemy, far_enemy])

    sync_pow_objectives(cast(Any, game))

    assert pow_entry.holding_cp_id == near_enemy.id


def test_sync_is_idempotent() -> None:
    friendly = _cp(Player.BLUE, 0.0, 0.0)
    enemy = _cp(Player.RED, 100.0, 100.0)
    game = _game(blue_pows=[PendingPowRecovery("A", 90.0, 90.0)], cps=[friendly, enemy])

    sync_pow_objectives(cast(Any, game))
    first = _pows([friendly])[0].id
    sync_pow_objectives(cast(Any, game))

    held = _pows([friendly])
    assert len(held) == 1  # not duplicated
    assert held[0].id != first  # rebuilt fresh
    assert len(game.db.tgos.objects) == 1  # registry not leaked


def test_recovered_pow_is_torn_down() -> None:
    friendly = _cp(Player.BLUE, 0.0, 0.0)
    enemy = _cp(Player.RED, 100.0, 100.0)
    pows = [PendingPowRecovery("A", 90.0, 90.0)]
    game = _game(blue_pows=pows, cps=[friendly, enemy])
    sync_pow_objectives(cast(Any, game))
    assert _pows([friendly])

    # The POW was recovered / aged out -> next sync removes its objective.
    game.coalitions[0].pending_pow_recoveries.clear()
    sync_pow_objectives(cast(Any, game))

    assert not _pows([friendly])
    assert not game.db.tgos.objects


def test_no_objective_without_an_enemy_base() -> None:
    friendly_only = _cp(Player.BLUE, 0.0, 0.0)
    game = _game(blue_pows=[PendingPowRecovery("A", 1.0, 2.0)], cps=[friendly_only])

    sync_pow_objectives(cast(Any, game))

    assert not _pows([friendly_only])
    assert not game.db.tgos.objects


def _pow_objective() -> CapturedPilotGroundObject:
    tgo = CapturedPilotGroundObject.__new__(CapturedPilotGroundObject)
    tgo.control_point = cast(
        Any,
        SimpleNamespace(
            captured=Player.BLUE,
            is_friendly=lambda p: p is Player.BLUE,
        ),
    )
    return tgo


def test_owner_is_offered_only_a_recovery() -> None:
    assert list(_pow_objective().mission_types(Player.BLUE)) == [FlightType.CSAR]


def test_enemy_is_offered_nothing() -> None:
    assert list(_pow_objective().mission_types(Player.RED)) == []
