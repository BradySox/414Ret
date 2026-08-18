"""The clause every fog rule opens with, and the one place it now lives.

`alive_for`, `known_for` and `hidden_on_player_map` each began with an identical
three-clause guard -- omniscient viewer, overview on, or looking at your own side
-- and each spelled it out again. It is now `viewer_sees_truth`.

Also pins an inconsistency the de-duplication surfaced but deliberately did NOT
change: see `test_map_hidden_site_can_read_hidden_and_known_at_once`.
"""

from __future__ import annotations

from typing import Any, cast

from game.theater.fogofwar import Visibility, set_fog_revealed, viewer_sees_truth
from game.theater.player import Player


class FakeGroundObject:
    def __init__(self, friendly_to: Player | None) -> None:
        self._friendly_to = friendly_to

    def is_friendly(self, viewer: Player) -> bool:
        return viewer is self._friendly_to


def _owner(friendly_to: Player | None = None) -> Any:
    return cast(Any, FakeGroundObject(friendly_to))


def test_the_omniscient_viewer_always_sees_truth() -> None:
    """AI, planner and threat math pass viewer=None and must never be fogged."""
    assert viewer_sees_truth(None, _owner()) is True


def test_a_side_sees_its_own() -> None:
    assert viewer_sees_truth(Player.BLUE, _owner(friendly_to=Player.BLUE)) is True


def test_an_enemy_viewer_does_not() -> None:
    assert viewer_sees_truth(Player.BLUE, _owner(friendly_to=Player.RED)) is False


def test_the_overview_forces_truth_for_anyone() -> None:
    owner = _owner(friendly_to=Player.RED)
    assert viewer_sees_truth(Player.BLUE, owner) is False
    try:
        set_fog_revealed(True)
        assert viewer_sees_truth(Player.BLUE, owner) is True
    finally:
        # Process-global; leaking it would god-view every later test.
        set_fog_revealed(False)
    assert viewer_sees_truth(Player.BLUE, owner) is False


def test_is_friendly_is_not_called_without_a_viewer() -> None:
    """It needs a real viewer, so the guard must short-circuit before it."""

    class Exploding:
        def is_friendly(self, viewer: Player) -> bool:
            raise AssertionError("is_friendly called with no viewer")

    assert viewer_sees_truth(None, cast(Any, Exploding())) is True


# --- the inconsistency the de-duplication surfaced, pinned but NOT changed ---


class _Settings:
    scar_command_post_intel = False
    recon_intel_fog = True


def _enemy_site(*, map_hidden: bool, discovered: bool) -> Any:
    """A real TheaterGroundObject with only what the two fog rules read.

    TheaterGroundObject is abstract, so this pins the concrete subclass the §50
    ambush teams actually use.
    """
    from game.theater.theatergroundobject import VehicleGroupGroundObject

    site = object.__new__(VehicleGroupGroundObject)
    site.map_hidden = map_hidden
    site.discovered_by_player = discovered
    site.category = "armor"
    site.control_point = cast(
        Any,
        type(
            "CP",
            (),
            {
                "captured": Player.RED,
                "is_friendly": staticmethod(lambda p: p is Player.RED),
                "coalition": type(
                    "Coalition",
                    (),
                    {"game": type("Game", (), {"settings": _Settings()})()},
                )(),
            },
        )(),
    )
    return site


def test_a_hidden_site_is_no_longer_also_known() -> None:
    """The contradiction this model was built to remove.

    Before the three-state merge, `hidden_on_player_map` short-circuited on
    `map_hidden` while `known_for` never consulted it -- so a §50 ambush team
    that a strike had marked `discovered_by_player` read hidden AND known at
    once: invisible on the map, while the composition layer believed the player
    knew what was there.

    This is the one deliberate BEHAVIOUR CHANGE of the merge. `known_for` on a
    `map_hidden` site now returns False for an enemy viewer whatever else is
    true of it. A site you cannot see cannot be a site whose composition you
    know.
    """
    site = _enemy_site(map_hidden=True, discovered=True)

    assert site.visibility_for(Player.BLUE) is Visibility.HIDDEN
    assert site.hidden_on_player_map(Player.BLUE) is True
    assert site.known_for(Player.BLUE) is False


def test_an_ordinary_undiscovered_site_is_a_marker_you_cannot_read() -> None:
    site = _enemy_site(map_hidden=False, discovered=False)

    assert site.visibility_for(Player.BLUE) is Visibility.UNKNOWN
    assert site.hidden_on_player_map(Player.BLUE) is False
    assert site.known_for(Player.BLUE) is False


def test_a_scouted_site_is_known() -> None:
    site = _enemy_site(map_hidden=False, discovered=True)

    assert site.visibility_for(Player.BLUE) is Visibility.KNOWN
    assert site.hidden_on_player_map(Player.BLUE) is False
    assert site.known_for(Player.BLUE) is True


def test_the_owner_sees_its_own_site_whatever_the_flags() -> None:
    site = _enemy_site(map_hidden=True, discovered=False)

    assert site.visibility_for(Player.RED) is Visibility.KNOWN


def test_the_omniscient_view_is_never_fogged() -> None:
    """AI, planner and threat math must see every site, including ambushes."""
    site = _enemy_site(map_hidden=True, discovered=False)

    assert site.visibility_for(None) is Visibility.KNOWN
    assert site.hidden_on_player_map(None) is False
    assert site.known_for(None) is True


def test_hidden_and_known_can_no_longer_both_be_true() -> None:
    """The invariant the three-state buys, over every combination."""
    for map_hidden in (True, False):
        for discovered in (True, False):
            site = _enemy_site(map_hidden=map_hidden, discovered=discovered)
            hidden = site.hidden_on_player_map(Player.BLUE)
            known = site.known_for(Player.BLUE)
            assert not (hidden and known), (map_hidden, discovered)


def test_the_two_booleans_partition_the_three_states() -> None:
    """Every state maps to exactly one pair, so nothing is unreachable."""
    seen = set()
    for map_hidden in (True, False):
        for discovered in (True, False):
            site = _enemy_site(map_hidden=map_hidden, discovered=discovered)
            seen.add(site.visibility_for(Player.BLUE))
    assert seen == {Visibility.HIDDEN, Visibility.UNKNOWN, Visibility.KNOWN}
