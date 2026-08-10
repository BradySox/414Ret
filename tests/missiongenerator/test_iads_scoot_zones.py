"""MANTIS point-defense displacement zones (§89).

The pins here are the contracts the generator shares with two things it cannot
call: MOOSE's ``SHORAD:onafterShootAndScoot`` (which silently ignores any zone
outside its distance window) and ``collect_pd`` in mantis-config.lua (which
decides which groups are in the SHORAD set at all). A drift in either would not
crash anything -- point defenses would just quietly never move.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

from dcs.mapping import Point
from dcs.mission import Mission
from dcs.terrain import Terrain
from dcs.triggers import Triggers

from game.missiongenerator.iadsscootzonegenerator import (
    INNER_RADIUS_FRACTION,
    MOOSE_MIN_SCOOT_DISTANCE,
    SCOOT_ZONE_PREFIX,
    IadsScootZoneGenerator,
)
from game.theater.iadsnetwork.iadsrole import IadsRole

if TYPE_CHECKING:
    from game.game import Game

TERRAIN = MagicMock(spec=Terrain)

DEFAULT_OPTIONS: dict[str, Any] = {
    "mantisiads": True,
    "mantisiads.shoradLink": True,
    "mantisiads.shoradScoot": True,
    "mantisiads.scootZones": 4,
    "mantisiads.scootRadiusNm": 1.3,
}


def _point(x: float = 0.0, y: float = 0.0) -> Point:
    return Point(x, y, TERRAIN)


def _pd_group(name: str, position: Point, alive: bool = True) -> Any:
    """A point-defense group as the generator reads it."""
    return SimpleNamespace(
        group_name=name,
        position=position,
        iads_role=IadsRole.POINT_DEFENSE,
        units=[SimpleNamespace(alive=alive)],
        ground_object=SimpleNamespace(name=f"{name} tgo"),
    )


def _node(role: IadsRole, connections: list[Any]) -> Any:
    return SimpleNamespace(
        group=SimpleNamespace(
            iads_role=role, ground_object=SimpleNamespace(name="sam tgo")
        ),
        connections={index: c for index, c in enumerate(connections)},
    )


def _mission() -> Mission:
    mission = MagicMock(spec=Mission)
    mission.triggers = Triggers(TERRAIN)
    return cast(Mission, mission)


def _game(
    nodes: list[Any],
    options: dict[str, Any] | None = None,
    on_land: bool = True,
    culled: bool = False,
) -> Game:
    opts = dict(DEFAULT_OPTIONS if options is None else options)

    def plugin_option(identifier: str) -> Any:
        return opts[identifier]

    return cast(
        "Game",
        SimpleNamespace(
            settings=SimpleNamespace(plugin_option=plugin_option),
            theater=SimpleNamespace(
                iads_network=SimpleNamespace(nodes=nodes),
                is_on_land=lambda point: on_land,
            ),
            iads_considerate_culling=lambda go: culled,
        ),
    )


def _generate(
    nodes: list[Any], **kwargs: Any
) -> tuple[int, Triggers, IadsScootZoneGenerator]:
    mission = _mission()
    generator = IadsScootZoneGenerator(mission, _game(nodes, **kwargs))
    return generator.generate(), mission.triggers, generator


def _one_site() -> list[Any]:
    return [_node(IadsRole.SAM, [_pd_group("0001 | PD ONE", _point())])]


def test_off_by_default_emits_nothing() -> None:
    options = dict(DEFAULT_OPTIONS, **{"mantisiads.shoradScoot": False})
    emitted, triggers, _ = _generate(_one_site(), options=options)
    assert emitted == 0
    assert triggers.zones() == []


def test_shorad_link_off_emits_nothing() -> None:
    """Scooting rides on the SHORAD object; without it the zones are dead weight."""
    options = dict(DEFAULT_OPTIONS, **{"mantisiads.shoradLink": False})
    emitted, _, _ = _generate(_one_site(), options=options)
    assert emitted == 0


def test_plugin_off_emits_nothing() -> None:
    options = dict(DEFAULT_OPTIONS, mantisiads=False)
    emitted, _, _ = _generate(_one_site(), options=options)
    assert emitted == 0


def test_missing_plugin_settings_degrade_to_off() -> None:
    """A save from before the option existed must generate as it always did."""
    emitted, _, _ = _generate(_one_site(), options={})
    assert emitted == 0


def test_emits_requested_zone_count_per_site() -> None:
    emitted, triggers, _ = _generate(_one_site())
    assert emitted == 4
    assert len(triggers.zones()) == 4


def test_zones_are_hidden_and_share_the_bridge_prefix() -> None:
    """The prefix is the only thing tying these to SET_ZONE:FilterPrefixes."""
    _, triggers, _ = _generate(_one_site())
    for zone in triggers.zones():
        assert zone.name.startswith(SCOOT_ZONE_PREFIX)
        assert zone.hidden


def test_zone_names_are_unique() -> None:
    """MOOSE keys its zone database by name; a collision silently drops a zone."""
    nodes = [
        _node(IadsRole.SAM, [_pd_group("0001 | PD ONE", _point())]),
        _node(IadsRole.SAM, [_pd_group("0002 | PD TWO", _point(50_000, 0))]),
    ]
    _, triggers, _ = _generate(nodes)
    names = [z.name for z in triggers.zones()]
    assert len(names) == len(set(names)) == 8


def test_every_zone_lies_inside_moose_selection_window() -> None:
    """The contract with SHORAD:onafterShootAndScoot.

    It only considers zones between minscootdist and maxscootdist of the group.
    A zone outside that band is never selected, so emitting one is a silent
    no-op -- exactly the failure this pin exists to catch.
    """
    origin = _point()
    _, triggers, generator = _generate(
        [_node(IadsRole.SAM, [_pd_group("0001 | PD ONE", origin)])]
    )
    inner = generator.inner_radius.meters
    outer = generator.outer_radius.meters
    assert inner >= MOOSE_MIN_SCOOT_DISTANCE.meters
    for zone in triggers.zones():
        distance = origin.distance_to_point(zone.position)
        assert inner <= distance <= outer


def test_radius_option_is_capped_below_moose_hard_limit() -> None:
    """MOOSE's maxscootdist default is 3 km and it clamps nothing itself."""
    options = dict(DEFAULT_OPTIONS, **{"mantisiads.scootRadiusNm": 1.6})
    _, _, generator = _generate(_one_site(), options=options)
    assert generator.outer_radius.meters < 3000


