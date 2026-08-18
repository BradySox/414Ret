"""The clause every fog rule opens with, and the one place it now lives.

`alive_for`, `known_for` and `hidden_on_player_map` each began with an identical
three-clause guard -- omniscient viewer, overview on, or looking at your own side
-- and each spelled it out again. It is now `viewer_sees_truth`.

Also pins an inconsistency the de-duplication surfaced but deliberately did NOT
change: see `test_map_hidden_site_can_read_hidden_and_known_at_once`.
"""

from __future__ import annotations

from typing import Any, cast

from game.theater.fogofwar import set_fog_revealed, viewer_sees_truth
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


def test_map_hidden_site_can_read_hidden_and_known_at_once() -> None:
    """Documented oddity, deliberately left alone.

    `hidden_on_player_map` short-circuits on `map_hidden`; `known_for` never
    consults it. So a §50 ambush team that a strike marked `discovered_by_player`
    reads hidden AND known simultaneously -- the site is invisible on the map
    while the composition layer believes the player knows what is there.

    Merging the two booleans into one three-state (HIDDEN / UNKNOWN / KNOWN)
    would make this unrepresentable, and is the natural next step. It is a
    BEHAVIOUR CHANGE in a load-bearing fog layer, so it is not being smuggled
    into a de-duplication. This test exists so the oddity is visible and any
    change to it is deliberate; update it together with that decision.
    """
    site = _enemy_site(map_hidden=True, discovered=True)

    assert site.hidden_on_player_map(Player.BLUE) is True
    assert site.known_for(Player.BLUE) is True  # <- the contradiction


def test_an_ordinary_undiscovered_site_is_visible_but_unknown() -> None:
    """The normal case, for contrast: a marker you can see but not read."""
    site = _enemy_site(map_hidden=False, discovered=False)

    assert site.hidden_on_player_map(Player.BLUE) is False
    assert site.known_for(Player.BLUE) is False
