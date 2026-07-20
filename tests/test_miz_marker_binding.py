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
