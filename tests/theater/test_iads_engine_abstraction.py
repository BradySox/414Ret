"""IADS-engine abstraction seams introduced for the Skynet -> MANTIS migration.

These guard the engine-agnostic renames and the single named Skynet
serialization seam, so the Skynet Lua output stays byte-identical while new
MANTIS code can avoid referencing Skynet by name. See
docs/dev/design/414th-mantis-migration-notes.md (§3) and the parity matrix.
"""

from types import SimpleNamespace
from typing import Any

from game.dcs.groundunittype import IadsProperties, SkynetProperties
from game.theater.iadsnetwork.iadsnetwork import IadsNode, SkynetNode
from game.theater.iadsnetwork.iadsrole import IadsRole
from game.theater.player import Player


def test_skynet_properties_is_alias_of_iads_properties() -> None:
    # Old name must remain a true alias so existing imports keep working.
    assert SkynetProperties is IadsProperties


def test_skynet_node_is_alias_of_iads_node() -> None:
    assert SkynetNode is IadsNode


def test_iads_properties_from_data_normalises_values() -> None:
    props = IadsProperties.from_data(
        {
            "can_engage_harm": True,
            "can_engage_air_weapon": False,
            "go_live_range_in_percent": 80,
            "harm_detection_chance": 0.5,
            "autonomous_behaviour": True,
        }
    )
    # Booleans are lowercased strings; numbers are stringified.
    assert props.can_engage_harm == "true"
    assert props.can_engage_air_weapon == "false"
    assert props.go_live_range_in_percent == "80"
    assert props.harm_detection_chance == "0.5"
    assert props.autonomous_behaviour == "True"


def test_iads_properties_to_dict_omits_unset_fields() -> None:
    assert IadsProperties.from_data({}).to_dict() == {}
    populated = IadsProperties.from_data(
        {"can_engage_harm": True, "go_live_range_in_percent": 100}
    )
    assert populated.to_dict() == {
        "can_engage_harm": "true",
        "go_live_range_in_percent": "100",
    }


def test_skynet_value_matches_enum_value_for_every_role() -> None:
    # The named seam must be a faithful pass-through of the Skynet token today.
    for role in IadsRole:
        assert role.skynet_value == role.value


def test_skynet_value_tokens_are_locked() -> None:
    # These strings are the literal Skynet Lua table keys; changing them would
    # silently break the generated mission. Lock them.
    assert IadsRole.SAM.skynet_value == "Sam"
    assert IadsRole.SAM_AS_EWR.skynet_value == "SamAsEwr"
    assert IadsRole.POINT_DEFENSE.skynet_value == "PD"
    assert IadsRole.EWR.skynet_value == "Ewr"
    assert IadsRole.CONNECTION_NODE.skynet_value == "ConnectionNode"
    assert IadsRole.POWER_SOURCE.skynet_value == "PowerSource"
    assert IadsRole.COMMAND_CENTER.skynet_value == "CommandCenter"
    assert IadsRole.NO_BEHAVIOR.skynet_value == "NoBehavior"


# Returns Any so the duck-typed stubs satisfy the IadsGroundGroup parameter type
# of the methods under test (matching how other theater tests fake objects).
def _group(iads_role: IadsRole, *, group_name: str, units: list[Any]) -> Any:
    return SimpleNamespace(
        iads_role=iads_role,
        group_name=group_name,
        units=units,
        ground_object=SimpleNamespace(coalition=SimpleNamespace(player=Player.BLUE)),
    )


def test_iads_node_from_group_uses_group_name_for_sam() -> None:
    group = _group(
        IadsRole.SAM,
        group_name="SAM-1",
        units=[SimpleNamespace(alive=True, unit_type=None, unit_name="u1")],
    )
    node = IadsNode.from_group(group)
    assert node.dcs_name == "SAM-1"
    assert node.iads_role is IadsRole.SAM
    assert node.player is Player.BLUE
    # unit_type is not a GroundUnitType, so no properties are attached.
    assert node.properties == {}


