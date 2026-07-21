"""Custom victory conditions (§75): alternate, legible ends to the war.

Design note: docs/dev/design/414th-victory-conditions-notes.md. The stock win
condition is total conquest -- ``Game.check_win_loss`` returns WIN only when the
enemy owns zero control points -- which forces every campaign, including a
limited war ("liberate Abkhazia", a maritime pressure campaign), into a full
ground invasion. This module adds the community-requested shallow layer over
that default:

* **Authored tier:** a campaign YAML ``victory:`` block (sibling of ``will:`` /
  ``phases:``) declaring ``win_when`` / ``lose_when`` condition lists -- victory
  control points, domination thresholds, named high-value target destruction,
  category decapitation, enemy strength attrition vs. the campaign-start
  baseline, and air denial. Parsed by :func:`parse_victory`, re-derived from the
  campaign YAML by name at load (the phases-S5 rederive-never-pickle rule; the
  module cache degrades to "no profile" on any failure, never a crash).
* **Generic tier:** two opt-in Settings knobs usable on ANY campaign with zero
  authoring -- ``alternate_victory_domination`` and
  ``alternate_victory_attrition`` -- synthesized into the same condition objects
  and stacked with any authored block.

Semantics: a victory entry is a *requirement*, so EVERY field set on one entry
must hold (AND within the entry) and the ``win_when`` / ``lose_when`` lists are
OR (any fully-met entry ends the war). That is what makes ``min_turn`` usable
as a guard ("not before turn 4") instead of nonsense ("win at turn 4").

Alternate conditions ADD to the stock endings, never replace them: capturing
everything still wins, losing everything still loses, and the W2 negotiation
ending -- absorbed into :func:`victory_verdict` (2026-07-19), which is the one
alternate-endings branch in ``check_win_loss`` -- outranks both. Evaluation is
ground truth (``viewer=None``) at the turn boundary only, and the planner never
reads these conditions (the S17 boundary: an author who wants the AI to pursue
the objectives authors a ``phases:`` emphasis alongside -- the blocks compose).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Optional

if TYPE_CHECKING:
    from game import Game
    from game.settings import Settings
    from game.theater.controlpoint import ControlPoint
    from game.theater.theatergroundobject import TheaterGroundObject

#: The generic attrition knob is capped here: "enemy air below 95% of start"
#: would end the war on the first kill, which is a losses counter, not a
#: victory condition.
MAX_ATTRITION_THRESHOLD = 90


@dataclass(frozen=True)
class VictoryCondition:
    """One ``win_when`` / ``lose_when`` entry.

    EVERY set field must hold for the entry to be met (AND) -- the opposite of
    an any-field trigger, as documented in the module docstring. ``label`` is an
    optional authored display prefix; the knobs
    synthesize unlabeled entries (their prose already says everything).
    """

    label: Optional[str] = None
    #: Guard: the entry cannot be met before this campaign turn.
    min_turn: int = 0
    #: ALL named control points are blue-owned.
    capture_cps: tuple[str, ...] = ()
    #: ANY named control point is red-owned (the ``lose_when`` staple).
    lose_cps: tuple[str, ...] = ()
    #: BLUE owns at least this fraction of the non-neutral control points.
    territory_above: Optional[float] = None
    #: BLUE owns less than this fraction of the non-neutral control points.
    territory_below: Optional[float] = None
    #: ALL ground objects with these names are fully dead (case-insensitive;
    #: a name matching nothing can never be met -- typos are visible in the UI,
    #: not silent wins).
    destroy_targets: tuple[str, ...] = ()
    #: NO red-owned ground object of these ``category`` strings has alive units,
    #: AND the campaign-start baseline counted at least one (so an absent
    #: category can never produce a vacuous instant win).
    destroy_categories: tuple[str, ...] = ()
    #: Red owned airframes (all squadrons) below this fraction of the baseline.
    enemy_air_below: Optional[float] = None
    #: Red front-line ground inventory below this fraction of the baseline.
    enemy_ground_below: Optional[float] = None
    #: Blue owned airframes below this fraction of the baseline (``lose_when``).
    friendly_air_below: Optional[float] = None
    #: The will meters (0-100, the meter's native scale). Live only while
    #: ``vietnam_political_will`` is on: with will tracking off the field can
    #: never fire, and the UI says so. Strict ``<`` -- these are authored
    #: *thresholds* ("resolve below 30"); the hard exhaustion-at-0 ending is
    #: the negotiation verdict, absorbed separately by :func:`victory_verdict`.
    blue_will_below: Optional[float] = None
    red_resolve_below: Optional[float] = None
    #: Front supply health (0-100, the SITREP/ribbon percent scale) via the §53
    #: war economy's ``coalition_supply_health``. Live only while ``war_economy``
    #: is on -- the starvation/blockade ending ("choke their front below 25%").
    enemy_supply_below: Optional[float] = None
    friendly_supply_below: Optional[float] = None
    #: NO red control point can currently field aircraft
    #: (``runway_is_operational``: cratered airfields and sunk carriers are
    #: denied; FOB helipads count as air power; a red off-map spawn is always
    #: operational, so this condition is unreachable on those campaigns -- by
    #: construction, documented in the design note).
    enemy_air_denied: bool = False


@dataclass(frozen=True)
class VictoryProfile:
    """A campaign's alternate endings: any met entry ends the war."""

    description: Optional[str] = None
    win_when: tuple[VictoryCondition, ...] = ()
    lose_when: tuple[VictoryCondition, ...] = ()


