"""Blue-block miz markers generate, and bind to blue control points.

The RED country block is the coalition-agnostic default marker block: blue air
defenses are conventionally authored as red-block markers near blue fields and
proximity decides the owner. But a marker authored in the BLUE block was
silently dropped for most classes (ships / SAMs / EWRs / missile / coastal /
offshore strike) -- 22 authored markers across 7 shipped campaigns never
generated -- and the classes that did walk both blocks bound coalition-blind,
so one side's marker could be handed to the other (Red Tide's "414th Red EWR 1"
bound blue Frankfurt and silently never spawned).

Contract locked here: every marker class also walks the blue block, and a
blue-block group binds to the nearest BLUE control point when one exists, while
red-block markers keep the nearest-any proximity convention.

Since 2026-07-20 the rule is total (the upstream #891 review ask): EVERY object
class walks both blocks — a red-block factory, a red-block front-line path, and
a blue-block neutral-FOB declaration all generate. The block never decides
whether an authored object exists; it only declares ownership where that is its
documented meaning (CP classes, and the bounded blue-marker preference).
"""

from pathlib import Path

import pytest
from dcs.countries import (
    CombinedJointTaskForcesBlue,
    CombinedJointTaskForcesRed,
)
from dcs.mission import Mission
from dcs.statics import Fortification
from dcs.terrain.caucasus import Caucasus
from dcs.vehicles import AirDefence, Armor, Unarmed

from game import persistency
from game.campaignloader.mizcampaignloader import MizCampaignLoader
from game.theater import ControlPoint
from game.theater.conflicttheater import ConflictTheater
from game.theater.player import Player
from game.theater.theaterloader import TheaterLoader


@pytest.fixture(autouse=True)
def _init_persistency(tmp_path_factory: pytest.TempPathFactory) -> None:
    persistency.setup(str(tmp_path_factory.mktemp("saved_games")), False, 0)


def _build_test_miz(path: Path) -> None:
    mission = Mission(terrain=Caucasus())
    blue_field = mission.terrain.airports["Kutaisi"]
    red_field = mission.terrain.airports["Senaki-Kolkhi"]
    blue_field.set_blue()
    red_field.set_red()

    blue_country = CombinedJointTaskForcesBlue()
    red_country = CombinedJointTaskForcesRed()
    mission.coalition["blue"].add_country(blue_country)
    mission.coalition["red"].add_country(red_country)

    # A BLUE-block EWR marker planted right next to the RED field: nearest-any
    # binding would hand it to red, but the blue block declares blue ownership.
    mission.vehicle_group(
        blue_country,
        "Blue EWR marker",
        AirDefence.x_1L13_EWR,
        red_field.position.point_from_heading(45, 3000),
    )

    # A RED-block SHORAD marker next to the BLUE field: the coalition-agnostic
    # proximity convention must keep binding it to the blue field (this is how
    # upstream campaigns author blue air defenses).
    mission.vehicle_group(
        red_country,
        "Red block SHORAD marker",
        AirDefence.Strela_1_9P31,
        blue_field.position.point_from_heading(90, 3000),
    )

    mission.save(str(path))


def test_marker_coalition_binding(tmp_path: Path) -> None:
    miz = tmp_path / "marker_binding.miz"
    _build_test_miz(miz)

    theater = TheaterLoader("caucasus").load()
    MizCampaignLoader(miz, theater).populate_theater()

    kutaisi = theater.control_point_named("Kutaisi")
    senaki = theater.control_point_named("Senaki-Kolkhi")

    # The blue-block EWR generated at all (was silently dropped) and bound the
    # blue field even though the red field is 3 km away.
    assert len(kutaisi.preset_locations.ewrs) == 1
    assert not senaki.preset_locations.ewrs

    # The red-block marker still binds by proximity: blue field owns it.
    assert len(kutaisi.preset_locations.short_range_sams) == 1
    assert not senaki.preset_locations.short_range_sams


