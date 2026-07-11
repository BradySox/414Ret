"""Role callsigns for the 414th rescue/EW package (SCAR rescue rework).

The C-130 on-scene commander is "King", the rescue helo "Jolly", the SCAR escort
"Sandy", and the EW C-130 "Toxic". These default a fresh flight's callsign and are
offered in the existing per-flight callsign picker. They are not stock DCS
callsigns, so FlightGroupSpawner registers the chosen one into the spawn country's
callsign pool before pydcs assigns it (pydcs ValueErrors on an unknown callsign).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from game.ato.flight import ROLE_CALLSIGNS, role_callsign
from game.ato.flighttype import FlightType
from game.missiongenerator.aircraft.flightgroupspawner import FlightGroupSpawner
from game.radio.CallsignContainer import Callsign


def test_role_callsign_by_type_and_airframe() -> None:
    assert role_callsign(FlightType.SCAR, is_helicopter=False) == "Sandy"
    assert role_callsign(FlightType.SCAR, is_helicopter=True) == "Sandy"  # Apache
    assert role_callsign(FlightType.JAMMING, is_helicopter=False) == "Toxic"
    # Combat SAR splits by airframe.
    assert role_callsign(FlightType.COMBAT_SAR, is_helicopter=False) == "King"  # C-130
    assert role_callsign(FlightType.COMBAT_SAR, is_helicopter=True) == "Jolly"  # helo
    # Everything else keeps its normal callsign.
    assert role_callsign(FlightType.CAS, is_helicopter=False) is None
    assert set(ROLE_CALLSIGNS) == {"King", "Jolly", "Sandy", "Toxic"}


def _spawner(callsign_name: str, category: str, pool: list[str]) -> Any:
    spawner = FlightGroupSpawner.__new__(FlightGroupSpawner)
    spawner.flight = cast(
        Any,
        SimpleNamespace(
            callsign=Callsign(callsign_name, 1),
            unit_type=SimpleNamespace(dcs_unit_type=SimpleNamespace(category=category)),
        ),
    )
    spawner.country = cast(Any, SimpleNamespace(callsign={category: pool}))
    return spawner


def test_role_callsign_is_registered_into_the_country_pool() -> None:
    # "Sandy" isn't a stock DCS callsign -> the spawner injects it so pydcs can
    # resolve it instead of raising ValueError.
    pool = ["Enfield", "Springfield"]
    _spawner("Sandy", "Plane", pool)._register_custom_callsign()
    assert "Sandy" in pool


def test_role_callsign_injection_is_idempotent() -> None:
    pool = ["Enfield"]
    spawner = _spawner("King", "Plane", pool)
    spawner._register_custom_callsign()
    spawner._register_custom_callsign()
    assert pool.count("King") == 1


def test_stock_callsign_is_left_untouched() -> None:
    pool = ["Enfield", "Springfield"]
    _spawner("Enfield", "Plane", pool)._register_custom_callsign()
    assert pool == ["Enfield", "Springfield"]  # not a role callsign -> no-op


def test_role_callsign_is_deregistered_after_spawn() -> None:
    # The role name must be pulled back out of the shared pool once it's stamped on
    # the group -- otherwise pydcs's next_callsign_category() (a random.choice over
    # the pool) hands King/Sandy/etc. to unrelated auto-named flights. This is the
    # "callsign applied to all aircraft" regression.
    pool = ["Enfield", "Springfield"]
    spawner = _spawner("Sandy", "Plane", pool)
    spawner._register_custom_callsign()
    assert "Sandy" in pool  # present only while this group is being spawned
    spawner._deregister_custom_callsign()
    assert pool == ["Enfield", "Springfield"]  # back to the stock pool -> no leak


def test_deregister_is_idempotent_and_skips_stock_callsigns() -> None:
    pool = ["Enfield"]
    # A role callsign never registered: removing it is a safe no-op.
    _spawner("King", "Plane", pool)._deregister_custom_callsign()
    assert pool == ["Enfield"]
    # A stock callsign: never removed even if it happens to be in the pool.
    _spawner("Enfield", "Plane", pool)._deregister_custom_callsign()
    assert pool == ["Enfield"]


# --- squadron custom event callsigns (e.g. "Voodoo") ---------------------------
# The same injection machinery now also carries a squadron's own custom callsign,
# not just the four role callsigns.


def test_squadron_custom_callsign_is_injected_then_pulled_back() -> None:
    pool = ["Enfield", "Springfield"]
    spawner = _spawner("Voodoo", "Plane", pool)
    spawner._register_custom_callsign()
    assert "Voodoo" in pool  # present while the group is being spawned
    spawner._deregister_custom_callsign()
    assert pool == ["Enfield", "Springfield"]  # no leak to other flights


def test_squadron_config_parses_callsign() -> None:
    from game.campaignloader.campaignairwingconfig import SquadronConfig

    assert SquadronConfig.from_data(
        {"primary": "CAS", "callsign": "Voodoo"}
    ).callsign == ("Voodoo")
    assert SquadronConfig.from_data({"primary": "CAS"}).callsign is None


def test_override_squadron_defaults_applies_callsign() -> None:
    from game.campaignloader.campaignairwingconfig import SquadronConfig
    from game.campaignloader.defaultsquadronassigner import DefaultSquadronAssigner

    squadron_def = cast(
        Any,
        SimpleNamespace(
            name="X", nickname=None, female_pilot_percentage=None, callsign=None
        ),
    )
    config = SquadronConfig.from_data({"primary": "CAS", "callsign": "Voodoo"})
    DefaultSquadronAssigner.override_squadron_defaults(squadron_def, config)
    assert squadron_def.callsign == "Voodoo"
