"""Vietnam campaign layer W6 -- phase-coupled red tempo.

Locks the three levers (trail_surge / ground_offensive / resolve_regen) to the
ACTIVE AUTHORED phase's ``red_tempo:`` block: parse, the window math, the raise-only
stance pulse, the once-per-turn regen guard, and the guarantee that Tier-0 (inferred)
phases and non-Vietnam campaigns are complete no-ops. Also guards the 4 shipped
Vietnam arcs' authored blocks. See docs/dev/design/414th-vietnam-red-tempo-notes.md.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

import pytest
import yaml

from game.fourteenth import phases
from game.fourteenth.phases import CampaignPhase, parse_phases
from game.fourteenth.red_tempo import (
    GROUND_OFFENSIVE_MIN_SURGE,
    announce_red_tempo,
    apply_red_tempo,
    ground_offensive_active,
    trail_surge_multiplier,
)
from game.ground_forces.combat_stance import CombatStance

_CAMPAIGNS = Path(__file__).resolve().parents[2] / "resources" / "campaigns"

_ARC_NAME = "Red Tempo Test"


def _arc() -> tuple[CampaignPhase, ...]:
    return (
        CampaignPhase(key="thunder", name="Thunder", narrative="", authored=True),
        CampaignPhase(
            key="halt",
            name="Halt",
            narrative="",
            authored=True,
            trail_surge=2.0,
            resolve_regen=1.5,
        ),
        CampaignPhase(
            key="offensive_pulse",
            name="Easter",
            narrative="",
            authored=True,
            ground_offensive_turns=3,
        ),
    )


@pytest.fixture()
def arc_cache() -> Any:
    phases._ARC_CACHE[_ARC_NAME] = _arc()
    yield
    del phases._ARC_CACHE[_ARC_NAME]


def _cp(name: str) -> Any:
    return SimpleNamespace(id=name, name=name, stances={})


def _front(red_cp: Any, blue_cp: Any) -> Any:
    return SimpleNamespace(
        control_point_friendly_to=lambda player: (
            red_cp if player == "RED" else blue_cp
        ),
        control_point_hostile_to=lambda player: (
            blue_cp if player == "RED" else red_cp
        ),
    )


def _game(
    *,
    key: Optional[str],
    turn: int = 5,
    entered: Optional[int] = 5,
    will_on: bool = True,
    red_will: float = 50.0,
    fronts: Optional[list[Any]] = None,
) -> Any:
    game = SimpleNamespace(
        settings=SimpleNamespace(campaign_phases=True, vietnam_political_will=will_on),
        campaign_name=_ARC_NAME,
        current_phase_key=key,
        phase_entered_on_turn=entered,
        turn=turn,
        red=SimpleNamespace(political_will=red_will, player="RED"),
        theater=SimpleNamespace(conflicts=lambda: list(fronts or [])),
        red_tempo_regen_turn=None,
    )
    game.messages = []
    game.message = lambda title, body, _m=game.messages: _m.append((title, body))
    return game


# ---- parse ---------------------------------------------------------------------------


def test_parse_reads_red_tempo_block() -> None:
    (phase,) = parse_phases(
        [
            {
                "key": "halt",
                "red_tempo": {
                    "trail_surge": 2.0,
                    "ground_offensive": 3,
                    "resolve_regen": 1.5,
                },
            }
        ]
    )
    assert phase.trail_surge == 2.0
    assert phase.ground_offensive_turns == 3
    assert phase.resolve_regen == 1.5


def test_parse_defaults_without_red_tempo() -> None:
    (phase,) = parse_phases([{"key": "thunder"}])
    assert phase.trail_surge == 1.0
    assert phase.ground_offensive_turns == 0
    assert phase.resolve_regen == 0.0


def test_parse_rejects_non_mapping_red_tempo() -> None:
    with pytest.raises(ValueError):
        parse_phases([{"key": "halt", "red_tempo": [2.0]}])


def test_tier0_phases_carry_no_red_tempo() -> None:
    for phase in phases.PHASES.values():
        assert phase.trail_surge == 1.0
        assert phase.ground_offensive_turns == 0
        assert phase.resolve_regen == 0.0


# ---- trail_surge_multiplier ------------------------------------------------------------


def test_surge_is_baseline_without_an_authored_phase(arc_cache: Any) -> None:
    # A Tier-0 key (not in the authored arc) resolves to an inferred phase: baseline.
    game = _game(key=None)
    assert trail_surge_multiplier(game) == 1.0
    game = _game(key="rollback")
    assert trail_surge_multiplier(game) == 1.0


def test_surge_reads_the_active_authored_phase(arc_cache: Any) -> None:
    assert trail_surge_multiplier(_game(key="halt")) == 2.0
    assert trail_surge_multiplier(_game(key="thunder")) == 1.0


def test_ground_offensive_implies_the_minimum_surge(arc_cache: Any) -> None:
    # The Easter pulse rides a logistics surge even though its phase authored none.
    game = _game(key="offensive_pulse", turn=5, entered=5)
    assert trail_surge_multiplier(game) == GROUND_OFFENSIVE_MIN_SURGE


# ---- ground_offensive window -----------------------------------------------------------


def test_offensive_window_spans_n_turns_from_entry(arc_cache: Any) -> None:
    for turn, active in ((5, True), (6, True), (7, True), (8, False)):
        game = _game(key="offensive_pulse", turn=turn, entered=5)
        assert ground_offensive_active(game) is active, turn
    # Phases without the lever never pulse.
    assert not ground_offensive_active(_game(key="halt"))
    # An unknown entry turn cannot open a window.
    assert not ground_offensive_active(
        _game(key="offensive_pulse", turn=5, entered=None)
    )


def test_offensive_raises_passive_stances_only(arc_cache: Any) -> None:
    red_cp, blue_cp = _cp("red"), _cp("blue")
    red_cp.stances[blue_cp.id] = CombatStance.DEFENSIVE
    winning_red, winning_blue = _cp("winning-red"), _cp("winning-blue")
    winning_red.stances[winning_blue.id] = CombatStance.BREAKTHROUGH
    game = _game(
        key="offensive_pulse",
        fronts=[_front(red_cp, blue_cp), _front(winning_red, winning_blue)],
    )
    apply_red_tempo(game)
    # Passive stance raised; an already-better stance is never lowered.
    assert red_cp.stances[blue_cp.id] is CombatStance.AGGRESSIVE
    assert winning_red.stances[winning_blue.id] is CombatStance.BREAKTHROUGH


def test_no_stance_change_outside_the_window(arc_cache: Any) -> None:
    red_cp, blue_cp = _cp("red"), _cp("blue")
    red_cp.stances[blue_cp.id] = CombatStance.DEFENSIVE
    game = _game(
        key="offensive_pulse", turn=9, entered=5, fronts=[_front(red_cp, blue_cp)]
    )
    apply_red_tempo(game)
    assert red_cp.stances[blue_cp.id] is CombatStance.DEFENSIVE


# ---- resolve_regen ----------------------------------------------------------------------


def test_regen_applies_once_per_turn_and_clamps(arc_cache: Any) -> None:
    game = _game(key="halt", red_will=50.0)
    apply_red_tempo(game)
    assert game.red.political_will == 51.5
    # Second init the same turn: the guard holds.
    apply_red_tempo(game)
    assert game.red.political_will == 51.5
    # Next turn it applies again.
    game.turn += 1
    apply_red_tempo(game)
    assert game.red.political_will == 53.0
    # And it clamps at 100.
    game.turn += 1
    game.red.political_will = 99.5
    apply_red_tempo(game)
    assert game.red.political_will == 100.0


def test_regen_gated_by_the_will_setting_and_the_phase(arc_cache: Any) -> None:
    game = _game(key="halt", will_on=False, red_will=50.0)
    apply_red_tempo(game)
    assert game.red.political_will == 50.0
    game = _game(key="thunder", red_will=50.0)
    apply_red_tempo(game)
    assert game.red.political_will == 50.0


# ---- the convoy lever end-to-end --------------------------------------------------------


def test_trail_surge_allows_a_second_bigger_convoy(arc_cache: Any) -> None:
    # During a surged phase the baseline concurrent-convoy budget (2) relaxes to 3
    # and the skim budget doubles (still capped by the source-fraction guard).
    from game.fourteenth.vietnam_convoy import ensure_enemy_trail_convoy
    from tests.fourteenth.test_vietnam_convoy import (
        _CP,
        _front as _convoy_front,
        _game as _convoy_game,
    )

    rear = _CP("rear", "RED", 100.0, {"tank": 20})
    near = _CP("near", "RED", 10.0, {})
    rear.convoy_routes[near] = object()
    near.convoy_routes[rear] = object()

    game = _convoy_game(
        on=True,
        control_points=[rear, near],
        fronts=[_convoy_front()],
        # Already at the (unrelaxed) baseline budget of 2 -- the surge is what
        # makes room for one more.
        convoys=[object(), object()],
    )
    # Activate the surged authored phase on the convoy duck.
    game.settings.campaign_phases = True
    game.campaign_name = _ARC_NAME
    game.current_phase_key = "halt"
    game.phase_entered_on_turn = 3

    ensure_enemy_trail_convoy(game)
    (order,) = game.red.transfers.created
    # Budget = round(MAX_CONVOY_UNITS * 2.0) = 20, clamped to the 50% source cap (10)
    # -- this fixture's fixed 20-unit rear stock is the binding constraint either way.
    assert sum(order.units.values()) == 10

    # Without the surge, the 2 already flowing satisfy the (unrelaxed) budget of 2.
    game.current_phase_key = "thunder"
    game.red.transfers.created.clear()
    ensure_enemy_trail_convoy(game)
    assert game.red.transfers.created == []


# ---- red-tempo legibility (announce Hanoi's response) -----------------------------------


def test_announce_fires_once_per_red_tempo_phase(arc_cache: Any) -> None:
    # The halt phase authors trail_surge + resolve_regen -> the player is told once.
    game = _game(key="halt", turn=8, entered=8)
    announce_red_tempo(game)
    assert len(game.messages) == 1
    title, body = game.messages[0]
    assert title == "Hanoi's response"
    assert "surge capacity" in body and "resolve steadies" in body
    # Idempotent: a second call in the same phase does not re-announce.
    announce_red_tempo(game)
    assert len(game.messages) == 1


def test_announce_describes_the_ground_offensive(arc_cache: Any) -> None:
    game = _game(key="offensive_pulse", turn=11, entered=11)
    announce_red_tempo(game)
    assert len(game.messages) == 1
    assert "ground offensive" in game.messages[0][1]


def test_announce_silent_without_a_red_tempo_block(arc_cache: Any) -> None:
    # The "thunder" phase carries no red_tempo -> nothing to announce.
    game = _game(key="thunder", turn=1, entered=1)
    announce_red_tempo(game)
    assert game.messages == []


# ---- the shipped Vietnam arcs -----------------------------------------------------------


@pytest.mark.parametrize(
    "campaign",
    [
        "1968_Yankee_Station.yaml",
        "operation_velvet_thunder.yaml",
    ],
)
def test_vietnam_arcs_author_the_red_tempo(campaign: str) -> None:
    data = yaml.safe_load((_CAMPAIGNS / campaign).read_text(encoding="utf-8"))
    by_key = {phase.key: phase for phase in parse_phases(data.get("phases"))}
    halt = by_key["bombing_halt"]
    assert halt.trail_surge == 2.0
    assert halt.resolve_regen == 1.5
    assert by_key["linebacker"].ground_offensive_turns == 3
    # Rolling Thunder and Linebacker II stay baseline tempo.
    assert by_key["rolling_thunder"].trail_surge == 1.0
    assert by_key["linebacker_ii"].ground_offensive_turns == 0
