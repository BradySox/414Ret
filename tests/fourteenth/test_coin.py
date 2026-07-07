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
    CELL_SIDC,
    IED_SIDC,
    REGEN_BASE_UNITS_PER_TURN,
    cache_health,
    regen_unit_pool,
    regenerate_insurgent_cells,
    symbol_insurgent_garrisons,
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


# ---- the TGO revival channel (C3: air-assault laydowns have no Base garrison) -----


def _cell_unit(
    *, alive: bool, unit_class: UnitClass = UnitClass.IFV, price: int = 2
) -> Any:
    unit = SimpleNamespace(
        alive=alive,
        is_vehicle=True,
        unit_type=SimpleNamespace(unit_class=unit_class, price=price),
        ground_object=None,
    )
    return unit


def _cell_tgo(name: str, units: list[Any]) -> Any:
    tgo = SimpleNamespace(category="vehicle", name=name, units=units)
    for unit in units:
        unit.ground_object = tgo
    return tgo


def test_revival_refills_dead_tgo_cells_toward_the_anchor() -> None:
    # The C3 laydown: no Base garrison at all -- the stronghold's force is its
    # vehicle-group TGOs. 4 alive at anchor; 3 die; full health revives 2/turn.
    units = [_cell_unit(alive=True) for _ in range(4)]
    cells = _cell_tgo("Stronghold cells", units)
    cp = _cp(caches=[cells])
    game = _game(turn=0, cps=[cp])
    regenerate_insurgent_cells(game)  # snapshot: tgo_cap 4
    assert game.coin_state["cp-1"]["tgo_cap"] == 4
    for unit in units[:3]:
        unit.alive = False
    _run_turns(game, 1, 1)
    assert sum(1 for u in units if u.alive) == 3
    _run_turns(game, 2, 2)
    assert sum(1 for u in units if u.alive) == 4
    _run_turns(game, 3, 6)
    assert sum(1 for u in units if u.alive) == 4  # revive, never grow


def test_revival_respects_the_whitelist() -> None:
    # Anchor = the eligible alive set at snapshot; a dead BMP (IFV over the price
    # ceiling) and a dead SAM are outside the whitelist AND the anchor -- they
    # never come back. Killing the anchored technical opens a revivable slot.
    technical = _cell_unit(alive=True, unit_class=UnitClass.IFV, price=2)
    bmp = _cell_unit(alive=False, unit_class=UnitClass.IFV, price=16)
    sam = _cell_unit(alive=False, unit_class=UnitClass.LAUNCHER, price=9)
    cells = _cell_tgo("Mixed cells", [technical, bmp, sam])
    cp = _cp(caches=[cells])
    game = _game(turn=0, cps=[cp])
    regenerate_insurgent_cells(game)
    # Anchor counts only eligible units: the one alive technical.
    assert game.coin_state["cp-1"]["tgo_cap"] == 1
    technical.alive = False
    _run_turns(game, 1, 4)
    assert technical.alive is True
    assert bmp.alive is False
    assert sam.alive is False


def test_revival_is_cache_throttled_too() -> None:
    caches = [_cache(), _cache()]
    units = [_cell_unit(alive=True) for _ in range(8)]
    cells = _cell_tgo("Cells", units)
    cp = _cp(caches=caches + [cells])
    game = _game(turn=0, cps=[cp])
    regenerate_insurgent_cells(game)
    for cache in caches:
        cache.units[0].alive = False
    for unit in units[:6]:
        unit.alive = False
    _run_turns(game, 1, 4)
    # Floor rate 0.5/turn: 2 units over 4 turns, not 8.
    assert sum(1 for u in units if u.alive) == 4


def test_armor_channel_takes_priority_over_revival() -> None:
    # A CP with BOTH a garrison deficit and a dead anchored cell: the 2/turn
    # budget fills the garrison first, then revives with the remainder.
    units = [_cell_unit(alive=True), _cell_unit(alive=True)]
    cells = _cell_tgo("Cells", units)
    cp = _cp(garrison={TECHNICAL: 4}, caches=[cells])
    game = _game(turn=0, cps=[cp])
    regenerate_insurgent_cells(game)  # caps: garrison 4, tgo 2
    cp.base.commit_losses({TECHNICAL: 1})
    units[1].alive = False
    _run_turns(game, 1, 1)
    assert cp.base.total_armor == 4  # 1 commissioned
    assert units[1].alive is True  # 1 revived with the remaining budget


