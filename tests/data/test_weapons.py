from datetime import date
from pathlib import Path
import re
from types import SimpleNamespace
from typing import cast

import pytest
from dcs.planes import F_16C_50, FA_18C_hornet

from game.data.weapons import Weapon, WeaponGroup, WeaponType
from game.ato.loadouts import Loadout
from game.ato.flighttype import FlightType
from game.dcs.aircrafttype import AircraftType
from game.factions.faction import Faction


def _bare_weapon(clsid: str) -> Weapon:
    group = WeaponGroup(
        name=f"test-{clsid}",
        type=WeaponType.UNKNOWN,
        introduction_year=None,
        fallback_name=None,
    )
    return Weapon(clsid=clsid, weapon_group=group)


def _f16c_50() -> AircraftType:
    return cast(
        AircraftType,
        SimpleNamespace(dcs_unit_type=F_16C_50, has_built_in_target_pod=False),
    )


def _fa_18c_hornet() -> AircraftType:
    return cast(
        AircraftType,
        SimpleNamespace(dcs_unit_type=FA_18C_hornet, has_built_in_target_pod=False),
    )


@pytest.mark.parametrize(
    "clsid",
    [
        "{LAU-131 - 7 AGR-20A}",
        "{LAU-131 - 7 AGR-20 M282}",
        "{BRU-32 GBU-12}",
        "DIS_GBU_12",
    ],
)
def test_accepts_laser_code_true_for_laser_guided_weapons(clsid: str) -> None:
    assert _bare_weapon(clsid).accepts_laser_code() is True


@pytest.mark.parametrize(
    "clsid",
    [
        "<CLEAN>",
        "{AUF2_MK82}",
        "definitely-not-a-real-clsid",
    ],
)
def test_accepts_laser_code_false_for_non_laser_or_unknown(clsid: str) -> None:
    assert _bare_weapon(clsid).accepts_laser_code() is False


def test_aaq_33_has_era_data_and_degrades_on_pre_intro_f16() -> None:
    weapon = Weapon.with_clsid("{AN_AAQ_33}")

    assert weapon is not None
    assert weapon.weapon_group.name == "AN/AAQ-33 - Advanced Targeting Pod"
    assert weapon.weapon_group.introduction_year == 2005

    faction = cast(Faction, SimpleNamespace(weapons_introduction_year_overrides={}))
    assert weapon.available_on(date(2004, 1, 1), faction) is False
    assert weapon.available_on(date(2005, 1, 1), faction) is True

    loadout = Loadout("Test", {11: weapon}, date=None)
    aircraft = _f16c_50()
    degraded = loadout.degrade_for_date(aircraft, date(2004, 1, 1), faction)

    degraded_weapon = degraded.pylons.get(11)
    assert degraded_weapon is None


def test_f16_litening_is_not_available_before_viper_integration_year() -> None:
    litening = Weapon.with_clsid("{A111396E-D3E8-4b9c-8AC9-2432489304D5}")

    assert litening is not None
    assert litening.weapon_group.name == "AN/AAQ-28 LITENING"
    assert litening.weapon_group.introduction_year == 1999

    faction = cast(Faction, SimpleNamespace(weapons_introduction_year_overrides={}))
    aircraft = _f16c_50()
    loadout = Loadout("Test", {11: litening}, date=None, is_custom=True)

    degraded = loadout.degrade_for_date(aircraft, date(2002, 1, 1), faction)
    assert degraded.pylons.get(11) is None

    available = loadout.degrade_for_date(aircraft, date(2005, 1, 1), faction)
    assert available.pylons.get(11) == litening


def test_f16_2002_sead_sweep_keeps_hts_but_removes_targeting_pod() -> None:
    hts = Weapon.with_clsid("{AN_ASQ_213}")
    atp = Weapon.with_clsid("{AN_AAQ_33}")

    assert hts is not None
    assert atp is not None

    faction = cast(Faction, SimpleNamespace(weapons_introduction_year_overrides={}))
    aircraft = _f16c_50()
    loadout = Loadout("Retribution SEAD Sweep", {10: hts, 11: atp}, date=None)

    degraded = loadout.degrade_for_date(aircraft, date(2002, 1, 1), faction)

    assert degraded.pylons.get(10) == hts
    assert degraded.pylons.get(11) is None


