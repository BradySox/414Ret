"""Decoy suspected-activity zones (§79) -- Maskirovka for the recon layer.

Fake "in here somewhere" contacts that render *identically* to a real concealed
enemy force (the §3 uncertainty circle), so the human planner cannot tell a real
hidden contact from a feint without spending recon on it. Flying recon (a TARPS
overfly or an attack) onto a decoy resolves it as empty -- "no activity, it was a
decoy" -- and the circle is removed.

A decoy is a *unitless* concealed :class:`TheaterGroundObject`:

* It renders as a circle by construction -- the server's concealed-uncertainty
  geometry keys off ``tgo.concealed`` and never inspects unit count, so a
  zero-unit TGO still produces the same jittered "suspected activity" circle as a
  real hidden force (and inherits the same red-casing + "?" styling).
* Because it has **zero alive units**, the AI planner -- which enumerates targets
  on ground truth via ``is_dead()`` -- skips it automatically. So the deception
  targets the HUMAN planner only, which is where it has teeth; the AI is immune
  for free and never wastes a strike on an empty zone. (A live-unit COIN-style
  spawn would be wrong here: the live unit is exactly what would leak the decoy
  to the planner.)

Two halves ("both", per the design call):

* an **authored budget** -- a campaign sets how many decoys stand at once (its
  ``settings.decoy_zone_count``, or a top-level ``decoy_zones:`` block), and
* a **per-turn refresh** -- :func:`advance_decoy_zones` (from ``finish_turn``)
  burns the ones the player reconned and tops the live count back up, so the map
  never runs dry and the player cannot simply memorize which circles are fake.

Gated ``decoy_zones`` (default OFF) and only meaningful when the concealment layer
is active (the setting is ``enabled_when=concealed_enemy_forces``) -- otherwise
real forces show exact markers and any circle would obviously be a decoy. No
plugin, no Lua: pure turn-model, the map presence rides the existing §3
concealment emit and the burn rides the existing discovery flip.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game
    from game.theater import ControlPoint

# Deterministic dice (module-level so tests can seed it); finish_turn runs once
# per turn, so decoy placement never re-rolls within a turn.
_RNG = random.Random()

#: Default live-decoy budget when the setting is on but no count/block is authored.
DEFAULT_DECOY_BUDGET = 4
#: Never stand more than this many at once, whatever a campaign asks for -- a
#: sanity bound so a fat authored budget can't blanket the whole map in circles.
MAX_DECOY_BUDGET = 12
#: A decoy sits this far (metres) off its host red CP, on land, so its jittered
#: circle lands in plausible near-front terrain rather than sitting on the base.
_MIN_OFFSET_M = 2000.0
_MAX_OFFSET_M = 9000.0


@dataclass(frozen=True)
class DecoyConfig:
    """A campaign's authored decoy plan (re-derived from YAML, never pickled)."""

    #: Target number of live decoys; ``None`` falls back to the ``decoy_zone_count``
    #: setting so the feature works with no campaign block at all.
    budget: Optional[int]
    #: Optional red-CP names to prefer as decoy hosts; empty ⇒ auto (front-adjacent
    #: red CPs, where a real hidden force would plausibly sit).
    near_cps: tuple[str, ...] = ()


_CONFIG_CACHE: dict[str, DecoyConfig] = {}


def parse_decoy_config(raw: object) -> DecoyConfig:
    """Parse a campaign's top-level ``decoy_zones:`` mapping.

    A malformed block raises (authored data is validated at load, like the
    ``red_tempo:`` parser); an absent block is simply "no authored plan".
    """
    if not raw:
        return DecoyConfig(budget=None)
    if not isinstance(raw, dict):
        raise ValueError(f"decoy_zones: must be a mapping: {raw!r}")
    budget = raw.get("budget")
    near = raw.get("near_cps", []) or []
    if not isinstance(near, list):
        raise ValueError(f"decoy_zones.near_cps must be a list of CP names: {near!r}")
    return DecoyConfig(
        budget=int(budget) if budget is not None else None,
        near_cps=tuple(str(name) for name in near),
    )


def config_for(game: "Game") -> DecoyConfig:
    """The campaign's authored decoy plan, or an empty one (cached per process)."""
    name = getattr(game, "campaign_name", None)
    if not name:
        return DecoyConfig(budget=None)
    if name in _CONFIG_CACHE:
        return _CONFIG_CACHE[name]
    cfg = DecoyConfig(budget=None)
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
                cfg = parse_decoy_config(data.get("decoy_zones"))
                break
    except Exception:  # noqa: BLE001
        logging.exception("Decoy zones: config lookup failed for %r", name)
        cfg = DecoyConfig(budget=None)
    _CONFIG_CACHE[name] = cfg
    return cfg


def _budget_for(game: "Game") -> int:
    cfg = config_for(game)
    budget = cfg.budget
    if budget is None:
        budget = int(getattr(game.settings, "decoy_zone_count", DEFAULT_DECOY_BUDGET))
    return max(0, min(budget, MAX_DECOY_BUDGET))