@dataclass
class VictoryBaseline:
    """Campaign-start strength snapshot the ratio conditions run against.

    Latched on the game the first time :func:`ensure_victory_baseline` runs
    (turn 0 for a new game; first load for a pre-feature save -- the accepted
    late-baseline migration). Snapshotted unconditionally so a knob flipped
    on at turn 20 still measures against the earliest state this build saw.
    ``red_categories`` counts red ground objects per ``category`` so
    ``destroy_categories`` can prove the target class ever existed.
    """

    red_air: int
    blue_air: int
    red_ground: int
    red_categories: dict[str, int] = field(default_factory=dict)


# --- live-state counters (self-contained: this module is an upstream-carve
# candidate, so it deliberately does not import the phases counters) -----------


def _air_strength(game: Game, blue: bool) -> int:
    """Owned airframes across ALL of one side's squadrons.

    The whole force, not the phases classifier's air-superiority slice --
    Starfire's ask is force strength, and a bomber wing is strength.
    """
    from game.theater.player import Player

    player = Player.BLUE if blue else Player.RED
    return sum(
        squadron.owned_aircraft
        for squadron in game.air_wing_for(player).iter_squadrons()
    )


def _ground_strength(game: Game, blue: bool) -> int:
    """One side's front-line ground inventory (the force plan_groundwar fields)."""
    from game.theater.player import Player

    player = Player.BLUE if blue else Player.RED
    return sum(
        cp.base.total_armor
        for cp in game.theater.controlpoints
        if cp.captured is player
    )


def _territory(game: Game) -> tuple[int, int]:
    """(blue-owned, total non-neutral) control points."""
    from game.theater.player import Player

    blue = 0
    total = 0
    for cp in game.theater.controlpoints:
        if cp.captured is Player.NEUTRAL:
            continue
        total += 1
        if cp.captured is Player.BLUE:
            blue += 1
    return blue, total


def _red_category_counts(game: Game) -> dict[str, int]:
    """Red-owned ground objects per ``category`` string (alive or dead)."""
    from game.theater.player import Player

    counts: dict[str, int] = {}
    for tgo in game.theater.ground_objects:
        if tgo.control_point.captured is Player.RED:
            counts[tgo.category] = counts.get(tgo.category, 0) + 1
    return counts


def _red_alive_in_category(game: Game, category: str) -> int:
    """Red-owned ground objects of ``category`` that still have alive units."""
    from game.theater.player import Player

    return sum(
        1
        for tgo in game.theater.ground_objects
        if tgo.control_point.captured is Player.RED
        and tgo.category == category
        and any(unit.alive for unit in tgo.units)
    )


