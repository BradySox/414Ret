"""§96: the neutral-border map payload the planning UI draws.

The border is authored in terrain XY and drawn by Leaflet in lat/lng, so the
conversion is the thing worth pinning: a silently wrong transform puts a
44-vertex ring somewhere plausible-looking and nobody notices until a player
routes around empty sky. The Lebanon fixture's real bounding box is the oracle.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

from dcs.terrain.syria import Syria

from game.server.game.models import NeutralBorderJs
from game.theater.neutralborder import NeutralBorderZone

# Lebanon's real extent, with a 0.1 degree (~11 km) margin. Tight enough that a
# broken transform cannot pass -- those land in the wrong country or the wrong
# hemisphere, not 11 km off -- and loose enough not to be brittle against the
# simplifier's vertex placement.
MARGIN = 0.1
LEBANON_LAT = (33.05 - MARGIN, 34.69 + MARGIN)
LEBANON_LNG = (35.10 - MARGIN, 36.62 + MARGIN)


def _zone() -> NeutralBorderZone:
    zone = NeutralBorderZone.from_yaml(
        {
            "country": "Lebanon",
            "airfield": "Rayak",
            "aircraft": "MiG-29A",
            "floor_ft": 10000,
            "sam": True,
            # A coarse box inside Lebanon is enough to prove the transform; the
            # shipped campaign carries the real 44-vertex trace.
            "border": [
                [-37713, 38996],
                [-211351, -80947],
                [-217426, -55276],
                [-44380, 42821],
            ],
        }
    )
    assert zone is not None
    return zone


def _game(enabled: bool = True, zones: list[Any] | None = None) -> Any:
    return SimpleNamespace(
        settings=SimpleNamespace(neutral_border_defense=enabled),
        current_day=date(2022, 6, 4),
        blue=SimpleNamespace(faction=SimpleNamespace(country=None)),
        theater=SimpleNamespace(
            neutral_border_zones=[_zone()] if zones is None else zones,
            terrain=Syria(),
        ),
    )


def test_border_converts_to_real_lebanese_coordinates() -> None:
    borders = NeutralBorderJs.all_in_game(_game())
    assert len(borders) == 1
    border = borders[0]
    assert border.country == "Lebanon"
    assert border.airfield == "Rayak"
    assert border.floor_ft == 10000

    # One ring, no holes -- the Leaflet array-of-arrays contract.
    assert len(border.border) == 1
    ring = border.border[0]
    assert len(ring) == 4

    lats = [p.lat for p in ring]
    lngs = [p.lng for p in ring]
    assert LEBANON_LAT[0] <= min(lats) and max(lats) <= LEBANON_LAT[1]
    assert LEBANON_LNG[0] <= min(lngs) and max(lngs) <= LEBANON_LNG[1]


def test_setting_off_hides_the_layer() -> None:
    assert NeutralBorderJs.all_in_game(_game(enabled=False)) == []


def test_no_authored_zones_hides_the_layer() -> None:
    assert NeutralBorderJs.all_in_game(_game(zones=[])) == []


def test_theater_without_the_attribute_is_tolerated() -> None:
    """An old save predates neutral_border_zones; the payload must not raise."""
    game = SimpleNamespace(
        settings=SimpleNamespace(neutral_border_defense=True),
        current_day=date(2022, 6, 4),
        blue=SimpleNamespace(faction=SimpleNamespace(country=None)),
        theater=SimpleNamespace(terrain=Syria()),
    )
    assert NeutralBorderJs.all_in_game(game) == []  # type: ignore[arg-type]


# -- the map must not promise an interception the mission will not fly ----------


def _toothless_zone() -> NeutralBorderZone:
    """A neutral with an origin but no airframe: DCS models no Turkmenistan, and
    Cyprus, Armenia, Azerbaijan and Argentina have no entry in the dated table."""
    zone = NeutralBorderZone.from_yaml(
        {
            "country": "Turkmenistan",
            "airfield": "Rayak",
            "border": [
                [-37713, 38996],
                [-211351, -80947],
                [-217426, -55276],
                [-44380, 42821],
            ],
        }
    )
    assert zone is not None
    return zone


def test_a_country_that_cannot_launch_is_not_drawn_as_closed() -> None:
    """The generator degrades it to drawn-and-toothless, so the map has to agree.

    It did not until 2026-08-27: the map computed enforcement from posture and
    consent alone and never asked whether the country could put a fighter up.
    Measured across the shipped terrains, 14 zones were drawn "closed to you at
    any altitude" over a mission that let you fly straight through them --
    Cyprus and Iraq on Syria, Armenia and Azerbaijan on Caucasus. The feature
    exists to be planned against, so overstating the threat is the expensive
    direction of wrong: you route around nothing and stop trusting the layer.
    """
    borders = NeutralBorderJs.all_in_game(_game(zones=[_toothless_zone()]))
    assert len(borders) == 1
    assert borders[0].overflight is True, "a country that cannot launch read closed"
    assert "permitted" in borders[0].airfield


def test_a_country_that_can_launch_is_still_drawn_as_closed() -> None:
    """The control: the fix must not open every border it touches."""
    borders = NeutralBorderJs.all_in_game(_game())
    assert len(borders) == 1
    assert borders[0].overflight is False, "a defended border was opened"