def test_revive_fires_tgo_events_when_provided() -> None:
    updated = []
    events = SimpleNamespace(update_tgo=lambda tgo: updated.append(tgo))
    unit = _cell_unit(alive=True)
    cells = _cell_tgo("Cells", [unit])
    cp = _cp(caches=[cells])
    game = _game(turn=0, cps=[cp])
    regenerate_insurgent_cells(game, events)
    updated.clear()  # drop the turn-0 garrison-symboling event; isolate the revive
    unit.alive = False
    game.turn = 1
    regenerate_insurgent_cells(game, events)
    assert unit.alive is True
    assert updated == [cells]


# ---- COIN map symbology (insurgent garrisons read as infantry) --------------------


def test_symbol_insurgent_garrisons_marks_only_eligible_red_militia() -> None:
    militia = _cell_tgo("Militia", [_cell_unit(alive=True), _cell_unit(alive=True)])
    # A SAM crust TGO: its launcher unit fails the whitelist, so it keeps its symbol.
    sam = _cell_tgo(
        "SAM", [_cell_unit(alive=True, unit_class=UnitClass.LAUNCHER, price=9)]
    )
    cache = _cache()
    red = _cp(caches=[militia, sam, cache], cp_id="red")
    blue_militia = _cell_tgo("Blue militia", [_cell_unit(alive=True)])
    blue = _cp(owner=Player.BLUE, caches=[blue_militia], cp_id="blue")
    game = _game(turn=1, cps=[red, blue])

    symbol_insurgent_garrisons(game)

    assert militia.sidc_entity_override == CELL_SIDC  # irregular militia -> infantry
    assert not hasattr(sam, "sidc_entity_override")  # radar-SAM crust left alone
    assert not hasattr(cache, "sidc_entity_override")  # cache keeps its own symbol
    assert not hasattr(blue_militia, "sidc_entity_override")  # blue side untouched


def test_symbol_insurgent_garrisons_never_repoints_a_discrete_spawn() -> None:
    ied = _cell_tgo("IED", [_cell_unit(alive=True)])
    ied.sidc_entity_override = IED_SIDC  # already a discrete COIN spawn
    game = _game(turn=1, cps=[_cp(caches=[ied], cp_id="red")])

    symbol_insurgent_garrisons(game)

    assert ied.sidc_entity_override == IED_SIDC  # not overwritten with infantry


def test_symbol_insurgent_garrisons_off_switch() -> None:
    militia = _cell_tgo("Militia", [_cell_unit(alive=True)])
    game = _game(on=False, turn=1, cps=[_cp(caches=[militia])])

    symbol_insurgent_garrisons(game)

    assert not hasattr(militia, "sidc_entity_override")


def test_regen_symbols_garrisons_on_turn_zero() -> None:
    # The symbol pass rides regenerate_insurgent_cells and runs even on the turn-0
    # snapshot (before regen begins), so the very first map already reads infantry.
    militia = _cell_tgo("Militia", [_cell_unit(alive=True)])
    game = _game(turn=0, cps=[_cp(caches=[militia])])

    regenerate_insurgent_cells(game)

    assert militia.sidc_entity_override == CELL_SIDC


# ---- the C3 campaign definition lock ----------------------------------------------


