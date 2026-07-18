"""Persistent downed pilots -- the §21 Combat SAR extension (2026-07-10 squadron call).

A blue pilot who ejects and is neither rescued nor captured by the end of the
mission no longer dies at debrief: they go **MIA** (``PilotStatus.MIA`` -- alive,
off the schedule) and persist on ``game.downed_pilots`` at their last known
position. The loop:

* **In-mission** the combatsar plugin mirrors every unresolved survivor into
  ``combat_sar_survivors`` (state.json); ``record_downed_pilots`` turns those into
  ledger entries at commit (and retires entries rescued/captured this mission).
* **Next mission** the ledger is handed back via ``persistentSurvivors`` on the
  CombatSAR node -- the evader re-spawns with fresh red smoke, a fresh enemy
  snatch race, and the normal rescue paths (player package or auto-dispatch).
* **At the turn boundary** (``resolve_downed_pilots`` from ``finish_turn``) an
  evader on friendly ground walks home (recovered -> Active), and one behind the
  lines rolls a **depth-weighted capture**: enemy search parties almost certainly
  find a pilot deep behind the FLOT during the gap, while one near the front
  keeps evading. A capture is the normal POW consequence (``PendingPowRecovery``
  -> the held-POW model, the will drain, the §51 comms compromise).

There is deliberately **no death clock** (squadron call: "no clock") -- the depth
roll is the clock. The don't-fly-deep incentive is the point: a deep ejection is
unprotectable and becomes a POW; a front-line ejection is a live rescue mission
next turn.

Gated by ``combat_sar_persistent_pilots`` (default ON) -- the gate covers only the
*creation* of new MIA entries. An existing entry is always emitted, resolved, and
rolled, so a mid-campaign toggle never strands an evader in limbo.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from game.utils import meters

if TYPE_CHECKING:
    from game.debriefing import Debriefing
    from game.game import Game
    from game.squadrons.pilot import Pilot
    from game.theater.controlpoint import ControlPoint

#: Turn-boundary capture odds for an evader NEAR the front (within
#: ``NEAR_DEPTH_NM`` of the lines): most likely they keep evading, so a
#: front-line ejection stays a live rescue mission next turn.
BASE_CAPTURE_CHANCE = 0.10
#: ...and for an evader DEEP behind the lines (``DEEP_DEPTH_NM`` or more): enemy
#: search parties almost certainly find them during the turn gap. This is the
#: "don't fly deep" incentive stated as a number; odds scale linearly between
#: the two depths.
MAX_CAPTURE_CHANCE = 0.90
NEAR_DEPTH_NM = 5.0
DEEP_DEPTH_NM = 40.0

#: Module RNG so tests can script the dice (the §50 convention).
_RNG = random.Random()


@dataclass
class DownedPilot:
    """One blue aviator down behind the lines and still evading.

    ``unit_name`` is the ejected aircraft's original DCS unit name -- the same
    key the combatsar plugin uses for rescues/captures, so a later mission's
    outcome maps straight back to this entry. ``(x, y)`` is the DCS vec2 of the
    survivor's position (x = north, y = east). ``pilot``/``aircraft`` are kept
    for the roster flip and the SITREP line (Optional/defaulted for
    save-migration safety)."""

    unit_name: str
    x: float
    y: float
    pilot: Optional[Pilot] = None
    aircraft: str = ""
    turn_downed: int = 0
    #: Turn the pilot-recovery surge (csar_surge.py) fragged this evader's op; 0 =
    #: never surged. The surge fires once per pilot -- read with getattr (pre-field
    #: saves lack it) and never reset.
    surge_turn: int = 0


def persistence_enabled(game: Game) -> bool:
    return bool(getattr(game.settings, "combat_sar_persistent_pilots", False))


def _ledger(game: Game) -> list[DownedPilot]:
    ledger = getattr(game, "downed_pilots", None)
    if ledger is None:
        ledger = []
        game.downed_pilots = ledger
    return ledger


def pilot_from_ledger(game: Game, unit_name: str) -> Optional[Pilot]:
    """The MIA aviator recorded for this airframe, if any.

    ``record_pow_captures`` resolves a captured pilot through the mission's unit
    map, but a persistent evader's airframe died on an EARLIER turn -- this
    ledger is the only thing that still knows whose pilot it was."""
    for dp in _ledger(game):
        if dp.unit_name == unit_name:
            return dp.pilot
    return None


def _pilot_label(dp: DownedPilot) -> str:
    if dp.pilot is not None:
        return dp.pilot.name
    if dp.aircraft:
        return f"The {dp.aircraft} pilot"
    return "A downed pilot"


def record_downed_pilots(game: Game, debriefing: Debriefing) -> None:
    """Reconcile the evader ledger against the mission that just ran.

    Runs at mission-results commit, after ``commit_air_losses`` (which spared
    the MIA kills) and ``record_pow_captures`` (which resolved captured evaders'
    pilots from this ledger). Retires entries rescued or captured this mission,
    then records each still-unresolved survivor the plugin reported as a new MIA
    entry (gated by ``combat_sar_persistent_pilots``)."""
    ledger = _ledger(game)
    state = debriefing.state_data
    rescued = set(state.combat_sar_rescues)
    captured = {
        unit for unit, _x, _y, _color in getattr(state, "combat_sar_captures", []) or []
    }

    kept: list[DownedPilot] = []
    for dp in ledger:
        if dp.unit_name in rescued:
            if dp.pilot is not None:
                dp.pilot.repatriate()
            logging.info(f"Combat SAR recovered the evading pilot of {dp.unit_name}.")
            game.message(
                "Evader recovered",
                f"{_pilot_label(dp)} was picked up after evading since turn "
                f"{dp.turn_downed} and returns to the roster.",
            )
            continue
        if dp.unit_name in captured:
            # The POW hold itself was recorded by record_pow_captures (which
            # resolved the aviator from this ledger); only retire the entry here.
            continue
        kept.append(dp)
    ledger[:] = kept

    if not persistence_enabled(game):
        return

    known = {dp.unit_name for dp in ledger}
    for unit_name, x, y in getattr(state, "combat_sar_survivors", []) or []:
        if unit_name in known or unit_name in rescued or unit_name in captured:
            # A prior-turn evader still unresolved keeps its existing entry (the
            # survivor never moves); a resolved one was handled above.
            continue
        flying = debriefing.unit_map.flight(unit_name)
        if flying is None:
            # Not an airframe this campaign tracks -- nothing to persist.
            continue
        pilot = flying.pilot
        if pilot is not None:
            pilot.go_missing()
        dp = DownedPilot(
            unit_name=unit_name,
            x=x,
            y=y,
            pilot=pilot,
            aircraft=str(flying.flight.unit_type),
            turn_downed=game.turn,
        )
        ledger.append(dp)
        logging.info(f"Pilot of {unit_name} is MIA, evading at ({x:.0f}, {y:.0f}).")
        game.message(
            "Pilot down -- MIA",
            f"{_pilot_label(dp)} is down behind the lines and still evading. "
            "A rescue can be flown next turn; enemy search parties are looking.",
        )


def capture_chance(depth_nm: float) -> float:
    """Turn-boundary capture odds for an evader ``depth_nm`` behind the lines."""
    if depth_nm <= NEAR_DEPTH_NM:
        return BASE_CAPTURE_CHANCE
    if depth_nm >= DEEP_DEPTH_NM:
        return MAX_CAPTURE_CHANCE
    fraction = (depth_nm - NEAR_DEPTH_NM) / (DEEP_DEPTH_NM - NEAR_DEPTH_NM)
    return BASE_CAPTURE_CHANCE + fraction * (MAX_CAPTURE_CHANCE - BASE_CAPTURE_CHANCE)


def _nearest_control_point(game: Game, position: Any) -> Optional[ControlPoint]:
    from game.theater.controlpoint import OffMapSpawn

    best: Optional[ControlPoint] = None
    best_distance: Optional[float] = None
    for cp in game.theater.controlpoints:
        if isinstance(cp, OffMapSpawn):
            continue
        distance = position.distance_to_point(cp.position)
        if best_distance is None or distance < best_distance:
            best, best_distance = cp, distance
    return best


def _depth_nm(game: Game, position: Any) -> float:
    """How deep behind the lines the evader sits, in NM.

    Distance to the nearest active front line; on a front-less laydown (COIN),
    distance to the nearest friendly-held control point instead. No reference
    at all (theoretical) reads as deep."""
    from game.theater.controlpoint import OffMapSpawn

    references = [front.position for front in game.theater.conflicts()]
    if not references:
        references = [
            cp.position
            for cp in game.theater.controlpoints
            if cp.captured.is_blue and not isinstance(cp, OffMapSpawn)
        ]
    if not references:
        return DEEP_DEPTH_NM
    return meters(
        min(position.distance_to_point(reference) for reference in references)
    ).nautical_miles


def resolve_downed_pilots(game: Game) -> None:
    """Advance every evader one turn: walk home off friendly ground, or roll the
    depth-weighted capture. Runs from ``finish_turn``; deliberately no expiry --
    an evader persists until rescued, recovered, or captured."""
    ledger = _ledger(game)
    if not ledger:
        return
    from game.pow_recovery import PendingPowRecovery, resolve_holding_airfield

    kept: list[DownedPilot] = []
    for dp in ledger:
        position = game.point_in_world(dp.x, dp.y)
        nearest = _nearest_control_point(game, position)
        if nearest is not None and nearest.captured.is_blue:
            # Down on friendly ground: friendly forces pick them up during the gap.
            if dp.pilot is not None:
                dp.pilot.repatriate()
            logging.info(f"Evading pilot of {dp.unit_name} recovered near {nearest}.")
            game.message(
                "Evader walked home",
                f"{_pilot_label(dp)} reached friendly forces near {nearest.name} "
                "and returns to the roster.",
            )
            continue
        chance = capture_chance(_depth_nm(game, position))
        if _RNG.random() < chance:
            pilot = dp.pilot
            if pilot is not None:
                pilot.capture()
            entry = PendingPowRecovery(
                airframe_unit_name=dp.unit_name,
                x=dp.x,
                y=dp.y,
                pilot=pilot,
                captured_turn=game.turn,
            )
            resolve_holding_airfield(game, game.blue, entry)
            game.blue.pending_pow_recoveries.append(entry)
            logging.info(
                f"Evading pilot of {dp.unit_name} captured by an enemy search "
                f"party (capture chance {chance:.0%})."
            )
            game.message(
                "Evader captured",
                f"Enemy search parties found {_pilot_label(dp)} -- now held as "
                "a POW.",
            )
            continue
        kept.append(dp)
    ledger[:] = kept


def mia_sitrep_lines(game: Game) -> list[str]:
    """One player-facing line per aviator still evading, for the SITREP band."""
    lines: list[str] = []
    for dp in _ledger(game):
        nearest = _nearest_control_point(game, game.point_in_world(dp.x, dp.y))
        near = f" near {nearest.name}" if nearest is not None else ""
        turns = max(game.turn - dp.turn_downed, 0)
        if turns <= 0:
            clock = "downed this turn"
        else:
            clock = f"{turns} turn{'s' if turns != 1 else ''} down"
        lines.append(f"{_pilot_label(dp)} — evading{near} ({clock})")
    return lines