def _tgos_named(game: Game, name: str) -> list[TheaterGroundObject]:
    """Every ground object matching ``name`` (case-insensitive, stripped)."""
    wanted = name.strip().casefold()
    return [
        tgo
        for tgo in game.theater.ground_objects
        if tgo.name.strip().casefold() == wanted
    ]


def _cp_named(game: Game, name: str) -> Optional[ControlPoint]:
    for cp in game.theater.controlpoints:
        if cp.name == name:
            return cp
    return None


def _operational_red_airbases(game: Game) -> int:
    """Red control points that can currently field aircraft."""
    from game.theater.player import Player

    return sum(
        1
        for cp in game.theater.controlpoints
        if cp.captured is Player.RED and cp.runway_is_operational()
    )


def _will_value(game: Game, blue: bool) -> Optional[float]:
    """One side's will meter, or None when will tracking is off/absent.

    The gate is the setting, not the attribute: a condition authored against a
    meter nobody is tracking must never fire (and the UI says why).
    """
    if not getattr(game.settings, "vietnam_political_will", False):
        return None
    coalition = game.blue if blue else game.red
    value = getattr(coalition, "political_will", None)
    return float(value) if value is not None else None


def _supply_percent(game: Game, blue: bool) -> Optional[float]:
    """One side's front supply health as 0-100, or None when the economy is off."""
    if not getattr(game.settings, "war_economy", False):
        return None
    try:
        from game.fourteenth.war_economy import coalition_supply_health

        coalition = game.blue if blue else game.red
        return coalition_supply_health(game, coalition) * 100.0
    except Exception:  # noqa: BLE001 -- a read-only display/eval aid, never a crash
        logging.exception("Victory conditions: supply read failed")
        return None


# --- the baseline latch ---------------------------------------------------------------


def ensure_victory_baseline(game: Game) -> VictoryBaseline:
    """Latch (or return) the campaign-start strength snapshot.

    Called from ``Game.initialize_turn`` so a new game latches at turn 0;
    verdict/overview also call it defensively so a pre-feature save latches on
    first read. Cheap (three sums + a category walk) and unconditional, so a
    late-enabled knob still measures honestly.
    """
    baseline = getattr(game, "victory_baseline", None)
    if baseline is None:
        baseline = VictoryBaseline(
            red_air=_air_strength(game, blue=False),
            blue_air=_air_strength(game, blue=True),
            red_ground=_ground_strength(game, blue=False),
            red_categories=_red_category_counts(game),
        )
        game.victory_baseline = baseline
    return baseline


# --- evaluation -----------------------------------------------------------------------


def _ratio_below(current: int, base: int, threshold: float) -> bool:
    """A strength ratio vs. an empty baseline is unmeasurable, never met."""
    if base <= 0:
        return False
    return current / base < threshold


