"""Dynamic spawn templates (§101).

Pins the two miz keys DCS reads: ``dynSpawnTemplate = true`` on the donor
group and ``aircrafts.<category>.<type>.linkDynTempl = <groupId>`` on the
base's warehouse entry, plus the donor choice and the two gates.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional
from uuid import uuid4

from dcs.helicopters import AH_64D_BLK_II
from dcs.mission import Mission
from dcs.planes import FA_18C_hornet
from dcs.terrain import Caucasus
from dcs.terrain.terrain import Airport
from dcs.unit import Skill
from dcs.unitgroup import FlyingGroup

from game.ato.starttype import StartType
from game.missiongenerator.dynamicspawntemplates import (
    DynamicSpawnTemplateGenerator,
    template_entry,
)


def make_mission() -> Mission:
    return Mission(Caucasus())


def make_group(
    mission: Mission,
    airport: Airport,
    unit_type: Any = FA_18C_hornet,
    client: bool = True,
    name: str = "Colt 1",
) -> FlyingGroup[Any]:
    group = mission.flight_group_from_airport(
        mission.country("USA"), name, unit_type, airport, group_size=2
    )
    if client:
        for unit in group.units:
            unit.skill = Skill.Client
    return group


class FakeControlPoint:
    def __init__(self, airport: Optional[Airport] = None) -> None:
        self.id = uuid4()
        if airport is not None:
            self.airport = airport


def make_flight(
    group: FlyingGroup[Any],
    cp: FakeControlPoint,
    unit_type: Any = FA_18C_hornet,
    client_count: int = 2,
    start_type: StartType = StartType.COLD,
    helicopter: bool = False,
) -> Any:
    return SimpleNamespace(
        client_count=client_count,
        group_id=group.id,
        departure=cp,
        unit_type=SimpleNamespace(dcs_unit_type=unit_type, helicopter=helicopter),
        start_type=start_type,
    )


def make_game(
    blue_flights: list[Any],
    dynamic_slots: bool = True,
    templates: bool = True,
) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(
            dynamic_slots=dynamic_slots, dynamic_slots_templates=templates
        ),
        blue=SimpleNamespace(
            ato=SimpleNamespace(packages=[SimpleNamespace(flights=blue_flights)])
        ),
        red=SimpleNamespace(ato=SimpleNamespace(packages=[])),
    )


def test_airfield_link_marks_the_client_flight() -> None:
    mission = make_mission()
    kutaisi = mission.terrain.airports["Kutaisi"]
    group = make_group(mission, kutaisi)
    cp = FakeControlPoint(kutaisi)
    flight = make_flight(group, cp)

    DynamicSpawnTemplateGenerator(mission, make_game([flight]), {}).generate()

    assert group.dyn_spawn_template is True
    assert group.dict()["dynSpawnTemplate"] is True
    entry = kutaisi.aircrafts["planes"][FA_18C_hornet.id]
    assert entry == template_entry(group.id)
    assert entry["linkDynTempl"] == group.id
    # The link reaches the file DCS reads, under the airport's own id.
    warehouses = str(mission.warehouses)
    assert f'["linkDynTempl"]={group.id}' in warehouses
    assert f'["{FA_18C_hornet.id}"]' in warehouses


def test_untouched_group_serializes_without_the_flag() -> None:
    mission = make_mission()
    group = make_group(mission, mission.terrain.airports["Kutaisi"])
    assert "dynSpawnTemplate" not in group.dict()


def test_nothing_written_when_dynamic_slots_are_off() -> None:
    mission = make_mission()
    kutaisi = mission.terrain.airports["Kutaisi"]
    group = make_group(mission, kutaisi)
    flight = make_flight(group, FakeControlPoint(kutaisi))

    for kwargs in ({"dynamic_slots": False}, {"templates": False}):
        DynamicSpawnTemplateGenerator(
            mission, make_game([flight], **kwargs), {}
        ).generate()
        assert group.dyn_spawn_template is False
        assert kutaisi.aircrafts == {}


def test_ai_flights_are_never_templates() -> None:
    mission = make_mission()
    kutaisi = mission.terrain.airports["Kutaisi"]
    group = make_group(mission, kutaisi, client=False)
    flight = make_flight(group, FakeControlPoint(kutaisi), client_count=0)

    DynamicSpawnTemplateGenerator(mission, make_game([flight]), {}).generate()

    assert group.dyn_spawn_template is False
    assert kutaisi.aircrafts == {}


def test_one_template_per_base_and_type_ground_start_preferred() -> None:
    mission = make_mission()
    kutaisi = mission.terrain.airports["Kutaisi"]
    cp = FakeControlPoint(kutaisi)
    airborne = make_group(mission, kutaisi, name="Colt 1")
    ground = make_group(mission, kutaisi, name="Colt 2")
    later = make_group(mission, kutaisi, name="Colt 3")
    flights = [
        make_flight(airborne, cp, start_type=StartType.IN_FLIGHT),
        make_flight(ground, cp),
        make_flight(later, cp),
    ]

    DynamicSpawnTemplateGenerator(mission, make_game(flights), {}).generate()

    assert ground.dyn_spawn_template is True
    assert airborne.dyn_spawn_template is False
    assert later.dyn_spawn_template is False
    assert kutaisi.aircrafts["planes"][FA_18C_hornet.id]["linkDynTempl"] == ground.id


def test_helicopters_link_under_their_own_category() -> None:
    mission = make_mission()
    kutaisi = mission.terrain.airports["Kutaisi"]
    group = make_group(mission, kutaisi, unit_type=AH_64D_BLK_II)
    flight = make_flight(
        group, FakeControlPoint(kutaisi), unit_type=AH_64D_BLK_II, helicopter=True
    )

    DynamicSpawnTemplateGenerator(mission, make_game([flight]), {}).generate()

    assert (
        kutaisi.aircrafts["helicopters"][AH_64D_BLK_II.id]["linkDynTempl"] == group.id
    )
    assert "planes" not in kutaisi.aircrafts


def test_carrier_link_goes_on_every_warehouse_of_the_control_point() -> None:
    mission = make_mission()
    # The group only needs an id; a carrier start is not modelled here.
    group = make_group(mission, mission.terrain.airports["Kutaisi"])
    boat = FakeControlPoint()
    flight = make_flight(group, boat)
    hull: dict[str, Any] = {"aircrafts": {}, "dynamicSpawn": True}
    escort: dict[str, Any] = {"aircrafts": {}, "dynamicSpawn": True}
    other: dict[str, Any] = {"aircrafts": {}, "dynamicSpawn": True}

    DynamicSpawnTemplateGenerator(
        mission,
        make_game([flight]),
        {boat.id: [hull, escort], uuid4(): [other]},
    ).generate()

    assert group.dyn_spawn_template is True
    for warehouse in (hull, escort):
        assert warehouse["aircrafts"]["planes"][FA_18C_hornet.id] == template_entry(
            group.id
        )
    assert other["aircrafts"] == {}


def test_a_flight_with_no_group_is_skipped() -> None:
    mission = make_mission()
    kutaisi = mission.terrain.airports["Kutaisi"]
    flight = SimpleNamespace(
        client_count=2,
        group_id=99999,
        departure=FakeControlPoint(kutaisi),
        unit_type=SimpleNamespace(dcs_unit_type=FA_18C_hornet, helicopter=False),
        start_type=StartType.COLD,
    )

    DynamicSpawnTemplateGenerator(mission, make_game([flight]), {}).generate()

    assert kutaisi.aircrafts == {}
