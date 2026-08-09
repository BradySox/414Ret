"""Save-load compat for the 2026-07-21 ROE / §40 / §55 and will / war-economy removals,
plus the 2026-07-29 §77 escort-jamming tier removal.

The modules ``game.fourteenth.{phases, red_intent, zone_drawings}`` were deleted in the ROE
drop, and ``game.fourteenth.{political_will, commitment_ceiling, static_front, war_economy}``
in the will / §53 / §54 economy drop. A pre-removal save pickled ``game.phase_baseline``
(``campaign_phases`` was default ON, so nearly every in-progress save carries a
``PhaseBaseline``), ``red_intent_*`` state (``RedIntentBaseline`` / ``RedIntentSample`` /
the ``RedPosture`` / ``FrontPosture`` enums), ``theater.zone_drawings`` (``DrawnZone``), and
``game.will_ledger`` (a list of ``WillLedgerEntry``) when those were enabled.

``game.data.escort_jamming`` (``EscortJammerTier`` / ``TierEffect``) was deleted by #734
when §77 escort jamming was restricted to dedicated jammers: the graduated-tier system,
and the ``escort_jammer_tier`` field it set on **every** ``AircraftType``, were removed.
A save written while §77 shipped tiers (#714 .. #734) therefore pickled an
``EscortJammerTier`` onto its aircraft (the flown ``Red Tide 7-27 M1`` save was one), and
its unpickle now hits this deleted module.

Four more modules joined them and were missed at removal time, so **every** save written
before 2026-08-07 that recorded a downed blue pilot refused to load outright:

* ``game.pow_recovery`` (``PendingPowRecovery``) and ``game.fourteenth.downed_pilots``
  (the fork's §21 ``DownedPilot``) went with upstream #929's CSAR adoption (#805). The
  ``DownedPilot`` name survives at ``game/squadrons/downedpilot.py``, but upstream's class
  shares no fields with the fork's, so it is degraded rather than remapped.
* ``game.ato.flightplans.combatsar`` / ``.scar`` went in the same commit. Their ``Builder``
  is pickled onto ``Flight._flight_plan_builder``.
* ``game.theater.unitplacement`` (``PendingUnitPlacement``) went with drop-spawn (§20, #750).

Unpickling any of these instances would raise ``ModuleNotFoundError``. The
``MigrationUnpickler`` degrades them to an inert ``DummyObject`` placeholder so the save
still loads. A placeholder alone only converts a load failure into a crash at first use,
so each one has a matching ``__setstate__`` that drops it (``Coalition`` for the pilot and
POW lists, ``Game`` for the placement queue) or rebuilds it (``Flight`` for the builder) --
those are pinned below too.
"""

from __future__ import annotations

import io
import pickle
from dataclasses import dataclass
from typing import Any
from unittest import mock

from game.ato.flight import Flight
from game.coalition import Coalition
from game.game import Game
from game.persistency import DummyObject, MigrationUnpickler

_REMOVED_MODULES = (
    "game.fourteenth.phases",
    "game.fourteenth.red_intent",
    "game.fourteenth.zone_drawings",
    "game.fourteenth.political_will",
    "game.fourteenth.commitment_ceiling",
    "game.fourteenth.static_front",
    "game.fourteenth.war_economy",
    "game.data.escort_jamming",
    "game.pow_recovery",
    "game.fourteenth.downed_pilots",
    "game.ato.flightplans.combatsar",
    "game.ato.flightplans.scar",
    "game.theater.unitplacement",
)


@dataclass
class _FakeRemovedDataclass:
    """Stands in for PhaseBaseline etc. (module-level so pickle can reference it)."""

    turn: int


def test_find_class_degrades_removed_modules_to_placeholder() -> None:
    unpickler = MigrationUnpickler(io.BytesIO(b""))
    for module in _REMOVED_MODULES:
        # Any class name from a deleted module resolves to the inert placeholder,
        # instead of raising ModuleNotFoundError from super().find_class.
        assert unpickler.find_class(module, "PhaseBaseline") is DummyObject
        assert unpickler.find_class(module, "AnythingAtAll") is DummyObject


def test_escort_jammer_tier_enum_degrades() -> None:
    # The concrete §77 (#734) case: an AircraftType pickled an
    # ``EscortJammerTier`` enum member, whose reconstruction is
    # ``game.data.escort_jamming.EscortJammerTier("full")``. The class must
    # resolve to the inert placeholder, and calling it with the pickled value
    # (the enum-reconstruction path) must not raise.
    unpickler = MigrationUnpickler(io.BytesIO(b""))
    tier = unpickler.find_class("game.data.escort_jamming", "EscortJammerTier")
    assert tier is DummyObject
    assert isinstance(tier("full"), DummyObject)


