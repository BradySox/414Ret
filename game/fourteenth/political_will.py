"""Vietnam campaign layer W1+W2: the political-will economy and negotiation ending.

Spec: docs/dev/design/414th-vietnam-political-will-roe-notes.md. One mechanic, two
labels: BLUE tracks **Political Will** (Washington's patience), RED tracks **Regime
Resolve** (Hanoi's capacity to absorb punishment). Both live on
``Coalition.political_will`` (0-100, start 100) and are fed **once per flown turn**
from the ``Debriefing`` the mission-results processor already has -- no new Lua, no
debrief-schema change (the §29 SITREP / §37 reconcile precedent).

W1 landed the observe-only economy (numbers move + SITREP band). W2 attaches the
consequence: ``negotiation_verdict`` backs a branch in ``Game.check_win_loss`` ahead
of the territory checks -- **RED resolve exhausted = WIN** (Hanoi agrees to terms;
you never had to take a base), **BLUE will exhausted = LOSS** (Washington orders
withdrawal, whatever the map says), with BLUE-loss precedence if both break on the
same turn (your patience broke first -- no cheap simultaneous win). Territory victory
stays untouched. Everything is behind the ``vietnam_political_will`` setting -- off
means this module never runs and the branch never fires.

The two sides drain differently (historically honest -- Hanoi absorbed catastrophic
loss ratios; Washington bled from every news cycle):

* **BLUE** drains from airframe losses (heavy bombers cost several times a tactical
  jet), aviators captured (an immediate hit **plus a trickle every turn the POW sits
  in captivity** -- the §15 POW clock becomes economy), and bases lost. Combat SAR
  rescues (§21) soften the blow; claimed enemy air kills and a slow passive
  regeneration restore it.
* **RED** drains mostly from **logistics strangulation** -- trail convoy losses (§35's
  real, tracked convoys) and ground attrition -- and barely from airframe losses.

**The mechanic is campaign-generic; only the defaults are Vietnam.** A campaign's
``will:`` YAML block (see :func:`parse_will_profile` and
docs/dev/design/414th-will-generalization-notes.md) can re-label both meters and
their exhaustion banners (Falklands: London vs. the Junta) and re-weight every feed
(a warship sunk outweighing an airframe). Profiles follow the phases-S5 rule:
re-derived from the campaign YAML by name at load, cached per process, never
pickled, and any lookup/parse failure degrades to the Vietnam-framed defaults with
a log -- so the 4 Vietnam campaigns (no ``will:`` block) behave exactly as before.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Any, Literal, Optional, cast

if TYPE_CHECKING:
    from game import Game
    from game.debriefing import AirLosses, Debriefing
    from game.theater import Player as PlayerT

# --- BLUE (Political Will) feed weights -- design-note §7 starting values; tuned in W2.
BLUE_AIRFRAME_LOSS = 1.0
BLUE_HEAVY_BOMBER_LOSS = 6.0  # a downed B-52 is a national event
BLUE_POW_TAKEN = 2.0  # an aviator captured this turn
BLUE_POW_HELD_PER_TURN = 0.5  # each turn a POW sits in Hanoi
BLUE_PILOT_RESCUED_REFUND = 0.5  # a Combat SAR save softens the airframe blow
BLUE_BASE_LOST = 3.0
BLUE_ENEMY_AIR_CLAIMED = 0.25  # restores: a claimed MiG kill plays well at home
BLUE_PASSIVE_REGEN = 0.5
#: W4 ROE coupling: each kill inside an active restricted zone (see
#: phases.count_roe_violations) is a headline -- the sharp soft-enforcement drain
#: that makes the zones bind the player without hard-blocking them.
BLUE_ROE_VIOLATION = 4.0
#: A warship sunk is front-page news (a Sheffield, not a truck). Counted from the
#: debriefing's ground-object losses by TheaterUnit.is_ship; rare in Vietnam, the
#: load-bearing feed for naval wars (Falklands re-weights it up).
BLUE_SHIP_LOST = 4.0

# --- RED (Regime Resolve) feed weights. Resolve is hard: airframes barely register;
# the trail is the artery.
RED_CONVOY_UNIT_LOST = 1.5
RED_GROUND_UNIT_LOST = 0.25
RED_AIRFRAME_LOSS = 0.25
RED_BASE_LOST = 3.0
RED_PASSIVE_REGEN = 0.75
#: Ships leave RED's generic ground-attrition pool and drain at their own weight.
RED_SHIP_LOST = 0.5
#: COIN C2: each of RED's ammo caches *destroyed* this turn (a ``category ==
#: "ammo"`` TGO whose last unit died -- the same objects the coin module throttles
#: regeneration on). Inert by default (0.0) so Vietnam and every non-COIN campaign
#: are untouched; the COIN campaign's ``will:`` block prices it (caches are the
#: insurgency's real currency). The cache's own building units still count in the
#: generic ground-attrition feed -- this weight is the *strategic* loss on top,
#: not a reclassification (unlike ships, which move pools).
RED_CACHE_LOST = 0.0

WILL_MAX = 100.0
WILL_MIN = 0.0

#: Turns of attribution kept on the game (the sparkline already covers the long
#: trend; the ledger answers "why did it move").
WILL_LEDGER_CAP = 60


@dataclass(frozen=True)
class WillSideCopy:
    """One side's player-facing framing: the meter label + the exhaustion banner."""

    #: Possessive meter framing, capitalized as it should print ("Washington's
    #: patience") -- used mid-sentence in the per-turn message, as the ribbon
    #: meter tooltip, and in the Stats chart legend.
    label: str
    exhaustion_title: str
    exhaustion_body: str