def test_hornet_litening_is_not_available_before_atflir_year() -> None:
    litening = Weapon.with_clsid("{AAQ-28_LEFT}")

    assert litening is not None
    assert litening.weapon_group.name == "AN/AAQ-28 LITENING"
    assert litening.weapon_group.introduction_year == 1999

    faction = cast(Faction, SimpleNamespace(weapons_introduction_year_overrides={}))
    aircraft = _fa_18c_hornet()
    loadout = Loadout("Test", {4: litening}, date=None, is_custom=True)

    degraded = loadout.degrade_for_date(aircraft, date(2002, 1, 1), faction)
    degraded_weapon = degraded.pylons.get(4)
    assert degraded_weapon is not None
    assert degraded_weapon.weapon_group.type is not WeaponType.TGP

    available = loadout.degrade_for_date(aircraft, date(2003, 1, 1), faction)
    assert available.pylons.get(4) == litening


def test_hornet_2002_atflir_does_not_fall_back_to_litening() -> None:
    atflir = Weapon.with_clsid("{AN_ASQ_228}")

    assert atflir is not None
    assert atflir.weapon_group.name == "AN/ASQ-228 ATFLIR"
    assert atflir.weapon_group.introduction_year == 2003

    faction = cast(Faction, SimpleNamespace(weapons_introduction_year_overrides={}))
    aircraft = _fa_18c_hornet()
    loadout = Loadout("Test", {4: atflir}, date=None)

    degraded = loadout.degrade_for_date(aircraft, date(2002, 1, 1), faction)

    degraded_weapon = degraded.pylons.get(4)
    assert degraded_weapon is not None
    assert degraded_weapon.weapon_group.type is not WeaponType.TGP


@pytest.mark.parametrize(
    ("clsid", "group_name", "introduction_year"),
    [
        ("{F-15E_AAQ-33_XR_ATP-SE}", "AN/AAQ-33 - Advanced Targeting Pod", 2005),
        ("{F-15E_AAQ-28_LITENING}", "AN/AAQ-28 LITENING", 1999),
        ("{SUPERHORNET_PYLON_05_TP_ASQ228}", "AN/ASQ-228 ATFLIR", 2003),
        ("{SUPERHORNET_PYLON_06_CN_TP_AAQ28}", "AN/AAQ-28 LITENING", 1999),
        ("_NiteHawk_FLIR", "AN/AAS-38 Nite Hawk", 1984),
        ("{HB_PAVE_SPIKE_FAST_TRACK}", "AN/AVQ-23 Pave Spike", 1974),
        ("{HB_PAVE_SPIKE_FAST_ON_ADAPTER_IN_AERO7}", "AN/AVQ-23 Pave Spike", 1974),
        ("{JAS39_Litening}", "AN/AAQ-28 LITENING", 1999),
        ("{JAS39_FLIR}", "AN/AAQ-28 LITENING", 1999),
        ("{LITENING_POD}", "AN/AAQ-28 LITENING", 1999),
        ("{DAMOCLES}", "DAMOCLES", 2009),
        ("{F111C_FLIR}", "AN/AVQ-26 Pave Tack", 1982),
        ("DIS_WMD7", "AVIC WMD-7", 2007),
    ],
)
def test_targeting_pod_variants_have_era_data(
    clsid: str, group_name: str, introduction_year: int
) -> None:
    weapon = Weapon.with_clsid(clsid)

    assert weapon is not None
    assert weapon.weapon_group.type is WeaponType.TGP
    assert weapon.weapon_group.name == group_name
    assert weapon.weapon_group.introduction_year == introduction_year


def test_custom_payload_targeting_pods_do_not_fall_back_to_unknown() -> None:
    payload_clsids: set[str] = set()
    for path in Path("resources/customized_payloads").glob("*.lua"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        payload_clsids.update(re.findall(r'\["CLSID"\]\s*=\s*"([^"]+)"', text))

    def is_targeting_pod(weapon: Weapon) -> bool:
        name = weapon.name.upper()
        return "NAV POD" not in name and any(
            marker in name
            for marker in (
                "AAQ",
                "AAS-38",
                "ATFLIR",
                "DAMOCLES",
                "LANTIRN",
                "LITENING",
                "NITE HAWK",
                "AVQ",
                "PAVE SPIKE",
                "PAVE TACK",
                "TGP",
                "WMD",
            )
        )

    targeting_pods = [
        weapon
        for clsid in sorted(payload_clsids)
        if (weapon := Weapon.with_clsid(clsid)) is not None and is_targeting_pod(weapon)
    ]

    assert targeting_pods
    for weapon in targeting_pods:
        assert weapon.weapon_group.type is WeaponType.TGP, weapon.clsid
        assert weapon.weapon_group.introduction_year is not None, (
            weapon.clsid,
            weapon.weapon_group.name,
        )


# A real, covered weapon CLSID used as a fixture for the valid_payload tests below.
_AIM9M_CLSID = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}"


