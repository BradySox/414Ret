"""COIN high-value targets -- hunt the insurgent leadership, mind the collateral.

The fourth COIN direction (after C1 replenishment, C1.5 re-infiltration, IEDs). A COIN
war is a manhunt: the strategic prize is not a body count but the **named leader**.
This layer surfaces a rotating HVT -- a small, named red group near an insurgent
stronghold, live for a **strike window** -- and drops the insurgency's momentum when
he is killed inside it. He often shelters where his people are (a stronghold sitting on
a population-center ROE ring), so the strike carries the **CDE dilemma the rings already
price**: killing an HVT inside a ring is a real momentum blow *and* a mandate-draining
ROE violation (the §40 ``count_roe_violations`` charge). Take the shot dirty, wait for a
clean one, or let the window close -- the choice is the feature.

Turn-boundary force-model work only (``Game.finish_turn``, after C1/C1.5/IED): no Lua, a
real recon-fogged red TGO that dies through the normal loss path. State lives in
``game.coin_state`` (an ``"hvt"`` dict + an ``"hvt_kills"`` counter, plain primitives,
pickled; ``getattr`` default so pre-feature saves are inert until the toggle is on).

Everything is behind ``coin_hvt`` (default OFF, requires ``coin_insurgency`` for the red
strongholds; campaign-preseeded). The momentum drop is priced by the campaign's ``will:``
profile via ``red_hvt_killed`` (default 0.0 -- inert until weighted up).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from game.fourteenth.coin import (
    HVT_SIDC,
    _cp_by_id,
    _despawn,
    _tgo_by_id,
    hvt_unit_types,
    spawn_red_ground_at,
)

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint

#: Turns an HVT stays targetable before he goes to ground (a missed chance, no penalty).
HVT_WINDOW_TURNS = 4

#: Turns after an HVT resolves (killed or escaped) before the next one surfaces.
HVT_COOLDOWN_TURNS = 3

#: Leader + an escort technical + a guard pair -- a small, findable, named convoy that
#: patrols its ROE zone in-mission (the ``coin`` plugin drives it), so hunting him reads
#: as running down a moving column rather than bombing a parked jeep.
HVT_UNITS = 4

#: Noms de guerre for the surfaced leader (flavour; the will effect is name-agnostic).
#: Turn-indexed (never random -- Math.random is unavailable and saves must be stable).
HVT_NAMES = (
    "Mullah Nasir",
    "Qari Zakir",
    "Mullah Dadullah",
    "Haji Lala",
    "Commander Faruq",
    "Mullah Rahim",
    "Qari Yousef",
    "Haji Bashir",
)


def advance_hvt(game: "Game", events: Any = None) -> None:
    """Resolve the live HVT (killed/escaped) and surface the next one. Call exactly
    once per turn from ``finish_turn``, after the C1/C1.5/IED hooks.

    No-op unless both ``coin_hvt`` and ``coin_insurgency`` are on, or before turn 1.
    """
    if not getattr(game.settings, "coin_hvt", False) or not getattr(
        game.settings, "coin_insurgency", False
    ):
        # Mid-campaign toggle-off: an active HVT convoy must not sit live (and
        # concealed) forever with nothing left to resolve it.
        off_state = getattr(game, "coin_state", None)
        off_hvt = off_state.get("hvt") if isinstance(off_state, dict) else None
        if isinstance(off_hvt, dict) and off_hvt.get("active"):
            _despawn(game, _tgo_by_id(game, off_hvt["active"].get("tgo_id")), events)
            off_hvt["active"] = None
        return
    if getattr(game, "turn", 0) < 1:
        return

    state = getattr(game, "coin_state", None)
    if not isinstance(state, dict):
        state = {}
        game.coin_state = state
    hvt: dict[str, Any] = state.setdefault("hvt", {})

    if hvt.get("cooldown", 0) > 0:
        hvt["cooldown"] = int(hvt["cooldown"]) - 1
        return

    if hvt.get("active"):
        _resolve_active_hvt(game, state, hvt, events)
    else:
        _surface_hvt(game, hvt, events)


def _resolve_active_hvt(
    game: "Game", state: dict[str, Any], hvt: dict[str, Any], events: Any
) -> None:
    active = hvt["active"]
    tgo = _tgo_by_id(game, active.get("tgo_id"))
    name = active.get("name", "the HVT")
    # A blue capture of the host stronghold clears its uncapturable TGOs -- the
    # convoy vanishing that way is NOT a decapitation (the base fall is already
    # charged via red_base_lost; crediting the HVT too double-dips the will feed).
    host_id = active.get("cp_id")
    if host_id is not None:
        host = _cp_by_id(game, host_id)
        if host is None or not host.captured.is_red:
            if tgo is not None:
                _despawn(game, tgo, events)
            _announce(
                game,
                f"HVT {name} slipped away in the fall of the stronghold.",
            )
            hvt["active"] = None
            hvt["cooldown"] = HVT_COOLDOWN_TURNS
            return
    if tgo is None:
        # The record dangles (the TGO was removed by some other path): not evidence
        # of a strike. Clear the window without crediting a decapitation -- the
        # IED/field-cell convention (a kill requires the TGO to have existed and died).
        hvt["active"] = None
        hvt["cooldown"] = HVT_COOLDOWN_TURNS
        return
    if not _tgo_alive(tgo):
        # Struck: a decapitation. Credit the momentum blow (consumed by the will layer).
        state["hvt_kills"] = int(state.get("hvt_kills", 0)) + 1
        _despawn(game, tgo, events)
        _announce(game, f"HVT {name} eliminated — a blow to the insurgent leadership.")
        hvt["active"] = None
        hvt["cooldown"] = HVT_COOLDOWN_TURNS
        return
    active["turns"] = int(active.get("turns", 0)) + 1
    if active["turns"] >= HVT_WINDOW_TURNS:
        # The window closed -- he has gone to ground. A missed chance, not a loss.
        _despawn(game, tgo, events)
        _announce(game, f"HVT {name} has gone to ground — the window has closed.")
        hvt["active"] = None
        hvt["cooldown"] = HVT_COOLDOWN_TURNS


def _surface_hvt(game: "Game", hvt: dict[str, Any], events: Any) -> None:
    stronghold = _pick_stronghold(game)
    if stronghold is None:
        return
    point = _hvt_point(game, stronghold)
    from game.data.groups import GroupTask

    tgo = spawn_red_ground_at(
        game,
        stronghold,
        point,
        GroupTask.FRONT_LINE,
        events,
        max_units=HVT_UNITS,
        sidc_override=HVT_SIDC,
        unit_types=hvt_unit_types(game),
        concealed=True,
    )
    if tgo is None:
        return
    # Rotate by SURFACE COUNT, not by turn: the untouched cadence (window 4 +
    # cooldown 3 + resurface = 8 turns) exactly aliases an 8-name table, so the
    # turn-indexed pick resurfaced the same leader eternally when ignored —
    # measured in the 2026-07-18 self-play probe (Qari Zakir at T1/T9/T17...).
    hvt["surfaced"] = int(hvt.get("surfaced", 0)) + 1
    name = HVT_NAMES[(hvt["surfaced"] - 1) % len(HVT_NAMES)]
    try:
        tgo.name = f"HVT {name}"
    except Exception:  # noqa: BLE001 -- name is cosmetic; never break the turn
        pass
    hvt["active"] = {
        "tgo_id": str(tgo.id),
        "cp_id": str(stronghold.id),
        "name": name,
        "turns": 0,
    }
    _announce(
        game,
        f"Intel: HVT {name} is on the move near {stronghold.name} — hunt his convoy "
        "down while the window is open, and mind the collateral.",
    )


def _pick_stronghold(game: "Game") -> Optional["ControlPoint"]:
    """The red stronghold to surface a leader at: the one nearest the fighting (the
    leadership is where the war is), or None if the insurgency holds nothing."""
    reference = _front_reference(game)
    if not reference:
        return None
    best: Optional[tuple[float, "ControlPoint"]] = None
    for cp in game.theater.controlpoints:
        if not cp.captured.is_red:
            continue
        dist = min(p.distance_to_point(cp.position) for p in reference)
        if best is None or dist < best[0]:
            best = (dist, cp)
    return best[1] if best is not None else None


def _front_reference(game: "Game") -> list[Any]:
    fronts = list(game.theater.conflicts())
    if fronts:
        return [front.position for front in fronts]
    return [
        cp.position
        for cp in game.theater.controlpoints
        if not cp.captured.is_red and not cp.captured.is_neutral
    ]


def _hvt_point(game: "Game", stronghold: "ControlPoint") -> Any:
    """A land point a couple of km off the stronghold (the leader is near, not on, the
    base). Falls back to the stronghold position if the offsets aren't on land."""
    from game.utils import Heading

    origin = stronghold.position
    for bearing in (0.0, 90.0, 180.0, 270.0):
        point = origin.point_from_heading(Heading.from_degrees(bearing).degrees, 2500.0)
        if game.theater.is_on_land(point):
            return point
    return origin


