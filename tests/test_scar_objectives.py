"""SCAR CSAR objective surfacing (Phase 2c-3, slice C2).

Each ``PendingSofRescue`` is rebuilt every turn into a friendly "downed SOF team"
``DownedSofGroundObject`` hung off the nearest friendly control point, registered
in the TGO database so the player can frag a recovery flight against it. These
tests pin the surfacing (anchor selection, idempotent rebuild, teardown, gate) and
the recovery-only offering.
"""

from __future__ import annotations

import itertools
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

from dcs.mapping import Point

from game.ato.flighttype import FlightType
from game.db.database import Database
from game.scar_objectives import sync_downed_sof_objectives
from game.scar_rescue import PendingSofRescue
from game.theater import Player
from game.theater.theatergroundobject import DownedSofGroundObject


def _cp(captured: Player, x: float, y: float) -> Any:
    return SimpleNamespace(
        id=uuid4(),
        captured=captured,
        position=Point(x, y, None),  # type: ignore[arg-type]
        connected_objectives=[],
    )


def _game(
    *, setting_on: bool, blue_rescues: list[PendingSofRescue], cps: list[Any]
) -> Any:
    ids = itertools.count(1)

    def find(cp_id: Any) -> Any:
        for cp in cps:
            if cp.id == cp_id:
                return cp
        raise KeyError(cp_id)

    blue = SimpleNamespace(player=Player.BLUE, pending_csars=blue_rescues)
    red = SimpleNamespace(player=Player.RED, pending_csars=[])
    return SimpleNamespace(
        settings=SimpleNamespace(scar_command_post_intel=setting_on),
        coalitions=[blue, red],
        db=SimpleNamespace(tgos=Database()),
        theater=SimpleNamespace(controlpoints=cps, find_control_point_by_id=find),
        point_in_world=lambda x, y: Point(x, y, None),  # type: ignore[arg-type]
        next_group_id=lambda: next(ids),
        next_unit_id=lambda: next(ids),
    )


def _downed(cps: list[Any]) -> list[DownedSofGroundObject]:
    return [
        tgo
        for cp in cps
        for tgo in cp.connected_objectives
        if isinstance(tgo, DownedSofGroundObject)
    ]


def test_rescue_is_surfaced_as_a_downed_team_objective() -> None:
    friendly = _cp(Player.BLUE, 0.0, 0.0)
    game = _game(
        setting_on=True,
        blue_rescues=[PendingSofRescue(100.0, 200.0)],
        cps=[friendly],
    )

    sync_downed_sof_objectives(cast(Any, game))

    teams = _downed([friendly])
    assert len(teams) == 1
    tgo = teams[0]
    # Placed at the strand point, anchored to the friendly CP, carries the team.
    assert (tgo.position.x, tgo.position.y) == (100.0, 200.0)
    assert tgo.control_point is friendly
    assert tgo.unit_count == 1
    # Registered so the frontend can build a recovery package against it.
    assert game.db.tgos.get(tgo.id) is tgo


def test_anchor_is_the_nearest_friendly_control_point() -> None:
    near = _cp(Player.BLUE, 90.0, 200.0)
    far = _cp(Player.BLUE, -5000.0, -5000.0)
    enemy = _cp(Player.RED, 101.0, 201.0)  # closest overall, but not friendly
    rescue = PendingSofRescue(100.0, 200.0)
    game = _game(setting_on=True, blue_rescues=[rescue], cps=[near, far, enemy])

    sync_downed_sof_objectives(cast(Any, game))

    assert rescue.anchor_cp_id == near.id
    assert _downed([near]) and not _downed([far]) and not _downed([enemy])


def test_sync_is_idempotent() -> None:
    friendly = _cp(Player.BLUE, 0.0, 0.0)
    game = _game(
        setting_on=True, blue_rescues=[PendingSofRescue(1.0, 2.0)], cps=[friendly]
    )

    sync_downed_sof_objectives(cast(Any, game))
    first = _downed([friendly])[0].id
    sync_downed_sof_objectives(cast(Any, game))

    teams = _downed([friendly])
    assert len(teams) == 1  # not duplicated
    assert teams[0].id != first  # rebuilt fresh
    assert len(game.db.tgos.objects) == 1  # registry not leaked


def test_resolved_rescue_is_torn_down() -> None:
    friendly = _cp(Player.BLUE, 0.0, 0.0)
    rescues = [PendingSofRescue(1.0, 2.0)]
    game = _game(setting_on=True, blue_rescues=rescues, cps=[friendly])
    sync_downed_sof_objectives(cast(Any, game))
    assert _downed([friendly])

    # The rescue was recovered/aged out -> next sync removes its objective.
    game.coalitions[0].pending_csars.clear()
    sync_downed_sof_objectives(cast(Any, game))

    assert not _downed([friendly])
    assert not game.db.tgos.objects


def test_no_objective_when_feature_off() -> None:
    friendly = _cp(Player.BLUE, 0.0, 0.0)
    game = _game(
        setting_on=False, blue_rescues=[PendingSofRescue(1.0, 2.0)], cps=[friendly]
    )

    sync_downed_sof_objectives(cast(Any, game))

    assert not _downed([friendly])
    assert not game.db.tgos.objects


def test_no_objective_without_a_friendly_base() -> None:
    enemy_only = _cp(Player.RED, 0.0, 0.0)
    game = _game(
        setting_on=True, blue_rescues=[PendingSofRescue(1.0, 2.0)], cps=[enemy_only]
    )

    sync_downed_sof_objectives(cast(Any, game))

    assert not _downed([enemy_only])


def _objective_with_settings(
    setting_on: bool, owner_view: bool
) -> DownedSofGroundObject:
    tgo = DownedSofGroundObject.__new__(DownedSofGroundObject)
    tgo.control_point = cast(
        Any,
        SimpleNamespace(
            captured=Player.BLUE,
            is_friendly=lambda p: p is Player.BLUE,
            coalition=SimpleNamespace(
                game=SimpleNamespace(
                    settings=SimpleNamespace(scar_command_post_intel=setting_on)
                )
            ),
        ),
    )
    return tgo


def test_owner_is_offered_only_a_recovery() -> None:
    tgo = _objective_with_settings(setting_on=True, owner_view=True)
    assert list(tgo.mission_types(Player.BLUE)) == [FlightType.CSAR]


def test_enemy_is_offered_nothing() -> None:
    tgo = _objective_with_settings(setting_on=True, owner_view=False)
    assert list(tgo.mission_types(Player.RED)) == []


def test_no_recovery_offered_when_feature_off() -> None:
    tgo = _objective_with_settings(setting_on=False, owner_view=True)
    assert list(tgo.mission_types(Player.BLUE)) == []