_VIETNAM_BLUE_COPY = WillSideCopy(
    label="Washington's patience",
    exhaustion_title="Washington orders withdrawal",
    exhaustion_body=(
        "Political will is exhausted -- the home front has turned. The war "
        "ends on their terms, whatever the map says."
    ),
)
_VIETNAM_RED_COPY = WillSideCopy(
    label="Hanoi's resolve",
    exhaustion_title="Hanoi agrees to terms",
    exhaustion_body=(
        "The regime's resolve is broken -- negotiators are en route to "
        "Paris. The pressure campaign has done what the front line never "
        "had to."
    ),
)


@dataclass(frozen=True)
class WillWeights:
    """Every feed weight, defaulting to the Vietnam constants above.

    A campaign's ``will: weights:`` mapping overrides fields by name; an unknown
    key is a parse error (caught by :func:`will_profile_for`, which degrades to
    the defaults) so a typo never silently no-ops a rebalance.
    """

    blue_airframe_loss: float = BLUE_AIRFRAME_LOSS
    blue_heavy_bomber_loss: float = BLUE_HEAVY_BOMBER_LOSS
    blue_pow_taken: float = BLUE_POW_TAKEN
    blue_pow_held_per_turn: float = BLUE_POW_HELD_PER_TURN
    blue_pilot_rescued_refund: float = BLUE_PILOT_RESCUED_REFUND
    blue_base_lost: float = BLUE_BASE_LOST
    blue_enemy_air_claimed: float = BLUE_ENEMY_AIR_CLAIMED
    blue_passive_regen: float = BLUE_PASSIVE_REGEN
    blue_roe_violation: float = BLUE_ROE_VIOLATION
    blue_ship_lost: float = BLUE_SHIP_LOST
    red_convoy_unit_lost: float = RED_CONVOY_UNIT_LOST
    red_ground_unit_lost: float = RED_GROUND_UNIT_LOST
    red_airframe_loss: float = RED_AIRFRAME_LOSS
    red_base_lost: float = RED_BASE_LOST
    red_passive_regen: float = RED_PASSIVE_REGEN
    red_ship_lost: float = RED_SHIP_LOST
    red_cache_lost: float = RED_CACHE_LOST


@dataclass(frozen=True)
class WillProfile:
    """A campaign's authored will framing + feed weights (default: Vietnam)."""

    blue: WillSideCopy = _VIETNAM_BLUE_COPY
    red: WillSideCopy = _VIETNAM_RED_COPY
    weights: WillWeights = WillWeights()


DEFAULT_WILL_PROFILE = WillProfile()

#: Parsed profiles per campaign name (the phases _ARC_CACHE precedent); tests may
#: seed/clear entries directly.
_PROFILE_CACHE: dict[str, WillProfile] = {}


