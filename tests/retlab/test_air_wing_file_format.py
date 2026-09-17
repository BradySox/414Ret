"""A saved air wing file must say which coalition each half belongs to.

Save built its payload from `self.tab_widget.currentWidget()`, so it wrote only
the side whose tab was in front and the file recorded nothing about which side
that was. Saving Red over a file holding Blue replaced it silently, and loading
a Red file with the Blue tab open handed blue the enemy's squadrons.

Files written before that fix are a bare control-point mapping. They cannot be
told apart by their side, so they must still load the old way rather than be
guessed at -- these tests pin the detection in both directions.
"""

from typing import Any

import pytest

from qt_ui.windows.AirWingConfigurationDialog import (
    AIR_WING_FILE_VERSION,
    BLUE,
    RED,
    air_wing_coalitions,
)

# Shape of one squadron entry, as _build_air_wing writes it.
SQUADRON: dict[str, Any] = {
    "primary": "BARCAP",
    "secondary": [],
    "aircraft": ["MiG-29S Fulcrum-C"],
    "aircraft_type": "MiG-29S Fulcrum-C",
    "size": 12,
    "country": "Russia",
}

# A file saved before the fix: control points at the top level, no marker. The
# integer key and the "Blue CV" string key are both real -- _build_air_wing uses
# the control point id, or its full name for a Point-based location.
LEGACY: dict[Any, Any] = {26: [SQUADRON], "Blue CV": [SQUADRON]}

VERSIONED: dict[str, Any] = {
    "version": AIR_WING_FILE_VERSION,
    "coalitions": {BLUE: {25: [SQUADRON]}, RED: {26: [SQUADRON]}},
}


def test_a_versioned_file_yields_both_sides() -> None:
    found = air_wing_coalitions(VERSIONED)
    assert found is not None
    assert set(found) == {BLUE, RED}
    assert found[RED] == {26: [SQUADRON]}


def test_a_versioned_file_may_carry_one_side() -> None:
    found = air_wing_coalitions({"version": 2, "coalitions": {RED: {26: [SQUADRON]}}})
    assert found is not None
    assert set(found) == {RED}


@pytest.mark.parametrize(
    "document",
    [
        pytest.param(LEGACY, id="control-points-at-top-level"),
        pytest.param({}, id="empty"),
        pytest.param(None, id="empty-file"),
        pytest.param([SQUADRON], id="not-a-mapping"),
        # A control point can be named, so guard against a name collision being
        # read as the new format.
        pytest.param({"coalitions": [SQUADRON]}, id="coalitions-not-a-mapping"),
        pytest.param({"coalitions": {"Blue CV": [SQUADRON]}}, id="unrecognized-side"),
        pytest.param({"coalitions": {BLUE: "nonsense"}}, id="payload-not-a-mapping"),
    ],
)
def test_anything_not_clearly_versioned_reads_as_legacy(document: Any) -> None:
    # Legacy means "load into the current tab", which is the old behaviour and
    # always safe. Guessing a side from the squadrons would be wrong for a
    # mixed-country wing.
    assert air_wing_coalitions(document) is None


def test_unknown_sides_are_dropped_but_known_ones_survive() -> None:
    found = air_wing_coalitions(
        {"version": 2, "coalitions": {BLUE: {25: [SQUADRON]}, "green": {1: []}}}
    )
    assert found is not None
    assert set(found) == {BLUE}
