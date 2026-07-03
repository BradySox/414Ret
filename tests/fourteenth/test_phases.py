"""Campaign phases (W3): the Tier-0 classifier, hysteresis, and planner emphasis.

Locks the §3.2 phase boundaries (incl. the pilot's absolute-SAM-floor gate and the
peer-fight guard), the §3.3 hysteresis (min-dwell, monotonic-forward default, the
asymmetric regression margin behind the authored-only flag), the §3.4 legibility
string, the per-turn update entry point's gating/idempotence, and the §4 soft
emphasis contract between game/fourteenth/phases.py and PlanNextAction.
"""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any, Optional, cast

import pytest

from game.commander.tasks.compound.nextaction import PlanNextAction
from game.fourteenth.phases import (
    AIR_THREAT_FLOOR,
    FRONT_ADVANCE_EPSILON,
    IADS_OFFENSIVE_CEILING,
    IADS_ROLLBACK_HOLD,
    OFFENSIVE_METHODS,
    PHASE_MIN_DWELL_TURNS,
    PHASES,
    CampaignPhase,
    PhaseBaseline,
    PhaseMetrics,
    ROLLBACK_SAM_FLOOR,
    _next_phase_key,
    _parse_restricted_zone,
    _resolve_zone,
    _zone_label,
    active_phase,
    active_restricted_zones,
    classify,
    collect_metrics,
    count_roe_violations,
    legibility,
    parse_phases,
    roe_blocks_target,
    update_campaign_phase,
)


def _metrics(
    *,
    sam_baseline: int = 12,
    iads_ratio: float = 1.0,
    air_threat_present: bool = False,
    front_delta: float = 0.0,
    recent_capture: bool = False,
    base_ratio: float = 0.5,
) -> PhaseMetrics:
    return PhaseMetrics(
        sam_baseline=sam_baseline,
        sam_alive=round(sam_baseline * iads_ratio),
        iads_ratio=iads_ratio,
        fighters_baseline=20,
        fighters_alive=20 if air_threat_present else 0,
        air_threat_present=air_threat_present,
        front_delta=front_delta,
        recent_capture=recent_capture,
        base_ratio=base_ratio,
    )


# --- §3.2 phase boundaries -----------------------------------------------------------


def test_dense_iads_opens_in_rollback() -> None:
    # Turn 0: every ratio is 1.0; the SAM belt keeps the opening in Rollback.
    assert classify(_metrics(sam_baseline=12, iads_ratio=1.0)) == "rollback"


def test_sam_floor_unmet_with_real_air_holds_air_superiority() -> None:
    # The pilot's "Air Superiority (fighter)" opening: no SAM belt, real MiGs.
    m = _metrics(sam_baseline=0, iads_ratio=0.0, air_threat_present=True)
    assert classify(m) == "rollback"


def test_sam_floor_unmet_and_weak_air_opens_in_interdiction() -> None:
    # The genuine below-floor shape (Shattered Dagger / Valley of Rotary et al.,
    # per the #379 engine-authoritative all-66 run): no belt + no real air => no
    # Rollback phase at all.
    m = _metrics(sam_baseline=0, iads_ratio=0.0, air_threat_present=False)
    assert classify(m) == "interdiction"


def test_sam_floor_boundary() -> None:
    below = _metrics(sam_baseline=ROLLBACK_SAM_FLOOR - 1, iads_ratio=1.0)
    at = _metrics(sam_baseline=ROLLBACK_SAM_FLOOR, iads_ratio=1.0)
    assert classify(below) == "interdiction"
    assert classify(at) == "rollback"


def test_degraded_iads_and_quiet_air_is_interdiction() -> None:
    m = _metrics(iads_ratio=IADS_ROLLBACK_HOLD - 0.1)
    assert classify(m) == "interdiction"


def test_peer_guard_air_threat_keeps_rollback_despite_dead_iads() -> None:
    # Slava Ukraini shape: IADS collapsed but red air is still a real threat --
    # Rollback only releases when BOTH are down.
    m = _metrics(iads_ratio=0.1, air_threat_present=True)
    assert classify(m) == "rollback"


def test_offensive_needs_low_iads_and_ground_movement() -> None:
    moving = _metrics(iads_ratio=0.2, front_delta=FRONT_ADVANCE_EPSILON)
    static = _metrics(iads_ratio=0.2, front_delta=0.0)
    captured = _metrics(iads_ratio=0.2, recent_capture=True)
    too_much_iads = _metrics(iads_ratio=IADS_OFFENSIVE_CEILING + 0.05, front_delta=0.2)
    assert classify(moving) == "offensive"
    assert classify(static) == "interdiction"
    assert classify(captured) == "offensive"
    assert classify(too_much_iads) == "interdiction"


# --- §3.3 hysteresis -----------------------------------------------------------------


