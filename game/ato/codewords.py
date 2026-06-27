"""Mission-wide SRS code words (Red Flag 81-2 style).

A squadron-grown idea, modelled on the Red Flag 81-2 kneeboards: the whole side
shares one code-word table — a **push word per task** (STRIKE / SEAD / OCA / …) plus
a couple of mission-wide event words — so every flight's kneeboard lists the same
table and a single call ("Cobalt") tells everyone that SEAD is pushing.

The table is generated once per turn from a randomly chosen *themed* pool (so a
mission's words feel deliberate), stored on the ``Coalition`` (stable while a planner
builds a briefing and regenerates the mission, pickled into the save), and re-drawn
next turn. Purely human comms aids — nothing scripts off them.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, unique
from typing import Dict, Iterable, List, Optional, Set

from game.ato.flighttype import FlightType


@unique
class PushCategory(Enum):
    """Task families that get their own push word. Order = display order."""

    STRIKE = "STRIKE"
    SEAD = "SEAD"
    OCA = "OCA"
    CAS = "CAS"
    ANTISHIP = "ANTISHIP"
    CAP = "CAP"
    EW = "EW"


_CATEGORY_BY_TASK: Dict[FlightType, PushCategory] = {
    FlightType.STRIKE: PushCategory.STRIKE,
    FlightType.SEAD: PushCategory.SEAD,
    FlightType.DEAD: PushCategory.SEAD,
    FlightType.SEAD_ESCORT: PushCategory.SEAD,
    FlightType.SEAD_SWEEP: PushCategory.SEAD,
    FlightType.OCA_RUNWAY: PushCategory.OCA,
    FlightType.OCA_AIRCRAFT: PushCategory.OCA,
    FlightType.CAS: PushCategory.CAS,
    FlightType.BAI: PushCategory.CAS,
    FlightType.SCAR: PushCategory.CAS,
    FlightType.ARMED_RECON: PushCategory.CAS,
    FlightType.ANTISHIP: PushCategory.ANTISHIP,
    FlightType.TARCAP: PushCategory.CAP,
    FlightType.BARCAP: PushCategory.CAP,
    FlightType.ESCORT: PushCategory.CAP,
    FlightType.SWEEP: PushCategory.CAP,
    FlightType.INTERCEPTION: PushCategory.CAP,
    FlightType.JAMMING: PushCategory.EW,
}


def push_category_for(flight_type: FlightType) -> Optional[PushCategory]:
    """The push category for a task, or None for tasks that don't push (support)."""
    return _CATEGORY_BY_TASK.get(flight_type)


def present_categories(tasks: Iterable[FlightType]) -> Set[PushCategory]:
    """The push categories represented among ``tasks`` (e.g. an ATO's primary tasks)."""
    out: Set[PushCategory] = set()
    for task in tasks:
        category = push_category_for(task)
        if category is not None:
            out.add(category)
    return out


#: Themed word pools — one is chosen per turn so a mission's code words read as a
#: coherent set. Deliberately **short single words** (quick to say and unambiguous
#: over the radio), and none are stock DCS callsigns or standard brevity terms. Each
#: pool needs at least ``len(PushCategory) + 3`` words.
_THEMES: Dict[str, List[str]] = {
    "Steel": [
        "Iron",
        "Cobalt",
        "Copper",
        "Bronze",
        "Pewter",
        "Tungsten",
        "Chrome",
        "Brass",
        "Nickel",
        "Titanium",
        "Gunmetal",
        "Zinc",
    ],
    "Spectrum": [
        "Crimson",
        "Scarlet",
        "Amber",
        "Indigo",
        "Onyx",
        "Ivory",
        "Teal",
        "Maroon",
        "Violet",
        "Magenta",
        "Umber",
        "Sienna",
    ],
    "Bedrock": [
        "Granite",
        "Obsidian",
        "Quartz",
        "Basalt",
        "Flint",
        "Cinder",
        "Slate",
        "Marble",
        "Shale",
        "Gravel",
        "Sandstone",
        "Limestone",
    ],
    "Pack": [
        "Jackal",
        "Lynx",
        "Badger",
        "Wolverine",
        "Bison",
        "Mongoose",
        "Gator",
        "Bobcat",
        "Hyena",
        "Caribou",
        "Marten",
        "Ferret",
    ],
}


@dataclass(frozen=True)
class MissionCodeWords:
    """One side's mission-wide code-word table for a turn."""

    theme: str
    push: Dict[PushCategory, str]
    success: str
    abort: str
    stop_jam: str

    @classmethod
    def generate(cls) -> "MissionCodeWords":
        theme = random.choice(list(_THEMES))
        words = random.sample(_THEMES[theme], len(PushCategory) + 3)
        chosen = iter(words)
        push = {category: next(chosen) for category in PushCategory}
        return cls(
            theme=theme,
            push=push,
            success=next(chosen),
            abort=next(chosen),
            stop_jam=next(chosen),
        )

    def push_for(self, flight_type: FlightType) -> Optional[str]:
        """The push word for a task's category, or None for non-pushing tasks."""
        category = push_category_for(flight_type)
        return self.push.get(category) if category is not None else None
