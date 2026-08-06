"""GPS jamming (§85) -- the campaign side.

Pins the site model (which units jam, how far, whose weapons), the recon fog on
the kneeboard brief, and the curated weapon list's hard exclusions: a laser, TV
or IR weapon must never be jammable, because a Paveway that mysteriously misses
reads as a bug rather than as a feature.
"""

from __future__ import annotations

import pathlib
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
    """The real tie-in, on real registered data: the two DCS "Radio jammer"
    vehicles are the feature's units, and both declare the same deliberate reach.

    15 nm is BELOW the 50 km (27 nm) DCS declares for the vehicle, and that is the
    point: the bubble is a GPS-denied TARGET area, not a denied release area (a
    weapon aimed inside it flies through it whatever the release range), so the
    radius is the size of the target set that loses guidance. 27 nm denied a large
    share of a medium map.
    """
    from game.dcs.groundunittype import GroundUnitType

    for variant in ("EW Radio Jammer (Red)", "EW Radio Jammer (Blue)"):
        unit = GroundUnitType.named(variant)
        assert unit.gps_jamming is not None, f"{variant} must declare gps_jamming"
        assert (
            unit.gps_jamming.radius_nm == 15
        ), f"{variant} should deny a target cluster (15 nm), not a region"
        # Sanity: still well inside what DCS says the vehicle can hear.
        assert nautical_miles(unit.gps_jamming.radius_nm).meters < (
            unit.dcs_unit_type.detection_range
        )


def test_the_standalone_jamming_site_layout_is_self_contained(
    _layouts: None,
) -> None:
    """Model 1: a placeable site of its own.

    It fields the jammers and its point defence, and deliberately NO radar, and
    must not be `generic`, so it can never be rolled at an ordinary air-defence
    marker by accident.
    """
    from game.layout import LAYOUTS

    LAYOUTS.initialize()
    layout = next(
        (lay for lay in LAYOUTS.layouts if lay.name == "GPS Jamming Site"), None
    )
    assert layout is not None, "the standalone GPS Jamming Site layout must exist"
    assert not layout.generic, "must be preset-only, never rolled by accident"

    slots = {
        unit_group.name: unit_group
        for group in layout.groups
        for unit_group in group.unit_groups
    }
    jammer = slots.get("GPS Jammer")
    assert jammer is not None and len(jammer.layout_units) >= 1
    assert {t.id for t in (jammer.unit_types or [])} == {
        "GPS_Spoofer_Red",
        "GPS_Spoofer_Blue",
    }
    assert "GPS Jammer Radar" not in slots, (
        "the site carries NO radar on purpose -- a real GPS jammer is L-band, so "
        "making it HARM-able was the unrealistic option (DM call 2026-08-05). It "
        "is a strike target found by recon, not a SEAD target."
    )


def test_a_sam_site_can_carry_an_attached_jamming_section(_layouts: None) -> None:
    """Model 2: the section that puts a jammer INSIDE an existing threat ring.

    Optional + fill: false is what keeps every shipped S-300 site unchanged --
    only a preset that explicitly lists a jammer fields one.
    """
    from game.layout import LAYOUTS

    LAYOUTS.initialize()
    for layout_name in ("S-300 Site", "S-300 Site (Single Radar)"):
        layout = next((lay for lay in LAYOUTS.layouts if lay.name == layout_name), None)
        assert layout is not None, f"{layout_name} must exist"
        slot = next(
            (
                unit_group
                for group in layout.groups
                for unit_group in group.unit_groups
                if unit_group.name == "S-300 Site GPS Jammer"
            ),
            None,
        )
        assert slot is not None, f"{layout_name} must offer the jamming section"
        assert (
            slot.optional is True and slot.fill is False
        ), "an existing S-300 site must never grow a jammer on its own"
        assert len(slot.layout_units) >= 1, "the .miz position group is missing"


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
        assert not [
            unit
            for unit in group.units
            if unit.dcs_unit_type.id in {"RLS_19J6", "NASAMS_Radar_MPQ64F1"}
        ], f"{preset_name} must field no radar -- the site is a strike target"
        assert "GPS Jamming Site" in {lay.name for lay in group.layouts}


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


