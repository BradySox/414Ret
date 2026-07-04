"""Continuous campaign clock + evolving weather (feature §47).

Exercises the two levers that make a campaign flow as one timeline:
`Conditions.advance` (a monotonic clock marched forward from the previous turn)
and the previous-turn weather bias in `Conditions.generate_weather`.
"""

from __future__ import annotations

import datetime

from game.theater.daytimemap import DaytimeMap
from game.theater.seasonalconditions import (
    Season,
    SeasonalConditions,
    WeatherTypeChances,
)
from game.timeofday import TimeOfDay
from game.weather.conditions import (
    MAX_TURN_ADVANCE_HOURS,
    MIN_TURN_ADVANCE_HOURS,
    Conditions,
)
from game.weather.weather import ClearSkies, Cloudy, Raining, Thunderstorm, Weather

# Whole-hour daytime bands (the DaytimeMap contract), Caucasus-like.
_DAYTIME = DaytimeMap(
    dawn=(datetime.time(6), datetime.time(8)),
    day=(datetime.time(8), datetime.time(16)),
    dusk=(datetime.time(16), datetime.time(20)),
    night=(datetime.time(20), datetime.time(23)),
)


def _seasonal(chances: WeatherTypeChances | None = None) -> SeasonalConditions:
    if chances is None:
        chances = WeatherTypeChances(
            thunderstorm=1.0, raining=1.0, cloudy=1.0, clear_skies=1.0
        )
    return SeasonalConditions(
        summer_avg_pressure=30.0,
        winter_avg_pressure=30.0,
        summer_avg_temperature=25.0,
        winter_avg_temperature=5.0,
        temperature_day_night_difference=10.0,
        high_avg_yearly_turbulence_per_10cm=1.0,
        low_avg_yearly_turbulence_per_10cm=0.1,
        solar_noon_turbulence_per_10cm=0.5,
        midnight_turbulence_per_10cm=0.1,
        weather_type_chances={season: chances for season in Season},
    )


class _FakeTheater:
    def __init__(self, seasonal: SeasonalConditions, daytime: DaytimeMap) -> None:
        self.seasonal_conditions = seasonal
        self.daytime_map = daytime


def _seed(seasonal: SeasonalConditions, weather: Weather | None = None) -> Conditions:
    start = datetime.datetime(2020, 6, 15, 8, 0)
    if weather is None:
        weather = ClearSkies(seasonal, start.date(), TimeOfDay.Day)
    return Conditions(time_of_day=TimeOfDay.Day, start_time=start, weather=weather)


def test_advance_marches_clock_forward_monotonically() -> None:
    seasonal = _seasonal()
    theater = _FakeTheater(seasonal, _DAYTIME)
    conditions = _seed(seasonal)

    previous = conditions.start_time
    for _ in range(200):
        conditions = Conditions.advance(conditions, theater)  # type: ignore[arg-type]
        delta = conditions.start_time - previous
        # Strictly forward, within the believable per-turn band.
        assert delta >= datetime.timedelta(hours=MIN_TURN_ADVANCE_HOURS)
        assert delta <= datetime.timedelta(hours=MAX_TURN_ADVANCE_HOURS)
        # Time of day is derived from the marched clock, not a rotation.
        assert conditions.time_of_day == _DAYTIME.best_guess_time_of_day_at(
            conditions.start_time.time()
        )
        # Missions still land on the hour.
        assert conditions.start_time.minute == 0
        previous = conditions.start_time


def test_advance_rolls_the_date_at_midnight() -> None:
    seasonal = _seasonal()
    theater = _FakeTheater(seasonal, _DAYTIME)
    # Seed late in the day so the first few advances cross midnight.
    late = Conditions(
        time_of_day=TimeOfDay.Night,
        start_time=datetime.datetime(2020, 6, 15, 22, 0),
        weather=ClearSkies(seasonal, datetime.date(2020, 6, 15), TimeOfDay.Night),
    )
    advanced = Conditions.advance(late, theater)  # type: ignore[arg-type]
    # 22:00 + at least 3h crosses midnight into the next day.
    assert advanced.start_time.date() == datetime.date(2020, 6, 16)