def test_valid_payload_ignores_empty_stations() -> None:
    # Sanity: the fixture weapon resolves.
    assert Weapon.with_clsid(_AIM9M_CLSID) is not None

    # A stray empty ("") or "<CLEAN>" station is an empty pylon, NOT an invalid
    # loadout. Without this, a single empty slot made valid_payload reject the whole
    # preset, so the planner silently flew a fallback (often clean A2A) or nothing --
    # e.g. the Tornado IDS STRIKE / Mosquito presets that carried real bombs.
    pylons = {
        1: {"CLSID": _AIM9M_CLSID},
        2: {"CLSID": ""},
        3: {"CLSID": "<CLEAN>"},
    }
    assert Loadout.valid_payload(pylons) is True

    # A genuinely unknown (dead) CLSID still invalidates the loadout.
    dead = {1: {"CLSID": _AIM9M_CLSID}, 2: {"CLSID": "{NOT_A_REAL_CLSID}"}}
    assert Loadout.valid_payload(dead) is False


def test_antiship_falls_back_to_strike_loadout_names() -> None:
    names = list(Loadout.default_loadout_names_for(FlightType.ANTISHIP))
    # The jet's own anti-ship presets are still preferred first (the §71
    # expanded-weapons candidate leads, then the regular names)...
    assert names[0] == f"Retribution Anti-ship{Loadout.EXPANDED_WEAPONS_SUFFIX}"
    assert names[1].endswith("Anti-ship")
    assert "ANTISHIP" in names
    # ...but Anti-ship now falls back to the Strike family, so a jet tasked Anti-ship
    # without a dedicated anti-ship preset carries iron bombs instead of an EMPTY
    # loadout. (Anti-ship was the only A2G task with no fallback.)
    strike_names = set(Loadout.default_loadout_names_for(FlightType.STRIKE))
    assert strike_names.issubset(set(names))


# Dead CLSIDs that reference MOD-pack weapons absent from base pydcs (and from
# pydcs_extensions): SA342 Gazelle, Su-57, Mirage F1, the F-22A pack, UH-60L, OH-6A,
# plus two non-task manufacturer presets. Their presets degrade via the fallback chain
# (not fatal), but the ids can't be resolved in a base install. Tracked as follow-up.
# Any NEW unresolved CLSID outside this set is a regression: a preset that references
# it is silently dropped (the bug this audit fixed), so the test fails loudly.
_KNOWN_MOD_STRAGGLER_CLSIDS = frozenset(
    {
        "<CLEAN-200.5>",  # Mi-8MT air-assault ballast marker
        "{2x Mk-82 SWA}",  # F-4E-45MC manufacturer preset
        "{DIS_RKT_90_UG}",  # JF-17 manufacturer preset
        "{BLG66_BELOUGA}",  # Mirage F1 (Aerges) cluster bomb
        "{KH_59MK2}",  # Su-57 (mod) standoff missile
        "{HOT3D}",  # SA342 Gazelle (mod) ATGM
        "{HOT3G}",  # SA342 Gazelle (mod) ATGM
        "FAS}",  # SA342 Gazelle (mod) malformed marker
        "{MBDA_MistralD}",  # SA342 Gazelle (mod) Mistral
        "{MBDA_MistralG}",  # SA342 Gazelle (mod) Mistral
        "{F22_IRST}",  # F-22A (mod) IRST pod
        "{GBU32_JDAM}",  # F-22A (mod) JDAM
        "{MAKO_A2G_C}",  # F-22A (mod) standoff
        "{OH-6 M134 Minigun}",  # OH-6A (mod) door gun
        "{OH-6 M60 Door}",  # OH-6A (mod) door gun
        "{UH60L_M2_GUNNER}",  # UH-60L (mod) door gun
        "{UH60L_M60_GUNNER}",  # UH-60L (mod) door gun
        "{UH60_FUEL_TANK_200}",  # UH-60L (mod) tank
        "{Exocet}",  # Super Etendard (mod) Exocet AShM
        "{AS_30L}",  # Super Etendard / Jaguar (mod) AS-30L
        "{SCALP}",  # Rafale / Mirage (mod) SCALP-EG cruise missile
        "{RAFALE_MBDA_METEOR}",  # Rafale (mod) Meteor
        "{Thales_RBE2}",  # Rafale (mod) RBE2 radar
        "{GBU_49}",  # Mirage 2000D / Rafale (mod) GBU-49
        "{PTB-1500}",  # mod aircraft fuel tank
        "{6C0D552F-570B-42ff-9F6D-F10D9C1D4E1C}",  # mod weapon (GUID id)
    }
)


