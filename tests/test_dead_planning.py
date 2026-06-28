from types import SimpleNamespace

from shapely.geometry import Point as ShapelyPoint

from game.ato.flighttype import FlightType
from game.commander.tasks.primitive.dead import PlanDead
from game.commander.theaterstate import TheaterState


def _flight(*xy: tuple[float, float]) -> SimpleNamespace:
    """A fake flight whose flight plan visits the given (x, y) waypoints."""
    waypoints = [SimpleNamespace(position=SimpleNamespace(x=x, y=y)) for x, y in xy]
    return SimpleNamespace(flight_plan=SimpleNamespace(waypoints=waypoints))


def _rings(
    *entries: tuple[object, float, float, float]
) -> list[tuple[object, ShapelyPoint, float]]:
    """(tgo, cx, cy, radius) -> the initial_radar_sam_rings shape."""
    return [(tgo, ShapelyPoint(cx, cy), radius) for tgo, cx, cy, radius in entries]


def test_dead_can_reach_true_when_route_avoids_other_sams() -> None:
    target = object()
    other = object()
    state = SimpleNamespace(
        initial_radar_sam_rings=_rings((target, 1000, 0, 50), (other, 0, 0, 100))
    )
    # Route runs well north of the `other` ring (200 m away from a 100 m ring).
    flights = [_flight((0, 200), (1000, 200))]
    assert TheaterState.dead_can_reach(state, target, flights) is True  # type: ignore[arg-type]


def test_dead_can_reach_false_when_route_crosses_another_sam() -> None:
    target = object()
    other = object()
    state = SimpleNamespace(
        initial_radar_sam_rings=_rings((target, 1000, 0, 50), (other, 0, 0, 100))
    )
    # Route drives straight through the `other` ring at (0, 0).
    flights = [_flight((-200, 0), (1000, 0))]
    assert TheaterState.dead_can_reach(state, target, flights) is False  # type: ignore[arg-type]


def test_dead_can_reach_excludes_targets_own_ring() -> None:
    target = object()
    state = SimpleNamespace(initial_radar_sam_rings=_rings((target, 1000, 0, 300)))
    # Route ends deep inside the target's own ring -- that must not count.
    flights = [_flight((900, 0), (1000, 0))]
    assert TheaterState.dead_can_reach(state, target, flights) is True  # type: ignore[arg-type]


def test_dead_apply_effects_clears_reachable_sam() -> None:
    target = object()
    eliminated: list[object] = []
    state = SimpleNamespace(
        unreachable_air_defenses=set(),
        dead_can_reach=lambda tgt, flights: True,
        eliminate_air_defense=eliminated.append,
    )
    task = PlanDead(target)  # type: ignore[arg-type]
    task.package = SimpleNamespace(flights=[])  # type: ignore[assignment]
    task.apply_effects(state)  # type: ignore[arg-type]

    assert eliminated == [target]
    assert target not in state.unreachable_air_defenses


def test_dead_apply_effects_defers_unreachable_sam() -> None:
    target = object()
    eliminated: list[object] = []
    state = SimpleNamespace(
        unreachable_air_defenses=set(),
        dead_can_reach=lambda tgt, flights: False,
        eliminate_air_defense=eliminated.append,
    )
    task = PlanDead(target)  # type: ignore[arg-type]
    task.package = SimpleNamespace(flights=[])  # type: ignore[assignment]
    task.apply_effects(state)  # type: ignore[arg-type]

    # The SAM is NOT optimistically cleared; it's recorded as unreachable so
    # dependent strikes stay deferred and we don't re-task the DEAD.
    assert eliminated == []
    assert target in state.unreachable_air_defenses


def _target(has_live_radar_sam: bool, tankers: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        alive_unit_count=lambda: 5,
        has_live_radar_sam=has_live_radar_sam,
        control_point=SimpleNamespace(
            coalition=SimpleNamespace(
                game=SimpleNamespace(
                    settings=SimpleNamespace(autoplan_tankers_for_dead=tankers)
                )
            )
        ),
    )


def test_dead_with_live_radar_sam_uses_dedicated_sead_not_sweep() -> None:
    task = PlanDead(_target(has_live_radar_sam=True))  # type: ignore[arg-type]
    task.propose_flights()

    assert [flight.task for flight in task.flights] == [
        FlightType.DEAD,
        FlightType.ESCORT,
        FlightType.SEAD,
    ]


def test_dead_without_live_radar_sam_uses_sead_escort_not_sweep() -> None:
    task = PlanDead(_target(has_live_radar_sam=False))  # type: ignore[arg-type]
    task.propose_flights()

    assert [flight.task for flight in task.flights] == [
        FlightType.DEAD,
        FlightType.ESCORT,
        FlightType.SEAD_ESCORT,
    ]


def test_vietnam_doctrine_scrubs_the_whole_dead_package() -> None:
    # The Vietnam tasking whitelist drops DEAD (a package primary), so fulfill_mission
    # must scrub the mission *before* it builds a fulfiller -- no SEAD planning, no
    # purchase requests, no A-1 grabbed for a SEAD escort. DEAD is proposed first, so
    # the primary-disallowed branch returns False before the fulfiller line is reached
    # (which is why this needs no theater/tracer/db fakes).
    from game.data.doctrine import VIETNAM_DOCTRINE

    task = PlanDead(_target(has_live_radar_sam=True))  # type: ignore[arg-type]
    state = SimpleNamespace(
        context=SimpleNamespace(
            coalition=SimpleNamespace(
                player=SimpleNamespace(is_blue=True),
                doctrine=VIETNAM_DOCTRINE,
            )
        )
    )
    assert task.fulfill_mission(state) is False  # type: ignore[arg-type]
