"""Per-package brevity code words (push / success / abort).

A squadron-grown idea: each package gets a small set of randomised code words its
flight calls over SRS for the key events — pushing to the target, target down, and
abort/knock-it-off. They are assigned once when first accessed and stored on the
``Package`` (so they stay stable while a planner builds a briefing and regenerates
the mission, and persist in the save), and a fresh package next turn draws new ones.

Purely human comms aids: nothing scripts off them, so they need no in-game trigger.
The pool is generic, unclassified, and deliberately avoids common DCS aircraft
callsigns so a code word can't be mistaken for a flight on the radio.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

#: Evocative single words, none of them stock DCS callsigns (so "ANVIL" can't be
#: confused with a flight). Three are drawn per package without replacement.
_CODE_WORD_POOL: List[str] = [
    "ANVIL",
    "AVALANCHE",
    "BEDROCK",
    "BLIZZARD",
    "CYCLONE",
    "DYNAMO",
    "EVEREST",
    "GLACIER",
    "GRANITE",
    "IRONCLAD",
    "JACKPOT",
    "KEYSTONE",
    "LANDSLIDE",
    "MONSOON",
    "NOMAD",
    "OMAHA",
    "OUTLAW",
    "OVERCAST",
    "QUICKSAND",
    "RAMPART",
    "RENEGADE",
    "SUNDOWN",
    "TEMPEST",
    "TROJAN",
    "UPROAR",
    "VANGUARD",
    "VERTIGO",
    "WARLOCK",
    "WILDFIRE",
    "ZIPLOCK",
    "ZODIAC",
]


@dataclass(frozen=True)
class PackageCodeWords:
    """The three event code words briefed for one package."""

    push: str
    success: str
    abort: str

    @classmethod
    def random(cls) -> "PackageCodeWords":
        push, success, abort = random.sample(_CODE_WORD_POOL, 3)
        return cls(push=push, success=success, abort=abort)
