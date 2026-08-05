"""GPS jamming (§85) -- the campaign side.

Pins the site model (which units jam, how far, whose weapons), the recon fog on
the kneeboard brief, and the curated weapon list's hard exclusions: a laser, TV
or IR weapon must never be jammable, because a Paveway that mysteriously misses
reads as a bug rather than as a feature.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import pytest

from game.dcs.groundunittype import GpsJammingProperties
from game.fourteenth.gps_jamming import (
    DEFAULT_MISS_RADIUS,
    DEFAULT_REACH,
    GPS_GUIDED_WEAPON_PATTERNS,
    briefed_jammer_areas,
    gps_jammer_sites,
)
from game.utils import meters, nautical_miles

# -- test doubles -------------------------------------------------------------


@dataclass
class FakePlayer:
    is_blue: bool


@dataclass
class FakePoint:
    x: float
    y: float


class FakeUnitType:
    def __init__(self, gps_jamming: Optional[GpsJammingProperties]) -> None:
        self.gps_jamming = gps_jamming


class FakeUnit:
    def __init__(
        self, alive: bool = True, jams: Optional[GpsJammingProperties] = None
    ) -> None:
        self.alive = alive
        self.unit_type = FakeUnitType(jams)


class FakeGroup:
    def __init__(self, group_name: str, units: list[FakeUnit]) -> None:
        self.group_name = group_name
        self.units = units


class FakeTgo:
    def __init__(
        self,
        name: str,
        groups: list[FakeGroup],
        position: FakePoint,
        known: bool = True,
    ) -> None:
        self.name = name
        self.groups = groups
        self.position = position
        self._known = known

    def known_for(self, viewer: Any) -> bool:
        return self._known


class FakeControlPoint:
    def __init__(self, captured: FakePlayer, ground_objects: list[FakeTgo]) -> None:
        self.captured = captured
        self.ground_objects = ground_objects


class FakeTheater:
    def __init__(self, controlpoints: list[FakeControlPoint]) -> None:
        self.controlpoints = controlpoints


class FakeSettings:
    def __init__(self, **kwargs: Any) -> None:
        self.gps_jamming = True
        self.gps_jamming_default_reach_nm = 30.0
        self.gps_jamming_miss_radius_m = 200.0
        self.__dict__.update(kwargs)


class FakeGame:
    def __init__(self, theater: FakeTheater, settings: FakeSettings) -> None:
        self.theater = theater
        self.settings = settings


BLUE = FakePlayer(is_blue=True)
RED = FakePlayer(is_blue=False)


def _jammer_tgo(
    name: str = "Haina jammer",
    *,
    props: Optional[GpsJammingProperties] = None,
    alive: bool = True,
    known: bool = True,
    extra_units: Optional[list[FakeUnit]] = None,
) -> FakeTgo:
    units = [FakeUnit(alive=alive, jams=props or GpsJammingProperties())]
    units.extend(extra_units or [])
    return FakeTgo(
        name, [FakeGroup(name + " grp", units)], FakePoint(100.0, 200.0), known
    )


def _game(tgos: list[FakeTgo], owner: FakePlayer = RED, **settings: Any) -> FakeGame:
    return FakeGame(
        FakeTheater([FakeControlPoint(owner, tgos)]), FakeSettings(**settings)
    )


# -- the site model -----------------------------------------------------------


def test_a_unit_with_the_yaml_block_is_a_jammer_on_the_campaign_defaults() -> None:
    sites = gps_jammer_sites(_game([_jammer_tgo()]))  # type: ignore[arg-type]
    assert len(sites) == 1
    site = sites[0]
    assert site.coalition == "red"
    assert site.reach == nautical_miles(30)
    assert site.miss_radius == meters(200)
    assert site.group_names == ("Haina jammer grp",)


def test_a_unit_without_the_block_never_jams() -> None:
    ordinary = FakeTgo(
        "Motor pool",
        [FakeGroup("Motor pool grp", [FakeUnit(jams=None)])],
        FakePoint(0.0, 0.0),
    )
    assert gps_jammer_sites(_game([ordinary])) == []  # type: ignore[arg-type]


def test_a_dead_jammer_stops_denying_gps() -> None:
    """The whole reward for finding and striking the site."""
    assert gps_jammer_sites(_game([_jammer_tgo(alive=False)])) == []  # type: ignore[arg-type]


def test_the_unit_definition_overrides_the_campaign_defaults() -> None:
    props = GpsJammingProperties(radius_nm=60.0, miss_radius_m=450.0)
    site = gps_jammer_sites(_game([_jammer_tgo(props=props)]))[0]  # type: ignore[arg-type]
    assert site.reach == nautical_miles(60)
    assert site.miss_radius == meters(450)


def test_a_mixed_site_takes_the_strongest_emitter_present() -> None:
    weak = GpsJammingProperties(radius_nm=20.0, miss_radius_m=100.0)
    strong = GpsJammingProperties(radius_nm=80.0, miss_radius_m=600.0)
    tgo = _jammer_tgo(props=weak, extra_units=[FakeUnit(jams=strong)])
    site = gps_jammer_sites(_game([tgo]))[0]  # type: ignore[arg-type]
    assert site.reach == nautical_miles(80)
    assert site.miss_radius == meters(600)


def test_a_blue_owned_jammer_is_emitted_as_blue() -> None:
    """Symmetric by construction -- the runtime degrades the OTHER side's weapons."""
    site = gps_jammer_sites(_game([_jammer_tgo()], owner=BLUE))[0]  # type: ignore[arg-type]
    assert site.coalition == "blue"