def test_min_dwell_holds_the_phase() -> None:
    m = _metrics(iads_ratio=0.2)  # target: interdiction
    held = _next_phase_key("rollback", 5, 5 + PHASE_MIN_DWELL_TURNS - 1, m)
    released = _next_phase_key("rollback", 5, 5 + PHASE_MIN_DWELL_TURNS, m)
    assert held == "rollback"
    assert released == "interdiction"


def test_monotonic_forward_by_default() -> None:
    # The IADS "rebuilds" but v1 never regresses (most narratives don't un-happen).
    m = _metrics(iads_ratio=0.9)
    assert _next_phase_key("offensive", 1, 10, m) == "offensive"
    assert _next_phase_key("interdiction", 1, 10, m) == "interdiction"


def test_regression_needs_the_asymmetric_margin() -> None:
    # The authored-tier flag (P2): a rebuild must clear the 0.6 re-enter margin,
    # not merely re-cross the 0.5 hold line.
    noise = _metrics(iads_ratio=0.55)
    rebuild = _metrics(iads_ratio=0.65)
    assert (
        _next_phase_key("interdiction", 1, 10, noise, allow_regression=True)
        == "interdiction"
    )
    assert (
        _next_phase_key("interdiction", 1, 10, rebuild, allow_regression=True)
        == "rollback"
    )


def test_first_assignment_ignores_dwell() -> None:
    m = _metrics(sam_baseline=0, air_threat_present=False)
    assert _next_phase_key(None, None, 0, m) == "interdiction"


# --- §3.4 legibility -----------------------------------------------------------------


def test_legibility_explains_itself() -> None:
    m = _metrics(iads_ratio=0.22, air_threat_present=False, front_delta=0.0)
    line = legibility(PHASES["interdiction"], m)
    assert "Interdiction" in line
    assert "22%" in line
    assert "air threat low" in line
    assert "front static" in line


def test_legibility_without_a_sam_belt() -> None:
    m = _metrics(sam_baseline=0, iads_ratio=0.0)
    line = legibility(PHASES["interdiction"], m)
    assert "no enemy SAM belt" in line


# --- the per-turn entry point --------------------------------------------------------


def _duck_game(
    *,
    on: bool = True,
    turn: int = 0,
    current: Optional[str] = None,
    entered: Optional[int] = None,
    baseline: Optional[PhaseBaseline] = None,
    campaign_name: Optional[str] = None,
    controlpoints: Optional[list[Any]] = None,
    blue_will: Optional[float] = None,
) -> Any:
    messages: list[tuple[str, str]] = []
    game = SimpleNamespace(
        settings=SimpleNamespace(campaign_phases=on),
        theater=SimpleNamespace(
            ground_objects=[],
            conflicts=lambda: [],
            controlpoints=controlpoints or [],
        ),
        air_wing_for=lambda player: SimpleNamespace(iter_squadrons=lambda: []),
        turn=turn,
        last_sitrep=None,
        current_phase_key=current,
        phase_entered_on_turn=entered,
        phase_status_line=None,
        phase_baseline=baseline,
        campaign_name=campaign_name,
        blue=SimpleNamespace(political_will=blue_will),
        messages=messages,
    )
    game.message = lambda title, text="": messages.append((title, text))
    return game


def test_update_disarmed_clears_state() -> None:
    game = _duck_game(on=False, current="rollback", entered=1)
    update_campaign_phase(game)
    assert game.current_phase_key is None
    assert game.phase_entered_on_turn is None
    assert game.phase_status_line is None
    assert active_phase(game) is None


def test_update_snapshots_baseline_and_assigns_opening_phase() -> None:
    game = _duck_game(on=True, turn=0)
    update_campaign_phase(game)
    # An empty theater has no SAM belt and no air: the Khe Sanh opening.
    assert game.phase_baseline is not None
    assert game.current_phase_key == "interdiction"
    assert game.phase_entered_on_turn == 0
    assert game.phase_status_line is not None
    assert active_phase(game) is PHASES["interdiction"]
    # The campaign-start assignment is not announced...
    assert game.messages == []
    # ...and a same-turn re-init (initialize_turn runs multiple times) is stable.
    update_campaign_phase(game)
    assert game.current_phase_key == "interdiction"
    assert game.messages == []


def test_update_announces_a_transition_once() -> None:
    # Start in rollback (as if the belt existed), with the live theater empty the
    # classifier targets interdiction once the dwell releases.
    baseline = PhaseBaseline(sam_sites=12, enemy_fighters=0)
    game = _duck_game(
        on=True,
        turn=PHASE_MIN_DWELL_TURNS,
        current="rollback",
        entered=0,
        baseline=baseline,
    )
    update_campaign_phase(game)
    assert game.current_phase_key == "interdiction"
    assert len(game.messages) == 1
    assert "Interdiction" in game.messages[0][0]
    # Re-init the same turn: no phase change, no repeat announcement.
    update_campaign_phase(game)
    assert len(game.messages) == 1