def _build_scoping_miz(path: Path) -> None:
    """Kutaisi (blue) far from two red fields, with blue-block objects on the
    red fields: an economy object (factory) and a marker (EWR) beyond the
    detour bound, plus a near-field marker that should still prefer blue."""
    mission = Mission(terrain=Caucasus())
    kutaisi = mission.terrain.airports["Kutaisi"]  # blue
    senaki = mission.terrain.airports["Senaki-Kolkhi"]  # red, ~37 km from Kutaisi
    min_vody = mission.terrain.airports["Mineralnye Vody"]  # red, ~235 km away
    kutaisi.set_blue()
    senaki.set_red()
    min_vody.set_red()

    blue_country = CombinedJointTaskForcesBlue()
    red_country = CombinedJointTaskForcesRed()
    mission.coalition["blue"].add_country(blue_country)
    mission.coalition["red"].add_country(red_country)

    # Blue-block FACTORY sitting on the distant red field. The blue block holds
    # the economy objects by convention; #590's all-class preference re-owned
    # them to distant blue fields. It must bind the red field it sits on.
    mission.static_group(
        blue_country,
        "Blue block factory",
        Fortification.Workshop_A,
        min_vody.position.point_from_heading(0, 3000),
    )

    # Blue-block EWR on the distant red field: nearest blue field (Kutaisi) is
    # ~235 km away, far past BLUE_BLOCK_MAX_DETOUR, so proximity decides.
    mission.vehicle_group(
        blue_country,
        "Blue EWR far",
        AirDefence.x_1L13_EWR,
        min_vody.position.point_from_heading(45, 3000),
    )

    # Blue-block EWR next to the near red field (~37 km detour, within the
    # bound): the #590 near-field preference still binds the blue field.
    mission.vehicle_group(
        blue_country,
        "Blue EWR near",
        AirDefence.x_1L13_EWR,
        senaki.position.point_from_heading(45, 3000),
    )

    mission.save(str(path))


def test_blue_block_preference_is_scoped_and_bounded(tmp_path: Path) -> None:
    miz = tmp_path / "scoping.miz"
    _build_scoping_miz(miz)

    theater = TheaterLoader("caucasus").load()
    MizCampaignLoader(miz, theater).populate_theater()

    kutaisi = theater.control_point_named("Kutaisi")
    senaki = theater.control_point_named("Senaki-Kolkhi")
    min_vody = theater.control_point_named("Mineralnye Vody")

    # Economy object is never preferred to a distant blue field -- binds the
    # red field it sits on.
    assert len(min_vody.preset_locations.factories) == 1
    assert not kutaisi.preset_locations.factories

    # Marker beyond the detour bound binds by proximity (the red field), not
    # the 235 km-distant blue field.
    assert len(min_vody.preset_locations.ewrs) == 1

    # Marker within the detour bound still prefers the blue field.
    assert len(kutaisi.preset_locations.ewrs) == 1
    assert not senaki.preset_locations.ewrs


def _build_cross_block_miz(path: Path) -> None:
    """The classes that historically read a single country block, each authored
    in the OTHER block: a red-block factory (was blue-only), a red-block
    front-line path (was blue-only), and a blue-block neutral-FOB declaration
    (was red-only). All must generate — the block never decides existence."""
    mission = Mission(terrain=Caucasus())
    blue_field = mission.terrain.airports["Kutaisi"]
    red_field = mission.terrain.airports["Senaki-Kolkhi"]
    blue_field.set_blue()
    red_field.set_red()

    blue_country = CombinedJointTaskForcesBlue()
    red_country = CombinedJointTaskForcesRed()
    mission.coalition["blue"].add_country(blue_country)
    mission.coalition["red"].add_country(red_country)

    # RED-block factory on the red field (the intuitive authoring choice; three
    # shipped campaigns did exactly this and the factory silently never
    # generated). Binds by proximity like every economy object.
    mission.static_group(
        red_country,
        "Red block factory",
        Fortification.Workshop_A,
        red_field.position.point_from_heading(0, 3000),
    )

    # RED-block front-line path from the blue field to the red field. A path
    # has no owner; its endpoint CPs bind it.
    front_line = mission.vehicle_group(
        red_country,
        "Red block frontline path",
        Armor.M_113,
        blue_field.position,
    )
    front_line.add_waypoint(red_field.position)

    # BLUE-block neutral-FOB declaration: the KrAZ itself declares neutrality,
    # so the block it sits in must not matter.
    mission.vehicle_group(
        blue_country,
        "Neutral FOB Alpha",
        Unarmed.KrAZ6322,
        blue_field.position.point_from_heading(180, 20000),
    )

    mission.save(str(path))


