from __future__ import annotations

import datetime
import inspect
import logging
from dataclasses import dataclass, field
from enum import unique, Enum
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Iterator, Optional, Any, ClassVar, Dict

import yaml
from dcs.flyingunit import FlyingUnit
from dcs.weapons_data import weapon_ids
from dcs.weapon_settings import WeaponSettings, has_settings, create_settings

from game.dcs.aircrafttype import AircraftType
from game.factions.faction import Faction

PydcsWeapon = Any
PydcsWeaponAssignment = tuple[int, PydcsWeapon]


def weapons_migrator(name: str) -> str:
    migration_map = {
        "AGM-88C HARM - High Speed Anti-Radiation Missile": "AGM-88C HARM",
        "Kh-25MPU (Updated AS-12 Kegler) - 320kg, ARM, IN & Pas Rdr": "Kh-25MPU",
        "Kh-31P (AS-17 Krypton) - 600kg, ARM, IN & Pas Rdr": "Kh-31P",
        "Kh-58U (AS-11 Kilter) - 640kg, ARM, IN & Pas Rdr": "Kh-58U",
    }
    while name in migration_map:
        name = migration_map[name]
    return name


def clsid_migrator(clsid: str) -> str:
    migration_map = {
        "{SUPERHORNET_PYLON_03_IB_FT_1X_FPU-8A}": "{SUPERHORNET_PYLON_03_IB_FT_1X_FPU-12A}",
        "{SUPERHORNET_PYLON_04_IB_FT_1X_FPU-8A}": "{SUPERHORNET_PYLON_04_IB_FT_1X_FPU-12A}",
        "{SUPERHORNET_PYLON_08_IB_FT_1X_FPU-8A}": "{SUPERHORNET_PYLON_08_IB_FT_1X_FPU-12A}",
        "{SUPERHORNET_PYLON_09_IB_FT_1X_FPU-8A}": "{SUPERHORNET_PYLON_09_IB_FT_1X_FPU-12A}",
        "{SUPERHORNET_PYLON_03_MB_FT_1X_FPU-8A}": "{SUPERHORNET_PYLON_03_MB_FT_1X_FPU-12A}",
        "{SUPERHORNET_PYLON_09_MB_FT_1X_FPU-8A}": "{SUPERHORNET_PYLON_09_MB_FT_1X_FPU-12A}",
        "{SUPERHORNET_PYLON_03_IB_FT_1X_FPU-8A_HV}": "{SUPERHORNET_PYLON_03_IB_FT_1X_FPU-12A_HV}",
        "{SUPERHORNET_PYLON_04_IB_FT_1X_FPU-8A_HV}": "{SUPERHORNET_PYLON_04_IB_FT_1X_FPU-12A_HV}",
        "{SUPERHORNET_PYLON_08_IB_FT_1X_FPU-8A_HV}": "{SUPERHORNET_PYLON_08_IB_FT_1X_FPU-12A_HV}",
        "{SUPERHORNET_PYLON_09_IB_FT_1X_FPU-8A_HV}": "{SUPERHORNET_PYLON_09_IB_FT_1X_FPU-12A_HV}",
        "{SUPERHORNET_PYLON_03_MB_FT_1X_FPU-8A_HV}": "{SUPERHORNET_PYLON_03_MB_FT_1X_FPU-12A_HV}",
        "{SUPERHORNET_PYLON_09_MB_FT_1X_FPU-8A_HV}": "{SUPERHORNET_PYLON_09_MB_FT_1X_FPU-12A_HV}",
        "{SUPERHORNET_PYLON_02_MB_JS_2X_BRU_AGM-154C}": "{SUPERHORNET_PYLON_02_MB_JS_2X_BRU55_AGM-154A}",
    }
    while clsid in migration_map:
        clsid = migration_map[clsid]
    return clsid


