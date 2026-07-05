"""Armed Recon package composition (414th call): a 4-ship sweep + an auto-added
recon drone + the (threat-gated) SEAD escort.

Two layers are pinned here:
- ``PlanArmedRecon.propose_flights`` proposes a fixed 4-ship ARMED_RECON primary
  plus the common escorts (SEAD/A2A, pruned later if unthreatened).
- ``PackageFulfiller._maybe_plan_tarps_recon`` frags an optional recon flight into
  an ARMED_RECON package (as it already does for Strike/DEAD). On a drone-fielding
  faction the auto-assignable TARPS squadron is the drone, so this is the "1 drone
  in each armed recon package" wiring. It never scrubs the package.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from game.ato.flighttype import FlightType
from game.commander.packagefulfiller import PackageFulfiller
from game.commander.tasks.primitive.armedrecon import PlanArmedRecon


def test_armed_recon_proposes_a_four_ship_sweep_plus_escorts() -> None:
    task = PlanArmedRecon(cast(Any, SimpleNamespace(name="Some CP")))
    task.propose_flights()

    recon = [f for f in task.flights if f.task is FlightType.ARMED_RECON]
    assert len(recon) == 1
    assert recon[0].num_aircraft == 4  # fixed 4-ship, not the 2-4 flight-size roll

    # The common escorts ride along (SEAD escort + A2A), pruned downstream when the
    # route is unthreatened -- on the OIR/Red Tide factions the SEAD escort resolves
    # to the Viper, i.e. "2 SEAD Vipers".
    escort_tasks = {f.task for f in task.flights if f.escort_type is not None}
    assert FlightType.SEAD_ESCORT in escort_tasks
    assert FlightType.ESCORT in escort_tasks


def _fulfiller(auto_add: bool, can_plan_tarps: bool) -> PackageFulfiller:
    ff = PackageFulfiller.__new__(PackageFulfiller)
    ff.auto_add_tarps_recon = auto_add
    ff.air_wing_can_plan = lambda mission_type: (  # type: ignore[method-assign]
        can_plan_tarps and mission_type is FlightType.TARPS
    )
    return ff


def _armed_recon_builder(planned: list[Any]) -> Any:
    primary = SimpleNamespace(flight_type=FlightType.ARMED_RECON)

    def plan_flight(proposed: Any, ignore_range: bool) -> bool:
        planned.append(proposed)
        return True

    return SimpleNamespace(
        package=SimpleNamespace(primary_flight=primary),
        plan_flight=plan_flight,
    )


def test_armed_recon_package_frags_a_recon_drone() -> None:
    planned: list[Any] = []
    ff = _fulfiller(auto_add=True, can_plan_tarps=True)
    builder = _armed_recon_builder(planned)
    # The Armed Recon target is a control point (no warrants_recon gate applies).
    mission = SimpleNamespace(location=SimpleNamespace(name="Mosul"))

    ff._maybe_plan_tarps_recon(
        cast(Any, mission), cast(Any, builder), ignore_range=False
    )

    assert [p.task for p in planned] == [FlightType.TARPS]
    assert planned[0].num_aircraft == 1  # a single recon bird / drone


def test_recon_drone_skipped_when_the_setting_is_off() -> None:
    planned: list[Any] = []
    ff = _fulfiller(auto_add=False, can_plan_tarps=True)
    builder = _armed_recon_builder(planned)
    mission = SimpleNamespace(location=SimpleNamespace(name="Mosul"))

    ff._maybe_plan_tarps_recon(
        cast(Any, mission), cast(Any, builder), ignore_range=False
    )

    assert planned == []  # gated by auto_add_tarps_recon


def test_recon_drone_skipped_when_no_tarps_squadron() -> None:
    planned: list[Any] = []
    ff = _fulfiller(auto_add=True, can_plan_tarps=False)
    builder = _armed_recon_builder(planned)
    mission = SimpleNamespace(location=SimpleNamespace(name="Mosul"))

    ff._maybe_plan_tarps_recon(
        cast(Any, mission), cast(Any, builder), ignore_range=False
    )

    assert planned == []  # no drone/TARPS bird available -> package flies as-is
