"""P1 of the Vietnam Retribution mode: the VIETNAM_DOCTRINE profile.

Locks the doctrine *model* (display-name rename layer + tasking-whitelist mechanism,
behaviour cloned from COLDWAR) and the faction repoint, so a regression that drops the
renames, re-gates the whitelist, or unpoints a faction fails CI. See
docs/dev/design/414th-vietnam-retribution-notes.md.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from game.ato.flighttype import FlightType
from game.data.doctrine import (
    ALL_DOCTRINES,
    COLDWAR_DOCTRINE,
    MODERN_DOCTRINE,
    VIETNAM_DOCTRINE,
    WWII_DOCTRINE,
)
from game.settings import Settings

_FACTIONS = Path(__file__).resolve().parents[1] / "resources" / "factions"

# The factions repointed from "coldwar" to "vietnam" doctrine in P1.
_VIETNAM_DOCTRINE_FACTIONS = [
    "USA 1970 Vietnam War.json",
    "USA 1971 Vietnam War.json",
    "USSR 1971 Vietnam War.json",
    "nva_1970.json",
    "vietcong_1965.json",
    "vietcong_1970.json",
    "vietnam_1965.json",
    "vietnam_1970.json",
    "usa_1965.json",
    "usa_1970.json",
]


def test_vietnam_doctrine_registered() -> None:
    assert VIETNAM_DOCTRINE in ALL_DOCTRINES
    assert VIETNAM_DOCTRINE.name == "vietnam"


def test_display_name_overrides_iconic_taskings() -> None:
    assert VIETNAM_DOCTRINE.display_name_for(FlightType.BARCAP) == "MiGCAP"
    assert VIETNAM_DOCTRINE.display_name_for(FlightType.STRIKE) == "Alpha Strike"
    assert VIETNAM_DOCTRINE.display_name_for(FlightType.SEAD) == "Iron Hand"
    assert VIETNAM_DOCTRINE.display_name_for(FlightType.SCAR) == "Sandy"


def test_unmapped_tasking_falls_back_to_enum_value() -> None:
    # CAS is intentionally not renamed -> the canonical persisted label.
    assert VIETNAM_DOCTRINE.display_name_for(FlightType.CAS) == FlightType.CAS.value


def test_existing_doctrines_have_no_renames() -> None:
    for doctrine in (MODERN_DOCTRINE, COLDWAR_DOCTRINE, WWII_DOCTRINE):
        assert dict(doctrine.task_display_names) == {}
        assert doctrine.display_name_for(FlightType.BARCAP) == FlightType.BARCAP.value


def test_non_vietnam_whitelists_stay_open() -> None:
    # Every non-Vietnam doctrine keeps its whitelist open (behaviour == COLDWAR).
    for doctrine in (MODERN_DOCTRINE, COLDWAR_DOCTRINE, WWII_DOCTRINE):
        assert doctrine.tasking_whitelist is None
        assert doctrine.allows(FlightType.DEAD)
        assert doctrine.allows(FlightType.ANTISHIP)


def test_vietnam_whitelist_drops_sead_dead_antiship() -> None:
    # P3: Vietnam has no reliable SEAD and no naval threat, so the auto-planner must not
    # produce SEAD/DEAD/anti-ship -- this is what stops an A-1 being tasked a SEAD sweep.
    for dropped in (
        FlightType.DEAD,
        FlightType.SEAD,
        FlightType.SEAD_ESCORT,
        FlightType.SEAD_SWEEP,
        FlightType.ANTISHIP,
    ):
        assert not VIETNAM_DOCTRINE.allows(dropped), dropped
    # The core taskings the campaign still flies stay allowed.
    for kept in (
        FlightType.STRIKE,
        FlightType.BAI,
        FlightType.CAS,
        FlightType.BARCAP,
        FlightType.ESCORT,
        FlightType.TARCAP,
        FlightType.ARMED_RECON,
        FlightType.AEWC,
    ):
        assert VIETNAM_DOCTRINE.allows(kept), kept


def test_allows_respects_a_whitelist() -> None:
    gated = replace(VIETNAM_DOCTRINE, tasking_whitelist=frozenset({FlightType.STRIKE}))
    assert gated.allows(FlightType.STRIKE)
    assert not gated.allows(FlightType.DEAD)


def test_vietnam_geometry_matches_coldwar() -> None:
    # Vietnam shares COLDWAR's planning geometry; it differs only in the display layer
    # (name + renames) and the P3 behaviour fields. Reset exactly those -> COLDWAR.
    rebadged = replace(
        VIETNAM_DOCTRINE,
        name="coldwar",
        task_display_names={},
        tasking_whitelist=None,
        strike_through_air_defense_threat=False,
        plan_strikes_without_full_escort=False,
        strike_flight_count=1,
    )
    assert rebadged == COLDWAR_DOCTRINE


def test_vietnam_relaxes_strike_gates_only() -> None:
    # P3: with no reliable SEAD and few fighters, Vietnam strikes into unsuppressed air
    # defenses AND flies unescorted rather than deadlocking the whole offensive fleet.
    assert VIETNAM_DOCTRINE.strike_through_air_defense_threat is True
    assert VIETNAM_DOCTRINE.plan_strikes_without_full_escort is True
    for d in (MODERN_DOCTRINE, COLDWAR_DOCTRINE, WWII_DOCTRINE):
        assert d.strike_through_air_defense_threat is False
        assert d.plan_strikes_without_full_escort is False


def test_vietnam_alpha_strike_fans_two_sections() -> None:
    # P3: a Vietnam STRIKE fans two coordinated sections onto one target; every other
    # doctrine keeps the stock single section.
    assert VIETNAM_DOCTRINE.strike_flight_count == 2
    for d in (MODERN_DOCTRINE, COLDWAR_DOCTRINE, WWII_DOCTRINE):
        assert d.strike_flight_count == 1


def test_from_settings_preserves_renames_whitelist_and_flags() -> None:
    # from_settings rebuilds the frozen dataclass field by field -- the additive fields
    # must survive, or a settings-adjusted Vietnam doctrine would silently lose them.
    out = VIETNAM_DOCTRINE.from_settings(Settings())
    assert out.display_name_for(FlightType.STRIKE) == "Alpha Strike"
    assert out.tasking_whitelist is not None
    assert not out.allows(FlightType.DEAD)
    assert out.allows(FlightType.STRIKE)
    assert out.strike_through_air_defense_threat is True
    assert out.plan_strikes_without_full_escort is True
    assert out.strike_flight_count == 2


def test_vietnam_faction_jsons_declare_vietnam_doctrine() -> None:
    for name in _VIETNAM_DOCTRINE_FACTIONS:
        data = json.loads((_FACTIONS / name).read_text(encoding="utf-8"))
        assert (
            data.get("doctrine") == "vietnam"
        ), f"{name} must declare 'doctrine: vietnam' (P1 repoint)."


def test_flight_task_display_name_resolves_through_coalition_doctrine() -> None:
    # P1b: the display read-path. Flight.task_display_name navigates
    # coalition -> doctrine -> display_name_for; lock that path + the rename.
    from types import SimpleNamespace

    from game.ato.flight import Flight

    flight = Flight.__new__(Flight)
    flight.coalition = SimpleNamespace(doctrine=VIETNAM_DOCTRINE)  # type: ignore[assignment]
    flight.flight_type = FlightType.SEAD
    assert flight.task_display_name == "Iron Hand"


def test_flightdata_task_display_name_resolves_through_squadron_doctrine() -> None:
    from types import SimpleNamespace

    from game.missiongenerator.aircraft.flightdata import FlightData

    fd = FlightData.__new__(FlightData)
    fd.squadron = SimpleNamespace(  # type: ignore[assignment]
        coalition=SimpleNamespace(doctrine=VIETNAM_DOCTRINE)
    )
    fd.flight_type = FlightType.STRIKE
    assert fd.task_display_name == "Alpha Strike"
