from __future__ import annotations

import datetime
import logging
import random
from dataclasses import dataclass
from typing import Tuple

from game.settings import Settings, NightMissions
from game.theater import ConflictTheater, SeasonalConditions
from game.theater.seasonalconditions import determine_season
from game.timeofday import TimeOfDay
from game.weather.weather import Weather, Thunderstorm, Raining, Cloudy, ClearSkies

# Continuous campaign clock (feature §47): how many hours the mission clock
# marches forward per turn -- a sortie plus turnaround -- jittered around a
# believable mean so the calendar advances monotonically instead of teleporting
# between time-of-day bands each turn. Whole hours preserve the "missions start
# on the hour" gameplay property.
MIN_TURN_ADVANCE_HOURS = 3
MAX_TURN_ADVANCE_HOURS = 7

# Weather severity ladder (calm -> violent). Turn-to-turn weather evolution
# biases the next turn's seasonal draw toward staying near the previous turn's
# rung, so fronts roll in and clear over several turns instead of a thunderstorm
# being followed by clear skies. Seasonal climatology still bounds the draw -- a
# near-zero seasonal chance for a type stays near zero after weighting.
_WEATHER_LADDER: list[type[Weather]] = [ClearSkies, Cloudy, Raining, Thunderstorm]
# Multiplier applied to a candidate's seasonal chance by its distance (in ladder
# rungs) from the previous turn's weather. Strong pull to stay, moderate to step
# one rung, small to jump further.
_WEATHER_PERSISTENCE_KERNEL: dict[int, float] = {0: 3.0, 1: 1.0, 2: 0.3, 3: 0.1}


@dataclass
class Conditions:
    time_of_day: TimeOfDay
    start_time: datetime.datetime
    weather: Weather

    @classmethod
    def generate(
        cls,
        theater: ConflictTheater,
        day: datetime.date,
        time_of_day: TimeOfDay,
        settings: Settings,
        forced_time: datetime.time | None = None,
    ) -> Conditions:
        # The time might be forced by the campaign for the first turn.
        if forced_time is not None:
            _start_time = datetime.datetime.combine(day, forced_time)
        else:
            _start_time = cls.generate_start_time(
                theater, day, time_of_day, settings.night_day_missions
            )

        return cls(
            time_of_day=time_of_day,
            start_time=_start_time,
            weather=cls.generate_weather(theater.seasonal_conditions, day, time_of_day),
        )

    @classmethod
    def advance(
        cls,
        previous: Conditions,
        theater: ConflictTheater,
    ) -> Conditions:
        """March a continuous campaign clock forward from the previous turn.

        Unlike `generate`, which re-rolls an independent time-of-day slot and a
        fresh, memoryless weather draw each turn, this advances the *actual*
        clock forward by a believable interval and evolves the weather from the
        previous turn's state, so the campaign reads as one continuous timeline
        (feature §47). Time of day is derived from the marched clock; the date
        rolls over naturally at midnight.
        """
        interval = datetime.timedelta(
            hours=random.randint(MIN_TURN_ADVANCE_HOURS, MAX_TURN_ADVANCE_HOURS)
        )
        start_time = previous.start_time + interval
        time_of_day = theater.daytime_map.best_guess_time_of_day_at(start_time.time())
        return cls(
            time_of_day=time_of_day,
            start_time=start_time,
            weather=cls.generate_weather(
                theater.seasonal_conditions,
                start_time.date(),
                time_of_day,
                previous=previous.weather,
            ),
        )

    @classmethod
    def generate_start_time(
        cls,
        theater: ConflictTheater,
        day: datetime.date,
        time_of_day: TimeOfDay,
        night_day_missions: NightMissions,
    ) -> datetime.datetime:
        from game.theater import DaytimeMap

        if night_day_missions == NightMissions.OnlyDay:
            logging.info("Skip Night mission due to user settings")
            time_range = DaytimeMap(
                dawn=(datetime.time(hour=8), datetime.time(hour=9)),
                day=(datetime.time(hour=10), datetime.time(hour=12)),
                dusk=(datetime.time(hour=12), datetime.time(hour=14)),
                night=(datetime.time(hour=14), datetime.time(hour=17)),
            ).range_of(time_of_day)
        elif night_day_missions == NightMissions.OnlyNight:
            logging.info("Skip Day mission due to user settings")
            time_range = DaytimeMap(
                dawn=(datetime.time(hour=0), datetime.time(hour=3)),
                day=(datetime.time(hour=3), datetime.time(hour=6)),
                dusk=(datetime.time(hour=21), datetime.time(hour=22)),
                night=(datetime.time(hour=22), datetime.time(hour=23)),
            ).range_of(time_of_day)
        else:
            time_range = theater.daytime_map.range_of(time_of_day)

        # Starting missions on the hour is a nice gameplay property, so keep the random
        # time constrained to that. DaytimeMap enforces that we have only whole hour
        # ranges for now, so we don't need to worry about accidentally changing the time
        # of day by truncating sub-hours.
        day, hours = Conditions.random_time_progression(day, time_range)
        time = datetime.time(hour=hours)
        return datetime.datetime.combine(day, time)

    @staticmethod
    def random_time_progression(
        day: datetime.date, time_range: Tuple[datetime.time, datetime.time]
    ) -> Tuple[datetime.date, int]:
        start, end = time_range[0].hour, time_range[1].hour
        if start > end:
            end += 24
            hours = random.randint(start, end)
            if hours > 23:
                day += datetime.timedelta(days=1.0)
                hours %= 24
        else:
            if start == 0:
                day += datetime.timedelta(days=1.0)
            hours = random.randint(start, end)
        return day, hours

    @classmethod
    def generate_weather(
        cls,
        seasonal_conditions: SeasonalConditions,
        day: datetime.date,
        time_of_day: TimeOfDay,
        previous: Weather | None = None,
    ) -> Weather:
        season = determine_season(day)
        logging.debug("Weather: Season {}".format(season))
        weather_chances = seasonal_conditions.weather_type_chances[season]
        chances: dict[
            type[ClearSkies] | type[Cloudy] | type[Raining] | type[Thunderstorm], float
        ] = {
            Thunderstorm: weather_chances.thunderstorm,
            Raining: weather_chances.raining,
            Cloudy: weather_chances.cloudy,
            ClearSkies: weather_chances.clear_skies,
        }
        logging.debug("Weather: Chances {}".format(weather_chances))
        weights = dict(chances)
        if previous is not None:
            # Continuous campaign weather (feature §47): bias the seasonal draw
            # toward the previous turn's rung on the severity ladder so systems
            # move through gradually. Seasonal climatology still bounds it.
            prev_index = _WEATHER_LADDER.index(type(previous))
            weights = {
                wtype: chance
                * _WEATHER_PERSISTENCE_KERNEL[
                    abs(_WEATHER_LADDER.index(wtype) - prev_index)
                ]
                for wtype, chance in chances.items()
            }
        weather_type = random.choices(
            list(weights.keys()), weights=list(weights.values())
        )[0]
        logging.debug("Weather: Type {}".format(weather_type))
        return weather_type(seasonal_conditions, day, time_of_day)
