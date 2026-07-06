"""§50 convoy ambush -> a CHANCE of real, hidden red ambush teams on blue's convoys.

Locks the force-model half of the feature: the chance-rolled ambush seeding -- 1..6 real,
``map_hidden`` red TGOs spread along an ambushed convoy's road, with last turn's despawned
first and NOTHING telegraphed to the UI (no marker, no uncertainty circle, no auto-fragged
escort package) -- plus every guard, so the feature no-ops rather than inventing free units
when a precondition is missing. (The convoys themselves come from the ambient-convoy layer
-- ``tests/fourteenth/test_ambient_convoys.py`` -- or any organic transfer; the roll covers
them all.)
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import game.fourteenth.coin as coin_module
import game.fourteenth.convoy_ambush as convoy_ambush_module
from game.fourteenth.convoy_ambush import (
    AMBUSH_TEAM_SIZE,
    MAX_AMBUSHES_PER_ROUTE,
    MIN_AMBUSHES_PER_ROUTE,
    ROUTE_END_MARGIN,
    _ambush_points,
    _nearest_cp,
    seed_convoy_ambushes,
)

# ---- fakes -------------------------------------------------------------------------


class _Owner:
    def __init__(self, blue: bool) -> None:
        self.is_blue = blue
        self.is_red = not blue


class _Pos:
    """A 1-D coordinate. ``distance_to_point`` is the real |Δx|, so a CP nearer a point
    reads a smaller distance (the corridor helpers place their reference front at x=0, so
    a CP's distance-to-front is just its own coordinate). ``heading_between_point`` /
    ``point_from_heading`` give the seeding helper a 1-D road to interpolate along."""

    def __init__(self, x: float) -> None:
        self.x = x

    def distance_to_point(self, other: "_Pos") -> float:
        return abs(self.x - other.x)

    def heading_between_point(self, other: "_Pos") -> float:
        return 0.0 if other.x >= self.x else 180.0

    def point_from_heading(self, heading: float, distance: float) -> "_Pos":
        return _Pos(self.x + (distance if heading == 0.0 else -distance))


class _CP:
    def __init__(self, name: str, blue: bool, dist: float) -> None:
        self.name = name
        self.captured = _Owner(blue)
        self.position = _Pos(dist)


class _Rng:
    """A scripted stand-in for the module RNG: pops ``rolls`` for random() (the per-convoy
    ambush chance, then the per-team placement jitter) and ``ints`` for randint (the
    team count)."""

    def __init__(self, rolls: list[float], ints: list[int]) -> None:
        self.rolls = list(rolls)
        self.ints = list(ints)

    def random(self) -> float:
        return self.rolls.pop(0) if self.rolls else 0.5

    def randint(self, a: int, b: int) -> int:
        value = self.ints.pop(0) if self.ints else a
        assert a <= value <= b, f"scripted randint {value} outside [{a}, {b}]"
        return value


# ---- _ambush_points / _nearest_cp ---------------------------------------------------


def _route_convoy(name: str, route: list[Any]) -> Any:
    return SimpleNamespace(
        name=name,
        origin=SimpleNamespace(convoy_route_to=lambda dest: route),
        destination="dest",
    )


#: A 100-km straight road built from three waypoints, so the placement helper has real
#: segment lengths to interpolate along.
_ROAD = [_Pos(0.0), _Pos(40_000.0), _Pos(100_000.0)]


def test_ambush_points_spread_along_the_road_inside_the_margins(
    monkeypatch: Any,
) -> None:
    # Jitter 0.5 -> each of 4 teams sits at the centre of its stratified slot.
    monkeypatch.setattr(convoy_ambush_module, "_RNG", _Rng(rolls=[0.5] * 4, ints=[]))
    convoy = _route_convoy("C1", _ROAD)
    points = _ambush_points(convoy, 4)
    assert len(points) == 4
    total = 100_000.0
    lo, hi = ROUTE_END_MARGIN * total, (1 - ROUTE_END_MARGIN) * total
    xs = [p.x for p in points]
    assert xs == sorted(xs)  # walked in order down the road
    assert all(lo <= x <= hi for x in xs)  # never near either endpoint base
    # Stratified slots -> genuinely spread, not stacked on one bend.
    assert xs[-1] - xs[0] > total * 0.4


def test_ambush_points_interpolate_between_sparse_waypoints(monkeypatch: Any) -> None:
    # A single team with jitter 0.5 lands mid-road (x=50km) -- INSIDE the second
    # segment, at a point that is not an authored waypoint.
    monkeypatch.setattr(convoy_ambush_module, "_RNG", _Rng(rolls=[0.5], ints=[]))
    convoy = _route_convoy("C1", _ROAD)
    points = _ambush_points(convoy, 1)
    assert len(points) == 1
    assert points[0].x == 50_000.0
    assert all(points[0].x != wp.x for wp in _ROAD)


def test_ambush_points_none_for_a_degenerate_road() -> None:
    for route in ([], [_Pos(0.0)], [_Pos(0.0), _Pos(0.0)]):  # missing or zero-length
        convoy = _route_convoy("C1", route)
        assert _ambush_points(convoy, 3) == []


def test_ambush_points_swallow_a_broken_convoy() -> None:
    def boom(dest: Any) -> Any:
        raise RuntimeError("no route")

    convoy = SimpleNamespace(
        origin=SimpleNamespace(convoy_route_to=boom), destination="dest"
    )
    assert _ambush_points(convoy, 3) == []


def test_nearest_cp_picks_the_closest() -> None:
    near = _CP("near", False, 5.0)
    far = _CP("far", False, 50.0)
    assert _nearest_cp([far, near], _Pos(0.0)) is near  # type: ignore[list-item]


# ---- seed_convoy_ambushes ----------------------------------------------------------


def _ambush_game(*, on: bool, red_cps: list[_CP], convoys: list[Any]) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(convoy_ambush=on),
        theater=SimpleNamespace(controlpoints=red_cps),
        blue=SimpleNamespace(transfers=SimpleNamespace(convoys=convoys)),
    )


def _capture_spawns(monkeypatch: Any) -> list[dict[str, Any]]:
    spawned: list[dict[str, Any]] = []

    def fake_spawn(
        g: Any, red_cp: Any, point: Any, task: Any, events: Any = None, **kw: Any
    ) -> Any:
        tgo = SimpleNamespace(id=f"tgo-{len(spawned) + 1}", map_hidden=False)
        spawned.append(
            {
                "point": point,
                "events": events,
                "max_units": kw.get("max_units"),
                "concealed": kw.get("concealed"),
                "tgo": tgo,
            }
        )
        return tgo

    monkeypatch.setattr(coin_module, "spawn_red_ground_at", fake_spawn)
    return spawned


def test_seed_off_is_a_noop(monkeypatch: Any) -> None:
    game = _ambush_game(on=False, red_cps=[_CP("r", False, 0.0)], convoys=[])
    seed_convoy_ambushes(game, events=None)
    assert not getattr(game, "convoy_ambush_state", {}).get("ambushes")


def test_seed_noop_without_red_cps(monkeypatch: Any) -> None:
    convoy = _route_convoy("C1", _ROAD)
    game = _ambush_game(on=True, red_cps=[], convoys=[convoy])
    spawned = _capture_spawns(monkeypatch)
    seed_convoy_ambushes(game, events=None)
    assert spawned == []
    assert game.convoy_ambush_state["ambushes"] == []


def test_seed_is_a_chance_not_a_certainty(monkeypatch: Any) -> None:
    # The convoy's chance roll misses (>= AMBUSH_CHANCE) -> a quiet road, no teams.
    red = _CP("stronghold", False, 0.0)
    convoy = _route_convoy("Convoy-1", _ROAD)
    game = _ambush_game(on=True, red_cps=[red], convoys=[convoy])
    spawned = _capture_spawns(monkeypatch)
    monkeypatch.setattr(convoy_ambush_module, "_RNG", _Rng(rolls=[0.99], ints=[]))
    seed_convoy_ambushes(game, events=None)
    assert spawned == []
    assert game.convoy_ambush_state["ambushes"] == []


def test_seed_rolls_multiple_hidden_teams_down_one_route(monkeypatch: Any) -> None:
    red = _CP("stronghold", False, 0.0)
    convoy = _route_convoy("Convoy-1", _ROAD)
    game = _ambush_game(on=True, red_cps=[red], convoys=[convoy])
    spawned = _capture_spawns(monkeypatch)
    # Chance roll hits (0.0), the count roll says a 3-team gauntlet, placement jitter 0.5.
    monkeypatch.setattr(
        convoy_ambush_module, "_RNG", _Rng(rolls=[0.0, 0.5, 0.5, 0.5], ints=[3])
    )
    seed_convoy_ambushes(game, events="EV")

    assert len(spawned) == 3
    for record in spawned:
        assert record["max_units"] == AMBUSH_TEAM_SIZE
        # Fully hidden, not circle-concealed: no marker, no uncertainty circle...
        assert record["concealed"] is None
        assert record["tgo"].map_hidden is True
        # ...and never pushed to the client as a TGO update.
        assert record["events"] is None
    xs = [record["point"].x for record in spawned]
    assert xs == sorted(xs)  # a gauntlet in order down the road
    records = game.convoy_ambush_state["ambushes"]
    assert records == [
        {"tgo_id": "tgo-1", "convoy": "Convoy-1"},
        {"tgo_id": "tgo-2", "convoy": "Convoy-1"},
        {"tgo_id": "tgo-3", "convoy": "Convoy-1"},
    ]


def test_seed_rolls_each_convoy_independently(monkeypatch: Any) -> None:
    red = _CP("stronghold", False, 0.0)
    hit = _route_convoy("Convoy-1", _ROAD)
    miss = _route_convoy("Convoy-2", _ROAD)
    game = _ambush_game(on=True, red_cps=[red], convoys=[hit, miss])
    spawned = _capture_spawns(monkeypatch)
    # Convoy-1 hits (0.0) with 1 team (jitter 0.5); Convoy-2 misses (0.99).
    monkeypatch.setattr(
        convoy_ambush_module, "_RNG", _Rng(rolls=[0.0, 0.5, 0.99], ints=[1])
    )
    seed_convoy_ambushes(game, events=None)
    assert len(spawned) == 1
    assert game.convoy_ambush_state["ambushes"] == [
        {"tgo_id": "tgo-1", "convoy": "Convoy-1"}
    ]


def test_seed_count_stays_inside_the_authored_band() -> None:
    assert 1 <= MIN_AMBUSHES_PER_ROUTE <= MAX_AMBUSHES_PER_ROUTE
    # The user-facing promise: "sometimes once, sometimes five or six times per route".
    assert MAX_AMBUSHES_PER_ROUTE == 6


def test_seed_despawns_last_turns_ambushes_first(monkeypatch: Any) -> None:
    red = _CP("stronghold", False, 0.0)
    convoy = _route_convoy("Convoy-1", _ROAD)
    game = _ambush_game(on=True, red_cps=[red], convoys=[convoy])
    game.convoy_ambush_state = {"ambushes": [{"tgo_id": "old-1", "convoy": "prev"}]}

    despawned: list[str] = []
    monkeypatch.setattr(
        coin_module, "_tgo_by_id", lambda g, tid: SimpleNamespace(id=tid)
    )
    monkeypatch.setattr(
        coin_module, "_despawn", lambda g, tgo, ev: despawned.append(tgo.id)
    )
    _capture_spawns(monkeypatch)
    monkeypatch.setattr(convoy_ambush_module, "_RNG", _Rng(rolls=[0.0, 0.5], ints=[1]))
    seed_convoy_ambushes(game, events=None)

    assert despawned == ["old-1"]  # the prior ambush was cleaned up
    assert game.convoy_ambush_state["ambushes"] == [
        {"tgo_id": "tgo-1", "convoy": "Convoy-1"}
    ]


# ---- nothing telegraphed: the map_hidden contract -----------------------------------
#
# The ambush teams must not surface anywhere in the campaign UI: no map marker (the
# server skips hidden TGOs), no AI-fragged package revealing them in the ATO (the
# commander's battle-position sweep skips them), and no auto-fragged escort (the old
# plan_convoy_escort hook is deleted -- supporting the column is an in-mission decision).


def test_map_hidden_tgo_is_hidden_from_the_player_map() -> None:
    from typing import cast

    from dcs.mapping import Point

    from game.theater import Player
    from game.theater.controlpoint import OffMapSpawn
    from game.theater.presetlocation import PresetLocation
    from game.theater.theatergroundobject import VehicleGroupGroundObject
    from game.utils import Heading

    location = PresetLocation(
        name="ambush",
        position=Point(0, 0, None),  # type: ignore[arg-type]
        heading=Heading(0),
    )
    control_point = OffMapSpawn(
        name="red-cp",
        position=Point(0, 0, None),  # type: ignore[arg-type]
        theater=None,  # type: ignore[arg-type]
        starts_blue=Player.RED,
    )
    tgo = VehicleGroupGroundObject(
        name="Ambush Team",
        location=location,
        control_point=control_point,
        task=None,
    )
    # hidden_on_player_map() reaches control_point.captured / .is_friendly() /
    # .coalition.game.settings (the scar-fog test pattern).
    tgo.control_point = cast(
        Any,
        SimpleNamespace(
            captured=Player.RED,
            is_friendly=lambda to_player: False,
            coalition=SimpleNamespace(
                game=SimpleNamespace(
                    settings=SimpleNamespace(
                        scar_command_post_intel=True,
                        recon_intel_fog=True,
                    )
                )
            ),
        ),
    )
    assert tgo.hidden_on_player_map(Player.BLUE) is False
    tgo.map_hidden = True
    # Hidden from the human even after discovery -- there is no reveal key...
    tgo.discovered_by_player = True
    assert tgo.hidden_on_player_map(Player.BLUE) is True
    # ...but the AI / threat math (viewer=None) still sees ground truth.
    assert tgo.hidden_on_player_map(None) is False


def test_map_hidden_tgo_is_not_a_battle_position() -> None:
    from game.commander.battlepositions import BattlePositions
    from game.theater.theatergroundobject import VehicleGroupGroundObject

    class _FakeVehicleTgo(VehicleGroupGroundObject):
        def __init__(self, hidden: bool) -> None:  # bypass the heavy base __init__
            self.map_hidden = hidden

        def is_dead(self, viewer: Any = None) -> bool:
            return False

        def distance_to(self, cp: Any) -> float:
            return 1e9  # "defending the front line", not blocking capture

    visible = _FakeVehicleTgo(hidden=False)
    hidden = _FakeVehicleTgo(hidden=True)
    cp = SimpleNamespace(ground_objects=[visible, hidden])
    positions = BattlePositions.for_control_point(cp)  # type: ignore[arg-type]
    assert visible in list(positions.in_priority_order)
    assert hidden not in list(positions.in_priority_order)


def test_no_escort_auto_frag_hook_remains() -> None:
    # The escort package is the player's in-mission choice now; the ATO hook is gone.
    assert not hasattr(convoy_ambush_module, "plan_convoy_escort")


# ---- the road inventory: campaigns known to field the feature must keep the road ----
#
# The hard prerequisite the 2026-07-05 flown test exposed: the convoy layer needs a
# blue->blue road corridor (a supply_routes entry linking two BLUE control points) or
# the whole blue side silently no-ops -- no convoy, no ambush. The two COIN campaigns
# shipped preseeding convoy_ambush: true with an all-red supply graph, so the flagship
# "ambush alley" campaigns could never field a convoy. With the 2026-07-06
# standardization (ambient convoys + the ambush default ON everywhere), the guard grew
# from the 4 preseeds into the full ROAD-BEARING INVENTORY: every campaign that had a
# blue->blue road at the standardization survey must keep one, so a laydown edit can't
# silently kill the feature on that campaign. A campaign NOT listed simply doesn't
# field a blue convoy (documented no-op -- island maps and all-red graphs); when a
# blue rear corridor is authored for one (see tools/supply_route_geo.py and the
# driveable-corridor standard), ADD it here.

#: The 2026-07-06 survey: every shipping campaign whose theater binds at least one
#: blue->blue supply road (and can therefore field ambient blue convoys + ambushes).
ROAD_BEARING_CAMPAIGNS = [
    "1968_Yankee_Station",
    "Caucasus_Multi_Full",
    "IntotheHornetsNest",
    "Invasion_of_Canary_Islands",
    "Northern Guardian",
    "Operation-Desert-Sabre",
    "WRL_AssaultonDamascus",
    "black_sea",
    "clash_of_the_titans",
    "coin_enduring_resolve",
    "crossing_the_rubicon",
    "exercise_able_archer",
    "exercise_bright_star",
    "exercise_quasar",
    "exercise_vegas_nerve",
    "golan_heights_lite",
    "graveyard_of_empires",
    "iraq_inherent_resolve",
    "marianas_guam_barrigada",
    "mozdok_to_maykop",
    "operation_allied_sword",
    "operation_dynamo",
    "operation_frostbite",
    "red_flag_81_2",
    "red_tide",
    "scenic_inland",
    "tripoint_hostility",
]


def _blue_blue_road_count(theater: Any) -> int:
    roads = set()
    for cp in theater.controlpoints:
        if not cp.starting_coalition.is_blue:
            continue
        for other in cp.convoy_routes.keys():
            if other.starting_coalition.is_blue:
                roads.add(tuple(sorted((cp.name, other.name))))
    return len(roads)


def test_flagship_ambush_campaigns_stay_in_the_inventory() -> None:
    # The four campaigns that pioneered the feature (and still preseed the plugin) must
    # never drop out of the road-bearing set.
    assert set(ROAD_BEARING_CAMPAIGNS) >= {
        "coin_enduring_resolve",
        "iraq_inherent_resolve",
        "1968_Yankee_Station",
        "red_tide",
    }


@pytest.mark.parametrize("stem", ROAD_BEARING_CAMPAIGNS)
def test_road_bearing_campaign_keeps_its_blue_road(stem: str, tmp_path: Any) -> None:
    from pathlib import Path

    from game import persistency
    from game.campaignloader.campaign import Campaign

    persistency.setup(str(tmp_path), False, 0)
    path = Path("resources/campaigns") / f"{stem}.yaml"
    assert path.exists(), (
        f"{stem} is in ROAD_BEARING_CAMPAIGNS but the campaign file is gone -- "
        "remove it from the inventory (or restore the campaign)."
    )
    campaign = Campaign.from_file(path)
    theater = campaign.load_theater(campaign.advanced_iads)
    assert _blue_blue_road_count(theater) >= 1, (
        f"{stem} is in the §50 road-bearing inventory but no longer binds a "
        "blue->blue supply road -- ambient blue convoys (and with them the whole "
        "ambush loop) will silently never exist there. Restore the blue rear "
        "corridor (see tools/supply_route_geo.py) or remove the campaign from "
        "ROAD_BEARING_CAMPAIGNS."
    )
