import re
from typing import Any

from dcs.weapons_data import Weapons, weapon_ids

_LEGACY_WEAPON_ALIASES = {
    "SUU_25___8_x_Illumination_Flare__LUU_2B": (
        "SUU_25_x_8_LUU_2___Target_Marker_Flares"
    ),
}


def _add_candidate_alias(aliases: set[str], alias: str) -> None:
    if not alias:
        return

    aliases.add(alias)

    # pydcs 2.9.28 renamed TER-9A rack attributes from TER_9_A to TER_9A.
    if "TER_9A" in alias:
        aliases.add(alias.replace("TER_9A", "TER_9_A"))
    if "TER_9_A" in alias:
        aliases.add(alias.replace("TER_9_A", "TER_9A"))

    # Some rack display names changed from singular to plural during generation.
    if "Bombs" in alias:
        aliases.add(alias.replace("Bombs", "Bomb"))
    if "CBUs" in alias:
        aliases.add(alias.replace("CBUs", "CBU"))


def _weapon_name_to_legacy_attribute(name: str) -> str:
    name = name.replace(" with ", "___")
    name = name.replace(" - ", "___")
    name = re.sub(r"[^0-9A-Za-z_]", "_", name)
    return name.strip("_")


def _legacy_weapon_aliases(attribute: str, weapon: dict[str, Any]) -> set[str]:
    aliases: set[str] = set()
    _add_candidate_alias(aliases, attribute.replace("_with_", "___"))
    rack, separator, store = attribute.partition("_with_")
    if separator and not re.match(r"\d+_x_", store):
        _add_candidate_alias(aliases, f"{rack}___1_x_{store}")

    weapon_name = weapon.get("name")
    if isinstance(weapon_name, str):
        _add_candidate_alias(aliases, _weapon_name_to_legacy_attribute(weapon_name))

    return aliases


def _inject_legacy_weapon_aliases() -> None:
    for attribute, weapon in tuple(vars(Weapons).items()):
        if not isinstance(weapon, dict):
            continue
        for alias in _legacy_weapon_aliases(attribute, weapon):
            if not hasattr(Weapons, alias):
                setattr(Weapons, alias, weapon)

    for alias, attribute in _LEGACY_WEAPON_ALIASES.items():
        if not hasattr(Weapons, alias) and hasattr(Weapons, attribute):
            setattr(Weapons, alias, getattr(Weapons, attribute))


_inject_legacy_weapon_aliases()


def inject_weapons(weapon_class: Any) -> None:
    """
    Inject custom weapons from mods into pydcs weapons databases via introspection
    :param weapon_class: The custom weapons class containing dictionaries with weapon info
    :return: None
    """
    for key, value in weapon_class.__dict__.items():
        if key.startswith("__"):
            continue
        if isinstance(value, dict) and value.get("clsid"):
            setattr(Weapons, key, value)
            weapon_ids[value["clsid"]] = value
