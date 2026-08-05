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
from game import persistency
from game.data.units import UnitClass
from game.utils import meters, nautical_miles


@pytest.fixture()
def _layouts(tmp_path_factory: pytest.TempPathFactory) -> None:
    """ForceGroup/layout preset loading reads the DCS saved-game folder, which
    only exists once the app boots. Point it at an empty temp dir so loading
    falls back to the bundled resources/ presets."""
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


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
    _seq = 0

    def __init__(
        self, alive: bool = True, jams: Optional[GpsJammingProperties] = None
    ) -> None:
        self.alive = alive
        self.unit_type = FakeUnitType(jams)
        FakeUnit._seq += 1
        # The generator's real shape: "<zero-padded id> | <name>".
        self.unit_name = f"{FakeUnit._seq:04d} | GPS jammer"


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
    assert len(site.unit_names) == 1 and " | GPS jammer" in site.unit_names[0]


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


def test_the_shipped_ew_radio_jammers_are_the_feature_s_units() -> None:
    """The real tie-in, on real registered data (§85's `GPS_Spoofer_*` units).

    These are the vehicles the feature exists for, so their yamls must actually
    carry the block -- and their reach must be the unit's OWN declared
    `detection_range` (50 km), not an invented number, so the bubble matches what
    DCS says the vehicle can hear.
    """
    from game.dcs.groundunittype import GroundUnitType
    from game.utils import meters

    for variant in ("EW Radio Jammer (Red)", "EW Radio Jammer (Blue)"):
        unit = GroundUnitType.named(variant)
        assert unit.gps_jamming is not None, f"{variant} must declare gps_jamming"
        assert unit.gps_jamming.radius_nm is not None
        declared = unit.dcs_unit_type.detection_range
        reach = nautical_miles(unit.gps_jamming.radius_nm)
        # Within a nautical mile of the DCS-declared detection range.
        assert abs(reach.meters - declared) < meters(1852).meters, (
            f"{variant} jams to {reach.nautical_miles:.0f} nm but DCS declares "
            f"{declared} m of reach"
        )


def test_the_ewr_layout_carries_an_optional_jammer_slot(_layouts: None) -> None:
    """The RWR/HARM pairing (§86).

    A GPS jammer emits in L-band, which no RWR covers and no HARM homes on, so a
    lone jammer could only ever be found by recon. Parking it in the EWR site
    gives it a real always-on emitter to hide behind -- the site paints RWRs and
    takes HARMs like any other radar.

    The slot must be optional + fill: false, or every existing EWR site in every
    shipped campaign would start fielding jammers.
    """
    from game.layout import LAYOUTS

    LAYOUTS.initialize()
    layout = next(
        (lay for lay in LAYOUTS.layouts if lay.name == "Early-Warning Radar"), None
    )
    assert layout is not None, "the Early-Warning Radar layout must exist"

    slot = None
    for group in layout.groups:
        for unit_group in group.unit_groups:
            if unit_group.name == "GPS Jammer 0":
                slot = unit_group
    assert slot is not None, "the EWR layout must carry the jammer slot"
    assert slot.optional is True, "an existing EWR site must not be forced to jam"
    assert slot.fill is False, "faction fill must never drop a jammer into an EWR site"
    # The slot names a group that really exists in the shared .miz -- a slot
    # naming a missing group is SILENTLY dropped (the dead-config class of bug).
    assert len(slot.layout_units) >= 1, "the slot's .miz position group is missing"
    ids = {unit_type.id for unit_type in (slot.unit_types or [])}
    assert ids == {"GPS_Spoofer_Red", "GPS_Spoofer_Blue"}

    # The companion ARM-able emitter slot, under the same gate.
    radar_slot = None
    for group in layout.groups:
        for unit_group in group.unit_groups:
            if unit_group.name == "GPS Jammer Radar 0":
                radar_slot = unit_group
    assert radar_slot is not None, "the ARM-able emitter slot must exist"
    assert radar_slot.optional is True and radar_slot.fill is False
    assert len(radar_slot.layout_units) >= 1
    assert {unit_type.id for unit_type in (radar_slot.unit_types or [])} == {
        "RLS_19J6",
        "NASAMS_Radar_MPQ64F1",
    }


def test_each_jamming_site_preset_pairs_a_radar_with_its_own_sides_jammer(
    _layouts: None,
) -> None:
    """Each preset must field BOTH halves -- the emitter that makes the site
    huntable, and the jammer that makes it worth hunting -- and must not be able
    to reach the other coalition's jammer."""
    from game.armedforces.forcegroup import ForceGroup
    from game.layout import LAYOUTS

    LAYOUTS.initialize()
    for preset_name, own, other in (
        ("GPS Jamming Site (Red)", "GPS_Spoofer_Red", "GPS_Spoofer_Blue"),
        ("GPS Jamming Site (Blue)", "GPS_Spoofer_Blue", "GPS_Spoofer_Red"),
    ):
        group = ForceGroup.from_preset_group(preset_name)
        ids = {unit.dcs_unit_type.id for unit in group.units}
        assert own in ids, f"{preset_name} must field its own jammer"
        assert other not in ids, f"{preset_name} must not reach the other side's"
        # ...and at least one real emitter, so the site is RWR-visible/HARM-able.
        radars = [
            unit
            for unit in group.units
            if unit.unit_class is UnitClass.EARLY_WARNING_RADAR
        ]
        assert radars, f"{preset_name} must pair the jammer with an EWR emitter"
        # ...and an ARM-able acquisition radar. Being on the RWR and being
        # HARM-able are two DIFFERENT DCS attributes: `GT.WS.radar_type` puts a
        # unit on the RWR (the EWRs have it), `RADAR_BAND1/2_FOR_ARM` is what an
        # anti-radiation seeker homes on -- and the EWRs do NOT carry it. Without
        # this second radar the site is a contact you cannot shoot a HARM at.
        arm_able = [
            unit
            for unit in group.units
            if unit.dcs_unit_type.id in {"RLS_19J6", "NASAMS_Radar_MPQ64F1"}
        ]
        assert arm_able, f"{preset_name} must field an ARM-able acquisition radar"
        assert "Early-Warning Radar" in {lay.name for lay in group.layouts}


def test_no_other_shipped_unit_jams_by_accident() -> None:
    """A stray `gps_jamming` block anywhere else would silently deny GPS across
    a campaign that never asked for it."""
    from game.dcs.groundunittype import GroundUnitType

    GroundUnitType._load_all()
    jammers = {
        unit.variant_id
        for unit in GroundUnitType._by_name.values()
        if unit.gps_jamming is not None
    }
    assert jammers == {"EW Radio Jammer (Red)", "EW Radio Jammer (Blue)"}