def test_iads_node_dcs_name_uses_unit_name_for_ewr() -> None:
    group = _group(
        IadsRole.EWR,
        group_name="EWR-group",
        units=[SimpleNamespace(alive=True, unit_type=None, unit_name="ewr-unit-1")],
    )
    assert IadsNode.dcs_name_for_group(group) == "ewr-unit-1"


# --- A destroyed C2 node must survive in the exported graph -------------------
# The runtime reads each SAM's comms/power dependency, and the coalition's
# command-centre list, from what iads_nodes() emits. Dropping a dead node dropped
# the dependency with it, so the degradation lasted exactly one mission: from the
# next turn the SAMs behind a bombed power station came back fully operational,
# and killing every command centre restored perfect command instead of removing
# it. Found in juanjux/dcs-retribution#97 against Skynet; the same hole was live
# here against MANTIS.


def _c2_group(
    iads_role: IadsRole, *, name: str, alive: bool, player: Player = Player.BLUE
) -> Any:
    ground_object = SimpleNamespace(
        coalition=SimpleNamespace(player=player),
        is_friendly=lambda other, _p=player: other is _p,
    )
    return SimpleNamespace(
        iads_role=iads_role,
        group_name=name,
        units=[
            SimpleNamespace(alive=alive, unit_type=None, unit_name=name, is_static=True)
        ],
        ground_object=ground_object,
    )


def _network(*nodes: Any) -> Any:
    from game.theater.iadsnetwork.iadsnetwork import IadsNetwork

    network = IadsNetwork(True, [])
    network.nodes = list(nodes)
    return network


def _node(group: Any, connections: list[Any] | None = None) -> Any:
    return SimpleNamespace(
        group=group,
        connections={i: c for i, c in enumerate(connections or [])},
    )


_GAME = SimpleNamespace(iads_considerate_culling=lambda tgo: False)


def test_dead_power_source_stays_a_connection_of_its_sam() -> None:
    sam = _c2_group(IadsRole.SAM, name="SAM-1", alive=True)
    power = _c2_group(IadsRole.POWER_SOURCE, name="power-1", alive=False)
    nodes = _network(_node(sam, [power])).iads_nodes(_GAME)
    assert len(nodes) == 1
    assert nodes[0].connections["PowerSource"] == ["power-1"]


def test_dead_point_defence_is_still_dropped_from_its_sam() -> None:
    # Only C2 edges are kept: a dead PD group is not a dependency, it is a corpse.
    sam = _c2_group(IadsRole.SAM, name="SAM-1", alive=True)
    pd = _c2_group(IadsRole.POINT_DEFENSE, name="pd-1", alive=False)
    nodes = _network(_node(sam, [pd])).iads_nodes(_GAME)
    assert nodes[0].connections["PD"] == []


def test_dead_command_center_is_still_exported() -> None:
    cc = _c2_group(IadsRole.COMMAND_CENTER, name="cc-1", alive=False)
    nodes = _network(_node(cc)).iads_nodes(_GAME)
    assert [n.dcs_name for n in nodes] == ["cc-1"]


def test_dead_sam_node_is_dropped() -> None:
    sam = _c2_group(IadsRole.SAM, name="SAM-1", alive=False)
    assert _network(_node(sam)).iads_nodes(_GAME) == []


def test_dead_c2_names_lists_only_destroyed_c2_nodes() -> None:
    network = _network(
        _node(_c2_group(IadsRole.POWER_SOURCE, name="power-dead", alive=False)),
        _node(_c2_group(IadsRole.POWER_SOURCE, name="power-alive", alive=True)),
        _node(_c2_group(IadsRole.COMMAND_CENTER, name="cc-dead", alive=False)),
        _node(_c2_group(IadsRole.SAM, name="SAM-dead", alive=False)),
    )
    assert network.dead_c2_names(_GAME) == {Player.BLUE: ["power-dead", "cc-dead"]}