def test_cross_block_classes_generate(tmp_path: Path) -> None:
    miz = tmp_path / "cross_block.miz"
    _build_cross_block_miz(miz)

    theater = TheaterLoader("caucasus").load()
    MizCampaignLoader(miz, theater).populate_theater()

    kutaisi = theater.control_point_named("Kutaisi")
    senaki = theater.control_point_named("Senaki-Kolkhi")

    # The red-block factory generated and bound the red field it sits on.
    assert len(senaki.preset_locations.factories) == 1
    assert not kutaisi.preset_locations.factories

    # The red-block front-line path created the convoy route between its
    # endpoint control points, both directions.
    assert any(dest.name == "Senaki-Kolkhi" for dest in kutaisi.convoy_routes)
    assert any(dest.name == "Kutaisi" for dest in senaki.convoy_routes)

    # The blue-block KrAZ produced a NEUTRAL FOB control point.
    fob = theater.control_point_named("Neutral FOB Alpha")
    assert fob.starting_coalition is Player.NEUTRAL


def _build_dynamic_spawn_miz(path: Path) -> None:
    mission = Mission(terrain=Caucasus())
    blue_field = mission.terrain.airports["Kutaisi"]
    red_field = mission.terrain.airports["Senaki-Kolkhi"]
    blue_field.set_blue()
    red_field.set_red()
    # A dynamic-spawn RED field: upstream would infer NEUTRAL; the 414th keeps
    # the .miz-declared coalition.
    red_field.dynamic_spawn = True

    mission.coalition["blue"].add_country(CombinedJointTaskForcesBlue())
    mission.coalition["red"].add_country(CombinedJointTaskForcesRed())
    mission.save(str(path))


def test_dynamic_spawn_airfield_keeps_its_coalition(tmp_path: Path) -> None:
    miz = tmp_path / "dynamic_spawn.miz"
    _build_dynamic_spawn_miz(miz)

    theater = TheaterLoader("caucasus").load()
    MizCampaignLoader(miz, theater).populate_theater()

    red_field = theater.control_point_named("Senaki-Kolkhi")
    assert red_field.starting_coalition is Player.RED


def _build_zoned_miz(path: Path) -> None:
    """A blue field with a tight influence zone and a blue-block garage just outside it.

    `operation_vectrons_claw` in miniature: the marker misses UNOMIG Sector HQ's
    6096 m zone by 617 m, and the zone fallback drops every zoned CP, so it bound
    RED Sukhumi-Babushara 75 km away and spawned a red motorpool beside a blue base.
    """
    mission = Mission(terrain=Caucasus())
    blue_field = mission.terrain.airports["Kutaisi"]
    red_field = mission.terrain.airports["Senaki-Kolkhi"]
    blue_field.set_blue()
    red_field.set_red()

    blue_country = CombinedJointTaskForcesBlue()
    mission.coalition["blue"].add_country(blue_country)
    mission.coalition["red"].add_country(CombinedJointTaskForcesRed())

    zone = mission.triggers.add_triggerzone(
        blue_field.position, radius=3000, name="Kutaisi"
    )
    # DCS stores both as 1-indexed dicts; ControlPointInfluenceRadius reads a
    # red zone whose first property names the control point.
    zone.color = {1: 1, 2: 0, 3: 0, 4: 0.15}
    zone.properties = {1: {"key": "PROPERTY_1", "value": "Kutaisi"}}

    mission.static_group(
        blue_country,
        "Static Garage A-1",
        Fortification.Garage_A,
        blue_field.position.point_from_heading(0, 3600),
    )
    mission.save(str(path))


def test_a_blue_block_marker_binds_its_own_zoned_field(tmp_path: Path) -> None:
    miz = tmp_path / "zoned_binding.miz"
    _build_zoned_miz(miz)

    theater = TheaterLoader("caucasus").load()
    MizCampaignLoader(miz, theater).populate_theater()

    kutaisi = theater.control_point_named("Kutaisi")
    senaki = theater.control_point_named("Senaki-Kolkhi")

    # 600 m outside its own field's zone -- and it stays that field's motorpool
    # instead of being thrown to the nearest control point with no zone at all.
    assert len(kutaisi.preset_locations.motorpools) == 1
    assert not senaki.preset_locations.motorpools