def test_collect_metrics_reads_the_duck_theater() -> None:
    baseline = PhaseBaseline(
        sam_sites=4, enemy_fighters=10, front_fractions={"a:b": 0.5}
    )
    game = _duck_game(on=True)
    m = collect_metrics(game, baseline)
    assert m.sam_baseline == 4
    assert m.sam_alive == 0
    assert m.iads_ratio == 0.0
    assert m.fighters_alive == 0
    assert not m.air_threat_present
    # No live front matches the baseline key: no vote, front reads static.
    assert m.front_delta == 0.0


# --- §4 planner emphasis -------------------------------------------------------------


def test_factories_and_phase_orderings_stay_in_sync() -> None:
    factories = list(PlanNextAction._OFFENSIVE_FACTORIES)
    assert factories == list(OFFENSIVE_METHODS)
    for phase in PHASES.values():
        assert sorted(phase.emphasis) == sorted(OFFENSIVE_METHODS), phase.key


def _planner_state(coalition: Any) -> Any:
    return SimpleNamespace(context=SimpleNamespace(coalition=coalition))


def _coalition(game: Any, blue: bool) -> Any:
    return SimpleNamespace(
        player=SimpleNamespace(is_blue=blue),
        game=game,
    )


def test_offensive_order_stock_without_a_phase() -> None:
    task = PlanNextAction(aircraft_cold_start=False)
    game = _duck_game(on=False)
    order = task._offensive_order(_planner_state(_coalition(game, blue=True)))
    assert order == list(OFFENSIVE_METHODS)


def test_offensive_order_follows_the_blue_phase() -> None:
    task = PlanNextAction(aircraft_cold_start=False)
    game = _duck_game(on=True, current="rollback", entered=0)
    order = task._offensive_order(_planner_state(_coalition(game, blue=True)))
    assert order == list(PHASES["rollback"].emphasis)
    assert order[0] == "DegradeIads"


def test_red_planner_keeps_stock_order() -> None:
    task = PlanNextAction(aircraft_cold_start=False)
    game = _duck_game(on=True, current="offensive", entered=0)
    order = task._offensive_order(_planner_state(_coalition(game, blue=False)))
    assert order == list(OFFENSIVE_METHODS)


def test_each_valid_method_keeps_the_reactive_prefix_and_tail() -> None:
    task = PlanNextAction(aircraft_cold_start=False)
    game = _duck_game(on=True, current="offensive", entered=0)
    state = _planner_state(_coalition(game, blue=True))
    names = [type(method[0]).__name__ for method in task.each_valid_method(state)]
    # The §17 boundary: support/defense lead in fixed order; recovery closes.
    assert names[:3] == ["TheaterSupport", "ProtectAirSpace", "DefendBases"]
    assert names[-1] == "RecoverySupport"
    assert names[3:-1] == list(PHASES["offensive"].emphasis)
    assert names[3] == "CaptureBases"


# --- W4: the authored tier + the ROE escalation layer ---------------------------------