def _parse_side_copy(raw: Any, default: WillSideCopy) -> WillSideCopy:
    """One side's ``will: blue:``/``red:`` mapping; absent fields keep the default."""
    if raw is None:
        return default
    if not isinstance(raw, dict):
        raise ValueError(f"will side block must be a mapping: {raw!r}")
    return WillSideCopy(
        label=str(raw.get("label", default.label)),
        exhaustion_title=str(raw.get("exhaustion_title", default.exhaustion_title)),
        exhaustion_body=str(raw.get("exhaustion_body", default.exhaustion_body)),
    )


def parse_will_profile(raw: Any) -> WillProfile:
    """Parse a campaign's ``will:`` YAML block; None means the Vietnam defaults.

    Schema (every key optional; anything absent keeps its default)::

        will:
          blue:
            label: Downing Street's patience
            exhaustion_title: London recalls the task force
            exhaustion_body: ...
          red:
            label: the Junta's resolve
            exhaustion_title: The Junta capitulates
            exhaustion_body: ...
          weights:
            blue_ship_lost: 8
            red_ship_lost: 6

    Raises ValueError on a malformed block (wrong shape, unknown weight key) --
    :func:`will_profile_for` catches it and degrades to the defaults with a log.
    """
    if raw is None:
        return DEFAULT_WILL_PROFILE
    if not isinstance(raw, dict):
        raise ValueError(f"will: must be a mapping: {raw!r}")
    weights_raw = raw.get("weights") or {}
    if not isinstance(weights_raw, dict):
        raise ValueError(f"will.weights: must be a mapping: {weights_raw!r}")
    known = {field.name for field in fields(WillWeights)}
    unknown = sorted(set(weights_raw) - known)
    if unknown:
        raise ValueError(f"will.weights: unknown keys {unknown}")
    return WillProfile(
        blue=_parse_side_copy(raw.get("blue"), _VIETNAM_BLUE_COPY),
        red=_parse_side_copy(raw.get("red"), _VIETNAM_RED_COPY),
        weights=WillWeights(
            **{key: float(value) for key, value in weights_raw.items()}
        ),
    )


def will_profile_for(game: "Game") -> WillProfile:
    """The campaign's authored will profile, or the Vietnam defaults.

    Re-derived from the campaign YAML by name (the phases-S5 rule: definitions
    are never pickled) and cached per process. Any lookup/parse failure degrades
    to the defaults with a log, never a crash -- an old save whose campaign was
    removed still plays.
    """
    name = getattr(game, "campaign_name", None)
    if not name:
        return DEFAULT_WILL_PROFILE
    if name in _PROFILE_CACHE:
        return _PROFILE_CACHE[name]
    profile = DEFAULT_WILL_PROFILE
    try:
        import yaml

        from game.campaignloader.campaign import Campaign

        for path in Campaign.iter_campaign_defs():
            try:
                with path.open(encoding="utf-8") as campaign_file:
                    data = yaml.safe_load(campaign_file)
            except Exception:  # noqa: BLE001 -- one bad yaml must not kill the scan
                continue
            if isinstance(data, dict) and data.get("name") == name:
                profile = parse_will_profile(data.get("will"))
                break
    except Exception:  # noqa: BLE001
        logging.exception("Political will: profile lookup failed for %r", name)
        profile = DEFAULT_WILL_PROFILE
    _PROFILE_CACHE[name] = profile
    return profile


@dataclass(frozen=True)
class WillLedgerEntry:
    """One flown turn's will movement with its component attribution.

    The legibility half of the W1 economy: the meters said *that* will moved;
    the ledger says *why* (which feed, how much) -- surfaced on the ribbon meter
    hover, the arc expander, and the SITREP band, and the instrument for the M1
    pacing pass. Moves are ``(label, signed value)`` in feed order; the deltas
    are their sums (pre-clamp, so a floor/ceiling turn still shows its physics).
    Pickled on ``Game.will_ledger`` (capped at :data:`WILL_LEDGER_CAP`).
    """

    turn: int
    blue_delta: float
    red_delta: float
    blue_moves: tuple[tuple[str, float], ...]
    red_moves: tuple[tuple[str, float], ...]