def condition_met(
    game: Game, condition: VictoryCondition, baseline: VictoryBaseline
) -> bool:
    """AND semantics: every field set on the entry must hold."""
    from game.theater.player import Player

    if game.turn < condition.min_turn:
        return False
    for name in condition.capture_cps:
        cp = _cp_named(game, name)
        if cp is None or not cp.captured.is_blue:
            return False
    if condition.lose_cps:
        if not any(
            (cp := _cp_named(game, name)) is not None and cp.captured is Player.RED
            for name in condition.lose_cps
        ):
            return False
    if condition.territory_above is not None:
        blue, total = _territory(game)
        if total == 0 or blue / total < condition.territory_above:
            return False
    if condition.territory_below is not None:
        blue, total = _territory(game)
        if total == 0 or blue / total >= condition.territory_below:
            return False
    for name in condition.destroy_targets:
        targets = _tgos_named(game, name)
        if not targets:
            return False
        for tgo in targets:
            if any(unit.alive for unit in tgo.units):
                return False
    for category in condition.destroy_categories:
        if baseline.red_categories.get(category, 0) <= 0:
            return False
        if _red_alive_in_category(game, category) > 0:
            return False
    if condition.enemy_air_below is not None and not _ratio_below(
        _air_strength(game, blue=False), baseline.red_air, condition.enemy_air_below
    ):
        return False
    if condition.enemy_ground_below is not None and not _ratio_below(
        _ground_strength(game, blue=False),
        baseline.red_ground,
        condition.enemy_ground_below,
    ):
        return False
    if condition.friendly_air_below is not None and not _ratio_below(
        _air_strength(game, blue=True), baseline.blue_air, condition.friendly_air_below
    ):
        return False
    # Meter conditions: unmeasurable (feature off) never fires -- the same
    # honesty rule as the empty strength baselines.
    if condition.blue_will_below is not None:
        will = _will_value(game, blue=True)
        if will is None or will >= condition.blue_will_below:
            return False
    if condition.red_resolve_below is not None:
        resolve = _will_value(game, blue=False)
        if resolve is None or resolve >= condition.red_resolve_below:
            return False
    if condition.friendly_supply_below is not None:
        supply = _supply_percent(game, blue=True)
        if supply is None or supply >= condition.friendly_supply_below:
            return False
    if condition.enemy_supply_below is not None:
        supply = _supply_percent(game, blue=False)
        if supply is None or supply >= condition.enemy_supply_below:
            return False
    if condition.enemy_air_denied and _operational_red_airbases(game) > 0:
        return False
    return True


# --- the knobs (generic tier) ---------------------------------------------------------


def _knob_conditions(settings: Settings) -> tuple[VictoryCondition, ...]:
    """The Settings-synthesized win conditions (0 = off, the default)."""
    out = []
    domination = int(getattr(settings, "alternate_victory_domination", 0) or 0)
    if 0 < domination <= 100:
        out.append(VictoryCondition(territory_above=domination / 100))
    attrition = int(getattr(settings, "alternate_victory_attrition", 0) or 0)
    if 0 < attrition <= MAX_ATTRITION_THRESHOLD:
        out.append(VictoryCondition(enemy_air_below=attrition / 100))
    return tuple(out)


# --- parsing + the campaign lookup (rederive-never-pickle) ----------------------------

_STRING_LIST_KEYS = ("capture_cps", "lose_cps", "destroy_targets", "destroy_categories")
_FRACTION_KEYS = (
    "territory_above",
    "territory_below",
    "enemy_air_below",
    "enemy_ground_below",
    "friendly_air_below",
)
#: Meter-scale thresholds (0-100, matching the meters' own display) -- vs the
#: ratio fields above, which are 0-1 fractions of a campaign-start baseline.
_METER_KEYS = (
    "blue_will_below",
    "red_resolve_below",
    "enemy_supply_below",
    "friendly_supply_below",
)
_ALLOWED_ENTRY_KEYS = (
    frozenset(_STRING_LIST_KEYS)
    | frozenset(_FRACTION_KEYS)
    | frozenset(_METER_KEYS)
    | {"label", "min_turn", "enemy_air_denied"}
)


def _parse_string_list(raw: object, key: str) -> tuple[str, ...]:
    if (
        not isinstance(raw, list)
        or not raw
        or not all(isinstance(item, str) and item.strip() for item in raw)
    ):
        raise ValueError(f"victory: {key} must be a non-empty list of names: {raw!r}")
    return tuple(str(item) for item in raw)


def _parse_fraction(raw: object, key: str) -> float:
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"victory: {key} must be a number in (0, 1): {raw!r}")
    if not 0 < value <= 1 or (key != "territory_above" and value == 1):
        # territory_above: 1.0 ("own everything") is legal, if redundant with
        # the stock ending; a *_below threshold of 1.0 is trivially near-true.
        raise ValueError(f"victory: {key} must be a fraction in (0, 1): {raw!r}")
    return value