def test_ewr_markers_honour_a_ground_forces_pin(_layouts: None) -> None:
    """`generate_ewrs` must route through `get_unit_group_for_task`.

    It used to call `random_group_for_task` directly, so a campaign's
    `ground_forces` pin on an EWR marker was silently ignored -- the identical
    hole naval groups had until `generate_navy` was routed through the same
    method. The failure did not look like a pin failure either: because the
    pinned preset is also registered on the faction (that is how its units become
    `accessible_units`), it joined the EWR candidate pool and was picked at a
    RANDOM SUBSET of markers, so the campaign generated a different shape every
    time (measured 1-to-5 of 5 sites before the fix).

    Pinned to the source rather than a full generation, which needs the mods
    enabled at New Game and cannot run headless.
    """
    import inspect

    from game.theater.start_generator import AirbaseGroundObjectGenerator

    source = inspect.getsource(AirbaseGroundObjectGenerator.generate_ewrs)
    # Comments discuss the old call by name, so compare code lines only.
    code = "\n".join(
        line for line in source.splitlines() if not line.strip().startswith("#")
    )
    assert "self.get_unit_group_for_task(" in code, (
        "generate_ewrs must honour ground_forces pins -- calling "
        "random_group_for_task directly silently ignores them"
    )
    assert "random_group_for_task" not in code


# -- density guard: few, large-effect, non-overlapping -------------------------

#: A campaign may field at most this many GPS-jamming sites.
#:
#: Bubbles are big and INVISIBLE on the campaign map, so a heavy hand is easy to
#: author and hard to notice until someone flies it -- the Marianas lesson, where
#: 13 of 30 max-radius rings "did not make the campaign harder, it made the map
#: unreadable". Few large-effect sites on distinct target clusters is the shape.
MAX_JAMMING_SITES_PER_CAMPAIGN = 3


def _campaign_jamming_pins() -> dict[str, list[tuple[str, str]]]:
    """{campaign yaml stem: [(marker name, preset name), ...]} for every pin whose
    preset fields a GPS jammer -- both placement models, since a standalone site
    and a jamming-equipped SAM battery both reach the map through a pin."""
    import yaml as _yaml

    from game.armedforces.forcegroup import ForceGroup

    out: dict[str, list[tuple[str, str]]] = {}
    for path in pathlib.Path("resources/campaigns").glob("*.yaml"):
        data = _yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        pins = data.get("ground_forces") or {}
        found: list[tuple[str, str]] = []
        for marker, preset_name in pins.items():
            try:
                preset = ForceGroup.from_preset_group(preset_name)
            except KeyError:
                continue  # an unknown preset is a different test's problem
            if any(
                getattr(unit, "gps_jamming", None) is not None for unit in preset.units
            ):
                found.append((str(marker), str(preset_name)))
        if found:
            out[path.stem] = found
    return out


def test_no_campaign_fields_more_than_three_jamming_sites(_layouts: None) -> None:
    from game.layout import LAYOUTS

    LAYOUTS.initialize()
    for campaign, pins in _campaign_jamming_pins().items():
        assert len(pins) <= MAX_JAMMING_SITES_PER_CAMPAIGN, (
            f"{campaign} authors {len(pins)} GPS-jamming sites "
            f"({[m for m, _ in pins]}); the cap is "
            f"{MAX_JAMMING_SITES_PER_CAMPAIGN}. Jamming bubbles are large and "
            "invisible on the map -- a few placed on distinct target clusters "
            "read as a decision, a carpet reads as the weapon class being off."
        )