def format_moves(moves: tuple[tuple[str, float], ...], limit: int = 4) -> str:
    """The biggest movers as one line: 'airframes x2 -2.0 · POWs held x3 -1.5'."""
    ranked = sorted(moves, key=lambda move: abs(move[1]), reverse=True)[:limit]
    return " · ".join(f"{label} {value:+.1f}" for label, value in ranked)


def latest_ledger_entry(game: "Game") -> Optional[WillLedgerEntry]:
    """The most recent flown turn's attribution, or None (feature off / turn 0)."""
    ledger = getattr(game, "will_ledger", None) or []
    return ledger[-1] if ledger else None


def ledger_notes(game: "Game") -> tuple[Optional[str], Optional[str]]:
    """Rendered (blue, red) attribution lines for the latest flown turn.

    One short line per side -- '−4.0: heavy bombers x1 down −6.0 · …' -- for the
    ribbon meter hover, the expander, and the SITREP band. (None, None) when the
    ledger is empty (feature off, turn 0, or a pre-feature save).
    """
    entry = latest_ledger_entry(game)
    if entry is None:
        return None, None
    blue = f"{entry.blue_delta:+.1f}: {format_moves(entry.blue_moves, limit=3)}"
    red = f"{entry.red_delta:+.1f}: {format_moves(entry.red_moves, limit=3)}"
    return blue, red


def negotiation_verdict(game: "Game") -> Optional[Literal["win", "loss"]]:
    """The W2 negotiation ending, or None while the war goes on.

    Backs the ``vietnam_political_will``-gated branch in ``Game.check_win_loss``
    (decoupled from ``TurnState`` so this module never imports the game core):

    * BLUE will exhausted -> ``"loss"`` -- Washington orders withdrawal, even with
      the front intact.
    * RED resolve exhausted -> ``"win"`` -- Hanoi agrees to terms; no base capture
      required.

    BLUE-loss takes precedence when both break on the same turn (your patience broke
    first -- a simultaneous collapse is never a cheap win). Returns None with the
    setting off, so non-Vietnam campaigns never touch this path.
    """
    if not getattr(game.settings, "vietnam_political_will", False):
        return None
    if game.blue.political_will <= WILL_MIN:
        return "loss"
    if game.red.political_will <= WILL_MIN:
        return "win"
    return None


def update_political_will(game: "Game", debriefing: "Debriefing") -> None:
    """Feed both sides' will from the turn's debriefing (observe-only in W1).

    Runs once per flown turn from the mission-results processor, after the loss and
    POW steps have committed (so the held-POW trickle reads post-recovery state).
    No-op unless ``vietnam_political_will`` is on. Values clamp to [0, 100]; hitting
    zero ends the war via the negotiation branch in ``Game.check_win_loss`` (W2),
    announced here with era-framed copy on the crossing edge.
    """
    if not getattr(game.settings, "vietnam_political_will", False):
        return

    profile = will_profile_for(game)
    blue_moves = _blue_moves(game, debriefing, profile.weights)
    red_moves = _red_moves(game, debriefing, profile.weights)
    blue_delta = sum(value for _label, value in blue_moves)
    red_delta = sum(value for _label, value in red_moves)

    blue_before = game.blue.political_will
    red_before = game.red.political_will
    game.blue.political_will = _clamp(blue_before + blue_delta)
    game.red.political_will = _clamp(red_before + red_delta)

    # The attribution ledger: why the numbers moved (meter hover / expander /
    # SITREP). getattr: duck-typed test games and pre-feature saves lack the list.
    ledger = getattr(game, "will_ledger", None)
    if ledger is None:
        ledger = []
        game.will_ledger = ledger
    ledger.append(
        WillLedgerEntry(
            turn=getattr(game, "turn", 0),
            blue_delta=blue_delta,
            red_delta=red_delta,
            blue_moves=tuple(blue_moves),
            red_moves=tuple(red_moves),
        )
    )
    del ledger[:-WILL_LEDGER_CAP]

    # Era-framed exhaustion cues (W2): the generic win/loss dialog fires from
    # check_win_loss; these messages carry the negotiation framing (from the
    # campaign's will profile; Vietnam copy by default). Crossing-edge only, so
    # a side sitting at zero doesn't repeat the banner every turn.
    if game.blue.political_will <= WILL_MIN < blue_before:
        game.message(profile.blue.exhaustion_title, profile.blue.exhaustion_body)
    if game.red.political_will <= WILL_MIN < red_before:
        game.message(profile.red.exhaustion_title, profile.red.exhaustion_body)

    logging.info(
        "Political will: BLUE %+0.1f -> %.1f, RED %+0.1f -> %.1f",
        blue_delta,
        game.blue.political_will,
        red_delta,
        game.red.political_will,
    )
    game.message(
        "Political will",
        f"{profile.blue.label} {game.blue.political_will:.0f}% "
        f"({blue_delta:+.1f} — {format_moves(tuple(blue_moves), limit=3)}); "
        f"{profile.red.label} {game.red.political_will:.0f}% "
        f"({red_delta:+.1f} — {format_moves(tuple(red_moves), limit=3)}).",
    )


