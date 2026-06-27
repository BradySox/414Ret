from __future__ import annotations

from enum import Enum, unique
from typing import Any, Optional, TYPE_CHECKING

from dcs.forcedoptions import ForcedOptions

if TYPE_CHECKING:
    from game.settings.settings import Settings

Views = ForcedOptions.Views


@unique
class DifficultyPreset(Enum):
    """One-click difficulty/realism bundles for the Difficulty & Realism page.

    A preset is a *starting point*: it sets the difficulty-defining fields
    (PRESET_VALUES) and the player can still hand-tune any of them afterward.
    """

    CASUAL = "Casual"
    NORMAL = "Normal"
    VETERAN = "Veteran"
    ACE = "Ace"


# Each preset sets exactly this set of difficulty-defining fields; nothing else
# is touched. Player coalition skill (AI wingman quality, not a difficulty
# lever) is deliberately left alone. NORMAL mirrors the Settings defaults, so
# picking it is a clean reset to stock.
PRESET_VALUES: dict[DifficultyPreset, dict[str, Any]] = {
    DifficultyPreset.CASUAL: {
        "enemy_skill": "Average",
        "enemy_vehicle_skill": "Average",
        "player_income_multiplier": 1.5,
        "enemy_income_multiplier": 0.7,
        "invulnerable_player_pilots": True,
        "manpads": False,
        "labels": "Full",
        "map_coalition_visibility": Views.All,
        "external_views_allowed": True,
        "easy_communication": True,
        "battle_damage_assessment": True,
        "restrict_weapons_by_date": False,
    },
    DifficultyPreset.NORMAL: {
        "enemy_skill": "High",
        "enemy_vehicle_skill": "High",
        "player_income_multiplier": 1.0,
        "enemy_income_multiplier": 1.0,
        "invulnerable_player_pilots": True,
        "manpads": True,
        "labels": "Full",
        "map_coalition_visibility": Views.All,
        "external_views_allowed": True,
        "easy_communication": None,
        "battle_damage_assessment": None,
        "restrict_weapons_by_date": False,
    },
    DifficultyPreset.VETERAN: {
        "enemy_skill": "High",
        "enemy_vehicle_skill": "High",
        "player_income_multiplier": 1.0,
        "enemy_income_multiplier": 1.1,
        "invulnerable_player_pilots": False,
        "manpads": True,
        "labels": "Abbreviated",
        "map_coalition_visibility": Views.Allies,  # Fog of war
        "external_views_allowed": False,
        "easy_communication": None,
        "battle_damage_assessment": None,
        "restrict_weapons_by_date": True,
    },
    DifficultyPreset.ACE: {
        "enemy_skill": "Excellent",
        "enemy_vehicle_skill": "Excellent",
        "player_income_multiplier": 0.8,
        "enemy_income_multiplier": 1.3,
        "invulnerable_player_pilots": False,
        "manpads": True,
        "labels": "Off",
        "map_coalition_visibility": Views.MyAircraft,  # Own aircraft only
        "external_views_allowed": False,
        "easy_communication": False,
        "battle_damage_assessment": False,
        "restrict_weapons_by_date": True,
    },
}

# The union of every field any preset controls (all presets set the same keys).
PRESET_FIELDS: frozenset[str] = frozenset(
    key for values in PRESET_VALUES.values() for key in values
)


def apply_preset(settings: Settings, preset: DifficultyPreset) -> None:
    """Set the difficulty-defining fields on ``settings`` to ``preset``.

    Only the fields in ``PRESET_VALUES`` are touched; every other setting is the
    player's (and these can still be hand-tuned afterward).
    """
    for name, value in PRESET_VALUES[preset].items():
        setattr(settings, name, value)


def detect_preset(settings: Settings) -> Optional[DifficultyPreset]:
    """Return the preset whose values all match ``settings``, else ``None``.

    Used to highlight the active preset; ``None`` means a custom mix (the player
    has tuned a field away from any preset).
    """
    for preset, values in PRESET_VALUES.items():
        if all(getattr(settings, name) == value for name, value in values.items()):
            return preset
    return None
