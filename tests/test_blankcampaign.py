"""Unit tests for the blank-canvas save-as-campaign serializer + rebuild routing.

The full terrain round-trip (build → serialize → load_theater → generate) loads a
heavy DCS terrain and is verified headlessly; here we pin the pure logic with fakes:
the task→preset map is valid, serialization captures the right sites/ownership, the
rebuild routes each site onto the correct PresetLocations list, and the campaign
document stamps a non-stale version with no `miz`.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional
from unittest.mock import MagicMock

from game.campaignloader.blankcampaign import (
    _TASK_TO_PRESET,
    _apply_sites,
    _task_by_name,
    blank_campaign_document,
    serialize_blank_campaign,
)
from game.data.groups import GroupTask
from game.theater.controlpoint import Airfield, PresetLocations
from game.theater.player import Player
from game.version import CAMPAIGN_FORMAT_VERSION


def _airfield(name: str, side: Player) -> Any:
    # A real Airfield instance (so isinstance checks pass) without the heavy
    # __init__ — set only the attributes the serializer/rebuild touch.
    cp = Airfield.__new__(Airfield)
    cp.airport = SimpleNamespace(name=name)  # type: ignore[assignment]
    # `captured` is a read-only property returning the live coalition's player.
    cp.starting_coalition = side
    cp._coalition = SimpleNamespace(player=side)  # type: ignore[assignment]
    cp.preset_locations = PresetLocations()
    return cp


def _tgo(task: Optional[GroupTask], cp: Any, x: float, y: float) -> Any:
    return SimpleNamespace(
        task=task, control_point=cp, position=SimpleNamespace(x=x, y=y)
    )


def test_task_to_preset_fields_exist_on_presetlocations() -> None:
    # A typo'd preset field name would silently drop a whole class of site on
    # rebuild; pin every mapping value to a real list attribute.
    pl = PresetLocations()
    for task, field in _TASK_TO_PRESET.items():
        assert hasattr(pl, field), f"{task.name} -> '{field}' is not on PresetLocations"
        assert isinstance(getattr(pl, field), list)


def test_task_by_name_round_trips_and_tolerates_garbage() -> None:
    assert _task_by_name("SHORAD") is GroupTask.SHORAD
    assert _task_by_name(None) is None
    assert _task_by_name("NOT_A_TASK") is None


def test_serialize_captures_ownership_and_rebuildable_sites() -> None:
    blue = _airfield("Anapa", Player.BLUE)
    red = _airfield("Krymsk", Player.RED)
    neutral = _airfield("Gray", Player.NEUTRAL)

    ground_objects = [
        _tgo(GroupTask.SHORAD, blue, 1.0, 2.0),
        _tgo(GroupTask.BASE_DEFENSE, red, 3.0, 4.0),
        _tgo(GroupTask.FUEL, blue, 5.0, 6.0),  # no preset generator -> skipped
        _tgo(None, blue, 7.0, 8.0),  # dynamic/untasked -> skipped
        _tgo(GroupTask.SHORAD, neutral, 9.0, 9.0),  # neutral CP -> skipped
    ]
    game = SimpleNamespace(
        theater=SimpleNamespace(
            controlpoints=[blue, red, neutral], ground_objects=ground_objects
        )
    )

    desc = serialize_blank_campaign(game)  # type: ignore[arg-type]

    assert desc["ownership"] == {"Anapa": "blue", "Krymsk": "red"}  # no neutral
    assert desc["sites"] == [
        {"anchor": "Anapa", "side": "blue", "task": "SHORAD", "x": 1.0, "y": 2.0},
        {"anchor": "Krymsk", "side": "red", "task": "BASE_DEFENSE", "x": 3.0, "y": 4.0},
    ]


def test_apply_sites_routes_each_task_to_its_preset_list() -> None:
    anapa = _airfield("Anapa", Player.BLUE)
    krymsk = _airfield("Krymsk", Player.RED)
    theater = SimpleNamespace(controlpoints=[anapa, krymsk], terrain=MagicMock())

    sites = [
        {"anchor": "Anapa", "side": "blue", "task": "SHORAD", "x": 1.0, "y": 2.0},
        {
            "anchor": "Anapa",
            "side": "blue",
            "task": "EARLY_WARNING_RADAR",
            "x": 3,
            "y": 4,
        },
        {"anchor": "Krymsk", "side": "red", "task": "BASE_DEFENSE", "x": 5, "y": 6},
        {
            "anchor": "Nowhere",
            "side": "red",
            "task": "SHORAD",
            "x": 7,
            "y": 8,
        },  # dropped
        {"anchor": "Krymsk", "side": "red", "task": "FUEL", "x": 9, "y": 9},  # unmapped
    ]

    placed = _apply_sites(theater, sites)  # type: ignore[arg-type]

    assert placed == 3
    assert len(anapa.preset_locations.short_range_sams) == 1
    assert len(anapa.preset_locations.ewrs) == 1
    assert len(krymsk.preset_locations.armor_groups) == 1
    assert anapa.preset_locations.short_range_sams[0].x == 1.0


def test_campaign_document_stamps_current_version_and_has_no_miz() -> None:
    game = SimpleNamespace(
        theater=SimpleNamespace(
            controlpoints=[],
            ground_objects=[],
            terrain=SimpleNamespace(name="Caucasus"),
            iads_network=SimpleNamespace(advanced_iads=False),
        ),
        blue=SimpleNamespace(faction=SimpleNamespace(name="USA 2005"), budget=2000),
        red=SimpleNamespace(faction=SimpleNamespace(name="Russia 2010"), budget=1500),
    )

    doc = blank_campaign_document(game, name="My War")  # type: ignore[arg-type]

    major, minor = CAMPAIGN_FORMAT_VERSION
    assert doc["version"] == f"{major}.{minor}"  # not version-gated out
    assert doc["theater"] == "Caucasus"
    assert doc["recommended_player_faction"] == "USA 2005"
    assert "miz" not in doc
    assert "blank_canvas" in doc and "ownership" in doc["blank_canvas"]
