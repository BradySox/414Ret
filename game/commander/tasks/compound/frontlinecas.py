from collections.abc import Iterator

from game.commander.tasks.primitive.cas import PlanCas
from game.commander.theaterstate import TheaterState
from game.htn import CompoundTask, Method


class PlanFrontLineCas(CompoundTask[TheaterState]):
    """Plan CAS on every contested front, independent of the ground-stance decision.

    CAS is otherwise only reachable as the *last* alternative inside
    ``CaptureBase`` -> ``DestroyEnemyGroundUnits``, behind the
    Breakthrough/Elimination/Aggressive ground-stance tasks. Those win whenever a
    side has a front-line force advantage (>= 0.8), and a winning Breakthrough
    removes the front from ``active_front_lines`` outright -- so a side that is
    *winning* the ground war set an aggressive stance and never fragged CAS at all.

    This task runs after ``CaptureBases`` (so contested fronts still get CAS in
    their original, higher-priority slot via the capture path, and the more
    urgent losing fronts are served first) and plans one CAS package per
    still-vulnerable front. ``PlanCas`` removes the front from
    ``vulnerable_front_lines`` once planned, so fronts already CAS'd by the capture
    path are skipped and nothing is double-planned; the stance machinery is
    untouched, so an aggressive ground stance and a CAS package now coexist.
    """

    def each_valid_method(self, state: TheaterState) -> Iterator[Method[TheaterState]]:
        for front in state.vulnerable_front_lines:
            yield [PlanCas(front)]
