"""Carrier CP naming stays consistent with the hull that actually sails.

The 2026-07-17 Scenic Route Merged fly surfaced the mismatch: the CP was named
"CVN-74 John C. Stennis" from the faction pool, but the supercarrier upgrade
(keyed by CP name) had no entry for that name and fell through to CVN_71 -- so
the boat sailed as a Roosevelt, and the §65 hull card named the flagship (and
its TACAN, 71X TRO) after a different ship than the ATO/briefing called it.

``hull_consistent_carrier_name`` closes it at naming time: a supercarrier game
only deals a Stennis-hull boat a name the upgrade map knows (the name then
picks WHICH supercarrier), and a non-supercarrier game (or an LHA) prefers the
pool name matching the hull's own display name. The pool remains the fallback
so flavored faction pools keep working.
"""

from __future__ import annotations

from dcs.ships import CVN_71, CVN_72, CVN_75, LHA_Tarawa, Stennis

from game.theater.controlpoint import (
    NavalControlPoint,
    STENNIS_SUPERCARRIER_UPGRADES,
)
from game.theater.start_generator import hull_consistent_carrier_name

USN_POOL = [
    "CVN-71 Theodore Roosevelt",
    "CVN-72 Abraham Lincoln",
    "CVN-73 George Washington",
    "CVN-74 John C. Stennis",
    "CVN-75 Harry S. Truman",
]


def test_supercarrier_game_never_deals_the_unmapped_stennis_name() -> None:
    # Every draw must come from the upgrade map -- "CVN-74 John C. Stennis" has
    # no supercarrier model of its own and would sail a mislabeled CVN-71.
    for _ in range(50):
        name = hull_consistent_carrier_name(USN_POOL, Stennis, supercarrier=True)
        assert name in STENNIS_SUPERCARRIER_UPGRADES, name


def test_supercarrier_pool_without_mapped_names_falls_back_to_the_pool() -> None:
    pool = ["CVN-74 John C. Stennis"]
    assert (
        hull_consistent_carrier_name(pool, Stennis, supercarrier=True)
        == "CVN-74 John C. Stennis"
    )


def test_free_hull_prefers_its_own_identity() -> None:
    # Supercarrier off: the free Stennis hull IS CVN-74.
    assert (
        hull_consistent_carrier_name(USN_POOL, Stennis, supercarrier=False)
        == "CVN-74 John C. Stennis"
    )


def test_lha_prefers_the_tarawa_name_over_the_saipan_flavor() -> None:
    pool = ["LHA-2 Saipan", "LHA-1 Tarawa"]
    assert (
        hull_consistent_carrier_name(pool, LHA_Tarawa, supercarrier=False)
        == "LHA-1 Tarawa"
    )
    # The setting is irrelevant for a hull with no supercarrier branch.
    assert (
        hull_consistent_carrier_name(pool, LHA_Tarawa, supercarrier=True)
        == "LHA-1 Tarawa"
    )


def test_pool_without_the_hull_name_stays_a_pool_pick() -> None:
    pool = ["LHA-2 Saipan", "LHA-4 Nassau"]
    assert hull_consistent_carrier_name(pool, LHA_Tarawa, supercarrier=False) in pool


def test_upgrade_map_refactor_keeps_the_legacy_mapping() -> None:
    up = NavalControlPoint.upgrade_to_supercarrier
    assert up(Stennis, "CVN-72 Abraham Lincoln") is CVN_72
    assert up(Stennis, "Carrier Strike Group 8") is CVN_75
    # Unmapped names keep the legacy CVN-71 fallback (existing saves keep the
    # boat they have been sailing; new games avoid the mismatch at naming time).
    assert up(Stennis, "CVN-74 John C. Stennis") is CVN_71
    assert up(LHA_Tarawa, "LHA-1 Tarawa") is LHA_Tarawa