def test_enduring_resolve_campaign_definition() -> None:
    # CI lock on the COIN campaign's authored blocks: a typo in the will profile or
    # arc degrades silently at runtime (by design), so the shipped YAML is asserted
    # here instead.
    from pathlib import Path

    import yaml

    from game.fourteenth.phases import parse_phases
    from game.fourteenth.political_will import parse_will_profile

    path = Path("resources/campaigns/coin_enduring_resolve.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    # The whole COIN stack preseeds on.
    for key in (
        "coin_insurgency",
        "vietnam_political_will",
        "vietnam_convoy_interdiction",
        "vietnam_airbase_harassment",
        "high_digit_sams",  # the faction's ERO technicals are HDS content
    ):
        assert data["settings"][key] is True, key
    # The miz the tool builds ships next to the yaml.
    assert (path.parent / data["miz"]).exists()
    # The original zeroed the economy; the fork restores a small real income.
    assert data["recommended_enemy_money"] > 0
    # The multi-nation coalition faction (CJTF Blue country, so the RNLAF/RAF
    # preset squadrons survive the country filter) ships with the campaign.
    assert data["recommended_player_faction"] == "OEF Coalition 2006"
    # Long-range carrier ops: the boat stands off ~800 km, so the campaign raises
    # the plane range gate and preseeds the deterministic carrier-package planner.
    assert data["settings"]["long_range_carrier_ops"] is True
    assert data["settings"]["max_mission_range_planes"] >= 500
    assert (path.parent.parent / "factions" / "oef_coalition_2006.json").exists()
    # The ratline: authored red<->red supply corridors (the original laydown had
    # zero CP connectivity, so the trail machinery had nothing to run on).
    assert len(data["supply_routes"]) >= 9
    for route in data["supply_routes"]:
        assert len(route["waypoints"]) >= 2

    profile = parse_will_profile(data["will"])
    assert profile.blue.label == "The Coalition's mandate"
    assert profile.red.label == "the insurgency's momentum"
    assert profile.weights.red_cache_lost == 4.0
    assert profile.weights.blue_roe_violation == 1.0  # CDE pressure, not taboo
    assert profile.weights.red_ground_unit_lost == 0.05  # body count buys nothing
    assert profile.weights.blue_passive_regen == 0.0  # time drains a mandate

    arc = parse_phases(data["phases"])
    assert [phase.key for phase in arc] == ["disrupt", "clear_hold", "build"]
    for phase in arc:
        # The caches must always be legal targets -- never lock ammo (or anything).
        assert phase.locked_target_classes == ()
        # The COIN ROE: 4 permanent positive-control VALLEYS (not town rings) -- big
        # box/corridor no-strike areas over the populated river valleys, shared by
        # every phase via the YAML anchor. Two corridors (Helmand Green Zone, Musa
        # Qala Valley) + two boxes (Tarin Kowt Bowl, Delaram), exercising both shapes.
        assert len(phase.restricted_zones) == 4
        kinds = sorted(z.kind for z in phase.restricted_zones)
        assert kinds == ["box", "box", "corridor", "corridor"]
        names = {z.name for z in phase.restricted_zones}
        assert names == {
            "Helmand Green Zone -- positive control",
            "Musa Qala Valley -- positive control",
            "Tarin Kowt Bowl -- positive control",
            "Delaram -- positive control",
        }
        # Each corridor carries a >=2-anchor centerline + a lane width; each box a
        # center + extents.
        for z in phase.restricted_zones:
            if z.kind == "corridor":
                assert len(z.path) >= 2 and z.corridor_width_nm > 0.0
            else:
                assert z.x is not None and z.y is not None
                assert z.width_nm > 0.0 and z.height_nm > 0.0

    # No inverted ROE: dropped the whole-map free-fire inversion for explicit no-strike
    # valleys, so no phase carries free-fire pockets.
    assert all(phase.free_fire_zones == () for phase in arc)


def test_despawn_emits_the_tgo_id_not_the_object() -> None:
    """The SSE model requires UUIDs in deleted_tgos; a TGO object poisons the
    GameUpdateEventsJs serialization and drops the whole event stream."""
    import uuid

    from game.fourteenth.coin import _despawn
    from game.sim.gameupdateevents import GameUpdateEvents

    tgo_id = uuid.uuid4()
    tgo = SimpleNamespace(id=tgo_id, control_point=None)
    game = SimpleNamespace(db=SimpleNamespace(tgos=SimpleNamespace(remove=lambda i: None)))
    events = GameUpdateEvents()
    _despawn(game, tgo, events)  # type: ignore[arg-type]
    assert events.deleted_tgos == {tgo_id}


def test_campaign_start_snapshot_pins_the_pre_loss_anchor() -> None:
    """finish_turn's regen hook only ever runs after the turn counter advanced,
    so the turn-0 anchor snapshot must come from initialize_turn (via
    snapshot_campaign_start_anchors) BEFORE the first mission's losses commit."""
    from game.fourteenth.coin import snapshot_campaign_start_anchors

    cp = _cp(garrison={TECHNICAL: 10})
    game = _game(turn=0, cps=[cp])
    snapshot_campaign_start_anchors(game)  # the initialize_turn(turn 0) hook
    # Mission 1 losses commit, then finish_turn increments to 1 and regens.
    cp.base.commit_losses({TECHNICAL: 4})
    _run_turns(game, 1, 2)
    # The anchor is the TRUE start state (10), not the post-loss 6.
    assert game.coin_state[str(cp.id)]["garrison_cap"] == 10
    assert cp.base.total_armor == 10


def test_campaign_start_snapshot_only_fires_at_turn_zero() -> None:
    from game.fourteenth.coin import snapshot_campaign_start_anchors

    cp = _cp(garrison={TECHNICAL: 10})
    game = _game(turn=3, cps=[cp])
    snapshot_campaign_start_anchors(game)
    assert getattr(game, "coin_state", None) is None
    game_off = _game(on=False, turn=0, cps=[cp])
    snapshot_campaign_start_anchors(game_off)
    assert getattr(game_off, "coin_state", None) is None
