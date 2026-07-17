"""Weather-aware auto-planning (§67).

The §47 continuous clock gave the campaign an evolving sky, but the theater
commander never read it: the planner happily fragged TARPS photo recon into a
thunderstorm and led its offensive plan with low-level visual attack in weather
that grounds it. This module is the read -- a couple of pure classifiers over
``game.conditions`` plus the two planner couplings:

1. **Recon stays home in the weather.** The optional auto-added TARPS bird
   (Strike/DEAD BDA pass, the Armed Recon overwatch drone) is suppressed while
   it is raining or storming -- cameras (optical *and* IR) photograph cloud
   deck, so the sortie banks nothing. Player-planned recon is never touched;
   this only gates the automatic add-on flight.
2. **Storms demote low-level visual attack.** In a thunderstorm the offensive
   HTN methods that live at low level under the weather -- front-line CAS,
   battle-position BAI, convoy interdiction -- are moved to the tail of the
   offensive order (soft demotion, the §40/§55 emphasis discipline: nothing is
   removed, the planner still services them if jets are left after the
   weather-tolerant taskings claim theirs).

Both couplings apply to BOTH coalitions -- it is the same sky. Night awareness
is deliberately absent: the model carries no per-airframe night-capability
data, so demoting night CAS would wrongly ground an A-10C II alongside an A-1.

Gated by ``weather_aware_planning`` (default ON -- clear skies are a
byte-identical no-op, so the gate only matters while the weather is actually
bad). Every read is getattr-guarded so headless fakes and old saves degrade to
"clear".
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from game.weather.weather import Raining, Thunderstorm

if TYPE_CHECKING:
    from game import Game

#: The offensive HTN root methods (by PlanNextAction factory name) that model
#: low-level visual attack -- the taskings a thunderstorm pushes to the back of
#: the line. Strike/OCA/ships/IADS keep their place: they are flown on
#: coordinates and sensors, and demoting DegradeIads would starve SEAD in
#: exactly the weather that grounds nobody's HARMs.
VISUAL_ATTACK_METHODS: tuple[str, ...] = (
    "InterdictReinforcements",
    "AttackBattlePositions",
    "PlanFrontLineCas",
)


def _enabled(game: "Game") -> bool:
    return bool(getattr(game.settings, "weather_aware_planning", False))


def _weather(game: "Game") -> object:
    conditions = getattr(game, "conditions", None)
    return getattr(conditions, "weather", None)


def poor_visibility_weather(game: "Game") -> bool:
    """True in rain or thunderstorm -- the camera-blind sky."""
    return isinstance(_weather(game), (Raining, Thunderstorm))


def storm(game: "Game") -> bool:
    """True in a thunderstorm -- the sky that grounds low-level visual attack."""
    return isinstance(_weather(game), Thunderstorm)


def recon_suppressed(game: "Game") -> bool:
    """Should the automatic TARPS add-on stay home this turn?

    True only when the feature is on and the sky is rain/storm. The caller
    (``PackageFulfiller._maybe_plan_tarps_recon``) treats True as "omit the
    optional recon flight" -- never a scrub, exactly like a missing squadron.
    """
    return _enabled(game) and poor_visibility_weather(game)


def demote_weather_hostile_methods(game: "Game", order: Iterable[str]) -> list[str]:
    """Reorder the offensive method names for the weather.

    In a thunderstorm (feature on), the low-level visual-attack methods move to
    the tail in their existing relative order; everything else keeps its place.
    Any other sky returns the order unchanged, so clear weather is
    byte-identical to the pre-feature planner.
    """
    ordered = list(order)
    if not _enabled(game) or not storm(game):
        return ordered
    kept = [name for name in ordered if name not in VISUAL_ATTACK_METHODS]
    demoted = [name for name in ordered if name in VISUAL_ATTACK_METHODS]
    return kept + demoted