def test_the_feature_off_emits_nothing() -> None:
    game = _game([_jammer_tgo()], gps_jamming=False)
    assert gps_jammer_sites(game) == []  # type: ignore[arg-type]


def test_defaults_apply_when_the_settings_are_absent_entirely() -> None:
    """An old save predating the knobs must still produce a usable site."""
    game = _game([_jammer_tgo()])
    del game.settings.gps_jamming_default_reach_nm
    del game.settings.gps_jamming_miss_radius_m
    site = gps_jammer_sites(game)[0]  # type: ignore[arg-type]
    assert site.reach == DEFAULT_REACH
    assert site.miss_radius == DEFAULT_MISS_RADIUS


# -- the briefing is recon-fogged ---------------------------------------------


def test_an_unscouted_jammer_is_not_briefed() -> None:
    game = _game([_jammer_tgo(known=False)])
    # The runtime still jams -- it works off ground truth, not the player's intel.
    assert gps_jammer_sites(game)  # type: ignore[arg-type]
    assert briefed_jammer_areas(game, BLUE) == []  # type: ignore[arg-type]


def test_a_scouted_enemy_jammer_is_briefed() -> None:
    game = _game([_jammer_tgo(known=True)])
    briefed = briefed_jammer_areas(game, BLUE)  # type: ignore[arg-type]
    assert [site.name for site in briefed] == ["Haina jammer"]


def test_a_friendly_jammer_is_never_briefed_as_a_threat() -> None:
    game = _game([_jammer_tgo()], owner=BLUE)
    assert briefed_jammer_areas(game, BLUE) == []  # type: ignore[arg-type]
    # ...but it IS a threat to the other side.
    assert [s.name for s in briefed_jammer_areas(game, RED)] == ["Haina jammer"]  # type: ignore[arg-type]


# -- the curated weapon list --------------------------------------------------


@pytest.mark.parametrize(
    "weapon",
    ["GBU-31", "GBU-38", "GBU-54", "AGM-154C", "AGM-158", "AGM-84H", "KAB-500S"],
)
def test_satellite_guided_stores_are_covered(weapon: str) -> None:
    assert any(
        pattern.lower() in weapon.lower() for pattern in GPS_GUIDED_WEAPON_PATTERNS
    ), f"{weapon} should be jammable"


@pytest.mark.parametrize(
    "weapon",
    [
        "GBU-12",  # laser
        "GBU-10",  # laser
        "GBU-24",  # laser
        "AGM-65D",  # IR Maverick
        "AGM-65E",  # laser Maverick
        "AGM-88C",  # anti-radiation
        "AGM-84D",  # active-radar Harpoon
        "Mk_82",  # unguided
        "CBU-87",  # unguided dispenser
        "KAB_500Kr",  # TV
        "BGM_109B",  # §63's ship-launched cruise missile -- deliberately out of scope
        "AIM_120C",  # a2a
    ],
)
def test_non_gps_weapons_are_never_jammable(weapon: str) -> None:
    """The load-bearing exclusion. A laser/TV/IR/ARM weapon that mysteriously
    misses is a bug report, not a feature -- and §63/§81 cruise missiles are
    their own flown features, deliberately left alone."""
    matched = [
        pattern
        for pattern in GPS_GUIDED_WEAPON_PATTERNS
        if pattern.lower() in weapon.lower()
    ]
    assert not matched, f"{weapon} must not be jammable (matched {matched})"


# -- the unit-definition parser ----------------------------------------------


def test_an_empty_block_is_a_jammer_on_defaults() -> None:
    props = GpsJammingProperties.from_data({})
    assert props == GpsJammingProperties(radius_nm=None, miss_radius_m=None)


def test_a_bare_true_block_is_a_jammer() -> None:
    assert GpsJammingProperties.from_data(True) == GpsJammingProperties()


def test_no_block_is_not_a_jammer() -> None:
    assert GpsJammingProperties.from_data(None) is None
    assert GpsJammingProperties.from_data(False) is None


def test_a_malformed_block_degrades_instead_of_crashing_new_game() -> None:
    assert GpsJammingProperties.from_data("yes please") is None
    assert (
        GpsJammingProperties.from_data({"radius_nm": "far"}) == GpsJammingProperties()
    )


def test_the_yaml_block_reaches_the_loaded_unit_type() -> None:
    """The wiring, on the real loader path: a unit definition carrying the block
    comes out of ``_variant_from_dict`` as a jammer, one without it does not.

    This is the contract a unit author relies on -- adding a jammer must be a
    data edit, with no id list in Python to touch.
    """
    from dcs.vehicles import Unarmed

    from game.dcs.groundunittype import GroundUnitType

    jammer = GroundUnitType._variant_from_dict(
        Unarmed.Ural_375,
        "Test jammer",
        {"class": "Fortification", "gps_jamming": {"radius_nm": 45}},
    )
    assert jammer.gps_jamming == GpsJammingProperties(radius_nm=45.0)

    ordinary = GroundUnitType._variant_from_dict(
        Unarmed.Ural_375, "Test truck", {"class": "Logistics"}
    )
    assert ordinary.gps_jamming is None