def weapons_migrator_lib(name: str) -> str:
    # Splitting this from our own migrations
    if "KH" in name:
        return "Kh" + name[2:]
    # UNCOMMENT BELOW WHEN IT BECOMES APPLICABLE
    # migration_map = {}
    # while name in migration_map:
    #     name = migration_map[name]
    return name


@dataclass(frozen=True)
class Weapon:
    """Wrapper for DCS weapons."""

    #: The CLSID used by DCS.
    clsid: str

    #: The group this weapon belongs to.
    weapon_group: WeaponGroup = field(compare=False)

    _by_clsid: ClassVar[dict[str, Weapon]] = {}
    _loaded: ClassVar[bool] = False

    def __str__(self) -> str:
        return self.name

    @cached_property
    def pydcs_data(self) -> PydcsWeapon:
        if self.clsid == "<CLEAN>":
            # Special case for a "weapon" that isn't exposed by pydcs.
            return {
                "clsid": self.clsid,
                "name": "Clean",
                "weight": 0,
            }
        return weapon_ids[self.clsid]

    @property
    def name(self) -> str:
        return self.pydcs_data["name"]

    def __setstate__(self, state: dict[str, Any]) -> None:
        # Update any existing models with new data on load.
        updated = Weapon.with_clsid(state["clsid"])
        if updated is not None:
            state.update(updated.__dict__)
        else:
            # The clsid is unknown to this build (a mod pack was disabled, or
            # the weapon data was removed without a migrator entry). Keep the
            # pickled state rather than leaving an EMPTY object whose first
            # attribute access blows up far from the cause.
            logging.warning(
                "Unknown weapon clsid %r in save; keeping pickled data",
                state.get("clsid"),
            )
        self.__dict__.update(state)

    @classmethod
    def register(cls, weapon: Weapon) -> None:
        if weapon.clsid in cls._by_clsid:
            duplicate = cls._by_clsid[weapon.clsid]
            raise ValueError(
                "Weapon CLSID used in more than one weapon type: "
                f"{duplicate.name} and {weapon.name}: {weapon.clsid}"
            )
        cls._by_clsid[weapon.clsid] = weapon

    @classmethod
    def with_clsid(cls, clsid: str) -> Optional[Weapon]:
        if not cls._loaded:
            cls._load_all()
        clsid = clsid_migrator(clsid)
        return cls._by_clsid.get(clsid)

    @classmethod
    def _load_all(cls) -> None:
        WeaponGroup.load_all()
        cls._loaded = True

    def available_on(self, date: datetime.date, faction: Faction) -> bool:
        introduction_year = self.weapon_group.introduction_year
        faction_introduction_year_overrides = getattr(
            faction, "weapons_introduction_year_overrides", {}
        )
        if self.weapon_group.name in faction_introduction_year_overrides:
            introduction_year = faction_introduction_year_overrides[
                self.weapon_group.name
            ]
        if introduction_year is None:
            return True
        return date >= datetime.date(introduction_year, 1, 1)

    @property
    def fallbacks(self) -> Iterator[Weapon]:
        yield self
        fallback: Optional[WeaponGroup] = self.weapon_group
        while fallback is not None:
            yield from fallback.weapons
            fallback = fallback.fallback

    def has_settings(self) -> bool:
        try:
            return has_settings(self.pydcs_data)
        except Exception:
            return False

    def accepts_laser_code(self) -> bool:
        try:
            settings = self.pydcs_data.get("settings")
        except Exception:
            return False
        if not isinstance(settings, list):
            return False
        return any(
            isinstance(s, dict) and s.get("id") == "laser_code" for s in settings
        )

    def create_settings(
        self, initial_values: Optional[Dict[str, Any]] = None
    ) -> Optional[WeaponSettings]:
        """Create settings, optionally loading initial values."""
        ws = create_settings(self.pydcs_data)
        if ws and initial_values:
            ws.from_dict(initial_values)
        return ws

    @lru_cache(maxsize=1)
    def get_target_overrides(self, targets: tuple[Any]) -> Dict[str, Any]:
        """
        Get weapon settings overrides for specific targets.

        Args:
            targets: Tuple of target IDs (strings)

        Returns:
            Dictionary of setting overrides, empty dict if none apply

        The target_overrides in weapon YAML is a list of override rules.
        Each rule has unit_ids (list) and settings (dict).
        First matching rule wins.
        """
        if targets and self.weapon_group.target_overrides:
            target_overrides_list = self.weapon_group.target_overrides
            target_ids = set(targets)

            for override_rule in target_overrides_list:
                rule_unit_ids = set(override_rule.get("unit_ids", []))
                try:
                    if target_ids & rule_unit_ids:
                        return override_rule["settings"].copy()
                except Exception as e:
                    raise ValueError(
                        f"Error processing target overrides for {self.name}, targets: {targets}: {e}"
                    )
        return {}