def test_find_class_leaves_live_modules_alone() -> None:
    from game.fourteenth.red_tempo import RedTempoWindow

    unpickler = MigrationUnpickler(io.BytesIO(b""))
    # A surviving fourteenth module still resolves to its real class.
    resolved = unpickler.find_class("game.fourteenth.red_tempo", "RedTempoWindow")
    assert resolved is RedTempoWindow


def test_placeholder_absorbs_dataclass_and_enum_reconstruction() -> None:
    # Removed *dataclass* path: pickle reconstructs via __new__ + __setstate__.
    obj = DummyObject.__new__(DummyObject)
    obj.__setstate__({"turn": 7})
    assert obj.__dict__ == {"turn": 7}
    # Removed *enum* path: pickle reconstructs an enum member via cls(value), which
    # must not crash (the old default __init__ took no args).
    assert isinstance(DummyObject("surge"), DummyObject)
    assert isinstance(DummyObject(3), DummyObject)


def test_pre_removal_save_object_unpickles_without_crashing() -> None:
    # Simulate a save that pickled a game.fourteenth.phases.PhaseBaseline: pickle a real
    # dataclass at protocol 0 (ASCII GLOBAL opcodes), rewrite the class reference to the
    # deleted module path, and prove MigrationUnpickler loads it to a placeholder that
    # still carries the pickled state (vs. the crash super().find_class would raise).
    raw = pickle.dumps(_FakeRemovedDataclass(turn=9), protocol=0)
    rewritten = raw.replace(
        f"c{_FakeRemovedDataclass.__module__}\n_FakeRemovedDataclass\n".encode(),
        b"cgame.fourteenth.phases\nPhaseBaseline\n",
    )
    assert rewritten != raw, "protocol-0 class reference was not where expected"
    loaded = MigrationUnpickler(io.BytesIO(rewritten)).load()
    assert isinstance(loaded, DummyObject)
    assert loaded.__dict__.get("turn") == 9


def test_coalition_drops_the_removed_csar_and_pow_lists() -> None:
    # The fork's §21 DownedPilot and upstream #929's share a name and nothing else,
    # so a pre-2026-08-07 entry arrives as a placeholder. It must be dropped, not
    # kept: Game._rebuild_downed_pilot_index dereferences .id on every member.
    from game.squadrons.downedpilot import DownedPilot

    survivor = DownedPilot.__new__(DownedPilot)
    stale = DummyObject.__new__(DummyObject)
    stale.__setstate__({"unit_name": "Enfield11", "x": 1.0, "y": 2.0})

    coalition = Coalition.__new__(Coalition)
    coalition.__setstate__(
        {
            "downed_pilots": [stale, survivor],
            "pending_pow_recoveries": [DummyObject.__new__(DummyObject)],
        }
    )

    assert len(coalition.downed_pilots) == 1
    assert coalition.downed_pilots[0] is survivor
    # The held-POW model went with #929; its list must not linger as a dead attribute.
    assert not hasattr(coalition, "pending_pow_recoveries")


def test_game_drops_the_removed_drop_spawn_queue() -> None:
    game = Game.__new__(Game)
    state: dict[str, Any] = {
        "pending_unit_placements": [DummyObject.__new__(DummyObject)],
        # Present so __setstate__ takes the "already allocated" branch instead of
        # walking a theater this bare instance does not have.
        "laser_code_registry": object(),
    }
    with mock.patch.object(Game, "on_load"):
        game.__setstate__(state)

    assert not hasattr(game, "pending_unit_placements")


def test_flight_rebuilds_a_placeholder_flight_plan_builder() -> None:
    # A save with a Combat SAR or SCAR flight pickled that module's Builder. The
    # flight type is already remapped by _LEGACY_FLIGHT_TYPE_VALUES, so the builder
    # is rebuilt from it rather than left as a placeholder that would AttributeError
    # on the first flight_plan access.
    flight = Flight.__new__(Flight)
    placeholder = DummyObject()
    flight._flight_plan_builder = placeholder  # type: ignore[assignment]

    rebuilt = object()
    builder_type = mock.Mock(return_value=rebuilt)
    with mock.patch(
        "game.ato.flightplans.flightplanbuildertypes.FlightPlanBuilderTypes.for_flight",
        return_value=builder_type,
    ) as for_flight:
        flight._ensure_flight_plan_builder()

    for_flight.assert_called_once_with(flight)
    builder_type.assert_called_once_with(flight)
    assert flight._flight_plan_builder is rebuilt


def test_flight_leaves_a_live_flight_plan_builder_alone() -> None:
    flight = Flight.__new__(Flight)
    live = object()
    flight._flight_plan_builder = live  # type: ignore[assignment]

    with mock.patch(
        "game.ato.flightplans.flightplanbuildertypes.FlightPlanBuilderTypes.for_flight"
    ) as for_flight:
        flight._ensure_flight_plan_builder()

    for_flight.assert_not_called()
    assert flight._flight_plan_builder is live
