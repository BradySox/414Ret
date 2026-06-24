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
