"""PlanFrontLineCas decouples CAS from the capture/ground-stance decision.

The compound task should offer one CAS package per still-vulnerable front,
regardless of stance -- that's what lets a side winning the ground war still
frag CAS (CaptureBase only reaches CAS as a last resort behind the stance tasks,
and a winning Breakthrough removes the front before CAS is ever considered).
"""

from __future__ import annotations

from types import SimpleNamespace

from game.commander.tasks.compound.frontlinecas import PlanFrontLineCas
from game.commander.tasks.primitive.cas import PlanCas


def _state(*fronts: object) -> SimpleNamespace:
    return SimpleNamespace(vulnerable_front_lines=list(fronts))


def test_yields_one_cas_method_per_vulnerable_front() -> None:
    a, b, c = object(), object(), object()
    methods = list(PlanFrontLineCas().each_valid_method(_state(a, b, c)))  # type: ignore[arg-type]

    assert len(methods) == 3
    for method, front in zip(methods, (a, b, c)):
        assert len(method) == 1
        (task,) = method
        assert isinstance(task, PlanCas)
        assert task.target is front


def test_no_vulnerable_fronts_yields_nothing() -> None:
    # No contested fronts -> no CAS offered (and the planner moves on).
    assert list(PlanFrontLineCas().each_valid_method(_state())) == []  # type: ignore[arg-type]
