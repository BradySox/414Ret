"""Player-facing lines for bases the enemy has cut off (§90 rung A, seam 5).

The supply tier decides whether a base recovers strength at all -- in full, at a
quarter, or not until the route is reopened. It had no surface anywhere, so a
player whose base stopped rebuilding had no way to find out why. An invisible
consequential mechanic is a fairness problem, not a polish one.

Says nothing when everything is supplied, which is the normal state: a healthy
theatre must not spend a SITREP line saying so.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.theater.player import Player
from game.theater.supply import SupplyStatus, supply_statuses

if TYPE_CHECKING:
    from game import Game


def supply_sitrep_lines(game: Game) -> list[str]:
    """One line per blue base that cannot be reinforced normally."""
    if not game.settings.supply_gated_reinforcement:
        return []
    points = game.theater.control_points_for(Player.BLUE)
    statuses = supply_statuses(points, game.blue.transit_network)

    isolated = sorted(
        cp.name for cp, s in statuses.items() if s is SupplyStatus.ISOLATED
    )
    airlifted = sorted(
        cp.name for cp, s in statuses.items() if s is SupplyStatus.AIRLIFTED
    )

    lines = []
    if isolated:
        lines.append(f"Cut off, not being reinforced: {', '.join(isolated)}")
    if airlifted:
        lines.append(f"Air resupply only, rebuilding slowly: {', '.join(airlifted)}")
    return lines