def _ship_losses(debriefing: "Debriefing", player: "PlayerT") -> int:
    """This turn's sunk warship units (naval TGO units in the ground-object losses).

    getattr-guarded like the rest of the feeds: lightweight test debriefings carry
    no ground_losses, and a missing attribute means no ships, never a crash.
    """
    ground_losses = getattr(debriefing, "ground_losses", None)
    if ground_losses is None:
        return 0
    losses = (
        getattr(ground_losses, "player_ground_objects", [])
        if player.is_blue
        else getattr(ground_losses, "enemy_ground_objects", [])
    )
    return sum(
        1
        for loss in losses
        if getattr(getattr(loss, "theater_unit", None), "is_ship", False)
    )


def _red_caches_destroyed(debriefing: "Debriefing") -> int:
    """RED ammo caches *destroyed* this turn (COIN C2).

    A cache is a ``category == "ammo"`` TGO -- the object the coin module throttles
    regeneration on. Counted as destroyed when it appears in the turn's RED
    ground-object losses AND no unit of it remains alive (this runs after the loss
    commit, so ``alive`` reflects post-strike truth); a damaged-but-standing cache
    is not a headline. Distinct TGOs, so a two-building cache never counts twice.
    getattr-guarded like the other feeds.
    """
    ground_losses = getattr(debriefing, "ground_losses", None)
    if ground_losses is None:
        return 0
    destroyed_ids = set()
    for loss in getattr(ground_losses, "enemy_ground_objects", []):
        tgo = getattr(getattr(loss, "theater_unit", None), "ground_object", None)
        if tgo is None or getattr(tgo, "category", None) != "ammo":
            continue
        if any(unit.alive for unit in tgo.units):
            continue
        destroyed_ids.add(id(tgo))
    return len(destroyed_ids)