def _parse_meter(raw: object, key: str) -> float:
    """A 0-100 meter threshold (will/resolve/supply -- the meters' own scale)."""
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"victory: {key} must be a number in (0, 100): {raw!r}")
    if not 0 < value < 100:
        # 100 is trivially near-true ("below 100" fires on the first scratch);
        # the hard exhaustion-at-0 ending is the negotiation verdict, which
        # victory_verdict absorbs on will campaigns without any authoring.
        raise ValueError(f"victory: {key} must be in (0, 100): {raw!r}")
    return value


def _parse_entry(raw: object) -> VictoryCondition:
    """One ``win_when`` / ``lose_when`` entry. Fails loudly on bad data, so a
    broken campaign dies in tests rather than silently losing its ending."""
    if not isinstance(raw, dict):
        raise ValueError(f"victory: condition entry must be a mapping: {raw!r}")
    unknown = set(raw) - _ALLOWED_ENTRY_KEYS
    if unknown:
        raise ValueError(
            f"victory: unknown condition field(s) {sorted(unknown)} in {raw!r}"
        )

    def strings(key: str) -> tuple[str, ...]:
        return _parse_string_list(raw[key], key) if key in raw else ()

    def fraction(key: str) -> Optional[float]:
        if key not in raw or raw[key] is None:
            return None
        return _parse_fraction(raw[key], key)

    def meter(key: str) -> Optional[float]:
        if key not in raw or raw[key] is None:
            return None
        return _parse_meter(raw[key], key)

    denied = raw.get("enemy_air_denied", False)
    if denied not in (False, True):
        raise ValueError(
            f"victory: enemy_air_denied must be true (omit it otherwise): {raw!r}"
        )
    condition = VictoryCondition(
        label=str(raw["label"]) if raw.get("label") else None,
        min_turn=int(raw.get("min_turn", 0)),
        capture_cps=strings("capture_cps"),
        lose_cps=strings("lose_cps"),
        territory_above=fraction("territory_above"),
        territory_below=fraction("territory_below"),
        destroy_targets=strings("destroy_targets"),
        destroy_categories=strings("destroy_categories"),
        enemy_air_below=fraction("enemy_air_below"),
        enemy_ground_below=fraction("enemy_ground_below"),
        friendly_air_below=fraction("friendly_air_below"),
        blue_will_below=meter("blue_will_below"),
        red_resolve_below=meter("red_resolve_below"),
        enemy_supply_below=meter("enemy_supply_below"),
        friendly_supply_below=meter("friendly_supply_below"),
        enemy_air_denied=bool(denied),
    )
    has_condition = bool(
        condition.capture_cps
        or condition.lose_cps
        or condition.territory_above is not None
        or condition.territory_below is not None
        or condition.destroy_targets
        or condition.destroy_categories
        or condition.enemy_air_below is not None
        or condition.enemy_ground_below is not None
        or condition.friendly_air_below is not None
        or condition.blue_will_below is not None
        or condition.red_resolve_below is not None
        or condition.enemy_supply_below is not None
        or condition.friendly_supply_below is not None
        or condition.enemy_air_denied
    )
    if not has_condition:
        raise ValueError(
            f"victory: entry has no condition (label/min_turn alone do not "
            f"end a war): {raw!r}"
        )
    return condition


def parse_victory(raw: object) -> Optional[VictoryProfile]:
    """Parse a campaign YAML ``victory:`` block, or None when absent."""
    if not raw:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"victory: must be a mapping, got {type(raw).__name__}")
    unknown = set(raw) - {"description", "win_when", "lose_when"}
    if unknown:
        raise ValueError(f"victory: unknown key(s) {sorted(unknown)}")
    win_raw = raw.get("win_when") or []
    lose_raw = raw.get("lose_when") or []
    if not isinstance(win_raw, list) or not isinstance(lose_raw, list):
        raise ValueError("victory: win_when/lose_when must be lists of conditions")
    win = tuple(_parse_entry(entry) for entry in win_raw)
    lose = tuple(_parse_entry(entry) for entry in lose_raw)
    if not win and not lose:
        raise ValueError("victory: needs at least one win_when or lose_when entry")
    description = raw.get("description")
    return VictoryProfile(
        description=str(description) if description else None,
        win_when=win,
        lose_when=lose,
    )