class _Pt:
    """Flat-plane point stub with the one method the zone math calls."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def distance_to_point(self, other: "_Pt") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


def _authored_arc() -> tuple[CampaignPhase, ...]:
    return parse_phases(
        [
            {
                "key": "rolling_thunder",
                "name": "Rolling Thunder",
                "narrative": "Restraint.",
                "emphasis": "interdiction",
                "restricted_zones": [
                    {"center": "Hanoi", "radius_nm": 10, "name": "Hanoi sanctuary"}
                ],
                "locked_targets": ["factory", "airfield"],
                "advance_when": {"blue_will_below": 75},
                "objectives": [
                    "Respect the sanctuaries",
                    {
                        "text": "Break the belt",
                        "done_when": {"enemy_iads_below": 0.5},
                    },
                ],
            },
            {
                "key": "linebacker",
                "name": "Linebacker",
                "emphasis": "rollback",
                "min_turn": 6,
            },
            {
                "key": "linebacker_ii",
                "name": "Linebacker II",
                "emphasis": "offensive",
                "min_turn": 10,
            },
        ]
    )


@pytest.fixture
def authored_game() -> Any:
    from game.fourteenth import phases

    hanoi = SimpleNamespace(name="Hanoi", position=_Pt(0.0, 0.0))
    game = _duck_game(campaign_name="ROE Test", controlpoints=[hanoi], blue_will=100.0)
    phases._ARC_CACHE["ROE Test"] = _authored_arc()
    yield game
    del phases._ARC_CACHE["ROE Test"]


def test_authored_arc_overrides_tier0_and_holds_opening(authored_game: Any) -> None:
    update_campaign_phase(authored_game)
    assert authored_game.current_phase_key == "rolling_thunder"
    phase = active_phase(authored_game)
    assert phase is not None and phase.authored
    # Borrowed Tier-0 emphasis reaches the planner order.
    assert phase.emphasis == PHASES["interdiction"].emphasis
    assert "phase 1 of 3" in authored_game.phase_status_line
    assert "ROE restrictions active" in authored_game.phase_status_line
    assert authored_game.messages == []  # opening assignment is silent


def test_authored_arc_advances_on_schedule_once(authored_game: Any) -> None:
    authored_game.current_phase_key = "rolling_thunder"
    authored_game.turn = 6
    update_campaign_phase(authored_game)
    assert authored_game.current_phase_key == "linebacker"
    assert len(authored_game.messages) == 1
    assert "Linebacker" in authored_game.messages[0][0]
    # Same-turn re-init: stable, no repeat announcement.
    update_campaign_phase(authored_game)
    assert authored_game.current_phase_key == "linebacker"
    assert len(authored_game.messages) == 1


def test_authored_arc_accelerates_on_bleeding_will(authored_game: Any) -> None:
    # Turn 2 is well before the schedule, but Washington is bleeding.
    authored_game.current_phase_key = "rolling_thunder"
    authored_game.turn = 2
    authored_game.blue.political_will = 60.0
    update_campaign_phase(authored_game)
    assert authored_game.current_phase_key == "linebacker"


def test_authored_arc_skips_ahead_for_a_late_adopting_save(authored_game: Any) -> None:
    # A mid-campaign save with no stored key enters at the turn-eligible phase.
    authored_game.turn = 11
    update_campaign_phase(authored_game)
    assert authored_game.current_phase_key == "linebacker_ii"


def test_roe_blocks_zone_and_locked_class(authored_game: Any) -> None:
    update_campaign_phase(authored_game)
    nm = 1852.0
    inside = SimpleNamespace(position=_Pt(5 * nm, 0.0))
    outside = SimpleNamespace(position=_Pt(50 * nm, 0.0))
    assert roe_blocks_target(authored_game, inside)
    assert not roe_blocks_target(authored_game, outside)
    # Advance to Linebacker II: no zones, nothing locked.
    authored_game.turn = 10
    update_campaign_phase(authored_game)
    assert authored_game.current_phase_key == "linebacker_ii"
    assert not roe_blocks_target(authored_game, inside)


def test_roe_ignores_everything_without_an_authored_phase() -> None:
    game = _duck_game(on=True, current="rollback", entered=0)
    target = SimpleNamespace(position=_Pt(0.0, 0.0))
    assert not roe_blocks_target(game, target)
    assert active_restricted_zones(game) == []


def test_count_roe_violations(authored_game: Any) -> None:
    update_campaign_phase(authored_game)
    nm = 1852.0

    def mapping(x: float) -> Any:
        return SimpleNamespace(theater_unit=SimpleNamespace(position=_Pt(x, 0.0)))

    debriefing = SimpleNamespace(
        ground_losses=SimpleNamespace(
            enemy_ground_objects=[mapping(2 * nm), mapping(8 * nm), mapping(60 * nm)]
        )
    )
    assert count_roe_violations(authored_game, debriefing) == 2  # type: ignore[arg-type]


def test_count_roe_violations_zero_without_zones() -> None:
    game = _duck_game(on=True, current="interdiction", entered=0)
    debriefing = SimpleNamespace(ground_losses=SimpleNamespace(enemy_ground_objects=[]))
    assert count_roe_violations(game, debriefing) == 0  # type: ignore[arg-type]


def test_parse_phases_rejects_bad_entries() -> None:
    with pytest.raises(ValueError):
        parse_phases([{"name": "no key"}])
    with pytest.raises(ValueError):
        parse_phases([{"key": "x", "emphasis": "not-a-phase"}])
    with pytest.raises(ValueError):
        parse_phases([{"key": "x", "restricted_zones": [{"radius_nm": 10}]}])


_NM = 1852.0


def test_box_zone_parses_resolves_and_contains() -> None:
    # A 20x10 nm axis-aligned box centered at the origin: spans +/-10 nm along x
    # (width) and +/-5 nm along y (height).
    zone = _parse_restricted_zone(
        {
            "shape": "box",
            "name": "The Box",
            "x": 0.0,
            "y": 0.0,
            "width_nm": 20,
            "height_nm": 10,
        }
    )
    assert zone.kind == "box"
    resolved = _resolve_zone(_duck_game(), zone)
    assert resolved is not None and resolved.kind == "box"
    assert len(resolved.outline_xy) == 4
    assert resolved.contains(_Pt(5 * _NM, 0.0))  # inside the width & height
    assert not resolved.contains(_Pt(0.0, 8 * _NM))  # past the 5 nm half-height
    assert not resolved.contains(_Pt(15 * _NM, 0.0))  # past the 10 nm half-width


def test_box_heading_rotates_the_footprint() -> None:
    # A point 8 nm east (0, 8nm) is outside the axis-aligned box but inside once the
    # box is rotated 90 degrees (width axis now runs east-west).
    base = {
        "shape": "box",
        "name": "b",
        "x": 0.0,
        "y": 0.0,
        "width_nm": 20,
        "height_nm": 10,
    }
    point = _Pt(0.0, 8 * _NM)
    flat = _resolve_zone(_duck_game(), _parse_restricted_zone(base))
    turned = _resolve_zone(
        _duck_game(), _parse_restricted_zone({**base, "heading": 90})
    )
    assert flat is not None and turned is not None
    assert not flat.contains(point)
    assert turned.contains(point)


def test_corridor_zone_parses_resolves_and_contains() -> None:
    # A 10 nm-wide lane along the x-axis from the origin to 100 km east-of-north.
    zone = _parse_restricted_zone(
        {
            "shape": "corridor",
            "name": "Trail",
            "path": [{"x": 0.0, "y": 0.0}, {"x": 100000.0, "y": 0.0}],
            "width_nm": 10,
        }
    )
    assert zone.kind == "corridor" and len(zone.path) == 2
    resolved = _resolve_zone(_duck_game(), zone)
    assert resolved is not None and resolved.kind == "corridor"
    assert resolved.contains(_Pt(50000.0, 5000.0))  # within the ~9.3 km half-width
    assert not resolved.contains(_Pt(50000.0, 20000.0))  # well outside the lane


def test_corridor_resolves_cp_named_anchors() -> None:
    a = SimpleNamespace(name="A", position=_Pt(0.0, 0.0))
    b = SimpleNamespace(name="B", position=_Pt(100000.0, 0.0))
    game = _duck_game(controlpoints=[a, b])
    zone = _parse_restricted_zone(
        {"shape": "corridor", "name": "AB", "path": ["A", "B"], "width_nm": 10}
    )
    resolved = _resolve_zone(game, zone)
    assert resolved is not None and resolved.contains(_Pt(50000.0, 0.0))
    # A path that names an absent CP drops below 2 anchors and resolves to nothing.
    missing = _parse_restricted_zone(
        {"shape": "corridor", "name": "AX", "path": ["A", "X"], "width_nm": 10}
    )
    assert _resolve_zone(game, missing) is None


def test_zone_labels_by_shape() -> None:
    circle = _resolve_zone(
        _duck_game(controlpoints=[SimpleNamespace(name="C", position=_Pt(0.0, 0.0))]),
        _parse_restricted_zone({"center": "C", "radius_nm": 12, "name": "Ring"}),
    )
    box = _resolve_zone(
        _duck_game(),
        _parse_restricted_zone(
            {
                "shape": "box",
                "name": "Box",
                "x": 0.0,
                "y": 0.0,
                "width_nm": 4,
                "height_nm": 4,
            }
        ),
    )
    assert circle is not None and _zone_label(circle) == "Ring 12 nm"
    assert box is not None and _zone_label(box) == "Box (box)"


def test_parse_restricted_zone_rejects_bad_shapes() -> None:
    with pytest.raises(ValueError):  # unknown shape
        _parse_restricted_zone({"shape": "blob", "name": "x"})
    with pytest.raises(ValueError):  # box needs a name
        _parse_restricted_zone(
            {"shape": "box", "x": 0.0, "y": 0.0, "width_nm": 4, "height_nm": 4}
        )
    with pytest.raises(ValueError):  # box needs extents
        _parse_restricted_zone({"shape": "box", "name": "b", "x": 0.0, "y": 0.0})
    with pytest.raises(ValueError):  # corridor needs >=2 anchors
        _parse_restricted_zone(
            {
                "shape": "corridor",
                "name": "c",
                "path": [{"x": 0.0, "y": 0.0}],
                "width_nm": 4,
            }
        )


def test_from_drawing_parses_to_a_drawing_zone() -> None:
    z = _parse_restricted_zone({"from_drawing": "Hanoi Box"})
    assert z.kind == "drawing" and z.drawing == "Hanoi Box" and z.name == "Hanoi Box"
    # An explicit name overrides the drawing name as the display label.
    z2 = _parse_restricted_zone({"from_drawing": "poly-1", "name": "Sanctuary"})
    assert z2.drawing == "poly-1" and z2.name == "Sanctuary"


def test_resolve_drawing_zone_circle_and_polygon() -> None:
    from game.fourteenth.zone_drawings import DrawnZone

    game = _duck_game()
    game.theater.zone_drawings = {
        "Ring": DrawnZone("Ring", "circle", center_xy=(0.0, 0.0), radius_m=10 * _NM),
        "Box": DrawnZone(
            "Box",
            "polygon",
            center_xy=(0.0, 0.0),
            outline_xy=(
                (-5 * _NM, -5 * _NM),
                (5 * _NM, -5 * _NM),
                (5 * _NM, 5 * _NM),
                (-5 * _NM, 5 * _NM),
            ),
        ),
    }
    ring = _resolve_zone(game, _parse_restricted_zone({"from_drawing": "Ring"}))
    assert ring is not None and ring.kind == "circle"
    assert ring.contains(_Pt(3 * _NM, 0.0)) and not ring.contains(_Pt(20 * _NM, 0.0))

    box = _resolve_zone(game, _parse_restricted_zone({"from_drawing": "Box"}))
    assert box is not None and box.kind == "polygon"
    assert box.contains(_Pt(0.0, 0.0)) and not box.contains(_Pt(10 * _NM, 0.0))


def test_resolve_drawing_zone_missing_reference_is_none() -> None:
    game = _duck_game()
    game.theater.zone_drawings = {}
    zone = _parse_restricted_zone({"from_drawing": "nope"})
    assert _resolve_zone(game, zone) is None


# --- inverted ROE: COIN free-fire zones --------------------------------------------


def _free_fire_game(entry: dict[str, Any], name: str) -> Any:
    """A game whose active authored phase is ``entry`` (a single-phase arc)."""
    from game.fourteenth import phases

    game = _duck_game(campaign_name=name, controlpoints=[], blue_will=100.0)
    phases._ARC_CACHE[name] = parse_phases([{"key": "coin", "name": "COIN", **entry}])
    update_campaign_phase(game)
    return game


def test_free_fire_zone_inverts_the_gate(monkeypatch: Any) -> None:
    from game.fourteenth import phases

    game = _free_fire_game(
        {
            "free_fire_zones": [
                {"x": 0.0, "y": 0.0, "radius_nm": 10, "name": "AO Bravo"}
            ]
        },
        "FF gate",
    )
    try:
        # Classify the duck targets by a .category attribute (a real TGO would).
        monkeypatch.setattr(
            phases, "_target_class", lambda t: getattr(t, "category", None)
        )
        inside = SimpleNamespace(position=_Pt(5 * _NM, 0.0), category="ammo")
        outside = SimpleNamespace(position=_Pt(50 * _NM, 0.0), category="ammo")
        frontline = SimpleNamespace(position=_Pt(50 * _NM, 0.0))  # no class
        assert not roe_blocks_target(game, inside)  # inside the pocket -> cleared
        assert roe_blocks_target(game, outside)  # outside -> weapons hold
        assert not roe_blocks_target(game, frontline)  # ground fight always legal
    finally:
        del phases._ARC_CACHE["FF gate"]


def test_free_fire_restricted_zone_carves_out_a_no_strike_hole(
    monkeypatch: Any,
) -> None:
    from game.fourteenth import phases

    game = _free_fire_game(
        {
            "free_fire_zones": [{"x": 0.0, "y": 0.0, "radius_nm": 20, "name": "AO"}],
            "restricted_zones": [
                {"x": 0.0, "y": 0.0, "radius_nm": 5, "name": "Village"}
            ],
        },
        "FF carveout",
    )
    try:
        monkeypatch.setattr(
            phases, "_target_class", lambda t: getattr(t, "category", None)
        )
        # Inside the pocket but inside the village no-strike hole -> still blocked.
        in_village = SimpleNamespace(position=_Pt(2 * _NM, 0.0), category="ammo")
        in_pocket = SimpleNamespace(position=_Pt(12 * _NM, 0.0), category="ammo")
        assert roe_blocks_target(game, in_village)
        assert not roe_blocks_target(game, in_pocket)
    finally:
        del phases._ARC_CACHE["FF carveout"]


def test_count_roe_violations_counts_kills_outside_the_pocket() -> None:
    game = _free_fire_game(
        {"free_fire_zones": [{"x": 0.0, "y": 0.0, "radius_nm": 10, "name": "AO"}]},
        "FF viol",
    )
    try:

        def mapping(x: float) -> Any:
            return SimpleNamespace(theater_unit=SimpleNamespace(position=_Pt(x, 0.0)))

        debriefing = SimpleNamespace(
            ground_losses=SimpleNamespace(
                enemy_ground_objects=[
                    mapping(5 * _NM),
                    mapping(50 * _NM),
                    mapping(60 * _NM),
                ]
            )
        )
        # 5 nm inside the pocket -> legal; 50 & 60 nm outside -> 2 violations.
        assert count_roe_violations(game, debriefing) == 2  # type: ignore[arg-type]
    finally:
        from game.fourteenth import phases

        del phases._ARC_CACHE["FF viol"]


def test_roe_summary_leads_with_weapons_free() -> None:
    from game.fourteenth.phases import roe_summary_lines

    game = _free_fire_game(
        {"free_fire_zones": [{"x": 0.0, "y": 0.0, "radius_nm": 8, "name": "AO Bravo"}]},
        "FF summary",
    )
    try:
        lines = dict(roe_summary_lines(game))
        assert "WEAPONS FREE" in lines
        assert "AO Bravo" in lines["WEAPONS FREE"]
        assert "all else off-limits" in lines["WEAPONS FREE"]
    finally:
        from game.fourteenth import phases

        del phases._ARC_CACHE["FF summary"]


def test_sanctuary_airfield_falls_out_of_the_zone(authored_game: Any) -> None:
    # W5 sanctuary basing: an enemy airfield inside an active restricted zone
    # cannot be OCA'd (blocked as a zone target AND as the "airfield" class while
    # locked), so the MiGs based there are safe on the ground until the zone
    # lifts -- the Rolling Thunder problem, emerging from W4 for free. Real
    # Airfield instance via the fork's __new__ trick so isinstance() runs.
    from game.theater.controlpoint import Airfield

    update_campaign_phase(authored_game)
    nm = 1852.0
    field = Airfield.__new__(Airfield)
    field.position = _Pt(5 * nm, 0.0)  # type: ignore[assignment]
    assert roe_blocks_target(authored_game, field)
    # Outside the zone it is still blocked in phase 1: "airfield" is a locked class.
    field.position = _Pt(50 * nm, 0.0)  # type: ignore[assignment]
    assert roe_blocks_target(authored_game, field)
    # Linebacker II releases everything -- the sanctuary lifts.
    authored_game.turn = 10
    update_campaign_phase(authored_game)
    field.position = _Pt(5 * nm, 0.0)  # type: ignore[assignment]
    assert not roe_blocks_target(authored_game, field)


def test_roe_summary_spells_out_off_limits_and_cleared(authored_game: Any) -> None:
    # The kneeboard cover's CAMPAIGN PHASE band: OFF LIMITS (zones with radii),
    # LOCKED (withheld classes), CLEARED (classes the enemy actually fields and
    # the phase released, plus the never-gated front fight).
    from game.fourteenth.phases import roe_summary_lines
    from game.theater import Player

    update_campaign_phase(authored_game)
    hanoi = authored_game.theater.controlpoints[0]
    hanoi.captured = Player.RED
    hanoi.dcs_airport = object()
    hanoi.connected_objectives = [
        SimpleNamespace(category="factory"),
        SimpleNamespace(category="aa"),
        SimpleNamespace(category="ammo"),
        SimpleNamespace(category="village"),  # never advertised as a target
    ]
    friendly = SimpleNamespace(
        name="Home Plate",
        position=_Pt(0.0, 0.0),
        captured=Player.BLUE,
        dcs_airport=object(),
        connected_objectives=[SimpleNamespace(category="fuel")],
    )
    authored_game.theater.controlpoints.append(friendly)

    lines = dict(roe_summary_lines(authored_game))
    assert lines["OFF LIMITS"] == "Hanoi sanctuary 10 nm"
    assert lines["LOCKED"] == "factories, airfields (OCA)"
    # Derived from the enemy laydown minus the locked classes; blue-owned fuel
    # and the enemy village never appear.
    assert lines["CLEARED"] == "air defenses, ammo depots, front-line forces & convoys"

    # Linebacker II releases everything: no ROE payload, no band.
    authored_game.turn = 10
    update_campaign_phase(authored_game)
    assert roe_summary_lines(authored_game) == []


def test_roe_summary_empty_without_an_authored_phase() -> None:
    from game.fourteenth.phases import roe_summary_lines

    game = _duck_game(on=True, current="rollback", entered=0)
    assert roe_summary_lines(game) == []
    assert roe_summary_lines(_duck_game(on=False)) == []


# --- the campaign-layer UI feeds (arc expander / badge reason / zone detail) ---------


def test_roe_restriction_reason_names_the_class_or_the_zone(
    authored_game: Any,
) -> None:
    from game.fourteenth.phases import roe_restriction_reason
    from game.theater.controlpoint import Airfield

    update_campaign_phase(authored_game)
    nm = 1852.0
    # A locked class far from any circle: the reason is the class lock (the
    # playtest confusion -- a badged factory with no zone nearby looked broken).
    field = Airfield.__new__(Airfield)
    field.position = _Pt(50 * nm, 0.0)  # type: ignore[assignment]
    assert roe_restriction_reason(authored_game, field) == (
        "airfield targets are locked this phase"
    )
    # An unlocked-class target inside the circle: the reason is the sanctuary.
    inside = SimpleNamespace(position=_Pt(5 * nm, 0.0))
    assert roe_restriction_reason(authored_game, inside) == "inside Hanoi sanctuary"
    # An unlocked-class target outside: no reason, no badge -- AAA is fair game.
    outside = SimpleNamespace(position=_Pt(50 * nm, 0.0))
    assert roe_restriction_reason(authored_game, outside) is None


def test_arc_overview_authored(authored_game: Any) -> None:
    from game.fourteenth.phases import arc_overview

    update_campaign_phase(authored_game)
    overview = arc_overview(authored_game)
    assert [entry["key"] for entry in overview] == [
        "rolling_thunder",
        "linebacker",
        "linebacker_ii",
    ]
    assert overview[0]["current"] is True
    assert overview[0]["locked"] == ["factory", "airfield"]
    assert overview[0]["zones"] == ["Hanoi sanctuary"]
    assert overview[1]["min_turn"] == 6 and overview[1]["current"] is False


def test_arc_overview_tier0_and_disarmed() -> None:
    from game.fourteenth.phases import arc_overview

    game = _duck_game(on=True, current="interdiction", entered=0)
    overview = arc_overview(game)
    assert [entry["key"] for entry in overview] == [
        "rollback",
        "interdiction",
        "offensive",
    ]
    assert [entry["current"] for entry in overview] == [False, True, False]
    assert arc_overview(_duck_game(on=False)) == []


def test_condition_red_resolve_and_capture_cp() -> None:
    from game.fourteenth.phases import PhaseCondition, _condition_satisfied

    baseline = PhaseBaseline(sam_sites=0, enemy_fighters=0)
    game = _duck_game()
    game.red = SimpleNamespace(political_will=20.0)
    assert _condition_satisfied(game, PhaseCondition(red_resolve_below=25), baseline)
    assert not _condition_satisfied(
        game, PhaseCondition(red_resolve_below=15), baseline
    )
    hue = SimpleNamespace(name="Hue", captured=SimpleNamespace(is_blue=True))
    cp_game = _duck_game(controlpoints=[hue])
    assert _condition_satisfied(cp_game, PhaseCondition(capture_cp="Hue"), baseline)
    hue.captured = SimpleNamespace(is_blue=False)
    assert not _condition_satisfied(cp_game, PhaseCondition(capture_cp="Hue"), baseline)
    # A CP name absent from the theater never satisfies (edited campaign safety).
    assert not _condition_satisfied(
        cp_game, PhaseCondition(capture_cp="Khe Sanh"), baseline
    )


def test_arc_overview_transition_transparency(authored_game: Any) -> None:
    # The expander spells out HOW the arc leaves each phase: the authored
    # advance_when with live values on the current phase, nothing on a phase
    # without an early-out or on the terminal phase.
    from game.fourteenth.phases import arc_overview

    update_campaign_phase(authored_game)
    overview = arc_overview(authored_game)
    assert overview[0]["advance"] == (
        "Escalates early if will falls below 75 (now 100)"
    )
    assert overview[1]["advance"] == ""  # schedule-only (min_turn on the next row)
    assert overview[2]["advance"] == ""  # terminal


def test_arc_overview_tier0_spells_out_the_classifier() -> None:
    # An inferred arc explains its transitions the same way an authored one does.
    from game.fourteenth.phases import arc_overview

    game = _duck_game(on=True, current="interdiction", entered=0)
    overview = arc_overview(game)
    assert "50%" in str(overview[0]["advance"])
    assert "30%" in str(overview[1]["advance"])
    assert overview[2]["advance"] == ""


def test_arc_overview_objectives_tick_live(authored_game: Any) -> None:
    from game.fourteenth.phases import arc_overview

    # Baseline of 4 SAM sites, live theater empty: the IADS objective is met.
    authored_game.phase_baseline = PhaseBaseline(sam_sites=4, enemy_fighters=0)
    update_campaign_phase(authored_game)
    overview = arc_overview(authored_game)
    objectives = overview[0]["objectives"]
    assert objectives == [
        {"text": "Respect the sanctuaries", "done": None},  # display-only bullet
        {"text": "Break the belt", "done": True},
    ]


def test_arc_overview_tier0_objectives() -> None:
    # The built-in Tier-0 objectives: measurable IADS goals tick from live state;
    # a belt-less duck theater with a real baseline reads as "belt beaten".
    from game.fourteenth.phases import arc_overview

    game = _duck_game(
        on=True,
        current="interdiction",
        entered=0,
        baseline=PhaseBaseline(sam_sites=4, enemy_fighters=0),
    )
    overview = arc_overview(game)
    rollback_objs = cast(Any, overview[0]["objectives"])
    assert rollback_objs[0]["done"] is True
    assert rollback_objs[1]["done"] is None
    interdiction_objs = cast(Any, overview[1]["objectives"])
    assert interdiction_objs[0]["done"] is True


def test_parse_phases_rejects_bad_objectives() -> None:
    with pytest.raises(ValueError):
        parse_phases([{"key": "x", "objectives": [{"done_when": {}}]}])
    with pytest.raises(ValueError):
        parse_phases([{"key": "x", "advance_when": "not-a-mapping"}])


def test_zone_detail_names_locks_and_the_lift(authored_game: Any) -> None:
    from game.fourteenth.phases import zone_detail

    update_campaign_phase(authored_game)
    detail = zone_detail(authored_game)
    assert "factory, airfield" in detail
    assert "Eases at Linebacker (~turn 6)" in detail
    # Tier-0 phases carry no authored ROE: no zone, no detail.
    assert zone_detail(_duck_game(on=True, current="interdiction", entered=0)) == ""
