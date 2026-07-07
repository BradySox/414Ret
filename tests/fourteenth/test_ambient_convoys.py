"""§50 ambient supply convoys -> a few randomized real columns on BOTH sides' roads.

Locks the standardization layer: each side's convoy flow is topped up to a randomized
target on randomly chosen **distinct** same-side corridors (one column per road, capped at
the road count -- the S5 fix, since same-corridor transfers coalesce into one deadlocking
column), existing convoys count toward the target, the corridors orient rear -> front, and
every guard (setting off, turn 0, no same-side road, no war to supply toward) no-ops.
Skim-only (2026-07-07 design call): columns relocate units that already exist in a rear
base and never commission free ones, so a base too thin to skim yields no column instead
of inventing reinforcements.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest

import game.fourteenth.ambient_convoys as ambient_module
import game.fourteenth.vietnam_convoy as vietnam_convoy_module
from game.fourteenth.ambient_convoys import (
    AMBIENT_CONVOY_UNITS,
    MAX_AMBIENT_CONVOYS,
    MIN_AMBIENT_CONVOYS,
    _same_side_corridors,
    ensure_ambient_convoys,
)

# ---- fakes -------------------------------------------------------------------------


class _Base:
    def __init__(self, armor: dict[Any, int]) -> None:
        self.armor = dict(armor)

    @property
    def total_armor(self) -> int:
        return sum(self.armor.values())

    def commission_units(self, units: dict[Any, int]) -> None:
        for unit_type, count in units.items():
            self.armor[unit_type] = self.armor.get(unit_type, 0) + count


class _Owner:
    def __init__(self, blue: bool) -> None:
        self.is_blue = blue
        self.is_red = not blue


class _Pos:
    """A 1-D coordinate; ``distance_to_point`` is |Δx| (the fakes put the front at x=0,
    so a CP's distance-to-front is its own coordinate)."""

    def __init__(self, x: float) -> None:
        self.x = x

    def distance_to_point(self, other: "_Pos") -> float:
        return abs(self.x - other.x)


BLUE_PLAYER = _Owner(True)
RED_PLAYER = _Owner(False)


class _CP:
    def __init__(
        self, name: str, owner: _Owner, dist: float, armor: dict[Any, int] | None = None
    ) -> None:
        self.name = name
        self.captured = owner  # identity-compared to coalition.player
        self.position = _Pos(dist)
        self.base = _Base(armor or {})
        self.convoy_routes: dict[Any, Any] = {}


def _road(a: _CP, b: _CP) -> None:
    a.convoy_routes[b] = ()
    b.convoy_routes[a] = ()


class _Unit:
    def __init__(self, name: str) -> None:
        self.display_name = name
        self.price = 2


class _Transfers:
    def __init__(self, convoys: list[Any] | None = None) -> None:
        self.convoys = convoys or []
        self.created: list[Any] = []

    def new_transfer(self, order: Any, now: Any) -> None:
        self.created.append(order)


def _coalition(player: _Owner, convoys: list[Any] | None = None) -> Any:
    return SimpleNamespace(
        player=player,
        transfers=_Transfers(convoys),
        faction=SimpleNamespace(frontline_units={_Unit("M113"), _Unit("Ural")}),
    )


class _Rng:
    """Scripted stand-in for the module RNG: pops ``ints`` for randint (the per-side
    target). ``sample`` returns the first ``k`` corridors -- deterministic and distinct,
    which is all these tests need (they assert on counts / distinctness, not order)."""

    def __init__(self, ints: list[int]) -> None:
        self.ints = list(ints)

    def randint(self, a: int, b: int) -> int:
        value = self.ints.pop(0) if self.ints else a
        assert a <= value <= b, f"scripted randint {value} outside [{a}, {b}]"
        return value

    def sample(self, seq: list[Any], k: int) -> list[Any]:
        assert k <= len(seq), f"scripted sample k={k} > len={len(seq)}"
        return list(seq)[:k]


def _game(
    *,
    on: bool,
    cps: list[_CP],
    turn: int = 3,
    fronts: list[Any] | None = None,
    coin: bool = False,
) -> Any:
    front_list = fronts if fronts is not None else [SimpleNamespace(position=_Pos(0.0))]
    return SimpleNamespace(
        settings=SimpleNamespace(ambient_supply_convoys=on, coin_insurgency=coin),
        turn=turn,
        blue=_coalition(BLUE_PLAYER),
        red=_coalition(RED_PLAYER),
        theater=SimpleNamespace(controlpoints=cps, conflicts=lambda: list(front_list)),
        conditions=SimpleNamespace(start_time=datetime(2000, 1, 1)),
    )


def _two_sided_map() -> list[_CP]:
    """A rear + forward base per side, one road each side, front at x=0."""
    blue_rear = _CP("blue-rear", BLUE_PLAYER, 200.0, {"tank": 40})
    blue_fwd = _CP("blue-fwd", BLUE_PLAYER, 10.0, {"tank": 2})
    red_rear = _CP("red-rear", RED_PLAYER, 220.0, {"btr": 40})
    red_fwd = _CP("red-fwd", RED_PLAYER, 12.0, {"btr": 2})
    _road(blue_rear, blue_fwd)
    _road(red_rear, red_fwd)
    return [blue_rear, blue_fwd, red_rear, red_fwd]


# ---- guards ------------------------------------------------------------------------


def test_off_is_a_noop() -> None:
    game = _game(on=False, cps=_two_sided_map())
    ensure_ambient_convoys(game)
    assert game.blue.transfers.created == []
    assert game.red.transfers.created == []


def test_turn_zero_is_a_noop() -> None:
    game = _game(on=True, cps=_two_sided_map(), turn=0)
    ensure_ambient_convoys(game)
    assert game.blue.transfers.created == []
    assert game.red.transfers.created == []


def test_side_without_a_same_side_road_gets_nothing(monkeypatch: Any) -> None:
    # Only blue has a road; red's silence must not block blue's traffic.
    blue_rear = _CP("blue-rear", BLUE_PLAYER, 200.0, {"tank": 40})
    blue_fwd = _CP("blue-fwd", BLUE_PLAYER, 10.0, {"tank": 2})
    red_lone = _CP("red-lone", RED_PLAYER, 15.0, {"btr": 10})
    _road(blue_rear, blue_fwd)
    game = _game(on=True, cps=[blue_rear, blue_fwd, red_lone])
    monkeypatch.setattr(ambient_module, "_RNG", _Rng(ints=[1, 1]))
    ensure_ambient_convoys(game)
    assert len(game.blue.transfers.created) == 1
    assert game.red.transfers.created == []


# ---- the randomized top-up ----------------------------------------------------------


def test_both_sides_get_a_column_on_their_road(monkeypatch: Any) -> None:
    # One road per side; each rolls 1 -> one column each, oriented rear -> front and
    # carrying skimmed rear units.
    game = _game(on=True, cps=_two_sided_map())
    monkeypatch.setattr(ambient_module, "_RNG", _Rng(ints=[1, 1]))
    ensure_ambient_convoys(game)

    blue_orders = game.blue.transfers.created
    red_orders = game.red.transfers.created
    assert len(blue_orders) == 1
    assert len(red_orders) == 1
    assert blue_orders[0].origin.name == "blue-rear"  # rear -> front orientation
    assert blue_orders[0].destination.name == "blue-fwd"
    assert sum(blue_orders[0].units.values()) == AMBIENT_CONVOY_UNITS
    assert red_orders[0].origin.name == "red-rear"
    assert red_orders[0].destination.name == "red-fwd"


def test_target_is_capped_at_the_road_count(monkeypatch: Any) -> None:
    # One road, but a rolled target of 3: the distinct-corridor cap (S5 fix) means one
    # column, never three transfers stacked onto the same road (which would coalesce into
    # a single deadlocking mega-column).
    game = _game(on=True, cps=_two_sided_map())
    monkeypatch.setattr(ambient_module, "_RNG", _Rng(ints=[3, 1]))
    ensure_ambient_convoys(game)
    assert len(game.blue.transfers.created) == 1  # capped at the one blue road
    assert len(game.red.transfers.created) == 1


def test_existing_convoys_count_toward_the_target(monkeypatch: Any) -> None:
    # Blue already runs 2 organic/trail convoys and rolls a target of 2 -> nothing
    # added (the ambience never forces numbers on top of existing traffic).
    game = _game(on=True, cps=_two_sided_map())
    game.blue.transfers.convoys = ["organic-1", "organic-2"]
    monkeypatch.setattr(ambient_module, "_RNG", _Rng(ints=[2, 1]))
    ensure_ambient_convoys(game)
    assert game.blue.transfers.created == []
    assert len(game.red.transfers.created) == 1


def test_columns_ride_distinct_roads(monkeypatch: Any) -> None:
    # Two blue roads to the front; a roll of 3 is capped at the 2 distinct corridors and
    # the columns ride DIFFERENT roads -- never two transfers on one road (the S5 fix:
    # the convoy map keys by (origin, destination), so same-road transfers would merge
    # into one oversized, deadlocking column).
    blue_rear = _CP("blue-rear", BLUE_PLAYER, 200.0, {"tank": 60})
    blue_fwd = _CP("blue-fwd", BLUE_PLAYER, 10.0, {"tank": 2})
    blue_alt = _CP("blue-alt", BLUE_PLAYER, 180.0, {"tank": 60})
    red_lone = _CP("red-lone", RED_PLAYER, 15.0, {"btr": 10})
    _road(blue_rear, blue_fwd)
    _road(blue_alt, blue_fwd)
    game = _game(on=True, cps=[blue_rear, blue_fwd, blue_alt, red_lone])
    monkeypatch.setattr(ambient_module, "_RNG", _Rng(ints=[3, 1]))
    ensure_ambient_convoys(game)
    origins = [order.origin.name for order in game.blue.transfers.created]
    assert len(origins) == 2  # rolled 3, capped at the 2 blue roads
    assert len(set(origins)) == 2  # ... and the two columns ride DISTINCT roads


def test_skim_only_never_commissions_free_units(monkeypatch: Any) -> None:
    # 2026-07-07 design call: ambient columns RELOCATE existing rear units only -- they
    # must never seed/commission free ones. A rear base too thin to skim (blue's empty
    # rear here) yields no column instead of inventing phantom reinforcements, and the
    # §35 seeding path is never taken for either side.
    blue_rear = _CP(
        "blue-rear", BLUE_PLAYER, 200.0, {}
    )  # empty rear -> nothing to skim
    blue_fwd = _CP("blue-fwd", BLUE_PLAYER, 10.0, {"tank": 2})
    red_rear = _CP("red-rear", RED_PLAYER, 220.0, {"btr": 40})
    red_fwd = _CP("red-fwd", RED_PLAYER, 12.0, {"btr": 2})
    _road(blue_rear, blue_fwd)
    _road(red_rear, red_fwd)
    game = _game(on=True, cps=[blue_rear, blue_fwd, red_rear, red_fwd])

    def boom(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("ambient convoys must not seed/commission free units")

    monkeypatch.setattr(vietnam_convoy_module, "_seed_trail_source", boom)
    monkeypatch.setattr(_Base, "commission_units", boom)
    monkeypatch.setattr(ambient_module, "_RNG", _Rng(ints=[3, 1]))
    ensure_ambient_convoys(game)

    # Blue's empty rear yields no column; red's stocked rear still runs its one convoy.
    assert game.blue.transfers.created == []
    assert len(game.red.transfers.created) == 1
    assert sum(game.red.transfers.created[0].units.values()) == AMBIENT_CONVOY_UNITS


def test_target_band_is_a_few_not_a_parade() -> None:
    assert 1 <= MIN_AMBIENT_CONVOYS <= MAX_AMBIENT_CONVOYS <= 4


# ---- corridor enumeration -----------------------------------------------------------


def test_corridors_enumerate_each_road_once_oriented_rear_to_front() -> None:
    cps = _two_sided_map()
    game = _game(on=True, cps=cps)
    blue = _same_side_corridors(game, game.blue)
    red = _same_side_corridors(game, game.red)
    assert [(s.name, d.name) for s, d in blue] == [("blue-rear", "blue-fwd")]
    assert [(s.name, d.name) for s, d in red] == [("red-rear", "red-fwd")]


def test_corridors_fall_back_to_enemy_cps_on_a_frontless_laydown() -> None:
    # No conflicts (the COIN air-assault geometry): orientation references the
    # opposing CPs instead, so the flow still runs toward the enemy.
    cps = _two_sided_map()
    game = _game(on=True, cps=cps, fronts=[])
    blue = _same_side_corridors(game, game.blue)
    # Red's CPs sit at x=220/12; blue-fwd (x=10) is nearer them than blue-rear (x=200).
    assert [(s.name, d.name) for s, d in blue] == [("blue-rear", "blue-fwd")]


def test_no_war_to_supply_means_no_corridors() -> None:
    # No fronts AND no enemy CPs: nothing to orient toward, so no corridors at all.
    blue_rear = _CP("blue-rear", BLUE_PLAYER, 200.0, {"tank": 40})
    blue_fwd = _CP("blue-fwd", BLUE_PLAYER, 10.0, {"tank": 2})
    _road(blue_rear, blue_fwd)
    game = _game(on=True, cps=[blue_rear, blue_fwd], fronts=[])
    assert _same_side_corridors(game, game.blue) == []


# ---- batch-2 red corridors: the authored campaigns must keep their red road ----------
#
# The §50 batch-2 pass (2026-07-07) authored red->red rear corridors for the nine
# campaigns whose red side had no road at all -- without one, red's ambient convoys
# (and the player's §35-style interdiction targets) silently never exist. The tool
# table (tools/supply_route_geo.py BATCH2_RED_REAR) is the source of truth; loading
# each theater here means a laydown edit can't silently drop a red road.


def _batch2_stems() -> list[str]:
    from tools.supply_route_geo import BATCH2_RED_REAR

    return sorted(BATCH2_RED_REAR)


@pytest.mark.parametrize("stem", _batch2_stems())
def test_batch2_campaign_keeps_its_red_road(stem: str, tmp_path: Any) -> None:
    from pathlib import Path

    from game import persistency
    from game.campaignloader.campaign import Campaign

    persistency.setup(str(tmp_path), False, 0)
    campaign = Campaign.from_file(Path("resources/campaigns") / f"{stem}.yaml")
    theater = campaign.load_theater(campaign.advanced_iads)
    red_roads = set()
    for cp in theater.controlpoints:
        if not cp.starting_coalition.is_red:
            continue
        for other in cp.convoy_routes.keys():
            if other.starting_coalition.is_red:
                red_roads.add(tuple(sorted((cp.name, other.name))))
    assert len(red_roads) >= 1, (
        f"{stem} is in the §50 batch-2 red-corridor set but no longer binds a "
        "red->red supply road -- red's ambient convoys (and the interdiction "
        "targets they provide) will silently never exist there. Restore the red "
        "corridor (tools/supply_route_geo.py BATCH2_RED_REAR) or remove the "
        "campaign from that table."
    )