def test_customized_payload_clsids_resolve_or_are_known_stragglers() -> None:
    payload_clsids: set[str] = set()
    for path in Path("resources/customized_payloads").glob("*.lua"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        payload_clsids.update(re.findall(r'\["CLSID"\]\s*=\s*"([^"]+)"', text))

    unresolved = {
        clsid
        for clsid in payload_clsids
        if clsid not in ("", "<CLEAN>")
        and Weapon.with_clsid(clsid) is None
        and clsid not in _KNOWN_MOD_STRAGGLER_CLSIDS
    }

    assert not unresolved, (
        "Customized-payload presets reference CLSID(s) that resolve to no weapon and "
        "are not known mod stragglers. The whole preset is silently dropped, so the "
        "jet flies a fallback or clean. Fix the CLSID (or add to "
        "_KNOWN_MOD_STRAGGLER_CLSIDS if it is a mod weapon):\n"
        + "\n".join(sorted(unresolved))
    )


# Deliberately-kept preset names in the fork namespace that intentionally match no loader
# lookup. See docs/dev/design/414th-loadout-integrity-audit-notes.md ("2026-07-06
# upstream-baseline reset").
#   - "Retribution CEAD": no CEAD FlightType exists; dead weight on A6E / CH_Su-27P1M /
#     MiG-29MU2, deliberately left in place.
#   - "Retribution Strike - Toilet": the A-1 Skyraider's joke toilet-bomb loadout. The A-1
#     already carries a real "Retribution Strike" preset, so this is an intentional cosmetic
#     ME-only extra, not a silent-fallback primary (and the file is upstream-identical).
_KNOWN_ORPHAN_PRESET_NAMES = frozenset(
    {"Retribution CEAD", "Retribution Strike - Toilet"}
)


def test_customized_payload_retribution_names_resolve_to_a_task() -> None:
    """Every fork-namespaced preset name must be one the loader actually looks up.

    The mission generator matches a flight's FlightType to a custom preset by *exact name*
    (``Loadout.default_loadout_names_for`` -> ``"Retribution {value}"`` / ``"Liberation
    {value}"`` + legacy aliases). A preset in the ``Retribution ``/``Liberation `` namespace
    whose name matches none of those lookups is dead weight: the jet silently falls back to a
    worse loadout (anti-ship, which has no fallback preset chain to a dedicated fit, degrades
    to iron bombs or empty). This is the bug the 2026-06 name-standardization pass fixed --
    and upstream still ships offenders (e.g. ``"Retribution Fighter Sweep"`` vs the enum's
    lowercase ``"Fighter sweep"``), so a byte-for-byte reset to upstream can silently
    reintroduce it. This guard fails loudly if one creeps back.
    """
    valid_names: set[str] = set()
    for task in FlightType:
        valid_names.update(Loadout.default_loadout_names_for(task))

    dead: dict[str, set[str]] = {}
    for path in Path("resources/customized_payloads").glob("*.lua"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name in re.findall(r'\["name"\]\s*=\s*"([^"]+)"', text):
            if not (name.startswith("Retribution ") or name.startswith("Liberation ")):
                continue
            if name in valid_names or name in _KNOWN_ORPHAN_PRESET_NAMES:
                continue
            dead.setdefault(name, set()).add(path.stem)

    assert not dead, (
        "Customized-payload preset(s) in the 'Retribution '/'Liberation ' namespace use a "
        "name the loader never looks up, so the jet silently flies a fallback loadout. Match "
        "FlightType.value casing exactly (e.g. 'Retribution Fighter sweep', not '...Sweep'):\n"
        + "\n".join(f"  {n} -> {sorted(files)}" for n, files in sorted(dead.items()))
    )
