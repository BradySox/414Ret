"""§37 Super Gaggle -> real squadron airframes + tracked losses (no free helos).

Locks the accounting rework that replaced the phantom, unbounded-respawn helo spawn: the
gaggle draws its helos + suppressors from real BLUE squadrons (``plan_super_gaggle``) and a
shot-down committed airframe is charged back to its squadron at debrief
(``reconcile_super_gaggle``). Survivors cost nothing (a returning detachment); a clean run
credits the besieged outpost.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from game.ato import FlightType
from game.fourteenth.super_gaggle import (
    DELIVERY_STRENGTH_BONUS,
    SuperGaggleCommitment,
    plan_super_gaggle,
    reconcile_super_gaggle,
)
from game.theater import ControlPointType, Player

# --- fakes --------------------------------------------------------------------------


def _pos(front_dist: float, coord: float = 0.0) -> Any:
    return SimpleNamespace(
        front_dist=front_dist,
        coord=coord,
        distance_to_point=lambda other: abs(coord - other.coord),
    )


def _front() -> Any:
    return SimpleNamespace(
        position=SimpleNamespace(distance_to_point=lambda pos: pos.front_dist)
    )


class _Base:
    def __init__(self) -> None:
        self.strength_delta = 0.0

    def affect_strength(self, delta: float) -> None:
        self.strength_delta += delta


class _CP:
    def __init__(
        self, name: str, captured: Any, cptype: Any, front_dist: float, coord: float
    ) -> None:
        self.name = name
        self.captured = captured
        self.cptype = cptype
        self.position = _pos(front_dist, coord)
        self.id = uuid4()
        self.base = _Base()

    @property
    def full_name(self) -> str:
        return self.name


class _Squadron:
    def __init__(
        self, *, helicopter: bool, owned: int, coord: float, cas: bool = True
    ) -> None:
        self.id = uuid4()
        self.owned_aircraft = owned
        self.destroyed_aircraft = 0
        task_priorities = {FlightType.CAS: 50} if cas else {}
        self.aircraft = SimpleNamespace(
            helicopter=helicopter,
            dcs_unit_type=SimpleNamespace(id="UH-1H" if helicopter else "A-4E-C"),
            task_priorities=task_priorities,
        )
        self.location = SimpleNamespace(position=_pos(0.0, coord))

    def __str__(self) -> str:
        return "TestSqn"


def _game(
    *,
    on: bool,
    control_points: list[Any],
    fronts: list[Any],
    squadrons: list[Any],
    turn: int = 3,
) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(vietnam_super_gaggle=on),
        turn=turn,
        theater=SimpleNamespace(
            controlpoints=control_points, conflicts=lambda: list(fronts)
        ),
        blue=SimpleNamespace(
            air_wing=SimpleNamespace(iter_squadrons=lambda: list(squadrons))
        ),
        super_gaggle_commitment=None,
        messages=[],
        message=lambda title, text="": None,
    )


def _debrief(killed_aircraft: list[str], killed_ground: list[str] | None = None) -> Any:
    return SimpleNamespace(
        state_data=SimpleNamespace(
            killed_aircraft=killed_aircraft, killed_ground_units=killed_ground or []
        )
    )


# --- plan_super_gaggle (runs in CI; imports game.theater/ato) ------------------------


def test_plan_commits_real_squadron_airframes() -> None:
    outpost = _CP("Hill 861", Player.BLUE, ControlPointType.FOB, 10_000, 0.0)
    launch = _CP("Khe Sanh", Player.BLUE, ControlPointType.AIRBASE, 60_000, 30_000)
    helo_sqn = _Squadron(helicopter=True, owned=5, coord=30_000, cas=False)
    supp_sqn = _Squadron(helicopter=False, owned=4, coord=30_000, cas=True)
    game = _game(
        on=True,
        control_points=[outpost, launch],
        fronts=[_front()],
        squadrons=[helo_sqn, supp_sqn],
    )
    plan_super_gaggle(game)
    c = game.super_gaggle_commitment
    assert c is not None
    assert c.outpost_name == "Hill 861"
    assert c.helo_squadron_id == helo_sqn.id
    assert c.helo_type == "UH-1H"
    assert len(c.helo_unit_names) == 3  # DESIRED_HELOS, capped by owned
    assert c.supp_squadron_id == supp_sqn.id
    assert len(c.supp_unit_names) == 2  # DESIRED_SUPPRESSORS
    # No airframes are debited at planning time (losses are charged at debrief).
    assert helo_sqn.owned_aircraft == 5
    assert supp_sqn.owned_aircraft == 4


def test_plan_clears_when_setting_off() -> None:
    outpost = _CP("Hill 861", Player.BLUE, ControlPointType.FOB, 10_000, 0.0)
    launch = _CP("Khe Sanh", Player.BLUE, ControlPointType.AIRBASE, 60_000, 30_000)
    game = _game(
        on=False,
        control_points=[outpost, launch],
        fronts=[_front()],
        squadrons=[_Squadron(helicopter=True, owned=5, coord=30_000)],
    )
    plan_super_gaggle(game)
    assert game.super_gaggle_commitment is None


def test_plan_no_commitment_without_a_helo_squadron() -> None:
    outpost = _CP("Hill 861", Player.BLUE, ControlPointType.FOB, 10_000, 0.0)
    launch = _CP("Khe Sanh", Player.BLUE, ControlPointType.AIRBASE, 60_000, 30_000)
    # Only a fixed-wing squadron -> nothing can fly the gaggle -> no free spawn.
    game = _game(
        on=True,
        control_points=[outpost, launch],
        fronts=[_front()],
        squadrons=[_Squadron(helicopter=False, owned=8, coord=30_000)],
    )
    plan_super_gaggle(game)
    assert game.super_gaggle_commitment is None


def test_plan_no_commitment_without_a_forward_outpost() -> None:
    # A friendly airbase but no FOB/FARP outpost near the front -> nothing besieged.
    launch = _CP("Da Nang", Player.BLUE, ControlPointType.AIRBASE, 30_000, 0.0)
    game = _game(
        on=True,
        control_points=[launch],
        fronts=[_front()],
        squadrons=[_Squadron(helicopter=True, owned=5, coord=0.0)],
    )
    plan_super_gaggle(game)
    assert game.super_gaggle_commitment is None


def test_plan_commits_helos_only_when_no_attack_squadron() -> None:
    outpost = _CP("Hill 861", Player.BLUE, ControlPointType.FOB, 10_000, 0.0)
    launch = _CP("Khe Sanh", Player.BLUE, ControlPointType.AIRBASE, 60_000, 30_000)
    game = _game(
        on=True,
        control_points=[outpost, launch],
        fronts=[_front()],
        squadrons=[_Squadron(helicopter=True, owned=5, coord=30_000, cas=False)],
    )
    plan_super_gaggle(game)
    c = game.super_gaggle_commitment
    assert c is not None
    assert c.supp_squadron_id is None
    assert c.supp_unit_names == []


def test_plan_helo_count_capped_by_owned_airframes() -> None:
    outpost = _CP("Hill 861", Player.BLUE, ControlPointType.FOB, 10_000, 0.0)
    launch = _CP("Khe Sanh", Player.BLUE, ControlPointType.AIRBASE, 60_000, 30_000)
    game = _game(
        on=True,
        control_points=[outpost, launch],
        fronts=[_front()],
        squadrons=[_Squadron(helicopter=True, owned=1, coord=30_000, cas=False)],
    )
    plan_super_gaggle(game)
    assert len(game.super_gaggle_commitment.helo_unit_names) == 1


# --- reconcile_super_gaggle ---------------------------------------------------------


def _committed_game(helo_sqn: Any, supp_sqn: Any, outpost: Any) -> Any:
    game = SimpleNamespace(
        blue=SimpleNamespace(
            air_wing=SimpleNamespace(iter_squadrons=lambda: [helo_sqn, supp_sqn])
        ),
        theater=SimpleNamespace(controlpoints=[outpost]),
        message=lambda title, text="": None,
    )
    game.super_gaggle_commitment = SuperGaggleCommitment(
        outpost_name="Hill 861",
        outpost_x=0.0,
        outpost_y=0.0,
        launch_x=0.0,
        launch_y=0.0,
        helo_squadron_id=helo_sqn.id,
        helo_type="UH-1H",
        helo_unit_names=["G-Helo-1", "G-Helo-2", "G-Helo-3"],
        supp_squadron_id=supp_sqn.id,
        supp_type="A-4E-C",
        supp_unit_names=["G-Sandy-1", "G-Sandy-2"],
        outpost_cp_id=outpost.id,
    )
    return game


def test_reconcile_charges_only_the_killed_airframes() -> None:
    helo_sqn = _Squadron(helicopter=True, owned=5, coord=0.0)
    supp_sqn = _Squadron(helicopter=False, owned=4, coord=0.0)
    outpost = _CP("Hill 861", Player.BLUE, ControlPointType.FOB, 0.0, 0.0)
    game = _committed_game(helo_sqn, supp_sqn, outpost)
    # Two helos + one suppressor died (names land in killed_ground_units for spawned units).
    debrief = _debrief([], ["G-Helo-1", "G-Helo-3", "G-Sandy-2"])
    reconcile_super_gaggle(game, debrief)
    assert helo_sqn.owned_aircraft == 3  # 5 - 2 lost
    assert helo_sqn.destroyed_aircraft == 2
    assert supp_sqn.owned_aircraft == 3  # 4 - 1 lost
    assert supp_sqn.destroyed_aircraft == 1
    # A helo survived -> delivery credited to the outpost.
    assert outpost.base.strength_delta == DELIVERY_STRENGTH_BONUS
    # Reconciled once: the commitment is cleared.
    assert game.super_gaggle_commitment is None


def test_reconcile_no_losses_full_survival_credits_delivery() -> None:
    helo_sqn = _Squadron(helicopter=True, owned=5, coord=0.0)
    supp_sqn = _Squadron(helicopter=False, owned=4, coord=0.0)
    outpost = _CP("Hill 861", Player.BLUE, ControlPointType.FOB, 0.0, 0.0)
    game = _committed_game(helo_sqn, supp_sqn, outpost)
    reconcile_super_gaggle(game, _debrief([], []))
    assert helo_sqn.owned_aircraft == 5  # nothing lost -> nothing debited
    assert helo_sqn.destroyed_aircraft == 0
    assert outpost.base.strength_delta == DELIVERY_STRENGTH_BONUS


def test_reconcile_all_helos_lost_no_delivery_credit() -> None:
    helo_sqn = _Squadron(helicopter=True, owned=5, coord=0.0)
    supp_sqn = _Squadron(helicopter=False, owned=4, coord=0.0)
    outpost = _CP("Hill 861", Player.BLUE, ControlPointType.FOB, 0.0, 0.0)
    game = _committed_game(helo_sqn, supp_sqn, outpost)
    reconcile_super_gaggle(game, _debrief([], ["G-Helo-1", "G-Helo-2", "G-Helo-3"]))
    assert helo_sqn.owned_aircraft == 2
    assert helo_sqn.destroyed_aircraft == 3
    # No helo survived -> the run failed -> no delivery credit.
    assert outpost.base.strength_delta == 0.0


def test_reconcile_no_commitment_is_a_noop() -> None:
    game = SimpleNamespace(super_gaggle_commitment=None)
    reconcile_super_gaggle(game, _debrief(["anything"]))  # must not raise


def test_reconcile_never_debits_below_zero() -> None:
    helo_sqn = _Squadron(helicopter=True, owned=1, coord=0.0)
    supp_sqn = _Squadron(helicopter=False, owned=0, coord=0.0)
    outpost = _CP("Hill 861", Player.BLUE, ControlPointType.FOB, 0.0, 0.0)
    game = _committed_game(helo_sqn, supp_sqn, outpost)
    # More helo names killed than the squadron owns -> floored at 0, not negative.
    reconcile_super_gaggle(game, _debrief([], ["G-Helo-1", "G-Helo-2", "G-Helo-3"]))
    assert helo_sqn.owned_aircraft == 0