def _all_decoys(game: "Game") -> list[Any]:
    """Every decoy TGO on the map (attached to its host red CP)."""
    out: list[Any] = []
    for cp in game.theater.controlpoints:
        for tgo in cp.connected_objectives:
            if getattr(tgo, "is_decoy", False):
                out.append(tgo)
    return out


def _candidate_red_cps(game: "Game") -> list["ControlPoint"]:
    """Red CPs a decoy can plausibly sit near: the authored hints, else front-
    adjacent red CPs, else any red land CP."""
    from game.theater.controlpoint import OffMapSpawn

    red_land = [
        cp
        for cp in game.theater.controlpoints
        if cp.captured.is_red and not isinstance(cp, OffMapSpawn)
    ]
    if not red_land:
        return []
    cfg = config_for(game)
    if cfg.near_cps:
        named = [cp for cp in red_land if cp.name in cfg.near_cps]
        if named:
            return named
    front = [cp for cp in red_land if getattr(cp, "has_active_frontline", False)]
    return front or red_land


def _pick_decoy_site(game: "Game") -> Optional[tuple["ControlPoint", Any]]:
    candidates = _candidate_red_cps(game)
    if not candidates:
        return None
    cp = _RNG.choice(candidates)
    for _ in range(6):
        heading_deg = _RNG.uniform(0.0, 360.0)
        dist = _RNG.uniform(_MIN_OFFSET_M, _MAX_OFFSET_M)
        point = cp.position.point_from_heading(heading_deg, dist)
        if game.theater.is_on_land(point):
            return cp, point
    return cp, cp.position


def _spawn_decoy(game: "Game", red_cp: "ControlPoint", point: Any, events: Any) -> Any:
    """Create a unitless concealed decoy TGO attached to *red_cp* at *point*."""
    from game.data.groups import GroupTask
    from game.naming import namegen
    from game.theater import PresetLocation
    from game.theater.theatergroundobject import VehicleGroupGroundObject
    from game.utils import Heading

    heading = game.theater.heading_to_conflict_from(point) or Heading.from_degrees(0)
    location = PresetLocation(namegen.random_objective_name(), point, heading)
    # A bare VehicleGroupGroundObject: groups stay empty, so it is unitless (the
    # AI planner's is_dead gate skips it) yet renders as a concealed circle.
    tgo = VehicleGroupGroundObject(
        location.original_name, location, red_cp, GroupTask.FRONT_LINE
    )
    tgo.concealed = True
    tgo.is_decoy = True
    red_cp.connected_objectives.append(tgo)
    game.db.tgos.add(tgo.id, tgo)
    if events is not None:
        events.update_tgo(tgo)
    return tgo


def _host_is_red(tgo: Any) -> bool:
    cp = getattr(tgo, "control_point", None)
    return bool(cp is not None and cp.captured.is_red)


def _burn(game: "Game", tgo: Any, events: Any) -> None:
    """Remove a reconned decoy and tell the player it was a feint."""
    from game.fourteenth.coin import _despawn

    cp = getattr(tgo, "control_point", None)
    where = getattr(cp, "name", None) or "the search area"
    _despawn(game, tgo, events)
    game.message(
        "Recon report",
        f"No enemy activity near {where} -- the suspected contact was a decoy.",
    )


def advance_decoy_zones(game: "Game", events: Any = None) -> None:
    """Burn the decoys the player reconned last mission, then top up to budget.

    Idempotent per turn; call once from ``finish_turn`` (after the debrief has set
    each reconned TGO's ``discovered_by_player``). No-op unless the ``decoy_zones``
    setting is on. Placement rides seeded dice so a test can pin it.
    """
    if not getattr(game.settings, "decoy_zones", False):
        return
    if getattr(game, "turn", 0) < 1:
        return
    # 1. Clear the decoys that should no longer stand. A player who reconned one
    #    (TARPS / attack) gets the "it was a decoy" report; a decoy whose host CP
    #    flipped to blue is a defunct friendly circle, so it is swept silently
    #    (not a recon result). Despawning also stops a revealed unitless TGO from
    #    rendering as a dead marker, since discovery already collapsed the circle.
    from game.fourteenth.coin import _despawn

    for tgo in _all_decoys(game):
        if getattr(tgo, "discovered_by_player", False):
            _burn(game, tgo, events)
        elif not _host_is_red(tgo):
            _despawn(game, tgo, events)
    # 2. Top the live count back up toward the budget with fresh feints.
    budget = _budget_for(game)
    live = [
        tgo
        for tgo in _all_decoys(game)
        if not getattr(tgo, "discovered_by_player", False)
    ]
    for _ in range(max(0, budget - len(live))):
        site = _pick_decoy_site(game)
        if site is None:
            break
        _spawn_decoy(game, site[0], site[1], events)
