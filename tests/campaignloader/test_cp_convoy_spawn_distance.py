"""A convoy spawn marker only serves the endpoint it was authored at.

``_find_closest_cp_spawn`` had no distance bound, so it returned the nearest
``M1043 HMMWV Armament`` marker *anywhere on the map*. Measured across the 26
shipped campaigns that author them, 308 of 388 route endpoints have their marker
within 2 km -- but 60-odd were claiming one 10-447 km away (Red Tide had two at
~171 km, Desert Storm one at 447 km). Two consequences, both bad:

* ``_interpolate_points`` builds the chain from the *endpoint* toward that
  marker, so the convoy was strung out in the wrong direction entirely.
* An authored chain is respected wholesale by ``ConvoyGenerator``, which
  suppressed the runway-clearance guard. On Caucasus - Slava Ukraini this parked
  eight T-80UDs across Anapa's runway 22 while eight AI flights taxied out.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence

from dcs.mapping import Point

from game.campaignloader.mizcampaignloader import MizCampaignLoader


def point(x: float, y: float) -> Point:
    return Point(x, y, None)  # type: ignore[arg-type]


@dataclass
class FakeMarker:
    position: Point


class LoaderWithMarkers(MizCampaignLoader):
    """Only the marker pool matters here, so skip the miz/theater machinery."""

    def __init__(self, markers: Sequence[FakeMarker]) -> None:
        self._markers = markers

    @property
    def cp_convoy_spawns(self) -> Iterator[FakeMarker]:  # type: ignore[override]
        return iter(self._markers)


ENDPOINT = point(0, 0)


def marker_at(distance: float) -> FakeMarker:
    return FakeMarker(point(distance, 0))


def test_a_marker_at_the_endpoint_is_claimed() -> None:
    near = marker_at(80)
    loader = LoaderWithMarkers([near])

    assert loader._find_closest_cp_spawn(ENDPOINT) is near


def test_a_marker_belonging_to_another_route_is_not_claimed() -> None:
    # The Slava Ukraini case: the nearest marker to Anapa's Novorossiysk
    # corridor served the Maykop front route 9.4 km away.
    loader = LoaderWithMarkers([marker_at(9_400)])

    assert loader._find_closest_cp_spawn(ENDPOINT) is None


def test_the_nearest_marker_still_wins_inside_the_bound() -> None:
    near = marker_at(400)
    loader = LoaderWithMarkers([marker_at(4_000), near, marker_at(120_000)])

    assert loader._find_closest_cp_spawn(ENDPOINT) is near


def test_a_distant_marker_does_not_mask_a_usable_one() -> None:
    # Order matters: the far marker is seen first, so a bound applied only to
    # the running "closest" would have discarded the usable one with it.
    near = marker_at(1_000)
    loader = LoaderWithMarkers([marker_at(447_000), near])

    assert loader._find_closest_cp_spawn(ENDPOINT) is near


def test_the_bound_is_inclusive_at_its_edge() -> None:
    edge = marker_at(MizCampaignLoader.MAX_CP_CONVOY_SPAWN_DISTANCE_M)
    loader = LoaderWithMarkers([edge])

    assert loader._find_closest_cp_spawn(ENDPOINT) is edge


def test_no_markers_at_all_is_not_an_error() -> None:
    assert LoaderWithMarkers([])._find_closest_cp_spawn(ENDPOINT) is None
