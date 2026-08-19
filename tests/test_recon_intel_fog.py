"""Recon intel-fog: enemy site composition/rings hidden until discovered.

Covers the discovery gate (``known_for``), the omniscient/setting escape hatches,
and the save-migration default. What actually trips the gate -- a strike or an
offensive overflight, never recon -- is asserted in ``test_recon_reveal_rule.py``
where the mission-results fixtures already live.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from dcs.mapping import Point

from game.theater import Player
from game.theater.controlpoint import OffMapSpawn
from game.theater.presetlocation import PresetLocation
from game.theater.theatergroundobject import SamGroundObject
from game.utils import Heading


class _EnemySam(SamGroundObject):
    def is_friendly(self, to_player: Player) -> bool:
        return False


def _enemy_sam(*, fog: bool = True) -> SamGroundObject:
    location = PresetLocation(
        name="target",
        position=Point(0, 0, None),  # type: ignore[arg-type]
        heading=Heading(0),
    )
    control_point = OffMapSpawn(
        name="enemy-cp",
        position=Point(0, 0, None),  # type: ignore[arg-type]
        theater=None,  # type: ignore[arg-type]
        starts_blue=Player.RED,
    )
    tgo = _EnemySam(
        name="Enemy SAM",
        location=location,
        control_point=control_point,
        task=None,
    )
    # known_for() reaches control_point.coalition.game.settings.recon_intel_fog.
    tgo.control_point = cast(
        Any,
        SimpleNamespace(
            captured=Player.RED,  # sidc_status reads captured.is_neutral
            coalition=SimpleNamespace(
                game=SimpleNamespace(settings=SimpleNamespace(recon_intel_fog=fog))
            ),
        ),
    )
    return tgo


def test_enemy_site_unknown_until_discovered() -> None:
    tgo = _enemy_sam()
    # New enemy sites start unknown to the player...
    assert tgo.discovered_by_player is False
    assert tgo.known_for(Player.BLUE) is False
    # ...but the omniscient view (AI planner / threat math) always sees truth.
    assert tgo.known_for(None) is True
    # Once engaged (struck, or overflown by a ground-attack sortie), it is known
    # and stays known.
    tgo.discovered_by_player = True
    assert tgo.known_for(Player.BLUE) is True


def test_setting_off_reveals_everything() -> None:
    tgo = _enemy_sam(fog=False)
    assert tgo.discovered_by_player is False
    # With the master toggle off, nothing is fogged even when undiscovered.
    assert tgo.known_for(Player.BLUE) is True


def test_setting_defaults_on() -> None:
    from game.settings import Settings

    assert Settings().recon_intel_fog is True


def test_air_defense_band_from_role() -> None:
    from game.data.groups import GroupTask

    tgo = _enemy_sam()
    # Range band comes from the designated role, so it is available even unscouted.
    assert tgo.air_defense_band is None  # task=None in the fixture
    tgo.task = GroupTask.LORAD
    assert tgo.air_defense_band == "Long-range SAM"
    tgo.task = GroupTask.MERAD
    assert tgo.air_defense_band == "Medium-range SAM"
    tgo.task = GroupTask.FACTORY  # non air-defense role
    assert tgo.air_defense_band is None


def test_old_saves_migrate_to_discovered() -> None:
    tgo = _enemy_sam()
    state = dict(tgo.__dict__)
    state.pop("discovered_by_player", None)  # simulate a pre-feature save
    state.pop("_threat_poly", None)
    tgo.__setstate__(state)
    # An in-progress campaign keeps everything visible rather than blanking.
    assert tgo.discovered_by_player is True


def test_the_map_symbol_does_not_leak_condition_while_fogged() -> None:
    """The SIDC status digit is the symbol's *operational condition*, and milsymbol
    draws it as the bar under the icon. Shipping ground truth there told the player
    an un-engaged site was fully capable (green bar) — or destroyed — without their
    ever touching it. Regression: the BDA-lag removal collapsed `sidc_status_for`
    into a plain property and `sidc_for` kept using it."""
    from game.sidc import Status

    tgo = _enemy_sam()  # no groups, so ground truth is "destroyed"
    assert tgo.sidc_status is Status.PRESENT_DESTROYED
    # The fogged viewer must not learn that. Plain PRESENT draws no condition bar.
    assert tgo.sidc_for(Player.BLUE).status is Status.PRESENT
    # The omniscient view (AI, planner, threat math) is unaffected.
    assert tgo.sidc_for(None).status is Status.PRESENT_DESTROYED
    # Engaging the site hands over the real condition.
    tgo.discovered_by_player = True
    assert tgo.sidc_for(Player.BLUE).status is Status.PRESENT_DESTROYED