#: Authored-profile cache keyed by campaign name (the phases ``_ARC_CACHE``
#: pattern). Definitions live in the campaign YAML and are re-derived per
#: process, never pickled; tests may inject here.
_PROFILE_CACHE: dict[str, Optional[VictoryProfile]] = {}


def authored_victory_for(game: Game) -> Optional[VictoryProfile]:
    """The campaign's authored ``victory:`` block, or None.

    Any lookup/parse failure degrades to None with a log, never a crash -- an
    old save whose campaign was removed (or whose block was broken by an edit)
    still plays with the stock endings.
    """
    name = getattr(game, "campaign_name", None)
    if not name:
        return None
    if name in _PROFILE_CACHE:
        return _PROFILE_CACHE[name]
    profile: Optional[VictoryProfile] = None
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
                profile = parse_victory(data.get("victory"))
                break
    except Exception:  # noqa: BLE001
        logging.exception("Victory conditions: lookup failed for %r", name)
        profile = None
    _PROFILE_CACHE[name] = profile
    return profile


def active_victory_profile(game: Game) -> Optional[VictoryProfile]:
    """The authored block + the knob-synthesized conditions, or None.

    The knobs are re-read every call (settings change mid-campaign); the
    authored block comes from the process cache.
    """
    authored = authored_victory_for(game)
    extra = _knob_conditions(game.settings)
    if authored is None and not extra:
        return None
    if authored is None:
        return VictoryProfile(win_when=extra)
    if not extra:
        return authored
    return VictoryProfile(
        description=authored.description,
        win_when=authored.win_when + extra,
        lose_when=authored.lose_when,
    )


# --- the verdict (the check_win_loss branch) ------------------------------------------


def _announce(game: Game, condition: VictoryCondition, defeat: bool) -> None:
    """Name the met condition beside the generic Victory!/Defeat! dialog.

    Latched per condition text: the Qt flow calls ``check_win_loss`` several
    times around a turn boundary, and the events feed should carry the "why"
    once. The latch persists (harmless -- the war is over).
    """
    text = condition.label or describe_condition(
        game, condition, ensure_victory_baseline(game), live=False
    )
    announced: set[str] = getattr(game, "victory_announced", set())
    key = ("defeat" if defeat else "victory") + ":" + text
    if key in announced:
        return
    announced.add(key)
    game.victory_announced = announced
    if defeat:
        game.message("Defeat condition met", text)
    else:
        game.message("Victory condition met", text)


def victory_verdict(game: Game) -> Optional[Literal["win", "loss"]]:
    """The alternate ending, or None while the war goes on.

    Backs the single alternate-endings branch in ``Game.check_win_loss`` ahead
    of the stock territory checks. The **W2 negotiation ending is absorbed
    here** (2026-07-19, the "adapt the meters to the victory framework" pass):
    will/resolve exhaustion is consulted first, exactly the precedence it had
    as its own branch -- negotiation loss > negotiation win > authored/knob
    loss > win -- and it carries no announce of its own because
    ``update_political_will`` already fires the profile's era-framed exhaustion
    banner on the crossing edge. Loss precedence throughout (the W2 rule: a
    simultaneous collapse is never a cheap win).
    """
    from game.fourteenth.political_will import negotiation_verdict

    negotiated = negotiation_verdict(game)
    if negotiated is not None:
        return negotiated

    profile = active_victory_profile(game)
    if profile is None:
        return None
    baseline = ensure_victory_baseline(game)
    for condition in profile.lose_when:
        if condition_met(game, condition, baseline):
            _announce(game, condition, defeat=True)
            return "loss"
    for condition in profile.win_when:
        if condition_met(game, condition, baseline):
            _announce(game, condition, defeat=False)
            return "win"
    return None


# --- display (the ribbon expander block + the SITREP lines) ---------------------------


