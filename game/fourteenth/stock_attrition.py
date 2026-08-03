"""Old-stock loadout attrition (§84).

Every flight of the same airframe and task flies a byte-identical loadout:
`Loadout.default_for` resolves by NAME and returns the first payload that
validates, with no randomness anywhere in the path. Six BARCAP flights therefore
put up six identical magazines of the newest missile the campaign date allows,
which is not how a war goes -- squadrons burn the good stock first and the tail
of the campaign is flown on whatever is left in the bunker.

This walks a flight's loadout DOWN the fallback ladder the weapon data already
declares, by a depth rolled per flight. The ladder is the generational one
(AIM-120C -> AIM-120B -> AIM-7MH -> AIM-7M ...), so "old stock" needs no new
data: a deep roll is what breaks out the Sparrows.

Three things keep it honest:

* **Pressure scales with the campaign clock.** The chance of flying old stock
  rises each turn from `stock_attrition_start` toward `stock_attrition_max`, so
  turn 1 is the well-supplied opening and turn 20 is scraping the bunker.
* **Depth is geometric in that pressure**, so one rung down is common, three is
  rare, and the rare deep rolls get less rare as the campaign drags.
* **Substitution never leaves the weapon's family.** `WeaponType` cannot express
  this (a Sidewinder and a JDAM are both UNKNOWN), and several fallbacks cross
  families deliberately -- `AN/ASQ-228 ATFLIR -> AIM-120C`,
  `AN/ALQ-131 ECM -> 2xAIM-120C`, `AGM-84A -> GBU-24` -- which are sane as a
  LAST RESORT for date gating but absurd as attrition: they would hang a missile
  on the targeting-pod station. So the walk stops at a category boundary, and
  equipment types (pods, jammers, decoys) are never touched at all.
* **A rung is only taken when it is provably older.** `fallback` is a
  date-gating answer and is not monotonic in year -- 18 same-category fallbacks
  in the shipped data point at a NEWER weapon (`2xAIM-120B` 1994 ->
  `AIM-120C` 2018; `AGM-65E` 1985 -> `AGM-65G` 1989 -> `AGM-65F` 1991). Date
  gating cannot save us here, because in a 1991 campaign AGM-65E and AGM-65F are
  both legal, so an unguarded walk would silently *upgrade* the flight. See
  `_older_group`.

Date gating still runs afterwards in the mission generator, so a substitution can
never be newer than the campaign allows -- but that is a ceiling, not this
module's ordering guarantee, which is the year guard above.
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Optional

from game.data.weapons import Pylon, Weapon, WeaponGroup, WeaponType

if TYPE_CHECKING:
    from game.ato.flight import Flight
    from game.ato.loadouts import Loadout

#: Equipment, not ammunition. A squadron does not run out of targeting pods and
#: start hanging missiles on the pod station, which is exactly what these
#: groups' cross-family fallbacks would do.
PROTECTED_TYPES = frozenset(
    {
        WeaponType.TGP,
        WeaponType.JAMMER,
        WeaponType.OFFENSIVE_JAMMER,
        WeaponType.DECOY,
    }
)

#: Ladders are long (AIM-120D reaches AIM-9B in 12 rungs). Past a few rungs the
#: substitution stops reading as "old stock" and starts reading as a bug.
MAX_DEPTH = 3

#: Module-level so tests can seed it, matching the §17/§50 convention.
_RNG = random.Random()


def attrition_pressure(settings: object, turn: int) -> float:
    """Chance that a flight reaches for older stock, as of `turn`.

    Turn 1 is `stock_attrition_start`; each turn adds `stock_attrition_per_turn`
    until `stock_attrition_max`. All three are authored as whole percents.
    """
    start = getattr(settings, "stock_attrition_start", 0) / 100
    per_turn = getattr(settings, "stock_attrition_per_turn", 0) / 100
    ceiling = getattr(settings, "stock_attrition_max", 0) / 100
    elapsed = max(0, turn - 1)
    return max(0.0, min(ceiling, start + per_turn * elapsed))


def roll_depth(pressure: float, rng: Optional[random.Random] = None) -> int:
    """How many rungs down the ladder this flight is flying.

    Geometric in `pressure`: each additional rung needs another hit, so depth 1
    is common, depth 3 rare, and both get likelier as the campaign wears on.
    """
    rng = rng or _RNG
    depth = 0
    while depth < MAX_DEPTH and rng.random() < pressure:
        depth += 1
    return depth


def _older_group(group: WeaponGroup, depth: int) -> WeaponGroup:
    """Walk down to `depth` provably-older rungs, hopping over newer ones.

    A rung is only ever *taken* when it is provably older than the deepest rung
    accepted so far, so the result can never be newer than `group`. That guard is
    load-bearing, because `fallback` answers "what do I use instead when this is
    unavailable" -- a DATE-GATING answer, which is **not** monotonic in year.
    **18 same-category fallbacks in the shipped data point at a newer weapon**, and
    date gating cannot catch it: in a 1991 campaign `AGM-65E` and `AGM-65F` are
    both legal, so an unguarded walk silently *upgrades* the flight.

    A newer rung is **skipped, not treated as the end of the ladder** -- keep
    walking past it. Stopping dead there loses real depth, and the rung on the
    far side is usually the one actually wanted:

    * `2xAIM-120B` (1994) -> ~~AIM-120C (2018)~~ -> **AIM-120B** (1994): the
      single rail of the same generation. Fewer missiles, not newer ones -- which
      is exactly what that yaml's "if we've run out of doubles, start over with
      the singles" was reaching for.
    * `AGM-65E` (1985) -> ~~AGM-65G, AGM-65F~~ -> **AGM-65B** (1975).

    Worth +15 groups of usable depth over stopping (191 -> 206) at zero upgrade
    paths. An undated rung is unprovable, so it ends the walk; `seen` guards
    against a fallback cycle.
    """
    category = getattr(group, "category", None)
    # A save written before WeaponGroup.category existed restores groups without
    # it; treat unknown as "do not cross" rather than guessing.
    if category is None or group.introduction_year is None:
        return group

    current = group
    probe = group
    seen = {group.name}
    taken = 0
    while taken < depth:
        older = probe.fallback
        if older is None or older.name in seen:
            break
        seen.add(older.name)
        if getattr(older, "category", None) != category:
            break
        probe = older
        older_year = older.introduction_year
        if older_year is None:
            break
        current_year = current.introduction_year
        assert current_year is not None  # `current` only ever holds dated groups
        if older_year > current_year:
            continue  # newer -- hop over it and keep looking
        current = older
        taken += 1
    return current


def _substitute(weapon: Weapon, pylon: Pylon, depth: int) -> Optional[Weapon]:
    """The oldest same-family weapon within `depth` rungs that fits this pylon."""
    if weapon.weapon_group.type in PROTECTED_TYPES:
        return None
    # Try the requested depth first, then shallower, so a flight that cannot go
    # three rungs deep on this station still goes as deep as it can.
    for attempt in range(depth, 0, -1):
        group = _older_group(weapon.weapon_group, attempt)
        if group is weapon.weapon_group:
            continue
        for candidate in group.weapons:
            if pylon.can_equip(candidate):
                return candidate
    return None


def degrade_loadout_for_stock(
    loadout: Loadout,
    flight: Flight,
    rng: Optional[random.Random] = None,
) -> Loadout:
    """Return `loadout` aged by a per-flight roll, or the original untouched.

    Guarded at every step: the feature off, a custom loadout, a turn-1 zero
    pressure, a depth roll of 0, or a loadout with nothing substitutable all
    return the input object unchanged.
    """
    try:
        game = flight.coalition.game
    except AttributeError:  # a duck-typed flight in a test harness
        return loadout

    settings = game.settings
    if not getattr(settings, "stock_attrition", False):
        return loadout
    if loadout.is_custom:
        return loadout

    pressure = attrition_pressure(settings, game.turn)
    if pressure <= 0:
        return loadout

    depth = roll_depth(pressure, rng)
    if depth <= 0:
        return loadout

    unit_type = flight.unit_type
    new_pylons = dict(loadout.pylons)
    substituted = False
    for number, weapon in loadout.pylons.items():
        if weapon is None:
            continue
        try:
            pylon = Pylon.for_aircraft(unit_type, number)
        except (KeyError, IndexError, AttributeError):
            continue
        older = _substitute(weapon, pylon, depth)
        if older is not None:
            new_pylons[number] = older
            substituted = True

    if not substituted:
        return loadout

    logging.debug(
        "Stock attrition: %s %s aged %d rung(s) at turn %d (pressure %.2f)",
        flight.unit_type.dcs_unit_type.id,
        loadout.name,
        depth,
        game.turn,
        pressure,
    )
    from game.ato.loadouts import Loadout as _Loadout

    return _Loadout(
        loadout.name,
        new_pylons,
        date=loadout.date,
        is_custom=loadout.is_custom,
        pylon_settings=loadout.pylon_settings.copy(),
    )
