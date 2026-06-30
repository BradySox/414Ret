"""Guard the 414th's tamed altitude winds.

Upstream's weather archetypes ramp the wind hard with altitude: the generator adds each
layer's Weibull scale onto the layer below (see ``WeibullWindSpeedGenerator.random_wind``),
so 8000m wind ~= ground + scale_2000m + scale_8000m. Upstream's 18-22 kt upper scales put
~45-60 kt winds aloft; the 414th pulled them down so winds stay flyable. This fails CI if an
upstream merge bumps the upper-level scales back up.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from game.utils import knots
from game.weather.weatherarchetype import WeatherArchetype
from game.weather.windspeedgenerators import WeibullWindSpeedGenerator

_ARCHETYPES = (
    Path(__file__).resolve().parents[1] / "resources" / "weather" / "archetypes"
)

# 414th cap on the upper-level Weibull scale (knots) -- tamed from upstream's 18-22. The
# additive model means each of these stacks on the layer below, so the cap keeps 8000m
# winds in a flyable band.
_MAX_UPPER_SCALE_KTS = 14.0


@pytest.mark.parametrize("archetype_id", ["clear", "cloudy", "raining", "thunderstorm"])
def test_upper_level_wind_scales_are_tamed(archetype_id: str) -> None:
    speed = WeatherArchetype.from_yaml(
        _ARCHETYPES / f"{archetype_id}.yaml"
    ).wind_parameters.speed
    assert isinstance(speed, WeibullWindSpeedGenerator)
    cap = knots(_MAX_UPPER_SCALE_KTS).meters_per_second
    assert speed.at_2000m.scale.meters_per_second <= cap, (
        f"{archetype_id}: at_2000m wind scale exceeds the 414th cap "
        f"({_MAX_UPPER_SCALE_KTS} kts) -- winds aloft regressed (upstream re-clobber?)."
    )
    assert speed.at_8000m.scale.meters_per_second <= cap, (
        f"{archetype_id}: at_8000m wind scale exceeds the 414th cap "
        f"({_MAX_UPPER_SCALE_KTS} kts) -- winds aloft regressed (upstream re-clobber?)."
    )