def describe_condition(
    game: Game,
    condition: VictoryCondition,
    baseline: VictoryBaseline,
    live: bool = True,
) -> str:
    """One entry as prose, with live values when ``live`` (the
    ``_describe_condition`` style from the phases expander)."""
    from game.theater.player import Player

    bits = []
    if condition.capture_cps:
        names = ", ".join(condition.capture_cps)
        now = ""
        if live:
            held = sum(
                1
                for name in condition.capture_cps
                if (cp := _cp_named(game, name)) is not None and cp.captured.is_blue
            )
            now = f" ({held}/{len(condition.capture_cps)} held)"
        bits.append(f"Capture {names}{now}")
    if condition.lose_cps:
        names = ", ".join(condition.lose_cps)
        now = ""
        if live:
            fallen = sum(
                1
                for name in condition.lose_cps
                if (cp := _cp_named(game, name)) is not None
                and cp.captured is Player.RED
            )
            now = f" ({fallen}/{len(condition.lose_cps)} fallen)"
        plural = "s" if len(condition.lose_cps) == 1 else ""
        bits.append(f"{names} fall{plural} to the enemy{now}")
    if condition.territory_above is not None:
        now = ""
        if live:
            blue, total = _territory(game)
            if total:
                now = f" (now {blue / total:.0%})"
        bits.append(f"Hold {condition.territory_above:.0%} of the bases{now}")
    if condition.territory_below is not None:
        now = ""
        if live:
            blue, total = _territory(game)
            if total:
                now = f" (now {blue / total:.0%})"
        bits.append(
            f"Friendly holdings fall below {condition.territory_below:.0%}{now}"
        )
    if condition.destroy_targets:
        names = ", ".join(condition.destroy_targets)
        now = ""
        if live:
            dead = 0
            for name in condition.destroy_targets:
                targets = _tgos_named(game, name)
                if targets and not any(
                    unit.alive for tgo in targets for unit in tgo.units
                ):
                    dead += 1
            now = f" ({dead}/{len(condition.destroy_targets)} destroyed)"
        bits.append(f"Destroy {names}{now}")
    if condition.destroy_categories:
        names = ", ".join(condition.destroy_categories)
        now = ""
        if live:
            alive = sum(
                _red_alive_in_category(game, category)
                for category in condition.destroy_categories
            )
            now = f" ({alive} still standing)"
        bits.append(f"Destroy every enemy {names} site{now}")
    if condition.enemy_air_below is not None:
        now = ""
        if live and baseline.red_air:
            ratio = _air_strength(game, blue=False) / baseline.red_air
            now = f" (now {ratio:.0%})"
        bits.append(
            f"Enemy air force below {condition.enemy_air_below:.0%} of start{now}"
        )
    if condition.enemy_ground_below is not None:
        now = ""
        if live and baseline.red_ground:
            ratio = _ground_strength(game, blue=False) / baseline.red_ground
            now = f" (now {ratio:.0%})"
        bits.append(
            f"Enemy ground force below "
            f"{condition.enemy_ground_below:.0%} of start{now}"
        )
    if condition.friendly_air_below is not None:
        now = ""
        if live and baseline.blue_air:
            ratio = _air_strength(game, blue=True) / baseline.blue_air
            now = f" (now {ratio:.0%})"
        bits.append(
            f"Friendly air force falls below "
            f"{condition.friendly_air_below:.0%} of start{now}"
        )
    if condition.blue_will_below is not None or condition.red_resolve_below is not None:
        from game.fourteenth.political_will import will_profile_for

        profile = will_profile_for(game)
        if condition.blue_will_below is not None:
            will = _will_value(game, blue=True)
            now = ""
            if live:
                now = (
                    f" (now {will:.0f})" if will is not None else " (will tracking off)"
                )
            bits.append(
                f"{profile.blue.label} falls below {condition.blue_will_below:g}{now}"
            )
        if condition.red_resolve_below is not None:
            resolve = _will_value(game, blue=False)
            now = ""
            if live:
                now = (
                    f" (now {resolve:.0f})"
                    if resolve is not None
                    else " (will tracking off)"
                )
            bits.append(
                f"{profile.red.label} falls below {condition.red_resolve_below:g}{now}"
            )
    if condition.enemy_supply_below is not None:
        supply = _supply_percent(game, blue=False)
        now = ""
        if live:
            now = (
                f" (now {supply:.0f}%)" if supply is not None else " (war economy off)"
            )
        bits.append(
            f"Enemy front supply falls below {condition.enemy_supply_below:g}%{now}"
        )
    if condition.friendly_supply_below is not None:
        supply = _supply_percent(game, blue=True)
        now = ""
        if live:
            now = (
                f" (now {supply:.0f}%)" if supply is not None else " (war economy off)"
            )
        bits.append(
            f"Friendly front supply falls below "
            f"{condition.friendly_supply_below:g}%{now}"
        )
    if condition.enemy_air_denied:
        now = ""
        if live:
            operating = _operational_red_airbases(game)
            plural = "" if operating == 1 else "s"
            now = f" ({operating} enemy base{plural} still operating)"
        bits.append(f"Deny the enemy air operations{now}")
    text = " and ".join(bits)
    if condition.min_turn > 1:
        text += f" (not before turn {condition.min_turn})"
    if condition.label:
        return f"{condition.label} — {text}"
    return text