def test_tiny_radius_is_floored_above_moose_minimum() -> None:
    options = dict(DEFAULT_OPTIONS, **{"mantisiads.scootRadiusNm": 0.01})
    _, triggers, generator = _generate(_one_site(), options=options)
    assert generator.outer_radius.meters > MOOSE_MIN_SCOOT_DISTANCE.meters
    assert generator.inner_radius.meters >= MOOSE_MIN_SCOOT_DISTANCE.meters
    assert len(triggers.zones()) == 4


def test_point_defense_shared_by_two_sams_is_one_site() -> None:
    """Mirrors collect_pd's dedupe: one group, one ring, not one ring per SAM."""
    shared = _pd_group("0001 | PD SHARED", _point())
    nodes = [_node(IadsRole.SAM, [shared]), _node(IadsRole.SAM, [shared])]
    emitted, _, _ = _generate(nodes)
    assert emitted == 4


def test_point_defense_under_a_non_sam_node_is_ignored() -> None:
    """collect_pd only scans Sam and SamAsEwr, so nothing else is in the set."""
    nodes = [_node(IadsRole.EWR, [_pd_group("0001 | PD ONE", _point())])]
    emitted, _, _ = _generate(nodes)
    assert emitted == 0


def test_sam_as_ewr_point_defense_is_included() -> None:
    nodes = [_node(IadsRole.SAM_AS_EWR, [_pd_group("0001 | PD ONE", _point())])]
    emitted, _, _ = _generate(nodes)
    assert emitted == 4


def test_non_point_defense_connections_are_ignored() -> None:
    comms = _pd_group("0001 | COMMS", _point())
    comms.iads_role = IadsRole.CONNECTION_NODE
    nodes = [_node(IadsRole.SAM, [comms])]
    emitted, _, _ = _generate(nodes)
    assert emitted == 0


def test_dead_point_defense_gets_no_zones() -> None:
    nodes = [_node(IadsRole.SAM, [_pd_group("0001 | PD ONE", _point(), alive=False)])]
    emitted, _, _ = _generate(nodes)
    assert emitted == 0


def test_culled_site_gets_no_zones() -> None:
    emitted, _, _ = _generate(_one_site(), culled=True)
    assert emitted == 0


def test_water_only_surroundings_emit_nothing() -> None:
    """A site with no driveable land around it must not get sea destinations."""
    emitted, triggers, _ = _generate(_one_site(), on_land=False)
    assert emitted == 0
    assert triggers.zones() == []


def test_placement_is_deterministic_for_a_regenerated_turn() -> None:
    first = [z.position for z in _generate(_one_site())[1].zones()]
    second = [z.position for z in _generate(_one_site())[1].zones()]
    assert first == second


BRIDGE = Path("resources/plugins/mantisiads/mantis-config.lua")


def test_bridge_filters_on_this_modules_prefix() -> None:
    """The prefix is the entire contract between the two files.

    A rename on either side leaves the bridge building an empty SET_ZONE and
    the miz full of zones nothing reads -- with no error anywhere.
    """
    assert f'SCOOT_ZONE_PREFIX = "{SCOOT_ZONE_PREFIX}"' in BRIDGE.read_text()


def test_bridge_inner_radius_matches_this_modules_ring() -> None:
    """The other half of the distance-window contract.

    The generator rings sites from INNER_RADIUS_FRACTION of the radius outward;
    the bridge writes the matching minscootdist onto the SHORAD object. If they
    drift apart MOOSE filters out zones it was just handed.
    """
    assert f"scootRadius * {INNER_RADIUS_FRACTION}" in BRIDGE.read_text()


def test_bridge_clamps_to_the_same_floor_as_this_module() -> None:
    """A radius under the floor inverts min/max and nothing is ever selectable."""
    floor = int((MOOSE_MIN_SCOOT_DISTANCE * 2).meters)
    assert f"* 1852, {floor}), 3000)" in BRIDGE.read_text()


def test_distinct_sites_get_distinct_rings() -> None:
    a = _generate([_node(IadsRole.SAM, [_pd_group("0001 | PD A", _point())])])[1]
    b = _generate([_node(IadsRole.SAM, [_pd_group("0002 | PD B", _point())])])[1]
    assert [z.position for z in a.zones()] != [z.position for z in b.zones()]
