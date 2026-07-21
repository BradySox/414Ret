"""Blue-side COMINT collection (§70, delivery phase C0).

Design note ``docs/dev/design/414th-comint-notes.md``. DCS cannot intercept real
communications (AI traffic isn't RF; no transmission event exists), so COMINT is
a **presentation-and-gating layer over ground truth the engine already knows** --
the §3 recon-fog shape. This module is the campaign-scale half (Feature A):

* **Sources** are the enemy's emitting net: alive red ``comms``/``commandcenter``
  TGOs (the same objects §51 jamming and §52 decapitation key on -- killing one
  degrades red AND dries up this take, the bomb-it-or-tap-it dilemma) plus alive
  concealed COIN spawns (an insurgency runs on radios; regulars whose C2 dies go
  landline/courier, an insurgency can't).
* **Tier 0** -- no alive sources: no product ("enemy net silent").
* **Tier 1** -- sources alive: the ambient national-collection take (the C1
  audible red net + the kneeboard active-nets listing).
* **Tier 2** -- a blue collector (a §2 JAMMING flight or a drone -- "a drone is
  always listening", the §3 always-filming rule) flew last mission and survived:
  a coarsened **tasking leak** (one red offensive package flying THIS mission)
  plus a **full-snap reveal** of one concealed enemy site near an alive source.

Zero planner coupling by design: the blue AI already plans on ground truth (§3
``viewer=None`` discipline), so everything here informs only the human. Pure
turn-model -- no ``.miz``/Lua/DCS. Gated ``comint_collection`` (default OFF);
OFF is an exact no-op. BLUE-only product (red's COMINT already exists as §51's
capture gate).
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Optional

from game.ato.flighttype import FlightType
from game.data.units import UAV_DCS_IDS

if TYPE_CHECKING:
    from game import Game
    from game.debriefing import Debriefing
    from game.sim.gameupdateevents import GameUpdateEvents

#: TGO categories that make up the enemy's emitting command net -- the same
#: object set §51 (comms jamming transmitter) and §52 (decapitation) read.
COMMS_CATEGORIES = frozenset({"comms", "commandcenter"})

#: A Tier-2 reveal must sit within this range of an alive source -- the fiction
#: is that the *site's own chatter* gave it away, so a silent corner of the map
#: stays dark.
COMINT_REVEAL_RANGE_M = 60_000.0

#: Half-width of the leaked TOT window. The intercept is honest but coarse (the
#: §5 approximate-precision precedent): the player learns roughly when, never
#: the minute.
LEAK_TOT_WINDOW = datetime.timedelta(minutes=30)

#: Offensive package classes the tasking leak considers, most threatening
#: first (design note: "Strike/BAI/OCA/anti-ship against blue assets").
_LEAK_CLASS_RANK: dict[FlightType, int] = {
    FlightType.STRIKE: 0,
    FlightType.OCA_RUNWAY: 1,
    FlightType.OCA_AIRCRAFT: 2,
    FlightType.BAI: 3,
    FlightType.ANTISHIP: 4,
}


def comint_enabled(game: "Game") -> bool:
    return bool(getattr(game.settings, "comint_collection", False))


def _tgo_alive(tgo: Any) -> bool:
    """Any unit alive -- the same aliveness test §52 uses."""
    return any(
        getattr(u, "alive", False)
        for g in getattr(tgo, "groups", [])
        for u in getattr(g, "units", [])
    )


def _red_tgos(game: "Game") -> list[Any]:
    red = game.red.player
    tgos: list[Any] = []
    for cp in game.theater.controlpoints:
        if cp.captured is not red:
            continue
        tgos.extend(getattr(cp, "ground_objects", []))
    return tgos


def comint_sources(game: "Game") -> list[Any]:
    """The enemy's alive emitters: comms/CC TGOs + concealed COIN spawns.

    The COIN clause covers campaigns with no authored C2 (insurgents field no
    IADS comms but are intrinsically comms-active): a concealed COIN-spawned
    cell/IED team/HVT is a source while it lives.
    """
    sources = []
    for tgo in _red_tgos(game):
        if not _tgo_alive(tgo):
            continue
        # §50 ambush teams are map_hidden and must never be comms-active
        # anywhere (no take, no transmission) -- nothing telegraphs them.
        if getattr(tgo, "map_hidden", False):
            continue
        if getattr(tgo, "category", None) in COMMS_CATEGORIES:
            sources.append(tgo)
        elif getattr(tgo, "coin_spawned", False) and getattr(tgo, "concealed", False):
            sources.append(tgo)
    return sources


def collector_flew_last_turn(game: "Game") -> bool:
    """True when a surviving blue collector flew the just-resolved mission."""
    collected = getattr(game, "comint_collected_turn", None)
    return collected is not None and collected == game.turn - 1


def collection_tier(game: "Game") -> int:
    """0 = net silent, 1 = ambient take, 2 = collected (leak + reveal).

    Sources are the prerequisite for everything: a dead net yields nothing even
    if a collector flew (there is no traffic to collect).
    """
    if not comint_enabled(game):
        return 0
    if not comint_sources(game):
        return 0
    return 2 if collector_flew_last_turn(game) else 1


def _is_collector(flight: Any) -> bool:
    """A §2 JAMMING flight, or any drone -- "a drone is always listening"."""
    if getattr(flight, "flight_type", None) is FlightType.JAMMING:
        return True
    try:
        return flight.unit_type.dcs_unit_type.id in UAV_DCS_IDS
    except AttributeError:
        return False


def record_comint_collection(game: "Game", debriefing: "Debriefing") -> None:
    """Debrief-commit hook: bank the collection when a collector survived.

    Runs before the turn increments (commit-time ``game.turn`` is the
    just-played turn), so Tier 2 next turn is ``comint_collected_turn ==
    turn - 1``. A shot-down collector collects nothing (the ``airecon``
    one-shot precedent).
    """
    if not comint_enabled(game):
        return
    air_losses = getattr(debriefing, "air_losses", None)
    if air_losses is None:
        return
    for package in game.blue.ato.packages:
        for flight in package.flights:
            if not _is_collector(flight):
                continue
            if air_losses.surviving_flight_members(flight) > 0:
                game.comint_collected_turn = game.turn
                return


def _concealed_population(game: "Game", tgo: Any) -> bool:
    """Is this TGO part of the dashed-circle population the reveal snaps?

    Mirrors the server model's concealment predicate
    (``game/server/tgos/models.py``): flag-concealed (the COIN spawns,
    intrinsic) or a §3 concealable field force (armor/missile/mobile-SAM
    categories, gated by ``concealed_enemy_forces``). ``map_hidden`` TGOs (the
    §50 ambush teams) are NEVER eligible -- nothing telegraphs them.
    """
    if getattr(tgo, "map_hidden", False):
        return False
    if getattr(tgo, "concealed", False):
        return True
    if not getattr(game.settings, "concealed_enemy_forces", False):
        return False
    category = getattr(tgo, "category", None)
    if category in ("armor", "missile"):
        return True
    if category == "aa":
        from game.data.groups import GroupTask

        return getattr(tgo, "task", None) in (
            GroupTask.MERAD,
            GroupTask.SHORAD,
            GroupTask.AAA,
        )
    return False


def _known_to_blue(tgo: Any) -> bool:
    from game.theater import Player

    known = getattr(tgo, "known_for", None)
    if known is None:
        return bool(getattr(tgo, "discovered_by_player", False))
    return bool(known(Player.BLUE))


def _eligible_reveals(game: "Game", sources: list[Any]) -> list[tuple[float, str, Any]]:
    """(distance-to-nearest-source, name, tgo) for every snappable site.

    Sorted ascending so the pick is deterministic: the concealed site closest
    to an alive emitter is the one whose chatter gave it away.
    """
    eligible = []
    for tgo in _red_tgos(game):
        if not _tgo_alive(tgo):
            continue
        if tgo in sources and getattr(tgo, "category", None) in COMMS_CATEGORIES:
            # The net's own nodes are exact map objects already; nothing to snap.
            continue
        if not _concealed_population(game, tgo):
            continue
        if _known_to_blue(tgo):
            continue
        distance = min(
            tgo.position.distance_to_point(source.position) for source in sources
        )
        if distance > COMINT_REVEAL_RANGE_M:
            continue
        eligible.append((distance, str(getattr(tgo, "name", "")), tgo))
    eligible.sort(key=lambda entry: (entry[0], entry[1]))
    return eligible


def apply_comint_reveal(game: "Game", events: "GameUpdateEvents") -> None:
    """Turn-init hook: at Tier 2, snap ONE concealed enemy site to exact.

    Reuses the shipped discovery path (``discovered_by_player`` -> ``known_for``
    -- the same flip a TARPS overflight earns), so the dashed circle becomes the
    real symbol on the map. Idempotent under initialize_turn's re-init cases via
    a per-turn stamp: without it, a re-init after a cheat would find the first
    pick already discovered and snap a second site.
    """
    if not comint_enabled(game):
        return
    if getattr(game, "comint_reveal_turn", None) == game.turn:
        return
    sources = comint_sources(game)
    if not sources or not collector_flew_last_turn(game):
        return
    game.comint_reveal_turn = game.turn
    game.comint_reveal_note = None
    eligible = _eligible_reveals(game, sources)
    if not eligible:
        return
    _, _, tgo = eligible[0]
    tgo.discovered_by_player = True
    events.update_tgo(tgo)
    note = f"{tgo.name} ({tgo.control_point.name} area)"
    game.comint_reveal_note = note
    game.message(
        "COMINT: enemy transmissions localized",
        f"Traffic analysis has fixed {note}. Marked exact on the map.",
    )


def _leak_package(game: "Game") -> Optional[Any]:
    """The red offensive package the intercept leaks -- deterministic.

    Most threatening first (class rank, then mass, then target name as the
    stable tiebreak); no RNG, so mission re-generation never rerolls the leak.
    """
    candidates = []
    for package in game.red.ato.packages:
        task = package.primary_task
        if task not in _LEAK_CLASS_RANK:
            continue
        target = getattr(package, "target", None)
        if target is None:
            continue
        size = sum(getattr(f, "count", 0) for f in package.flights)
        candidates.append((_LEAK_CLASS_RANK[task], -size, str(target.name), package))
    if not candidates:
        return None
    candidates.sort(key=lambda entry: entry[:3])
    return candidates[0][3]


def comint_leak_line(game: "Game") -> Optional[str]:
    """The Tier-2 tasking-leak kneeboard line, or None with nothing to leak."""
    package = _leak_package(game)
    if package is None:
        return None
    task = package.primary_task
    task_name = task.value if task is not None else "offensive"
    size = sum(getattr(f, "count", 0) for f in package.flights)
    line = (
        f"Intercepted tasking traffic: enemy {task_name} package, "
        f"~{size} aircraft — objective {package.target.name}"
    )
    tot = getattr(package, "time_over_target", None)
    if isinstance(tot, datetime.datetime) and tot != datetime.datetime.min:
        start = (tot - LEAK_TOT_WINDOW).strftime("%H:%M")
        end = (tot + LEAK_TOT_WINDOW).strftime("%H:%M")
        line += f", window {start}–{end}"
    return line + "."


#: Cap on the kneeboard active-nets listing; the rest fold into a "+N more".
MAX_LISTED_NETS = 5


def _active_net_lines(red_net: Any) -> list[str]:
    """The C2 findability tie: one briefed line per transmitting enemy net.

    Fixed C2 stations are public map objects, so their name + frequency print
    plainly. A **clandestine** station (a concealed spawn) is briefed as
    exactly what the SIGINT shop would know — a net and a coarse area — never
    the TGO's identity or position: the dashed circle plus this line IS the
    hunt, and DF-ing an open window is how you close it.
    """
    nodes = list(getattr(red_net, "nodes", []) or [])
    if not nodes:
        return []
    lines = ["Active nets (UHF AM):"]
    for node in nodes[:MAX_LISTED_NETS]:
        freq = f"{node.freq_mhz:.3f}"
        area = f" — {node.area} area" if getattr(node, "area", "") else ""
        if getattr(node, "clandestine", False):
            lines.append(f"  suspected clandestine net @ {freq}{area}")
        else:
            lines.append(f"  {node.name} @ {freq}{area}")
    if len(nodes) > MAX_LISTED_NETS:
        lines.append(f"  …plus {len(nodes) - MAX_LISTED_NETS} more net(s) active.")
    return lines


def comint_kneeboard_lines(game: "Game", red_net: Any = None) -> list[str]:
    """The Mission Info COMINT block (empty when the feature is off).

    Tier 0 reads as a consequence, not a bug; Tier 1 briefs the active nets
    (when the §70 C1 red net is transmitting this mission); Tier 2 carries the
    leak + the reveal.
    """
    if not comint_enabled(game):
        return []
    sources = comint_sources(game)
    if not sources:
        return ["Enemy C2 net silent — no COMINT take."]
    lines = [f"Enemy net active: {len(sources)} emitter(s) up."]
    lines.extend(_active_net_lines(red_net))
    if not collector_flew_last_turn(game):
        lines.append(
            "Ambient take only — no collection sortie (jamming bird or drone) "
            "survived last mission."
        )
        return lines
    lines.append("Collection sortie banked a full take last mission:")
    leak = comint_leak_line(game)
    if leak is not None:
        lines.append(leak)
    note = getattr(game, "comint_reveal_note", None)
    if note is not None:
        lines.append(f"Transmissions localized: {note} — marked exact on the map.")
    if leak is None and note is None:
        lines.append("No actionable traffic this cycle — enemy offensive net quiet.")
    return lines
