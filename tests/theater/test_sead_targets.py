"""The SEAD steerpoint list: emitters only, not the whole site roster.

Plain SEAD loiters at standoff and fires HARMs, so a steerpoint on a fuel bowser
or an optically aimed gun is unusable -- and enumerating every unit hands the
player the site composition and exact unit counts the SEAD kneeboard page
deliberately withholds (recon fog §3).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from game.ato.flightplans.formationattack import FormationAttackBuilder
from game.data.units import UnitClass
from game.theater.theatergroundobject import TheaterGroundObject


def _unit(name: str, unit_class: UnitClass) -> Any:
    return SimpleNamespace(
        name=name,
        type=SimpleNamespace(id=name),
        unit_type=SimpleNamespace(unit_class=unit_class),
    )


class _UnregisteredUnit:
    """A mod unit with no yaml: ``unit_type`` raises rather than returning None."""

    name = "mod-radar"
    type = SimpleNamespace(id="mod-radar")

    @property
    def unit_type(self) -> Any:
        raise StopIteration


def _sead_targets(units: list[Any]) -> list[Any]:
    location = SimpleNamespace(strike_targets=units)
    return TheaterGroundObject.sead_targets.fget(location)  # type: ignore[attr-defined]


def test_sead_targets_keep_emitters_and_launchers_and_drop_support() -> None:
    # The SA-2 site from the report: a search radar, two track radars (§60
    # doubling), launchers, and the Logistics/Fuel/AAA slots the layout adds.
    search = _unit("p-19 s-125 sr", UnitClass.SEARCH_RADAR)
    track = _unit("SNR_75V", UnitClass.TRACK_RADAR)
    launcher = _unit("S_75M_Volhov", UnitClass.LAUNCHER)
    cargo = _unit("GAZ-66", UnitClass.LOGISTICS)
    bowser = _unit("TZ-22_KrAZ", UnitClass.LOGISTICS)
    gun = _unit("Ural-375 ZU-23", UnitClass.AAA)

    assert _sead_targets([search, track, launcher, cargo, bowser, gun]) == [
        search,
        track,
        launcher,
    ]


def test_sead_targets_keep_self_contained_and_radar_directed_air_defense() -> None:
    telar = _unit("SA-11 Buk LN", UnitClass.TELAR)
    shorad = _unit("Tor 9A331", UnitClass.SHORAD)
    ewr = _unit("1L13 EWR", UnitClass.EARLY_WARNING_RADAR)
    aaa_radar = _unit("ZSU-23-4 Shilka", UnitClass.AAA_RADAR)
    manpad = _unit("SA-18 Igla", UnitClass.MANPAD)

    assert _sead_targets([telar, shorad, ewr, aaa_radar, manpad]) == [
        telar,
        shorad,
        ewr,
        aaa_radar,
    ]


def test_sead_targets_keep_units_whose_type_is_not_registered() -> None:
    # Unknown is not the same as absent: a mod emitter with no yaml must not be
    # silently dropped from the shooter's steerpoints.
    unregistered = _UnregisteredUnit()
    static = SimpleNamespace(name="s", type=SimpleNamespace(id="s"), unit_type=None)
    cargo = _unit("GAZ-66", UnitClass.LOGISTICS)

    assert _sead_targets([unregistered, static, cargo]) == [unregistered, static]


def test_sead_targets_fall_back_to_the_full_roster_when_nothing_matches() -> None:
    # A SEAD flight hand-fragged onto a site with no classified emitter still
    # needs steerpoints; targets[0] anchors the flight plan's timing math.
    cargo = _unit("GAZ-66", UnitClass.LOGISTICS)
    gun = _unit("Ural-375 ZU-23", UnitClass.AAA)

    assert _sead_targets([cargo, gun]) == [cargo, gun]


def test_sead_targets_for_numbers_the_filtered_list_contiguously() -> None:
    # The kneeboard pairs its rows to these waypoints by position, so the
    # indices must run over the filtered list with no gaps.
    search = _unit("p-19 s-125 sr", UnitClass.SEARCH_RADAR)
    cargo = _unit("GAZ-66", UnitClass.LOGISTICS)
    launcher = _unit("S_75M_Volhov", UnitClass.LAUNCHER)
    location = SimpleNamespace(
        strike_targets=[search, cargo, launcher],
        sead_targets=[search, launcher],
    )

    targets = FormationAttackBuilder.sead_targets_for(location)  # type: ignore[arg-type]

    assert [t.name for t in targets] == ["p-19 s-125 sr #0", "S_75M_Volhov #1"]
    assert [t.target for t in targets] == [search, launcher]
