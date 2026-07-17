from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from game.settings import Settings
from game.squadrons.squadron import Squadron
from game.theater import ControlPoint


def _bare_squadron(
    owned: int, reserve: int, intercept_enabled: bool = True, player_manned: int = 0
) -> Squadron:
    squadron = Squadron.__new__(Squadron)
    squadron.current_roster = []
    squadron.owned_aircraft = owned
    squadron.intercept_reserve = reserve
    squadron.qra_player_manned = player_manned
    squadron.settings = cast(
        Settings, SimpleNamespace(plugins={"intercept": intercept_enabled})
    )
    return squadron


def _fuel_starved_base(*, total_depots: int, active_depots: int) -> SimpleNamespace:
    """Duck-typed control point for fuel_readiness (the §53 P3 coupling)."""
    game = SimpleNamespace(settings=SimpleNamespace(fuel_air_readiness=True))
    return SimpleNamespace(
        coalition=SimpleNamespace(game=game),
        total_fuel_depots_count=total_depots,
        active_fuel_depots_count=active_depots,
    )


def test_reset_holds_back_qra_reserve_from_plannable_inventory() -> None:
    squadron = _bare_squadron(owned=10, reserve=4)
    squadron.return_all_pilots_and_aircraft()
    assert squadron.untasked_aircraft == 6


def test_reset_with_zero_reserve_leaves_all_aircraft_plannable() -> None:
    squadron = _bare_squadron(owned=10, reserve=0)
    squadron.return_all_pilots_and_aircraft()
    assert squadron.untasked_aircraft == 10


def test_reset_clamps_plannable_inventory_at_zero() -> None:
    squadron = _bare_squadron(owned=3, reserve=5)
    squadron.return_all_pilots_and_aircraft()
    assert squadron.untasked_aircraft == 0


def test_reset_benches_reserve_regardless_of_plugin_flag() -> None:
    # The reserve (intercept_reserve > 0) is the single on/off switch for QRA:
    # emission and loss commit gate on it alone, so benching must too. The plugin
    # flag must NOT change benching, otherwise a reserve could be both
    # ATO-plannable and fielded as QRA.
    squadron = _bare_squadron(owned=10, reserve=4, intercept_enabled=False)
    squadron.return_all_pilots_and_aircraft()
    assert squadron.untasked_aircraft == 6


def test_set_intercept_reserve_releases_jets_into_pool_immediately() -> None:
    # Editing the reserve mid-turn must update the plannable pool at once, without
    # a full return_all_pilots_and_aircraft() (which would return tasked flights).
    squadron = _bare_squadron(owned=10, reserve=4)
    squadron.return_all_pilots_and_aircraft()
    assert squadron.untasked_aircraft == 6

    squadron.set_intercept_reserve(0)
    assert squadron.intercept_reserve == 0
    assert squadron.untasked_aircraft == 10


def test_set_intercept_reserve_benches_jets_immediately() -> None:
    squadron = _bare_squadron(owned=10, reserve=0)
    squadron.return_all_pilots_and_aircraft()
    assert squadron.untasked_aircraft == 10

    squadron.set_intercept_reserve(4)
    assert squadron.intercept_reserve == 4
    assert squadron.untasked_aircraft == 6


def test_set_intercept_reserve_reclamps_player_manned() -> None:
    # §1 coupling: lowering the reserve below the player-manned count must pull
    # the manned count down with it, or planning would frag a phantom manned
    # alert flight against airframes no longer held on QRA.
    squadron = _bare_squadron(owned=10, reserve=4, player_manned=3)
    squadron.return_all_pilots_and_aircraft()

    squadron.set_intercept_reserve(2)
    assert squadron.qra_player_manned == 2

    squadron.set_intercept_reserve(4)
    assert squadron.qra_player_manned == 2  # never raised, only clamped


def test_set_intercept_reserve_respects_fuel_readiness_ceiling() -> None:
    # §53 P3 coupling: return_all_pilots_and_aircraft scales the pool by the
    # base's fuel readiness AFTER subtracting the reserve. Freeing the reserve
    # at a fuel-starved base must not un-ground the jets the depot damage
    # grounded: owned 10 / reserve 4 at readiness 0.5 -> untasked 3; dropping
    # the reserve to 0 caps at int(10 * 0.5) = 5, not the delta's 7.
    squadron = _bare_squadron(owned=10, reserve=4)
    squadron.location = cast(
        ControlPoint, _fuel_starved_base(total_depots=4, active_depots=0)
    )
    squadron.return_all_pilots_and_aircraft()
    assert squadron.untasked_aircraft == 3

    squadron.set_intercept_reserve(0)
    assert squadron.untasked_aircraft == 5
