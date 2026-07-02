"""COIN C1: the insurgent cell-regeneration core (design-note §3).

Locks the model: free anchored-cap regeneration into insurgent-held CPs' garrisons,
cache-health throttling with the 25% floor (squadron call §7.1), the hard unit
whitelist (class set + price ceiling -- technicals in, BMPs/Grads/SAMs out), the
fractional-carry accumulator, and the safety rails (off-switch, turn-0 snapshot
only, blue/neutral untouched, refill-never-grow).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.data.units import UnitClass
from game.fourteenth.coin import (
    CACHE_HEALTH_FLOOR,
    REGEN_BASE_UNITS_PER_TURN,
    cache_health,
    regen_unit_pool,
    regenerate_insurgent_cells,
)
from game.theater import Player
from game.theater.base import Base


class _Unit:
    """Hashable GroundUnitType fake (it keys Base.armor)."""

    def __init__(self, name: str, unit_class: UnitClass, price: int) -> None:
        self.display_name = name
        self.unit_class = unit_class
        self.price = price

    def __repr__(self) -> str:
        return self.display_name


TECHNICAL = _Unit("Toyota technical", UnitClass.IFV, 2)
INFANTRY = _Unit("Insurgent infantry", UnitClass.INFANTRY, 1)
ZU23 = _Unit("ZU-23 emplacement", UnitClass.AAA, 4)
BMP2 = _Unit("BMP-2", UnitClass.IFV, 16)
GRAD = _Unit("BM-21 Grad", UnitClass.ARTILLERY, 15)
TANK = _Unit("T-55", UnitClass.TANK, 12)
SAM = _Unit("SA-9", UnitClass.LAUNCHER, 9)

_DEFAULT_POOL = {TECHNICAL, INFANTRY, ZU23}


def _cache(alive: bool = True) -> Any:
    return SimpleNamespace(category="ammo", units=[SimpleNamespace(alive=alive)])


def _cp(
    *,
    owner: Player = Player.RED,
    garrison: dict[Any, int] | None = None,
    caches: list[Any] | None = None,
    cp_id: str = "cp-1",
) -> Any:
    base = Base()
    base.commission_units(garrison or {})
    return SimpleNamespace(
        captured=owner,
        id=cp_id,
        base=base,
        ground_objects=caches or [],
    )


def _game(
    *,
    on: bool = True,
    turn: int = 0,
    cps: list[Any] | None = None,
    pool: set[Any] | None = None,
) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(coin_insurgency=on),
        turn=turn,
        red=SimpleNamespace(
            faction=SimpleNamespace(
                frontline_units=pool if pool is not None else set(_DEFAULT_POOL)
            )
        ),
        theater=SimpleNamespace(controlpoints=cps or []),
    )


def _run_turns(game: Any, first: int, last: int) -> None:
    for turn in range(first, last + 1):
        game.turn = turn
        regenerate_insurgent_cells(game)


# ---- safety rails ----------------------------------------------------------------


def test_off_switch_touches_nothing() -> None:
    cp = _cp(garrison={TECHNICAL: 4})
    game = _game(on=False, turn=3, cps=[cp])
    regenerate_insurgent_cells(game)
    assert cp.base.total_armor == 4
    assert getattr(game, "coin_state", None) is None


def test_turn_zero_snapshots_but_does_not_regenerate() -> None:
    cp = _cp(garrison={TECHNICAL: 6}, caches=[_cache(), _cache()])
    game = _game(turn=0, cps=[cp])
    regenerate_insurgent_cells(game)
    assert cp.base.total_armor == 6
    anchor = game.coin_state["cp-1"]
    assert anchor["garrison_cap"] == 6
    assert anchor["cache_total"] == 2


def test_blue_and_neutral_cps_are_untouched() -> None:
    blue = _cp(owner=Player.BLUE, garrison={TECHNICAL: 1}, cp_id="cp-blue")
    neutral = _cp(owner=Player.NEUTRAL, garrison={TECHNICAL: 1}, cp_id="cp-n")
    game = _game(turn=1, cps=[blue, neutral])
    _run_turns(game, 1, 5)
    assert blue.base.total_armor == 1
    assert neutral.base.total_armor == 1
    assert "cp-blue" not in game.coin_state
    assert "cp-n" not in game.coin_state


def test_no_eligible_units_is_a_noop() -> None:
    cp = _cp(garrison={TECHNICAL: 2})
    game = _game(turn=1, cps=[cp], pool={BMP2, TANK, SAM})
    _run_turns(game, 1, 4)
    assert cp.base.total_armor == 2


# ---- the anchored cap ------------------------------------------------------------


def test_regen_refills_toward_anchor_and_never_exceeds() -> None:
    # Anchored at 10 on turn 0, attrited to 6: at full health (no caches authored ->
    # full rate) the garrison refills by 2/turn and stops exactly at the anchor.
    cp = _cp(garrison={TECHNICAL: 10})
    game = _game(turn=0, cps=[cp])
    regenerate_insurgent_cells(game)  # snapshot
    cp.base.commit_losses({TECHNICAL: 4})
    assert cp.base.total_armor == 6
    _run_turns(game, 1, 2)
    assert cp.base.total_armor == 10
    _run_turns(game, 3, 6)
    assert cp.base.total_armor == 10  # refill, never grow


def test_mid_campaign_enable_anchors_to_current_garrison() -> None:
    # First seen insurgent-held at turn 5: the cap is the *current* garrison, so an
    # intact stronghold never grows past what it had when the toggle came on.
    cp = _cp(garrison={TECHNICAL: 4})
    game = _game(turn=5, cps=[cp])
    _run_turns(game, 5, 9)
    assert cp.base.total_armor == 4
    cp.base.commit_losses({TECHNICAL: 2})
    _run_turns(game, 10, 10)
    assert cp.base.total_armor == 4


# ---- the cache throttle ----------------------------------------------------------


def test_cache_health_scales_and_floors() -> None:
    caches = [_cache(), _cache(), _cache(), _cache()]
    cp = _cp(caches=caches)
    assert cache_health(cp, 4) == 1.0
    caches[0].units[0].alive = False
    caches[1].units[0].alive = False
    assert cache_health(cp, 4) == 0.5
    for cache in caches:
        cache.units[0].alive = False
    assert cache_health(cp, 4) == CACHE_HEALTH_FLOOR


def test_no_authored_caches_means_full_rate() -> None:
    assert cache_health(_cp(caches=[]), 0) == 1.0


def test_dead_caches_throttle_regen_to_the_floor() -> None:
    # Anchored with 2 caches; both destroyed. Base 2/turn * 0.25 floor = 0.5/turn:
    # the fractional carry lands one unit every other turn instead of rounding to
    # zero forever -- a cleared stronghold decays under pressure but never flatlines.
    assert REGEN_BASE_UNITS_PER_TURN * CACHE_HEALTH_FLOOR == 0.5
    caches = [_cache(), _cache()]
    cp = _cp(garrison={TECHNICAL: 10}, caches=caches)
    game = _game(turn=0, cps=[cp])
    regenerate_insurgent_cells(game)  # snapshot: cap 10, caches 2
    for cache in caches:
        cache.units[0].alive = False
    cp.base.commit_losses({TECHNICAL: 6})
    assert cp.base.total_armor == 4
    _run_turns(game, 1, 4)
    assert cp.base.total_armor == 6  # 0.5/turn * 4 turns = 2 units
    _run_turns(game, 5, 12)
    assert cp.base.total_armor == 10


def test_half_caches_half_rate() -> None:
    caches = [_cache(), _cache()]
    cp = _cp(garrison={TECHNICAL: 8}, caches=caches)
    game = _game(turn=0, cps=[cp])
    regenerate_insurgent_cells(game)
    caches[0].units[0].alive = False
    cp.base.commit_losses({TECHNICAL: 4})
    _run_turns(game, 1, 2)
    # 2/turn * 0.5 health = 1/turn.
    assert cp.base.total_armor == 6


# ---- the whitelist ---------------------------------------------------------------


def test_pool_admits_irregular_kit_only() -> None:
    coalition = SimpleNamespace(
        faction=SimpleNamespace(
            frontline_units={TECHNICAL, INFANTRY, ZU23, BMP2, GRAD, TANK, SAM}
        )
    )
    pool = regen_unit_pool(coalition)  # type: ignore[arg-type]
    # Technicals (IFV price 2) in; BMP-2 (IFV 16) priced out; Grad (15) priced out;
    # tank and SAM classes never admitted.
    assert pool == [INFANTRY, TECHNICAL, ZU23]  # cheapest-first


def test_regen_commissions_a_mix_from_the_pool() -> None:
    cp = _cp(garrison={TECHNICAL: 12})
    game = _game(turn=0, cps=[cp])
    regenerate_insurgent_cells(game)
    cp.base.commit_losses({TECHNICAL: 8})
    _run_turns(game, 1, 3)
    # 6 units regenerated across 3 turns; the pool is cycled, so more than one
    # eligible type appears rather than a monoculture of the cheapest.
    regenerated = {
        unit: count for unit, count in cp.base.armor.items() if unit is not TECHNICAL
    }
    assert sum(cp.base.armor.values()) == 10
    assert len(regenerated) >= 1


# ---- the multi-turn shell sanity (the C1.5 trigger bar) ---------------------------


def test_shell_sanity_regen_refills_and_cache_kills_throttle() -> None:
    # The design-note C1.5 bar: over a played arc, regen visibly refills a
    # stronghold, and killing its caches visibly throttles it.
    caches = [_cache(), _cache()]
    cp = _cp(garrison={TECHNICAL: 12}, caches=caches)
    game = _game(turn=0, cps=[cp])
    regenerate_insurgent_cells(game)

    # Phase 1 -- BLUE attrits cells only: the hole refills at full rate.
    cp.base.commit_losses({TECHNICAL: 4})
    _run_turns(game, 1, 2)
    full_rate_refill = cp.base.total_armor
    assert full_rate_refill == 12

    # Phase 2 -- BLUE kills the caches, then attrits again: the same hole now
    # refills at the floor rate, so after the same two turns it is NOT closed.
    for cache in caches:
        cache.units[0].alive = False
    cp.base.commit_losses({TECHNICAL: 4})
    _run_turns(game, 3, 4)
    assert cp.base.total_armor == 9  # 8 + floor(0.5*2) = 9, hole still open
    assert cp.base.total_armor < 12