@unique
class WeaponType(Enum):
    ARM = "ARM"
    LGB = "LGB"
    TGP = "TGP"
    DECOY = "DECOY"
    JAMMER = "JAMMER"
    OFFENSIVE_JAMMER = "OFFENSIVE_JAMMER"
    UNKNOWN = "unknown"


# §54 munitions availability -- the curated "scarce" taxonomy (M0). Only the
# munitions worth *running out of* are tracked; everything else (dumb bombs, IR
# dogfight missiles, rockets, guns, tanks) is effectively infinite. Keyed by exact
# ``WeaponGroup.name`` (every rack/quantity variant listed) so the set is explicit
# and auditable rather than an opaque runtime classifier -- hand-audited 2026-07-08,
# and ``tests/fourteenth/test_scarce_munitions.py`` fails CI if any name here stops
# resolving to a real weapon group (the dead-name guard). Families are coarse on
# purpose (M1 tracks stock per family). Expand as new scarce weapons ship.
_SCARCE_MUNITIONS: dict[str, tuple[str, ...]] = {
    # Radar / medium-to-long-range A2A (IR dogfight missiles stay infinite).
    "a2a_medium": (
        "2xAIM-120B",
        "2xAIM-120C",
        "AIM-120B",
        "AIM-120C",
        "AIM-54A-MK47",
        "AIM-54A-MK60",
        "AIM-54C-MK47",
        "AIM-54C-MK60",
        "AIM-7E",
        "AIM-7E-2",
        "AIM-7F",
        "AIM-7M",
        "AIM-7MH",
        "AIM-7P",
        "R-24R",
        "R-27ER",
        "R-27ET",
        "R-27R",
        "R-27T",
        "R-37 (AA-13 Axehead)",
        "R-37M (AA-13 Axehead)",
        "R-40R",
        "R-77",
        "R530F EM",
        "R530F IR",
        "S530D",
        "S530F",
    ),
    # Anti-radiation (authoritative: DB type ARM), plus the anti-radar Kh-25MP.
    "arm": (
        "2 x ALARM",
        "AGM-122A",
        "AGM-45A Shrike ARM",
        "AGM-45B Shrike ARM (Imp)",
        "AGM-78A Standard ARM",
        "AGM-78B Standard ARM",
        "AGM-88C HARM",
        "ALARM",
        "KSR-2P (passive)",
        "KSR-5P (passive)",
        "Kh-22P",
        "Kh-25MP",
        "Kh-25MPU",
        "Kh-31P",
        "Kh-58U",
        "LD-10",
        "LD-10 x 2",
        "MAR-1 High Speed Anti-Radiation Missile",
    ),
    # Guided bombs (laser / GPS / EO).
    "pgm_bomb": (
        "16xGBU-38",
        "2xCBU-103",
        "2xCBU-105",
        "2xGBU-10",
        "2xGBU-12",
        "2xGBU-16",
        "2xGBU-38",
        "2xGBU-54B",
        "3xGBU-12",
        "3xGBU-38",
        "3xGBU-54B",
        "8xGBU-31(V)1/B",
        "8xGBU-31(V)3/B",
        "CBU-103",
        "CBU-105",
        "GBU-10",
        "GBU-12",
        "GBU-15",
        "GBU-16",
        "GBU-24",
        "GBU-27",
        "GBU-31(V)1/B",
        "GBU-31(V)2/B",
        "GBU-31(V)3/B",
        "GBU-31(V)4/B",
        "GBU-32(V)2/B",
        "GBU-38",
        "GBU-39 SDB",
        "GBU-54B",
        "GBU-8/B HOBOS",
        "JDAM-ER",
        "KAB-1500KR",
        "KAB-1500L",
        "KAB-1500LG-Pr",
        "KAB-500Kr",
        "KAB-500LG",
        "KAB-500S",
    ),
    # Cruise / long-range & anti-ship / glide standoff.
    "standoff": (
        "20xAGM-86C",
        "20xAGM-86D",
        "2xAGM-154A JSOW",
        "2xAGM-154B JSOW",
        "2xAGM-154C JSOW",
        "4xAGM-154C",
        "6xAGM-86C",
        "6xAGM-86D",
        "8xAGM-84A",
        "8xAGM-86C",
        "8xAGM-86D",
        "AGM-130",
        "AGM-142 Popeye",
        "AGM-154A JSOW",
        "AGM-154B JSOW",
        "AGM-154C JSOW",
        "AGM-158B JASSM-ER",
        "AGM-158C LRASM",
        "AGM-62 Walleye I",
        "AGM-62 Walleye II",
        "AGM-84A",
        "AGM-84D",
        "AGM-84E SLAM",
        "AGM-84H SLAM-ER",
        "AGM-86C",
        "AGM-86D",
        "Kh-101",
        "Kh-20 (AS-3 Kangaroo)",
        "Kh-22 (AS-4 Kitchen)",
        "Kh-22MA",
        "Kh-28",
        "Kh-31A",
        "Kh-35",
        "Kh-36 Grom-E1",
        "Kh-41 Moskit (Sunburn)",
        "Kh-555",
        "Kh-59M",
        "Kh-59MK2 (AS-22 Kazoo)",
        "Kh-65",
        "Kh-66 Grohm",
        "Storm Shadow",
    ),
    # Tactical precision air-to-ground (Maverick / Hellfire / short guided ASM).
    "guided_asm": (
        "2xAGM-65A",
        "2xAGM-65B",
        "2xAGM-65D",
        "2xAGM-65E",
        "2xAGM-65H",
        "2xAGM-65K",
        "3xAGM-65A",
        "3xAGM-65B",
        "3xAGM-65D",
        "3xAGM-65E",
        "3xAGM-65H",
        "3xAGM-65K",
        "AGM-114K * 1",
        "AGM-114K * 2",
        "AGM-114K * 3",
        "AGM-114K * 4",
        "AGM-114L * 1",
        "AGM-114L * 2",
        "AGM-114L * 3",
        "AGM-12A",
        "AGM-12B",
        "AGM-12C",
        "AGM-65A",
        "AGM-65B",
        "AGM-65D",
        "AGM-65E",
        "AGM-65E2/L",
        "AGM-65F",
        "AGM-65G",
        "AGM-65H",
        "AGM-65K",
        "Kh-25ML",
        "Kh-25MR",
        "Kh-29L",
        "Kh-29T",
    ),
}

