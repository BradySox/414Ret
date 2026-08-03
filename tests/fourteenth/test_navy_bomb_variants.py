"""Carrier airframes carry the Navy case of a bomb, not the Air Force one.

DCS models only a handful of stores as service-specific pairs -- the 2000lb
JDAMs (``GBU-31(V)1/B`` AF / ``(V)2/B`` Navy on the Mk-84 body, ``(V)3/B`` AF /
``(V)4/B`` Navy on the BLU-109 penetrator) and Paveway III (``GBU-24A/B`` AF /
``GBU-24B/B`` Navy).  Everything else a carrier jet drops -- GBU-10/12/16,
GBU-38, Mk-82/83/84 -- is one store shared by both services, with the Navy
variation expressed through the cockpit fuzing menu rather than a separate
weapon, so there is nothing to pick there.

The sweep below is the standing guard: no carrier-capable airframe may ship an
Air Force-cased store on a pylon where the Navy twin is mountable.  "Where
mountable" is load-bearing -- the CJS Super Hornet only offers the Navy
``(V)4/B`` on its two midboard stations, so a jet that genuinely cannot hang
the Navy case keeps the Air Force one rather than flying naked (DCS silently
strips a store the pylon tables reject).

The payload files are parsed straight off disk instead of through
``FlyingType.load_payloads`` so the assertion is about the data this repo
ships, never about whatever a developer has in their own ``UnitPayloads``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterator, Optional, Type

import pytest
from dcs import lua
from dcs.unittype import FlyingType

from game import persistency
from game.dcs.aircrafttype import AircraftType

PAYLOADS_DIR = Path(__file__).parent.parent.parent / "resources" / "customized_payloads"

# Air Force store -> its Navy twin, matched on the DCS display name.
SERVICE_PAIRS = [
    ("GBU-31(V)1/B", "GBU-31(V)2/B"),
    ("GBU-31(V)3/B", "GBU-31(V)4/B"),
    ("GBU-24A/B", "GBU-24B/B"),
]

# The Navy fit authored for the CJS Super Hornet: the 2000lb penetrator on the
# two midboard stations (the only ones CJS clears for the (V)4) with 1000lb
# Navy JDAM on the outboards.  Keyed by pydcs pylon index.
SUPER_HORNET_NAVY_FIT = {
    2: "{SUPERHORNET_PYLON_02_OB_MK_1X_GBU-32}",
    3: "{SUPERHORNET_PYLON_03_MB_MK_1X_GBU-31_V_4B}",
    7: "{SUPERHORNET_PYLON_09_MB_MK_1X_GBU-31_V_4B}",
    8: "{SUPERHORNET_PYLON_10_OB_MK_1X_GBU-32}",
}
SUPER_HORNET_BOMB_FITS = ["Retribution Strike", "Retribution OCA/Runway"]

# The white (thermally-protected) Navy bomb body is not a separate store -- it is
# a per-loadout *visual* setting, model draw argument 57, written by the Mission
# Editor's weapon-settings ("fuzing") panel.  1 = Navy white, 0 = green.  ED's own
# `CoreMods/aircraft/F14/UnitPayloads/F-14BU.lua` sets 1 on every bomb the Bombcat
# carries, which is the reference for "Navy jet, all bombs white".
CASING_KEY = "NFP_VIS_DrawArgNo_57"
NAVY_WHITE = 1

# US Navy / USMC fixed-wing strike jets.  Deliberately excludes F-14A-95-GR (the
# Export/Iranian Tomcat), the VSN and VWV mods (wrong nation or wrong era -- the
# thermal coating postdates Vietnam), and every helo.
NAVY_PAYLOAD_FILES = {
    "FA-18C_hornet.lua",
    "FA-18E.lua",
    "FA-18F.lua",
    "AV8BNA.lua",
    "A6E.lua",
    "A-7E.lua",
    "F-14A-135-GR.lua",
    "F-14A-135-GR-Early.lua",
    "F-14B.lua",
    "F-14BU.lua",
}

# A floor, not an inventory: these must carry the white casing, so the pass cannot
# be silently undone for the jets it was actually asked for.
CASING_REQUIRED = [
    ("FA-18C_hornet.lua", "{GBU_31_V_4B}"),
    ("FA-18C_hornet.lua", "{GBU_31_V_2B}"),
    ("FA-18E.lua", "{SUPERHORNET_PYLON_03_MB_MK_1X_GBU-31_V_4B}"),
    ("FA-18F.lua", "{SUPERHORNET_PYLON_09_MB_MK_1X_GBU-31_V_4B}"),
    ("F-14BU.lua", "{BRU-32 GBU-38}"),  # 500 lb
    ("F-14BU.lua", "{BRU-32 GBU-16}"),  # 1000 lb
    ("AV8BNA.lua", "{GBU_32_V_2B}"),
]


@pytest.fixture(autouse=True)
def _persistency(tmp_path: Path) -> None:
    # AircraftType.iter_all() loads the unit data + weapon DB.
    persistency.setup(str(tmp_path), prefer_liberation_payloads=False, port=16892)


def _pylon_stores(dcs_type: Type[FlyingType], pylon: int) -> dict[str, str]:
    """clsid -> display name for everything mountable on ``pylon``."""
    table = getattr(dcs_type, f"Pylon{pylon}", None)
    if table is None:
        return {}
    stores = {}
    for name, value in vars(table).items():
        if name.startswith("_"):
            continue
        # pydcs pylon entries are (pylon_number, weapon_dict) tuples.
        if isinstance(value, tuple) and len(value) == 2 and isinstance(value[1], dict):
            clsid = value[1].get("clsid")
            if clsid is not None:
                stores[clsid] = value[1].get("name", "")
    return stores


def _shipped_payloads() -> Iterator[tuple[str, Optional[str], dict[str, Any]]]:
    """Yield (file name, dcs unit id, payload) for every shipped payload file."""
    for path in sorted(PAYLOADS_DIR.glob("*.lua")):
        try:
            parsed = lua.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:  # pragma: no cover - a parse break is its own bug
            continue
        unit_payloads = parsed.get("unitPayloads")
        if not isinstance(unit_payloads, dict):
            continue
        unit_type = unit_payloads.get("unitType")
        for payload in unit_payloads.get("payloads", {}).values():
            yield path.name, unit_type, payload


def _carrier_dcs_types() -> dict[str, Type[FlyingType]]:
    types: dict[str, Type[FlyingType]] = {}
    for aircraft in AircraftType.iter_all():
        if aircraft.carrier_capable:
            types[aircraft.dcs_unit_type.id] = aircraft.dcs_unit_type
    return types


def test_carrier_airframes_never_ship_an_air_force_case_where_the_navy_one_fits() -> (
    None
):
    carriers = _carrier_dcs_types()
    offenders = []
    for file_name, unit_id, payload in _shipped_payloads():
        dcs_type = carriers.get(unit_id) if unit_id is not None else None
        if dcs_type is None:
            # Not carrier-capable, or an airframe this fork does not field
            # (e.g. the AI-only F/A-18C, which has no unit data file).
            continue
        for entry in payload.get("pylons", {}).values():
            pylon = entry.get("num")
            clsid = entry.get("CLSID")
            stores = _pylon_stores(dcs_type, pylon)
            display = stores.get(clsid, "")
            for air_force, navy in SERVICE_PAIRS:
                if air_force not in display:
                    continue
                navy_options = [c for c, d in stores.items() if navy in d]
                if navy_options:
                    offenders.append(
                        f"{file_name} '{payload.get('name')}' pylon {pylon} carries "
                        f"{air_force} ({clsid}) but {navy} is mountable there: "
                        f"{sorted(navy_options)}"
                    )
    assert not offenders, "\n".join(offenders)


def test_navy_jets_never_ship_a_green_bomb_casing() -> None:
    # The setting is only ever written for a store that supports it, so "present
    # but 0" is a real regression (a green case on a Navy jet); "absent" just
    # means that store has no visual section and is left alone.
    green = []
    for file_name, _unit_id, payload in _shipped_payloads():
        if file_name not in NAVY_PAYLOAD_FILES:
            continue
        for entry in payload.get("pylons", {}).values():
            settings = entry.get("settings") or {}
            value = settings.get(CASING_KEY)
            if value is None:
                continue
            # 0.1 on this key is an unrelated missile visual (AIM-9 seeker), not
            # a bomb casing -- only whole 0/1 values are the casing selector.
            if value in (0, 1) and value != NAVY_WHITE:
                green.append(
                    f"{file_name} '{payload.get('name')}' pylon {entry.get('num')} "
                    f"{entry.get('CLSID')} carries the green casing ({CASING_KEY}=0)"
                )
    assert not green, "\n".join(green)


def test_the_asked_for_jets_actually_carry_the_white_casing() -> None:
    found = set()
    for file_name, _unit_id, payload in _shipped_payloads():
        for entry in payload.get("pylons", {}).values():
            settings = entry.get("settings") or {}
            if settings.get(CASING_KEY) == NAVY_WHITE:
                found.add((file_name, entry.get("CLSID")))
    missing = [pair for pair in CASING_REQUIRED if pair not in found]
    assert not missing, f"white casing missing for: {missing}"


def test_super_hornet_bomb_fits_are_the_authored_navy_load() -> None:
    from pydcs_extensions.fa18efg.fa18efg import FA_18E, FA_18F

    seen = set()
    for file_name, unit_id, payload in _shipped_payloads():
        if unit_id not in ("FA-18E", "FA-18F"):
            continue
        name = payload.get("name")
        if name not in SUPER_HORNET_BOMB_FITS:
            continue
        seen.add((unit_id, name))
        by_pylon = {
            entry["num"]: entry["CLSID"] for entry in payload.get("pylons", {}).values()
        }
        for pylon, clsid in SUPER_HORNET_NAVY_FIT.items():
            assert by_pylon.get(pylon) == clsid, (
                f"{file_name} '{name}' pylon {pylon}: expected {clsid}, "
                f"got {by_pylon.get(pylon)}"
            )

    assert seen == {
        (unit, fit) for unit in ("FA-18E", "FA-18F") for fit in SUPER_HORNET_BOMB_FITS
    }, f"missing Super Hornet bomb fits: {sorted(seen)}"

    for dcs_type in (FA_18E, FA_18F):
        stations = []
        for pylon, clsid in SUPER_HORNET_NAVY_FIT.items():
            stores = _pylon_stores(dcs_type, pylon)
            assert clsid in stores, f"{dcs_type.id} pylon {pylon} cannot mount {clsid}"
            # " [ STA 03   | SUU79 | BRU32 ] - 1x GBU-31(V)4/B ..."
            match = re.search(r"\[\s*STA\s+([0-9]+)", stores[clsid])
            assert match is not None, f"no station in {stores[clsid]!r}"
            stations.append(match.group(1))
        # Each CJS pylon index reaches more than one physical station, so the
        # collision this guards is real: the (V)4 claims the midboards, which
        # rules out the BRU-55 GBU-32 pairs that sit on those same stations.
        assert sorted(stations) == ["02", "03", "09", "10"], stations