def _blue_moves(
    game: "Game", debriefing: "Debriefing", weights: WillWeights
) -> list[tuple[str, float]]:
    """BLUE's labeled feed components this turn, in feed order (sum = the delta)."""
    from game.missiongenerator.vietnamopsluadata import HEAVY_BOMBER_DCS_IDS
    from game.theater import Player

    moves: list[tuple[str, float]] = [("passive regen", weights.blue_passive_regen)]

    # Airframe losses, weighted by what fell. by_type keys are AircraftTypes; heavy
    # bombers reuse the §32 Arc Light identification set. getattr+cast sidesteps the
    # mypy has-type quirk on Debriefing's init-assigned attrs (the sitrep.py precedent).
    air_losses = cast("AirLosses", getattr(debriefing, "air_losses"))
    heavies = 0
    tactical = 0
    for aircraft_type, count in air_losses.by_type(Player.BLUE).items():
        if aircraft_type.dcs_unit_type.id in HEAVY_BOMBER_DCS_IDS:
            heavies += count
        else:
            tactical += count
    if heavies:
        moves.append(
            (
                f"heavy bombers x{heavies} down",
                -heavies * weights.blue_heavy_bomber_loss,
            )
        )
    if tactical:
        moves.append(
            (f"airframes x{tactical} lost", -tactical * weights.blue_airframe_loss)
        )

    # Warships sunk (naval TGO units): rare in Vietnam, the headline feed for
    # naval wars -- a Falklands profile re-weights it up.
    ships = _ship_losses(debriefing, Player.BLUE)
    if ships:
        moves.append((f"warships x{ships} sunk", -ships * weights.blue_ship_lost))

    # Aviators: fresh captures hit now; every POW still held drains a trickle. Runs
    # after commit_pow_recoveries, so a freed aviator stops draining the same turn.
    captures = getattr(debriefing.state_data, "combat_sar_captures", []) or []
    if captures:
        moves.append(
            (
                f"aviators captured x{len(captures)}",
                -len(captures) * weights.blue_pow_taken,
            )
        )
    pows = len(game.blue.pending_pow_recoveries)
    if pows:
        moves.append((f"POWs held x{pows}", -pows * weights.blue_pow_held_per_turn))

    # A rescue is a headline: refund part of the airframe cost per pilot saved.
    rescues = getattr(debriefing.state_data, "combat_sar_rescues", []) or []
    if rescues:
        moves.append(
            (
                f"pilots rescued x{len(rescues)}",
                len(rescues) * weights.blue_pilot_rescued_refund,
            )
        )

    bases_lost = debriefing.loss_counts(Player.BLUE).bases_lost
    if bases_lost:
        moves.append(
            (f"bases lost x{bases_lost}", -bases_lost * weights.blue_base_lost)
        )

    # ROE violations (W4): kills inside an active restricted zone draw a sharp
    # penalty -- the LBJ-era pilot could break the rules, but Washington answered
    # for it. Zero whenever no authored phase with zones is active.
    from game.fourteenth.phases import count_roe_violations

    violations = count_roe_violations(game, debriefing)
    if violations:
        moves.append(
            (f"ROE violations x{violations}", -violations * weights.blue_roe_violation)
        )
        game.message(
            "ROE violation",
            f"{violations} target(s) destroyed inside a restricted zone this "
            "turn. Washington takes the heat -- political will pays the bill.",
        )

    # Claimed enemy air kills play well at home (claimed, per the recon-fog framing).
    claimed = debriefing.loss_counts(Player.RED).aircraft
    if claimed:
        moves.append(
            (f"claimed MiG kills x{claimed}", claimed * weights.blue_enemy_air_claimed)
        )

    return moves


def _red_moves(
    game: "Game", debriefing: "Debriefing", weights: WillWeights
) -> list[tuple[str, float]]:
    """RED's labeled feed components this turn, in feed order (sum = the delta)."""
    from game.theater import Player

    moves: list[tuple[str, float]] = [("passive regen", weights.red_passive_regen)]

    red_losses = debriefing.loss_counts(Player.RED)
    # The trail is the artery: convoy kills (the §35 real convoys) bite hardest.
    if red_losses.convoy:
        moves.append(
            (
                f"trail convoys x{red_losses.convoy}",
                -red_losses.convoy * weights.red_convoy_unit_lost,
            )
        )
    # Warships leave the generic attrition pool and drain at their own weight
    # (never below zero: a fake debriefing may set the count without the lists).
    ships = _ship_losses(debriefing, Player.RED)
    ground = red_losses.front_line + max(0, red_losses.ground_objects - ships)
    if ground:
        moves.append(
            (f"ground attrition x{ground}", -ground * weights.red_ground_unit_lost)
        )
    if ships:
        moves.append((f"warships x{ships} sunk", -ships * weights.red_ship_lost))
    # COIN C2: destroyed ammo caches are the insurgency's strategic loss, on top of
    # the generic attrition their building units already count as. Inert unless the
    # campaign's will profile prices red_cache_lost (default 0.0), so the count is
    # only computed when it can matter.
    if weights.red_cache_lost:
        caches = _red_caches_destroyed(debriefing)
        if caches:
            moves.append(
                (f"ammo caches x{caches} destroyed", -caches * weights.red_cache_lost)
            )
    if red_losses.aircraft:
        moves.append(
            (
                f"airframes x{red_losses.aircraft} lost",
                -red_losses.aircraft * weights.red_airframe_loss,
            )
        )
    if red_losses.bases_lost:
        moves.append(
            (
                f"bases lost x{red_losses.bases_lost}",
                -red_losses.bases_lost * weights.red_base_lost,
            )
        )

    return moves


def _clamp(value: float) -> float:
    return max(WILL_MIN, min(WILL_MAX, value))