def test_jamming_bubbles_do_not_overlap(_layouts: None) -> None:
    """Two bubbles covering the same ground buy redundancy, not depth.

    The runtime does NOT stack effects -- a weapon faces only the single
    strongest bubble covering it (the §77 non-stacking rule) -- so a second
    overlapping site adds no new decision for the player, and killing one
    restores nothing. Deliberate defence-in-depth is a fair reason to override
    this, but it should be a conscious one.
    """
    from dcs.mission import Mission

    from game.armedforces.forcegroup import ForceGroup
    from game.layout import LAYOUTS
    from game.utils import nautical_miles

    LAYOUTS.initialize()
    for campaign, pins in _campaign_jamming_pins().items():
        miz = pathlib.Path("resources/campaigns") / f"{campaign}.miz"
        if not miz.exists():
            continue
        mission = Mission()
        mission.load_file(str(miz))
        positions = {
            group.name: (group.units[0].position.x, group.units[0].position.y)
            for coalition in mission.coalition.values()
            for country in coalition.countries.values()
            for group in country.vehicle_group
            if group.units
        }
        placed: list[tuple[str, float, float, float]] = []
        for marker, preset_name in pins:
            if marker not in positions:
                continue
            radii = []
            for unit in ForceGroup.from_preset_group(preset_name).units:
                jamming = getattr(unit, "gps_jamming", None)
                if jamming is None:
                    continue
                radii.append(
                    nautical_miles(jamming.radius_nm).meters
                    if jamming.radius_nm
                    else DEFAULT_REACH.meters
                )
            reach = max(radii)
            x, y = positions[marker]
            placed.append((marker, x, y, reach))
        for i, (name_a, xa, ya, ra) in enumerate(placed):
            for name_b, xb, yb, rb in placed[i + 1 :]:
                gap = ((xa - xb) ** 2 + (ya - yb) ** 2) ** 0.5
                assert gap >= ra + rb, (
                    f"{campaign}: jamming bubbles {name_a} and {name_b} overlap "
                    f"({gap / 1000:.0f} km apart, radii sum "
                    f"{(ra + rb) / 1000:.0f} km). Effects do not stack, so the "
                    "second site adds no decision -- spread them onto distinct "
                    "target clusters."
                )


def test_every_jamming_pin_sits_on_ground_its_owner_holds(_layouts: None) -> None:
    """A jamming pin must bind to a control point owned by the side that fields
    the jammer, or it is silently discarded.

    The override gate checks the preset's units against the OWNING control
    point's faction (`get_unit_group_for_task` reads `self.faction`), so a red
    jamming preset pinned to a marker that binds to a BLUE control point fails
    the check and an ordinary site generates there instead -- no error, no
    warning that reaches the author, just a campaign quietly missing the feature
    it asked for. Caught exactly this way when three campaigns each generated one
    of their two pinned sites.
    """
    import yaml as _yaml

    from game.campaignloader.campaign import Campaign
    from game.layout import LAYOUTS

    LAYOUTS.initialize()
    for campaign, pins in _campaign_jamming_pins().items():
        path = pathlib.Path("resources/campaigns") / f"{campaign}.yaml"
        data = _yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        theater = Campaign.from_file(path).load_theater(
            advanced_iads=bool(data.get("advanced_iads", False))
        )
        owner_of: dict[str, str] = {}
        for control_point in theater.controlpoints:
            if control_point.starting_coalition.name == "NEUTRAL":
                side = "neutral"
            else:
                side = "blue" if control_point.starting_coalition.is_blue else "red"
            for location in control_point.preset_locations.ewrs:
                owner_of[location.original_name] = side
        for marker, preset_name in pins:
            if marker not in owner_of:
                continue  # not an EWR-band marker; a different placement model
            side = owner_of[marker]
            wanted = "blue" if "(Blue)" in preset_name else "red"
            assert side == wanted, (
                f"{campaign}: {marker} is pinned to {preset_name} but binds to a "
                f"{side.upper()} control point -- the override will be silently "
                "discarded and an ordinary site generated there instead"
            )