#: Reverse lookup name -> family, built once at import from :data:`_SCARCE_MUNITIONS`.
_SCARCE_FAMILY_BY_NAME: dict[str, str] = {
    name: family for family, names in _SCARCE_MUNITIONS.items() for name in names
}

#: The scarce-munition family keys (§54 M1 consumers iterate this to seed per-base
#: stock). Declaration order.
SCARCE_FAMILIES: tuple[str, ...] = tuple(_SCARCE_MUNITIONS.keys())


@dataclass(frozen=True)
class WeaponGroup:
    """Group of "identical" weapons loaded from resources/weapons.

    DCS has multiple unique "weapons" for each type of weapon. There are four distinct
    class IDs for the AIM-7M, some unique to certain aircraft. We group them in the
    resources to make year/fallback data easier to track.
    """

    #: The name of the weapon group in the resource file.
    name: str

    #: The type of the weapon group.
    type: WeaponType = field(compare=False)

    #: The year of introduction.
    introduction_year: Optional[int] = field(compare=False)

    #: The name of the fallback weapon group.
    fallback_name: Optional[str] = field(compare=False)

    #: The specific weapons that belong to this weapon group.
    weapons: list[Weapon] = field(init=False, default_factory=list)

    #: Target-based overrides for weapon settings
    target_overrides: list[Dict[str, Any]] = field(init=False, default_factory=list)

    _by_name: ClassVar[dict[str, WeaponGroup]] = {}
    _loaded: ClassVar[bool] = False

    def __str__(self) -> str:
        return self.name

    @property
    def fallback(self) -> Optional[WeaponGroup]:
        if self.fallback_name is None:
            return None
        return WeaponGroup.named(self.fallback_name)

    @property
    def scarce_family(self) -> Optional[str]:
        """§54: the curated scarce-munitions family, or None if this group is not
        stock-tracked (dumb bombs, IR dogfight missiles, rockets, guns, tanks -- all
        effectively infinite). See :data:`_SCARCE_MUNITIONS`. Pure lookup, no state.
        """
        return _SCARCE_FAMILY_BY_NAME.get(self.name)

    def __setstate__(self, state: dict[str, Any]) -> None:
        # Update any existing models with new data on load.
        name = weapons_migrator(state["name"])
        name = weapons_migrator_lib(name)
        try:
            updated = WeaponGroup.named(name)
        except KeyError:
            # The group was removed/renamed without a migrator entry. Keep the
            # pickled state instead of aborting the entire load ("Invalid Save
            # game") -- the same unknown-value tolerance FlightType has.
            logging.warning(
                "Unknown weapon group %r in save; keeping pickled data", name
            )
            self.__dict__.update(state)
            return
        state.update(updated.__dict__)
        self.__dict__.update(state)

    @classmethod
    def register(cls, group: WeaponGroup) -> None:
        if group.name in cls._by_name:
            duplicate = cls._by_name[group.name]
            raise ValueError(
                "Weapon group name used in more than one weapon type: "
                f"{duplicate.name} and {group.name}"
            )
        cls._by_name[group.name] = group

    @classmethod
    def named(cls, name: str) -> WeaponGroup:
        if not cls._loaded:
            cls.load_all()
        return cls._by_name[name]

    @classmethod
    def _each_weapon_group(cls) -> Iterator[WeaponGroup]:
        names = []
        links = []
        for group_file_path in Path("resources/weapons").glob("**/*.yaml"):
            with group_file_path.open(encoding="utf8") as group_file:
                data = yaml.safe_load(group_file)
            name = data["name"]
            names.append(name)
            try:
                weapon_type = WeaponType(data["type"])
            except KeyError:
                weapon_type = WeaponType.UNKNOWN
            year = data.get("year")
            fallback_name = data.get("fallback")
            if fallback_name:
                links.append((name, fallback_name))
            group = WeaponGroup(name, weapon_type, year, fallback_name)

            target_overrides = data.get("target_overrides", {})
            object.__setattr__(group, "target_overrides", target_overrides)

            for clsid in data["clsids"]:
                weapon = Weapon(clsid, group)
                Weapon.register(weapon)
                group.weapons.append(weapon)
            yield group

        for name, fb in links:
            if fb not in names:
                sn = "Unknown"
                for n in names:
                    if fb in n:
                        sn = n
                        break
                logging.error(
                    f"Weapon '{name}' has invalid fallback '{fb}': suggested = {sn}"
                )

    @classmethod
    def register_clean_pylon(cls) -> None:
        group = WeaponGroup(
            "Clean pylon",
            type=WeaponType.UNKNOWN,
            introduction_year=None,
            fallback_name=None,
        )
        cls.register(group)
        weapon = Weapon("<CLEAN>", group)
        Weapon.register(weapon)
        group.weapons.append(weapon)

    @classmethod
    def register_unknown_weapons(cls, seen_clsids: set[str]) -> None:
        unknown_weapons = set(weapon_ids.keys()) - seen_clsids
        group = WeaponGroup(
            "Unknown",
            type=WeaponType.UNKNOWN,
            introduction_year=None,
            fallback_name=None,
        )
        cls.register(group)
        for clsid in unknown_weapons:
            weapon = Weapon(clsid, group)
            Weapon.register(weapon)
            group.weapons.append(weapon)

    @classmethod
    def load_all(cls) -> None:
        if cls._loaded:
            return
        seen_clsids: set[str] = set()
        for group in cls._each_weapon_group():
            cls.register(group)
            seen_clsids.update(w.clsid for w in group.weapons)
        cls.register_clean_pylon()
        cls.register_unknown_weapons(seen_clsids)
        cls._loaded = True