def _build_tight_zone_miz(
    path: Path, offset_m: int, unzoned_is_far: bool = True
) -> None:
    """`operation_desert_trident` in miniature.

    A RED field whose influence zone hugs the runway, an armour marker just
    outside that zone, and the nearest UNZONED field far away. The zone fallback
    drops every zoned control point, so the marker skipped the field it sits next
    to and bound the distant one: six armour groups and a fuel depot 15-25 km
    from red King Abdullah II became blue Ben Gurion's, 110-140 km away.

    Armour is the point -- it does not pass ``prefer_blue``, so the blue-block
    preference cannot reach it and the fallback is the only rule in play.

    ``unzoned_is_far`` picks which unzoned field exists: Mineralnye Vody (~200 km,
    a stranding) or Kutaisi (~37 km, an ordinary neighbour).
    """
    mission = Mission(terrain=Caucasus())
    red_field = mission.terrain.airports["Senaki-Kolkhi"]
    blue_field = mission.terrain.airports[
        "Mineralnye Vody" if unzoned_is_far else "Kutaisi"
    ]
    red_field.set_red()
    blue_field.set_blue()

    mission.coalition["blue"].add_country(CombinedJointTaskForcesBlue())
    red_country = CombinedJointTaskForcesRed()
    mission.coalition["red"].add_country(red_country)

    # Tight zone on the red field only, so the blue field is the sole fallback
    # candidate. DCS stores colour and properties as 1-indexed dicts.
    zone = mission.triggers.add_triggerzone(
        red_field.position, radius=2000, name="Senaki-Kolkhi"
    )
    zone.color = {1: 1, 2: 0, 3: 0, 4: 0.15}
    zone.properties = {1: {"key": "PROPERTY_1", "value": "Senaki-Kolkhi"}}

    mission.vehicle_group(
        red_country,
        "Red armor outside the zone",
        Armor.M_1_Abrams,
        red_field.position.point_from_heading(180, offset_m),
    )
    mission.save(str(path))


def _load(miz: Path) -> tuple[ConflictTheater, ControlPoint]:
    theater = TheaterLoader("caucasus").load()
    MizCampaignLoader(miz, theater).populate_theater()
    return theater, theater.control_point_named("Senaki-Kolkhi")


def test_a_nearby_zoned_field_adopts_a_stranded_marker(tmp_path: Path) -> None:
    miz = tmp_path / "tight_zone.miz"
    _build_tight_zone_miz(miz, offset_m=4000)
    theater, senaki = _load(miz)
    far = theater.control_point_named("Mineralnye Vody")

    # 2 km outside its own field's zone, and ~200 km from the nearest unzoned
    # field. It stays the red field's armour instead of being thrown across the
    # map to a blue one.
    assert len(senaki.preset_locations.armor_groups) == 1
    assert not far.preset_locations.armor_groups


def test_a_distant_zoned_field_does_not_adopt(tmp_path: Path) -> None:
    # The near bound matters as much as the rule: a marker out in open country
    # is not claimed by a zoned field just because that field happens to be
    # nearest. Past ADOPT_ZONED_WITHIN the unzoned fallback still decides.
    miz = tmp_path / "tight_zone_far.miz"
    _build_tight_zone_miz(miz, offset_m=30000)
    theater, senaki = _load(miz)
    far = theater.control_point_named("Mineralnye Vody")

    assert not senaki.preset_locations.armor_groups
    assert len(far.preset_locations.armor_groups) == 1


def test_a_healthy_binding_is_never_reshuffled(tmp_path: Path) -> None:
    """The other bound, and the one that cost a measurement to find.

    Proximity alone moves 40 of 7653 bindings, and 14 of them are Velvet
    Thunder markers hopping between neighbouring fields already 2.2-12.4 km
    away. Nothing is wrong in that campaign, and #924 measured and rejected the
    same outcome. Adoption only rescues a marker the fallback would strand past
    STRANDED_BEYOND; a marker whose owner is merely a bit farther stays put.
    """
    miz = tmp_path / "tight_zone_healthy.miz"
    _build_tight_zone_miz(miz, offset_m=4000, unzoned_is_far=False)
    theater, senaki = _load(miz)
    near = theater.control_point_named("Kutaisi")

    assert not senaki.preset_locations.armor_groups
    assert len(near.preset_locations.armor_groups) == 1