def test_weather_biases_toward_previous_turn() -> None:
    # Equal seasonal chances: any bias is purely the persistence kernel.
    seasonal = _seasonal()
    day = datetime.date(2020, 6, 15)
    previous = ClearSkies(seasonal, day, TimeOfDay.Day)

    counts = {ClearSkies: 0, Cloudy: 0, Raining: 0, Thunderstorm: 0}
    for _ in range(4000):
        weather = Conditions.generate_weather(
            seasonal, day, TimeOfDay.Day, previous=previous
        )
        counts[type(weather)] += 1

    total = sum(counts.values())
    # Clear (the previous rung) dominates, and the far rung (Thunderstorm) is
    # the rarest -- a clear ordering the memoryless draw (all ~25%) never has.
    assert counts[ClearSkies] / total > 0.4
    assert counts[ClearSkies] > counts[Cloudy] > counts[Raining] > counts[Thunderstorm]


def _weather_chain(seasonal: SeasonalConditions, n: int) -> list[type[Weather]]:
    day = datetime.date(2020, 6, 15)
    previous: Weather = ClearSkies(seasonal, day, TimeOfDay.Day)
    seq: list[type[Weather]] = []
    for _ in range(n):
        previous = Conditions.generate_weather(
            seasonal, day, TimeOfDay.Day, previous=previous
        )
        seq.append(type(previous))
    return seq


def test_weather_preserves_seasonal_climatology_over_a_chain() -> None:
    # The whole point: persistence must NOT skew the long-run mix. A naive
    # seasonal*kernel reweight halved the rain frequency (measured); the
    # Metropolis-Hastings evolution keeps the marginal at the authored season.
    # Caucasus-summer-like chances (clear-heavy, so the skew bug bit hardest).
    chances = WeatherTypeChances(
        thunderstorm=1.0, raining=10.0, cloudy=35.0, clear_skies=55.0
    )
    seasonal = _seasonal(chances)
    total = (
        chances.thunderstorm + chances.raining + chances.cloudy + chances.clear_skies
    )
    target = {
        ClearSkies: chances.clear_skies / total,
        Cloudy: chances.cloudy / total,
        Raining: chances.raining / total,
        Thunderstorm: chances.thunderstorm / total,
    }

    n = 40000
    names = [wtype.__name__ for wtype in _weather_chain(seasonal, n)]
    for wtype, want in target.items():
        got = names.count(wtype.__name__) / n
        # Within ~2.5pp of the authored climatology (sampling noise), NOT the
        # 5-8pp skew the naive kernel produced. In particular rain stays ~10%.
        assert abs(got - want) < 0.025, f"{wtype.__name__}: {got:.3f} vs {want:.3f}"


def test_weather_persists_across_a_chain() -> None:
    # Autocorrelation is real: consecutive turns usually hold, and when weather
    # changes it steps to an adjacent rung far more than it jumps across the
    # ladder -- fronts roll in and clear rather than teleporting.
    seasonal = _seasonal()
    n = 20000
    seq = _weather_chain(seasonal, n)

    ladder = [ClearSkies, Cloudy, Raining, Thunderstorm]
    stayed = big_jumps = 0
    for a, b in zip(seq, seq[1:]):
        distance = abs(ladder.index(a) - ladder.index(b))
        if distance == 0:
            stayed += 1
        elif distance >= 2:
            big_jumps += 1
    transitions = n - 1
    # Sticky (memoryless would be ~1/4 with equal chances) and rarely a big jump.
    assert stayed / transitions > 0.5
    assert big_jumps / transitions < 0.10


def test_weather_respects_zero_seasonal_chance() -> None:
    # A season that never storms must not conjure a storm no matter the bias.
    seasonal = _seasonal(
        WeatherTypeChances(thunderstorm=0.0, raining=1.0, cloudy=1.0, clear_skies=1.0)
    )
    day = datetime.date(2020, 6, 15)
    previous = Raining(seasonal, day, TimeOfDay.Day)  # adjacent to Thunderstorm

    for _ in range(2000):
        weather = Conditions.generate_weather(
            seasonal, day, TimeOfDay.Day, previous=previous
        )
        assert not isinstance(weather, Thunderstorm)


def test_weather_without_previous_matches_seasonal_draw() -> None:
    # No previous turn -> the legacy memoryless behaviour (a valid draw).
    seasonal = _seasonal()
    day = datetime.date(2020, 6, 15)
    weather = Conditions.generate_weather(seasonal, day, TimeOfDay.Day)
    assert isinstance(weather, (ClearSkies, Cloudy, Raining, Thunderstorm))