@dataclass(frozen=True)
class Pylon:
    number: int
    allowed: set[Weapon]

    def can_equip(self, weapon: Weapon) -> bool:
        # TODO: Fix pydcs to support the <CLEAN> "weapon".
        # <CLEAN> is a special case because pydcs doesn't know about that "weapon", so
        # it's not compatible with *any* pylon. Just trust the loadout and try to equip
        # it.
        #
        # A similar hack exists in QPylonEditor to forcibly add "Clean" to the list of
        # valid configurations for that pylon if a loadout has been seen with that
        # configuration.
        return weapon in self.allowed or weapon.clsid == "<CLEAN>"

    def equip(
        self,
        unit: FlyingUnit,
        weapon: Weapon,
        settings: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.can_equip(weapon):
            logging.error(f"Pylon {self.number} cannot equip {weapon.name}")
        assignment = self.make_pydcs_assignment(weapon, settings)
        unit.load_pylon(assignment, self.number)

    def make_pydcs_assignment(
        self, weapon: Weapon, settings: Optional[Dict[str, Any]] = None
    ) -> PydcsWeaponAssignment:
        weapon_data = dict(weapon.pydcs_data)
        # Add settings if provided and weapon supports them
        if settings and weapon.has_settings():
            weapon_data["settings"] = settings
        return self.number, weapon_data

    def available_on(self, date: datetime.date, faction: Faction) -> Iterator[Weapon]:
        for weapon in self.allowed:
            if weapon.available_on(date, faction):
                yield weapon

    @classmethod
    def for_aircraft(cls, aircraft: AircraftType, number: int) -> Pylon:
        # In pydcs these are all arbitrary inner classes of the aircraft type.
        # The only way to identify them is by their name.
        pylons = [
            v
            for v in aircraft.dcs_unit_type.__dict__.values()
            if inspect.isclass(v) and v.__name__.startswith("Pylon")
        ]

        # And that Pylon class has members with irrelevant names that have
        # values of (pylon number, allowed weapon).
        allowed = set()
        for pylon in pylons:
            for key, value in pylon.__dict__.items():
                if key.startswith("__"):
                    continue
                pylon_number, weapon = value
                if pylon_number != number:
                    continue
                allowed_weapon = Weapon.with_clsid(weapon["clsid"])
                if allowed_weapon is not None:
                    allowed.add(allowed_weapon)

        return cls(number, allowed)

    @classmethod
    def iter_pylons(cls, aircraft: AircraftType) -> Iterator[Pylon]:
        for pylon in sorted(list(aircraft.dcs_unit_type.pylons)):
            yield cls.for_aircraft(aircraft, pylon)