def _will_ending_rows(game: Game) -> list[dict[str, object]]:
    """The negotiation ending as checklist rows -- will campaigns, zero authoring.

    Before the absorption the will ending was invisible in the victory UI: the
    meters sat on the ribbon while the actual win/loss lived in code. Now every
    will campaign's VICTORY checklist leads with its real endings, labeled by
    the campaign's own will profile ("Break Hanoi's resolve (now 87 of 100)").
    Empty when will tracking is off.
    """
    blue = _will_value(game, blue=True)
    red = _will_value(game, blue=False)
    if blue is None or red is None:
        return []
    from game.fourteenth.political_will import will_profile_for

    profile = will_profile_for(game)
    return [
        {
            "text": f"Break {profile.red.label} (now {red:.0f} of 100)",
            "met": red <= 0,
            "defeat": False,
        },
        {
            "text": f"{profile.blue.label} runs out (now {blue:.0f} of 100)",
            "met": blue <= 0,
            "defeat": True,
        },
    ]


def victory_overview(game: Game) -> list[dict[str, object]]:
    """The conditions for the ribbon expander: one row per entry, live prose.

    Leads with the negotiation ending's rows on will campaigns (the client
    groups by the ``defeat`` flag, so ordering within the list is free).
    ``defeat`` rows render as risks; ``met`` will essentially only show once
    the war is over (a met condition ends the game at the next turn boundary),
    so the live parentheticals are the real display. Empty when nothing is
    configured, which hides the whole block.
    """
    rows: list[dict[str, object]] = _will_ending_rows(game)
    profile = active_victory_profile(game)
    if profile is None:
        return rows
    baseline = ensure_victory_baseline(game)
    for condition in profile.win_when:
        rows.append(
            {
                "text": describe_condition(game, condition, baseline),
                "met": condition_met(game, condition, baseline),
                "defeat": False,
            }
        )
    for condition in profile.lose_when:
        rows.append(
            {
                "text": describe_condition(game, condition, baseline),
                "met": condition_met(game, condition, baseline),
                "defeat": True,
            }
        )
    return rows


def victory_description(game: Game) -> Optional[str]:
    """The authored block's description line, for the expander header."""
    profile = active_victory_profile(game)
    return profile.description if profile else None


def victory_sitrep_lines(game: Game, limit: int = 4) -> list[str]:
    """The SITREP band's victory-progress digest (capped)."""
    rows = victory_overview(game)
    lines = []
    for row in rows[:limit]:
        prefix = "Defeat if" if row["defeat"] else "Victory"
        lines.append(f"{prefix}: {row['text']}")
    if len(rows) > limit:
        lines.append(f"(+{len(rows) - limit} more conditions)")
    return lines