def _tgo_alive(tgo: Any) -> bool:
    return any(getattr(unit, "alive", False) for unit in getattr(tgo, "units", []))


def active_hvt_status(game: "Game") -> Optional[tuple[str, int]]:
    """``(name, turns left in the strike window)`` for the live HVT, or None.

    Read by the campaign-status ribbon: the window used to be an invisible
    clock -- announced once in the events feed, then untimed on every surface
    (2026-07-18 UI audit). Existence + name are already-announced intel; the
    concealed map position stays fogged, so surfacing the countdown leaks
    nothing positional.
    """
    if not getattr(game.settings, "coin_hvt", False):
        return None
    state = getattr(game, "coin_state", None)
    if not isinstance(state, dict):
        return None
    hvt = state.get("hvt")
    if not isinstance(hvt, dict):
        return None
    active = hvt.get("active")
    if not isinstance(active, dict):
        return None
    turns_left = max(HVT_WINDOW_TURNS - int(active.get("turns", 0)), 0)
    return (str(active.get("name", "the HVT")), turns_left)


def consume_hvt_kills(game: "Game") -> int:
    """Number of HVT kills since the last call, cleared to zero. The will layer charges
    these as a red-momentum drop (a finish_turn detection, never a generic debrief line).
    """
    state = getattr(game, "coin_state", None)
    if not isinstance(state, dict):
        return 0
    count = int(state.get("hvt_kills", 0))
    state["hvt_kills"] = 0
    return count


def _announce(game: "Game", message: str) -> None:
    try:
        game.message("HVT", message)
    except Exception:  # noqa: BLE001 -- messaging is best-effort, never break the turn
        pass
