"""Command-center decapitation -> degraded enemy planning (§52, C2 family Feature A).

The IADS **command center** is a TGO the model already tracks (`category ==
"commandcenter"`, `IadsRole.COMMAND_CENTER`), but its only gameplay was inside
MANTIS's runtime SAM-autonomy graph -- nothing coupled it to the campaign's
*planning*. So "bomb the enemy HQ" was a strike checkbox, not a strategic move.

This couples a side's **auto-planner quality to its own command-network health**:
as a coalition's command centers are destroyed, its offensive target selection
gets sloppier -- the effective planner unpredictability (§17) is scaled up in
proportion to how decapitated the C2 network is, so a headless HQ services worse
targets and hits the same things less reliably. Reactive defensive tasking is
untouched (the §17 boundary -- a decapitated enemy still defends itself; it just
plans worse *offense*).

Pure turn-model: no `.miz` change, no Lua, no DCS integration. Symmetric in code
(each side reads its own C2 health), but only a side with an HTN auto-planner is
affected in practice. Gated by ``c2_decapitation_effects`` (default off); a
fully-intact network (or a campaign with no command centers) is a byte-identical
no-op, so the deterministic planner and its tests are preserved.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from game import Game
    from game.coalition import Coalition
    from game.settings import Settings
    from game.theater import ConflictTheater, Player

#: The TGO category that is the command network. Deliberately ONLY the command
#: centers -- comms/power nodes are MANTIS's runtime SAM concern (Feature B),
#: never the planning coupling.
C2_CATEGORY = "commandcenter"

#: Extra planner unpredictability (percentage points) added when a side's command
#: network is *fully* decapitated, layered on top of its base
#: ``*_planner_unpredictability``. Scales linearly with the dead fraction, then
#: the sum is clamped to the 0-100 range the shuffler expects.
MAX_DECAP_UNPREDICTABILITY = 60

#: §52 Phase A2 (the package-count throttle): the offensive package ceiling a
#: side's planner works under while its command network is degraded. At full C2
#: health there is no ceiling; as command centers fall the cap shrinks linearly
#: from this value toward MIN_OFFENSIVE_PACKAGES. 12 sits above what the HTN
#: typically frags even on a large campaign, so a barely-scratched network (one
#: of many CCs down) rarely bites, while a decapitated one visibly thins the
#: air tasking order.
FULL_OFFENSIVE_PACKAGE_CAP = 12

#: The A2 floor: a decapitated enemy still plans *some* offense -- the goal is
#: pressure, not a walkover (the design note's "never zero red out" guardrail).
MIN_OFFENSIVE_PACKAGES = 2


def _command_centers(
    coalition: "Coalition", theater: "ConflictTheater"
) -> Tuple[int, int]:
    """(alive, total) command-center TGO count over the coalition's own bases.

    A command center counts as alive while any of its units is alive (the same
    aliveness test the IADS emitter uses)."""
    alive = 0
    total = 0
    for cp in theater.controlpoints:
        if cp.captured is not coalition.player:
            continue
        for tgo in cp.ground_objects:
            if getattr(tgo, "category", None) != C2_CATEGORY:
                continue
            total += 1
            if any(
                getattr(u, "alive", False)
                for g in getattr(tgo, "groups", [])
                for u in getattr(g, "units", [])
            ):
                alive += 1
    return alive, total


def c2_health(coalition: "Coalition", theater: "ConflictTheater") -> float:
    """Fraction (0..1) of the coalition's command centers still operational.

    1.0 when the side fields no command centers (nothing to decapitate), so a
    C2-less campaign is unaffected."""
    alive, total = _command_centers(coalition, theater)
    if total == 0:
        return 1.0
    return alive / total


def unpredictability_bonus(
    coalition: "Coalition", theater: "ConflictTheater", settings: "Settings"
) -> int:
    """Extra planner unpredictability from this coalition's decapitated C2.

    0 when the feature is off or the network is intact -- so the returned value
    is added to the base setting and the whole thing degrades gracefully to
    today's behavior."""
    if not getattr(settings, "c2_decapitation_effects", False):
        return 0
    health = c2_health(coalition, theater)
    return round((1.0 - health) * MAX_DECAP_UNPREDICTABILITY)


def offensive_package_cap(
    coalition: "Coalition", theater: "ConflictTheater", settings: "Settings"
) -> Optional[int]:
    """The offensive package ceiling for this side, or None for no ceiling.

    §52 Phase A2: a headless HQ generates fewer offensive taskings. The cap
    shrinks linearly with the dead command-center fraction, floored at
    MIN_OFFENSIVE_PACKAGES so red always plans some offense. None (no throttle)
    when the feature is off, the network is intact, or the side fields no
    command centers -- so the planner is byte-identical to today until a CC
    actually falls. Reactive defensive tasking is never throttled (the §17
    boundary); the consumer applies this only to the HTN's offensive middle.
    """
    if not getattr(settings, "c2_decapitation_effects", False):
        return None
    health = c2_health(coalition, theater)
    if health >= 1.0:
        return None
    return max(MIN_OFFENSIVE_PACKAGES, round(FULL_OFFENSIVE_PACKAGE_CAP * health))


def c2_status_line(game: "Game", player: "Player") -> Optional[str]:
    """A one-line SITREP descriptor of a side's command-network status.

    None when the feature is off, the side fields no command centers, or the
    network is fully intact (nothing to report). Counts are the player's own
    BDA claim, framed as claimed by the SITREP that renders this."""
    if not getattr(game.settings, "c2_decapitation_effects", False):
        return None
    coalition = game.coalition_for(player)
    alive, total = _command_centers(coalition, game.theater)
    if total == 0 or alive >= total:
        return None
    return f"{alive}/{total} command posts operational"
