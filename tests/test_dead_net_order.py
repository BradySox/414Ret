"""DEAD in net order: DegradeIads offers detectors before opportunistic SAMs.

Test 32 (2026-09-15): a Skynet-held SA-11 stays dark until its target is inside
the kill zone, and DCS AI fires a HARM only at an emitter, so an AI DEAD flight at
a netted site never gets a shot off. Once the EWR covering the site is dead the
site runs autonomous and live. Doctrine-mining note row 8, minimal shape.

Fakes are duck-typed per the local convention; narrow ignores where the real
signatures expect engine types.
"""

from __future__ import annotations

from types import SimpleNamespace

from game.commander.tasks.compound.degradeiads import DegradeIads
from game.data.groups import GroupTask
from game.theater import Airfield, Player


def _cp() -> Airfield:
    return object.__new__(Airfield)


def _sam(owner: Airfield, task: GroupTask = GroupTask.MERAD) -> SimpleNamespace:
    return SimpleNamespace(
        control_point=owner,
        distance_to=lambda _cp: 10_000.0,
        task=task,
        max_threat_range=lambda: SimpleNamespace(meters=40_000.0),
    )


def _state(**lists: object) -> SimpleNamespace:
    # Unpredictability 0 keeps shuffled_by_priority a no-op, so order is exact.
    settings = SimpleNamespace(
        region_priorities=False,
        ownfor_planner_unpredictability=0,
        opfor_planner_unpredictability=0,
        c2_decapitation_effects=False,
    )
    context = SimpleNamespace(
        settings=settings,
        coalition=SimpleNamespace(player=Player.BLUE),
        theater=SimpleNamespace(),
    )
    return SimpleNamespace(context=context, priority_cp=None, **lists)


def _targets_of(methods: object) -> list[object]:
    return [m[0].target for m in methods]  # type: ignore[attr-defined]


def test_detectors_are_offered_before_opportunistic_sams() -> None:
    cp = _cp()
    ewr = _sam(cp, GroupTask.EARLY_WARNING_RADAR)
    merad = _sam(cp)
    state = _state(
        enemy_air_defenses=[merad],
        threatening_air_defenses=[],
        detecting_air_defenses=[ewr],
    )
    assert _targets_of(DegradeIads().each_valid_method(state)) == [ewr, merad]  # type: ignore[arg-type]


def test_a_threatening_sam_still_comes_first() -> None:
    """The reactive tier is a threat response and is not reordered."""
    cp = _cp()
    ewr = _sam(cp, GroupTask.EARLY_WARNING_RADAR)
    shooter, merad = _sam(cp), _sam(cp)
    state = _state(
        enemy_air_defenses=[merad],
        threatening_air_defenses=[shooter],
        detecting_air_defenses=[ewr],
    )
    assert _targets_of(DegradeIads().each_valid_method(state)) == [  # type: ignore[arg-type]
        shooter,
        ewr,
        merad,
    ]
