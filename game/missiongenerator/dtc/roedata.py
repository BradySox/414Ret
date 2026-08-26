"""The F-16C ROE tab's Air Target Data Table, derived per campaign (§74).

The MMC's ROE logic reads a per-type sovereignty table the jet can only get
from a cartridge, and the shipped default is all-UNKNOWN. Retribution knows
every squadron's airframe and coalition, which is exactly the input the table
wants: a type only blue flies is FRIENDLY, only red HOSTILE, both (or neither)
stays UNKNOWN — the family-level collision rule, so one side's variant can
never mark the other side's variant of the same family friendly.

The row set mirrors ``CoreMods/aircraft/F-16C/DTC/MPD/ROE_defs.lua`` (the 48
groups the ROE grid carries) and the membership mirrors ``threat_base.lua``,
whose loader compiles rows from its own base and reads ONLY ``sovereignty``
from the cartridge — so the emitted rows are ``{group_name, sovereignty}`` and
membership stays DCS's problem. Families threat_base identifies by wsType
rather than unit id (F-15C, MiG-23, E-3, …) are resolved here from its own
``hint`` strings; the lock test pins every id to pydcs so a rename fails
loudly instead of silently dropping a family.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from game import Game

SOVEREIGNTY_FRIENDLY = 1
SOVEREIGNTY_HOSTILE = 2
SOVEREIGNTY_UNKNOWN = 3

#: ROE group -> the DCS unit type ids it covers. Order matches ROE_defs.lua.
ATDT_FAMILIES: dict[str, tuple[str, ...]] = {
    "A-6": ("A6E",),
    "A-10": ("A-10A", "A-10C", "A-10C_2"),
    "AJS37": ("AJS37",),
    "An-26": ("An-26B",),
    "An-30": ("An-30M",),
    "AV-8B": ("AV8BNA",),
    "B-1": ("B-1B",),
    "B-52": ("B-52H",),
    "C-17": ("C-17A",),
    "C-130": ("C-130", "C-130J-30", "KC130"),
    "E-2": ("E-2C",),
    "E-3": ("E-3A",),
    "F-4": ("F-4E", "F-4E-45MC", "QF-4E"),
    "F-5": ("F-5E", "F-5E-3", "F-5E-3_FC"),
    "F-14": (
        "F-14A",
        "F-14A-135-GR",
        "F-14A-135-GR-Early",
        "F-14A-95-GR",
        "F-14B",
        "F-14BU",
    ),
    "F-15": ("F-15C", "F-15E", "F-15ESE"),
    "F-16": ("F-16A", "F-16A MLU", "F-16C bl.50", "F-16C bl.52d", "F-16C_50"),
    "F/A-18": ("F/A-18A", "F/A-18C", "FA-18C_hornet"),
    "Il-76": ("A-50", "IL-76MD"),
    "Il-78": ("IL-78M",),
    "JF-17": ("JF-17",),
    "KC-135": ("KC-135", "KC135MPRS"),
    "KJ-2000": ("KJ-2000",),
    "L-39": ("L-39C", "L-39ZA"),
    "MiG-19": ("MiG-19P",),
    "MiG-21": ("MiG-21Bis",),
    "MiG-23": ("MiG-23MLD",),
    "MiG-25": ("MiG-25PD", "MiG-25RBT"),
    "MiG-27": ("MiG-27K",),
    "MiG-29": ("MiG-29 Fulcrum", "MiG-29A", "MiG-29G", "MiG-29S"),
    "MiG-31": ("MiG-31",),
    "Mirage 2000": ("M-2000C", "Mirage 2000-5"),
    "Mirage F1": (
        "Mirage-F1AD",
        "Mirage-F1AZ",
        "Mirage-F1B",
        "Mirage-F1BD",
        "Mirage-F1BE",
        "Mirage-F1BQ",
        "Mirage-F1C",
        "Mirage-F1C-200",
        "Mirage-F1CE",
        "Mirage-F1CG",
        "Mirage-F1CH",
        "Mirage-F1CJ",
        "Mirage-F1CK",
        "Mirage-F1CR",
        "Mirage-F1CT",
        "Mirage-F1CZ",
        "Mirage-F1DDA",
        "Mirage-F1ED",
        "Mirage-F1EDA",
        "Mirage-F1EE",
        "Mirage-F1EH",
        "Mirage-F1EQ",
        "Mirage-F1JA",
        "Mirage-F1M-CE",
        "Mirage-F1M-EE",
    ),
    "S-3": ("S-3B", "S-3B Tanker"),
    "Su-17": ("Su-17M4",),
    "Su-24": ("Su-24M", "Su-24MR"),
    "Su-25": ("Su-25", "Su-25T", "Su-25TM"),
    "Su-27": ("Su-27", "J-11A"),
    "Su-30": ("Su-30",),
    "Su-33": ("Su-33",),
    "Su-34": ("Su-34",),
    "Tornado GR1": ("Tornado IDS",),
    "Tornado GR4": ("Tornado GR4",),
    "Tu-16": ("H-6J",),
    "Tu-22": ("Tu-22M3",),
    "Tu-95": ("Tu-95MS",),
    "Tu-142": ("Tu-142",),
    "Tu-160": ("Tu-160",),
}

_ID_TO_GROUPS: dict[str, list[str]] = {}
for _group, _ids in ATDT_FAMILIES.items():
    for _id in _ids:
        _ID_TO_GROUPS.setdefault(_id, []).append(_group)


def _squadron_ids(game: Game, blue: bool) -> Iterator[str]:
    coalition = game.blue if blue else game.red
    for squadron in coalition.air_wing.iter_squadrons():
        yield squadron.aircraft.dcs_unit_type.id


def build_atdt(game: Game) -> list[dict[str, Any]]:
    """The 48 ROE rows with campaign-derived sovereignty.

    Every group is emitted, UNKNOWN included, so a re-fly after a squadron
    transfer overwrites a stale declaration instead of leaving it standing.
    """
    blue_groups: set[str] = set()
    red_groups: set[str] = set()
    for blue, bucket in ((True, blue_groups), (False, red_groups)):
        for unit_id in _squadron_ids(game, blue):
            for group in _ID_TO_GROUPS.get(unit_id, ()):
                bucket.add(group)

    rows = []
    for group in ATDT_FAMILIES:
        if group in blue_groups and group not in red_groups:
            sovereignty = SOVEREIGNTY_FRIENDLY
        elif group in red_groups and group not in blue_groups:
            sovereignty = SOVEREIGNTY_HOSTILE
        else:
            sovereignty = SOVEREIGNTY_UNKNOWN
        rows.append({"group_name": group, "sovereignty": sovereignty})
    return rows
