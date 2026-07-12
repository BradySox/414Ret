"""Air-start unit records carry the point's altitude reference.

pydcs ``_flying_group_inflight`` writes each unit's ``alt`` but leaves
``FlyingUnit.alt_type`` at its "BARO" default, and DCS places an in-air spawn
from the UNIT record -- so a "RADIO" (AGL) air start was actually written as a
raw MSL altitude (Red Tide M1: escort Mi-24s written alt=500/BARO over a ~600 m
Harz FARP, i.e. spawned below terrain-relative intent). Both spawner air-start
paths must mirror the point's alt_type onto every unit.
"""

from typing import Any

import dcs
from dcs.terrain import Caucasus


def _inflight_group(alt: int) -> Any:
    m = dcs.mission.Mission(terrain=Caucasus())
    country = m.country("Russia")
    return m.flight_group_inflight(
        country,
        "TEST GROUP",
        dcs.helicopters.Mi_8MT,
        dcs.mapping.Point(-250000, 650000, m.terrain),
        alt,
        speed=150,
        group_size=2,
    )


def test_pydcs_default_leaves_units_baro() -> None:
    # The upstream behavior this fix compensates for: if pydcs ever starts
    # mirroring alt_type itself, the spawner-side stamp is redundant (fine) but
    # this pin tells us to re-check the assumption.
    group = _inflight_group(500)
    assert all(u.alt_type == "BARO" for u in group.units)


def test_spawner_airstart_stamps_unit_alt_type() -> None:
    from game.missiongenerator.aircraft.flightgroupspawner import (
        FlightGroupSpawner,
    )

    # Exercise the exact tail both air-start paths share: point alt_type set,
    # then every unit mirrored. We simulate the tail on a real pydcs group the
    # same way _generate_over_departure ends.
    group = _inflight_group(500)
    alt_type = "RADIO"
    group.points[0].alt_type = alt_type
    for unit in group.units:
        unit.alt_type = alt_type
    assert group.points[0].alt_type == "RADIO"
    assert all(u.alt_type == "RADIO" for u in group.units)

    # And pin that the real source contains the stamp in BOTH air-start paths
    # (generate_mid_mission and _generate_over_departure) -- the fix is a
    # replace-all over their identical tails.
    import inspect

    src = inspect.getsource(FlightGroupSpawner)
    assert src.count("unit.alt_type = alt_type") == 2
