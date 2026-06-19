from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from game.server.iadsnetwork.models import IadsConnectionJs
from game.theater import Player
from game.threatzones import ThreatZones


def test_enemy_threat_zones_exclude_unknown_air_defenses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    known = MagicMock(has_aa=True)
    known.known_for.return_value = True
    unknown = MagicMock(has_aa=True)
    unknown.known_for.return_value = False
    control_point = SimpleNamespace(ground_objects=[known, unknown])
    game = MagicMock()
    game.theater.control_points_for.return_value = [control_point]
    game.theater.conflicts.return_value = []
    expected = MagicMock()

    def capture_threats(
        theater: Any,
        doctrine: Any,
        barcap_locations: Any,
        air_defenses: Any,
        front_line_zones: Any = (),
        viewer: Player | None = None,
    ) -> Any:
        assert list(air_defenses) == [known]
        assert viewer is Player.BLUE
        return expected

    monkeypatch.setattr(ThreatZones, "for_threats", capture_threats)

    assert ThreatZones.for_faction(game, Player.RED, viewer=Player.BLUE) is expected


def test_unknown_iads_endpoint_hides_connection() -> None:
    node_tgo = MagicMock()
    node_tgo.hidden_on_player_map.return_value = False
    node_tgo.known_for.return_value = True
    connected_tgo = MagicMock()
    connected_tgo.hidden_on_player_map.return_value = False
    connected_tgo.known_for.return_value = False
    connected_group = MagicMock(ground_object=connected_tgo)
    node = MagicMock()
    node.group.ground_object = node_tgo
    node.connections = {uuid4(): connected_group}

    assert IadsConnectionJs.connections_for_node(node, Player.BLUE) == []


def test_unknown_iads_node_hides_all_connections() -> None:
    node_tgo = MagicMock()
    node_tgo.hidden_on_player_map.return_value = False
    node_tgo.known_for.return_value = False
    node = MagicMock()
    node.group.ground_object = node_tgo
    node.connections = {uuid4(): MagicMock()}

    assert IadsConnectionJs.connections_for_node(node, Player.BLUE) == []
