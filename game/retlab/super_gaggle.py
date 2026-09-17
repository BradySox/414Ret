"""Vietnam Ops Super Gaggle -> real squadron airframes + tracked losses (§37).

The Khe Sanh "Super Gaggle" runs a formation of transport helos (with a fast-mover
AAA-suppression flight) into a cut-off forward outpost. v1 spawned those helos and
suppressors as **phantom** units at runtime (``coalition.addGroup`` in the ``vietnamops``
plugin) on an unbounded respawn loop -- free BLUE airframes the campaign never accounted
for, whose loss was never a real loss.

This module wires the gaggle into the force model without needing the (blocked) auto-plannable
CTLD cargo run. The approach ("debit a squadron + track losses"):

* **Plan once per turn** (``plan_super_gaggle`` from ``finish_turn``): pick the besieged
  outpost + launch field (as before), pick a **real BLUE helicopter squadron** to fly the
  gaggle and a **real BLUE attack squadron** for the suppressors, and record a
  :class:`SuperGaggleCommitment` (which squadrons, the exact per-airframe unit names the plugin
  will spawn, and the geometry). The gaggle uses those squadrons' own aircraft types, so it is
  an authentic detachment of the real force.
* **Emit the commitment** (``_populate_super_gaggle`` reads it): the plugin spawns exactly the
  committed airframes, by name, **once** (the respawn loop is gone -- airframes are now bounded
  to the commitment).
* **Reconcile at debrief** (``reconcile_super_gaggle``): a committed airframe whose name shows up
  in the debrief's killed units is a **real loss** -- the squadron's ``owned_aircraft`` is
  debited and ``destroyed_aircraft`` incremented, exactly like any other airframe lost that
  mission. Survivors cost nothing (a resupply detachment that returns), so no pre-debit/return
  bookkeeping is needed.

**Losses-only accounting -- no delivery credit (2026-07-07 design call).** There is
deliberately *no* garrison-strength boost for a "delivered" run. The only thing the debrief
carries is which committed airframes died, and an airframe's *absence* from the kill list means
"survived and delivered" OR "never spawned at all" (e.g. the player ended the mission before the
plugin's launch delay elapsed) -- indistinguishable without a runtime "delivered" signal the
plugin does not emit, and emitting one would need exactly the Lua/debrief-schema change this
module set out to avoid. So a clean run is simply free: the gaggle costs the wing only the
airframes it actually loses.

No base-Lua / debrief-schema changes: the plugin's spawned units already fire the DCS death
events ``dcs_retribution.lua`` records, so their names land in the debrief killed lists (as
untracked ground units, since they are not in the ``UnitMap``) and we match by name. Fully
guarded -- no outpost / no launch / no helo squadron with airframes ⇒ no commitment ⇒ the plugin
no-ops.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional
from uuid import UUID

if TYPE_CHECKING:
    from game import Game
    from game.debriefing import Debriefing
    from game.squadrons.squadron import Squadron
    from game.theater import ControlPoint

#: How near a front an outpost must be to count as "cut off" and worth a gaggle. ~150 km.
OUTPOST_FRONT_REACH_M = 150_000.0

#: Airframes the gaggle / suppression flight commit (capped by what the chosen squadron owns).
DESIRED_HELOS = 3
DESIRED_SUPPRESSORS = 2


@dataclass
class SuperGaggleCommitment:
    """A planned Super Gaggle run drawn from real squadrons (persisted on the game).

    Carries everything the emitter needs to spawn the run and everything the debrief needs to
    charge losses back: the flying squadrons (by id) and the exact per-airframe unit names the
    plugin will spawn (so a killed name maps straight back to a squadron airframe).
    """

    outpost_name: str
    outpost_x: float
    outpost_y: float
    launch_x: float
    launch_y: float
    helo_squadron_id: UUID
    helo_type: str
    helo_unit_names: list[str]
    supp_squadron_id: Optional[UUID]
    supp_type: Optional[str]
    supp_unit_names: list[str] = field(default_factory=list)
    #: Set at reconcile if the outpost CP still exists; purely informational.
    outpost_cp_id: Optional[UUID] = None


def plan_super_gaggle(game: "Game") -> None:
    """(Re)plan the turn's Super Gaggle from real squadrons, or clear it.

    Runs once per turn from ``finish_turn``. Sets ``game.super_gaggle_commitment`` to a fresh
    :class:`SuperGaggleCommitment`, or ``None`` when the feature is off or the geography /
    squadrons aren't available. Read-mostly: it only *records* which squadrons will fly and the
    names they'll use; airframes are charged at debrief (losses only), so re-running is safe.
    """
    game.super_gaggle_commitment = None
    if not game.settings.vietnam_super_gaggle:
        return

    from game.theater import ControlPointType, Player

    # Besieged-outpost (a forward FOB/FARP) and launch (a rear helo-capable field) CP types.
    outpost_types = frozenset({ControlPointType.FOB, ControlPointType.FARP})
    launch_types = frozenset({ControlPointType.AIRBASE, ControlPointType.FARP})

    fronts = list(game.theater.conflicts())
    if not fronts:
        return

    def distance_to_front(cp: "ControlPoint") -> float:
        return min(front.position.distance_to_point(cp.position) for front in fronts)

    outposts = [
        cp
        for cp in game.theater.controlpoints
        if cp.captured == Player.BLUE
        and cp.cptype in outpost_types
        and distance_to_front(cp) <= OUTPOST_FRONT_REACH_M
    ]
    if not outposts:
        return
    outpost = min(outposts, key=distance_to_front)

    launch_fields = [
        cp
        for cp in game.theater.controlpoints
        if cp.captured == Player.BLUE
        and cp is not outpost
        and cp.cptype in launch_types
    ]
    if not launch_fields:
        return
    launch = min(
        launch_fields, key=lambda cp: cp.position.distance_to_point(outpost.position)
    )

    helo_squadron = _pick_squadron(game, launch, helicopter=True)
    if helo_squadron is None:
        return  # no real helo airframes to fly the gaggle -> no free spawn.
    helo_count = min(DESIRED_HELOS, helo_squadron.owned_aircraft)
    if helo_count < 1:
        return

    supp_squadron = _pick_squadron(game, launch, helicopter=False)
    supp_count = (
        min(DESIRED_SUPPRESSORS, supp_squadron.owned_aircraft)
        if supp_squadron is not None
        else 0
    )

    tag = f"SuperGaggle-T{game.turn}"
    game.super_gaggle_commitment = SuperGaggleCommitment(
        outpost_name=outpost.full_name,
        outpost_x=outpost.position.x,
        outpost_y=outpost.position.y,
        launch_x=launch.position.x,
        launch_y=launch.position.y,
        helo_squadron_id=helo_squadron.id,
        helo_type=helo_squadron.aircraft.dcs_unit_type.id,
        helo_unit_names=[f"{tag}-Helo-{i + 1}" for i in range(helo_count)],
        supp_squadron_id=supp_squadron.id if (supp_squadron and supp_count) else None,
        supp_type=(
            supp_squadron.aircraft.dcs_unit_type.id
            if supp_squadron and supp_count
            else None
        ),
        supp_unit_names=[f"{tag}-Sandy-{i + 1}" for i in range(supp_count)],
        outpost_cp_id=outpost.id,
    )


def _pick_squadron(
    game: "Game", launch: "ControlPoint", *, helicopter: bool
) -> Optional["Squadron"]:
    """Pick the BLUE squadron nearest the launch field that can fly this leg with airframes.

    ``helicopter=True`` selects the transport-helo squadron for the gaggle; ``False`` selects a
    fixed-wing attack squadron (CAS-capable) for the suppressors. Returns None if none has a
    spare airframe (so the caller emits no free units).
    """
    from game.ato import FlightType

    best: Optional["Squadron"] = None
    best_distance = float("inf")
    for squadron in game.blue.air_wing.iter_squadrons():
        if squadron.owned_aircraft < 1:
            continue
        aircraft = squadron.aircraft
        if helicopter:
            if not aircraft.helicopter:
                continue
        else:
            if aircraft.helicopter:
                continue
            if not aircraft.task_priorities.get(FlightType.CAS):
                continue
        distance = squadron.location.position.distance_to_point(launch.position)
        if distance < best_distance:
            best_distance = distance
            best = squadron
    return best


def reconcile_super_gaggle(game: "Game", debriefing: "Debriefing") -> None:
    """Charge Super Gaggle airframe losses back to their squadrons.

    A committed airframe whose unit name appears in the debrief's killed units (aircraft *or*
    ground -- runtime-spawned units aren't in the ``UnitMap`` so they land in the ground list)
    is a real loss: debit ``owned_aircraft`` and bump ``destroyed_aircraft``, exactly like any
    other airframe lost that mission. Clears the commitment so it is charged only once.

    Losses-only (2026-07-07 design call): there is no delivery strength credit. An airframe's
    absence from the kill list can't be distinguished from "never spawned" without a runtime
    "delivered" signal the plugin does not emit, so a clean run simply costs nothing rather than
    handing out a garrison boost the gaggle may never have earned.
    """
    commitment = getattr(game, "super_gaggle_commitment", None)
    if commitment is None:
        return

    killed = set(debriefing.state_data.killed_aircraft) | set(
        debriefing.state_data.killed_ground_units
    )

    _charge_losses(
        game, commitment.helo_squadron_id, commitment.helo_unit_names, killed
    )
    _charge_losses(
        game, commitment.supp_squadron_id, commitment.supp_unit_names, killed
    )

    game.super_gaggle_commitment = None


def _charge_losses(
    game: "Game",
    squadron_id: Optional[UUID],
    unit_names: list[str],
    killed: set[str],
) -> int:
    """Debit each committed unit name found in ``killed`` from its squadron. Returns the count."""
    if squadron_id is None or not unit_names:
        return 0
    lost = sum(1 for name in unit_names if name in killed)
    if lost <= 0:
        return 0
    squadron = _squadron_by_id(game, squadron_id)
    if squadron is None:
        return lost
    squadron.owned_aircraft = max(0, squadron.owned_aircraft - lost)
    squadron.destroyed_aircraft += lost
    game.message(
        "Super Gaggle losses",
        f"{lost} {squadron.aircraft} lost from {squadron} on the resupply run.",
    )
    return lost


def _squadron_by_id(game: "Game", squadron_id: UUID) -> Optional["Squadron"]:
    for squadron in game.blue.air_wing.iter_squadrons():
        if squadron.id == squadron_id:
            return squadron
    return None
