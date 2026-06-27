"""Locks the 414th merge invariant for PR #823's frontline maneuver: when the
TIC plugin is enabled (the fork default), TIC owns frontline movement and the
imported #823 DCS-task maneuver must NOT run for any role. When TIC is off, the
#823 cohesive maneuver drives the groups instead.

See docs/dev/design/414th-pr823-frontline-merge-notes.md (Bucket C).
"""

from unittest.mock import MagicMock

from game.ground_forces.ai_ground_planner import CombatGroup, CombatGroupRole
from game.ground_forces.combat_stance import CombatStance
from game.missiongenerator.flotgenerator import FlotGenerator


def _gen(tic_enabled: bool) -> FlotGenerator:
    gen = FlotGenerator.__new__(FlotGenerator)
    gen.tic_enabled = tic_enabled
    gen.game = MagicMock()
    gen.game.settings.perf_moving_units = True
    gen.game.settings.perf_artillery = True
    # Stub every action method so we can assert which one fires.
    gen._plan_tic_action = MagicMock()  # type: ignore[method-assign]
    gen._plan_tank_ifv_action = MagicMock()  # type: ignore[method-assign]
    gen._plan_apc_atgm_action = MagicMock()  # type: ignore[method-assign]
    gen._plan_follower_action = MagicMock()  # type: ignore[method-assign]
    gen._plan_artillery_action = MagicMock()  # type: ignore[method-assign]
    return gen


def _call(gen: FlotGenerator, group: CombatGroup) -> None:
    gen.plan_action_for_groups(
        CombatStance.AGGRESSIVE,
        ally_groups=[(MagicMock(), group)],
        enemy_groups=[],
        forward_heading=MagicMock(),
        from_cp=MagicMock(),
        to_cp=MagicMock(),
    )


def _grp(role: CombatGroupRole) -> CombatGroup:
    return CombatGroup(role, MagicMock(), 5)


def test_tic_build_tank_routes_through_tic_action() -> None:
    gen = _gen(tic_enabled=True)
    _call(gen, _grp(CombatGroupRole.TANK))
    gen._plan_tic_action.assert_called_once()  # type: ignore[attr-defined]
    gen._plan_tank_ifv_action.assert_not_called()  # type: ignore[attr-defined]


def test_tic_build_atgm_routes_through_tic_action() -> None:
    gen = _gen(tic_enabled=True)
    _call(gen, _grp(CombatGroupRole.ATGM))
    gen._plan_tic_action.assert_called_once()  # type: ignore[attr-defined]
    gen._plan_follower_action.assert_not_called()  # type: ignore[attr-defined]
    gen._plan_apc_atgm_action.assert_not_called()  # type: ignore[attr-defined]


def test_tic_build_shorad_gets_no_maneuver() -> None:
    # SHORAD is not TIC-managed; on a TIC build it must stay static (no #823
    # follower maneuver leaking onto it).
    gen = _gen(tic_enabled=True)
    _call(gen, _grp(CombatGroupRole.SHORAD))
    gen._plan_tic_action.assert_not_called()  # type: ignore[attr-defined]
    gen._plan_follower_action.assert_not_called()  # type: ignore[attr-defined]
    gen._plan_apc_atgm_action.assert_not_called()  # type: ignore[attr-defined]
    gen._plan_tank_ifv_action.assert_not_called()  # type: ignore[attr-defined]


def test_non_tic_anchored_member_uses_follower_action() -> None:
    gen = _gen(tic_enabled=False)
    atgm = _grp(CombatGroupRole.ATGM)
    atgm.anchor = _grp(CombatGroupRole.TANK)
    _call(gen, atgm)
    gen._plan_follower_action.assert_called_once()  # type: ignore[attr-defined]
    gen._plan_tic_action.assert_not_called()  # type: ignore[attr-defined]


def test_non_tic_unanchored_member_uses_apc_atgm() -> None:
    gen = _gen(tic_enabled=False)
    atgm = _grp(CombatGroupRole.ATGM)  # anchor is None
    _call(gen, atgm)
    gen._plan_apc_atgm_action.assert_called_once()  # type: ignore[attr-defined]
    gen._plan_follower_action.assert_not_called()  # type: ignore[attr-defined]


def test_non_tic_apc_joins_wedge_branch() -> None:
    # APC now maneuvers as armor (WEDGE_ROLES) on the TIC-off path.
    gen = _gen(tic_enabled=False)
    _call(gen, _grp(CombatGroupRole.APC))
    gen._plan_tank_ifv_action.assert_called_once()  # type: ignore[attr-defined]
    gen._plan_apc_atgm_action.assert_not_called()  # type: ignore[attr-defined]
