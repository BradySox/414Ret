from __future__ import annotations

import itertools
import uuid
from abc import ABC
from typing import Any, Iterator, List, Optional, TYPE_CHECKING

from dcs.mapping import Point
from shapely.geometry import Point as ShapelyPoint

from game.sidc import (
    Entity,
    LandEquipmentEntity,
    LandInstallationEntity,
    LandUnitEntity,
    SeaSurfaceEntity,
    SidcDescribable,
    StandardIdentity,
    Status,
    SymbolSet,
    SymbolIdentificationCode,
)
from game.theater.presetlocation import PresetLocation
from .missiontarget import MissionTarget
from .player import Player
from ..data.groups import GroupTask
from ..utils import Distance, Heading, meters

if TYPE_CHECKING:
    from game.ato.flighttype import FlightType
    from game.threatzones import ThreatPoly
    from .theatergroup import TheaterUnit, TheaterGroup
    from .controlpoint import ControlPoint, Coalition


NAME_BY_CATEGORY = {
    "ewr": "Early Warning Radar",
    "aa": "AA Defense Site",
    "allycamp": "Camp",
    "ammo": "Ammo depot",
    "armor": "Armor group",
    "coastal": "Coastal defense",
    "commandcenter": "Command Center",
    "comms": "Communications tower",
    "derrick": "Derrick",
    "factory": "Factory",
    "farp": "FARP",
    "fob": "FOB",
    "fuel": "Fuel depot",
    "missile": "Missile site",
    "oil": "Oil platform",
    "power": "Power plant",
    "ship": "Ship",
    "village": "Village",
    "ware": "Warehouse",
    "ww2bunker": "Bunker",
}


class TheaterGroundObject(MissionTarget, SidcDescribable, ABC):
    def __init__(
        self,
        name: str,
        category: str,
        location: PresetLocation,
        control_point: ControlPoint,
        sea_object: bool,
        task: Optional[GroupTask],
        hide_on_mfd: bool = False,
    ) -> None:
        super().__init__(name, location)
        self.id = uuid.uuid4()
        self.category = category
        self.heading = location.heading
        self.control_point = control_point
        self.sea_object = sea_object
        self.groups: List[TheaterGroup] = []
        self.original_name = location.original_name
        self._threat_poly: ThreatPoly | None = None
        self.task = task
        self.hide_on_mfd = hide_on_mfd
        # Recon intel-fog: has the human (BLUE) player discovered what is actually
        # at this site? New enemy sites start unknown (composition + threat rings
        # hidden) until attacked, scouted, or destroyed. Friendly/neutral sites and
        # omniscient (viewer=None) callers are handled by known_for(), so this flag
        # only matters for enemy sites from the player's perspective.
        self.discovered_by_player = False

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        del state["_threat_poly"]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        state["_threat_poly"] = None
        # Save compatibility: a campaign saved before recon intel-fog has every
        # site already on the player's map, so treat it as fully discovered rather
        # than suddenly blanking an in-progress campaign. The fog is felt on new
        # campaigns (where the flag defaults False).
        if "discovered_by_player" not in state:
            state["discovered_by_player"] = True
        self.__dict__.update(state)

    def _command_post_revealed(self) -> bool:
        """SCAR: True once an enemy command post is revealed to the human side.

        Two keys (SME 2026-06-18): the side captured an enemy commander (reveals
        ALL command posts, permanently), OR the site was discovered the normal way
        (attacked / scouted / TARPS). Only meaningful for an enemy viewer — the
        callers gate ``None``/friendly first.
        """
        return (
            self.control_point.coalition.opponent.captured_commander
            or self.discovered_by_player
        )

    def known_for(self, viewer: Optional[Player] = None) -> bool:
        """Whether the viewer knows what is actually at this site.

        ``viewer=None`` (omniscient — AI, planner, threat math) and friendly
        viewers always know. An enemy viewer only knows once the site has been
        discovered (attacked / scouted / destroyed). The whole feature can be
        switched off via the ``recon_intel_fog`` campaign setting.
        """
        if viewer is None or self.is_friendly(viewer):
            return True
        settings = self.control_point.coalition.game.settings
        # SCAR campaign engine: an enemy command post is known only once revealed
        # (commander captured or site discovered). Its own gate, independent of the
        # general recon fog.
        if self.category == "commandcenter" and settings.scar_command_post_intel:
            return self._command_post_revealed()
        if not settings.recon_intel_fog:
            return True
        return self.discovered_by_player

    def hidden_on_player_map(self, viewer: Optional[Player] = None) -> bool:
        """SCAR: True if this site must not appear on ``viewer``'s map at all.

        Normally every enemy site shows as a targetable marker and only its
        composition is fogged (see ``known_for``). SCAR command posts are the
        exception: an enemy command post is hidden ENTIRELY — no marker, not
        plannable or strikable — until it is revealed (commander captured, or the
        site discovered by strike/scout/TARPS). After that it shows fully, with
        exact coordinates (SME 2026-06-18). ``viewer=None`` (omniscient: AI /
        planner / threat math) and friendly viewers see everything, so AI planning
        is never fogged.
        """
        if viewer is None or self.is_friendly(viewer):
            return False
        settings = self.control_point.coalition.game.settings
        if self.category == "commandcenter" and settings.scar_command_post_intel:
            return not self._command_post_revealed()
        return False

    @property
    def sidc_status(self) -> Status:
        # SidcDescribable requires this as a property (the base `sidc` builder
        # reads it). It is the ground-truth status; the viewer-aware map symbol
        # uses sidc_status_for(viewer).
        return self.sidc_status_for(None)

    @property
    def standard_identity(self) -> StandardIdentity:
        if self.control_point.captured.is_blue:
            return StandardIdentity.FRIEND
        elif self.control_point.captured.is_neutral:
            return StandardIdentity.UNKNOWN
        else:
            return StandardIdentity.HOSTILE_FAKER

    def is_dead(self, viewer: Optional[Player] = None) -> bool:
        return self.alive_unit_count(viewer) == 0

    @property
    def units(self) -> Iterator[TheaterUnit]:
        """
        :return: all the units at this location
        """
        yield from itertools.chain.from_iterable([g.units for g in self.groups])

    @property
    def statics(self) -> Iterator[TheaterUnit]:
        for group in self.groups:
            for unit in group.units:
                if unit.is_static:
                    yield unit

    def dead_units(self, viewer: Optional[Player] = None) -> list[TheaterUnit]:
        """All units at this location that are dead from the viewer's perspective.

        ``viewer=None`` is ground truth; an enemy viewer sees confirmed kills.
        """
        return [unit for unit in self.units if not unit.alive_for(viewer)]

    @property
    def group_name(self) -> str:
        """The name of the unit group."""
        return f"{self.category}|{self.name}"

    @property
    def display_name(self) -> str:
        """The display name of the tgo which will be shown on the map."""
        return self.group_name

    @property
    def waypoint_name(self) -> str:
        return f"[{self.name}] {self.category}"

    def __str__(self) -> str:
        return NAME_BY_CATEGORY[self.category]

    @property
    def air_defense_band(self) -> Optional[str]:
        """Human-readable range band for an air-defense site, e.g. "Long-range SAM".

        Derived from the site's designated role (``task``), not its live units, so it
        is intel-level information available even before the site is scouted (you know
        the threat tier; recon still reveals the exact system and its ring). Returns
        None for non air-defense sites.
        """
        bands = {
            GroupTask.LORAD: "Long-range SAM",
            GroupTask.MERAD: "Medium-range SAM",
            GroupTask.SHORAD: "Short-range SAM",
            GroupTask.POINT_DEFENSE: "Point-defense SAM",
            GroupTask.AAA: "AAA",
            GroupTask.EARLY_WARNING_RADAR: "Early-warning radar",
        }
        if self.task is None:
            return None
        return bands.get(self.task)

    @property
    def obj_name(self) -> str:
        return self.name

    @property
    def faction_color(self) -> str:
        return "BLUE" if self.control_point.captured else "RED"

    def is_friendly(self, to_player: Player) -> bool:
        if self.control_point.captured.is_neutral:
            return False
        return self.control_point.is_friendly(to_player)

    def mission_types(self, for_player: Player) -> Iterator[FlightType]:
        from game.ato import FlightType

        if self.is_friendly(for_player):
            yield from [
                # TODO: FlightType.LOGISTICS
                # TODO: FlightType.TROOP_TRANSPORT
            ]
        else:
            yield from [
                FlightType.STRIKE,
                FlightType.REFUELING,
            ]
            if self.warrants_recon:
                yield FlightType.TARPS
            # SOF insert (a C-130 airdrop of a SCAR capture team) is a player-only
            # companion to a SCAR tasking on this target. Gated behind the
            # commander-capture feature and the CTLD plugin it delivers through;
            # the AI never plans it (no proposing task), so this only adds a
            # manually selectable option. The settings lookup is defensive because
            # some lightweight contexts hold a control point without a coalition.
            try:
                settings = self.control_point.coalition.game.settings
            except (RuntimeError, AttributeError):
                settings = None
            if (
                settings is not None
                and settings.scar_command_post_intel
                and settings.plugin_option("ctld")
            ):
                yield FlightType.SOF
        yield from super().mission_types(for_player)

    @property
    def warrants_recon(self) -> bool:
        """Whether this target is worth a TARPS photo-recon / BDA overflight.

        Gates both the auto-paired TARPS flight and the manually selectable TARPS
        mission type to high-value targets. Default False; subclasses opt in (air
        defenses, and strategic infrastructure such as factories, command posts,
        and bridges).
        """
        return False

    @property
    def unit_count(self) -> int:
        return sum(g.unit_count for g in self.groups)

    def alive_unit_count(self, viewer: Optional[Player] = None) -> int:
        return sum(g.alive_units(viewer) for g in self.groups)

    @property
    def has_aa(self) -> bool:
        """Returns True if the ground object contains a working anti air unit"""
        return any(u.alive and u.is_anti_air for u in self.units)

    @property
    def has_live_radar_sam(self) -> bool:
        """Returns True if the ground object contains a unit with working radar SAM."""
        return any(g.max_threat_range(radar_only=True) for g in self.groups)

    def max_detection_range(self, viewer: Optional[Player] = None) -> Distance:
        """Maximum detection range of the ground object (viewer=None is truth)."""
        return max(
            (g.max_detection_range(viewer) for g in self.groups), default=meters(0)
        )

    def max_threat_range(self, viewer: Optional[Player] = None) -> Distance:
        """Maximum threat range of the ground object (viewer=None is truth)."""
        return max((g.max_threat_range(viewer) for g in self.groups), default=meters(0))

    def sidc_status_for(self, viewer: Optional[Player] = None) -> Status:
        if self.control_point.captured.is_neutral:
            return Status.PRESENT
        if self.is_dead(viewer):
            return Status.PRESENT_DESTROYED
        elif self.dead_units(viewer):
            return Status.PRESENT_DAMAGED
        else:
            return Status.PRESENT

    def sidc_for(self, viewer: Optional[Player] = None) -> SymbolIdentificationCode:
        symbol_set, entity = self.symbol_set_and_entity
        return SymbolIdentificationCode(
            standard_identity=self.standard_identity,
            symbol_set=symbol_set,
            status=self.sidc_status_for(viewer),
            entity=entity,
        )

    def sync_confirmed_status(self) -> None:
        for unit in self.units:
            unit.sync_confirmed_status()

    def threat_poly(self) -> ThreatPoly | None:
        if self._threat_poly is None:
            self._threat_poly = self._make_threat_poly()
        return self._threat_poly

    def invalidate_threat_poly(self) -> None:
        self._threat_poly = None

    def _make_threat_poly(self) -> ThreatPoly | None:
        threat_range = self.max_threat_range()
        if not threat_range:
            return None

        point = ShapelyPoint(self.position.x, self.position.y)
        return point.buffer(threat_range.meters)

    @property
    def is_ammo_depot(self) -> bool:
        return self.category == "ammo"

    @property
    def is_factory(self) -> bool:
        return self.category == "factory"

    @property
    def is_control_point(self) -> bool:
        """True if this TGO is the group for the control point itself (CVs and FOBs)."""
        return False

    @property
    def strike_targets(self) -> list[TheaterUnit]:
        return [unit for unit in self.units if unit.alive]

    @property
    def mark_locations(self) -> Iterator[Point]:
        yield self.position

    def clear(self) -> None:
        self.invalidate_threat_poly()
        self.groups = []

    @property
    def capturable(self) -> bool:
        raise NotImplementedError

    @property
    def purchasable(self) -> bool:
        raise NotImplementedError

    @property
    def value(self) -> int:
        """The value of all units of the Ground Objects"""
        return sum(u.unit_type.price for u in self.units if u.unit_type and u.alive)

    def group_by_name(self, name: str) -> Optional[TheaterGroup]:
        for group in self.groups:
            if group.name == name:
                return group
        return None

    def rotate(self, heading: Heading) -> None:
        """Rotate the whole TGO clockwise to the new heading"""
        rotation = heading - self.heading
        if rotation.degrees < 0:
            rotation = Heading.from_degrees(rotation.degrees + 360)

        self.heading = heading
        # Rotate the whole TGO to match the new heading
        for unit in self.units:
            unit.rotate_heading_clockwise(rotation)
            unit.rotate_position_clockwise(self.position, rotation)

    @property
    def should_head_to_conflict(self) -> bool:
        """Should this TGO head towards the closest conflict to work properly?"""
        return False

    @property
    def is_iads(self) -> bool:
        return False

    @property
    def coalition(self) -> Coalition:
        return self.control_point.coalition

    @property
    def is_naval_control_point(self) -> bool:
        return False


class BuildingGroundObject(TheaterGroundObject):
    def __init__(
        self,
        name: str,
        category: str,
        location: PresetLocation,
        control_point: ControlPoint,
        task: Optional[GroupTask],
        is_fob_structure: bool = False,
    ) -> None:
        super().__init__(
            name=name,
            category=category,
            location=location,
            control_point=control_point,
            sea_object=False,
            task=task,
        )
        self.is_fob_structure = is_fob_structure

    @property
    def symbol_set_and_entity(self) -> tuple[SymbolSet, Entity]:
        if self.category == "allycamp":
            entity = LandInstallationEntity.TENTED_CAMP
        elif self.category == "ammo":
            entity = LandInstallationEntity.AMMUNITION_CACHE
        elif self.category == "commandcenter":
            entity = LandInstallationEntity.MILITARY_INFRASTRUCTURE
        elif self.category == "comms":
            entity = LandInstallationEntity.TELECOMMUNICATIONS_TOWER
        elif self.category == "derrick":
            entity = LandInstallationEntity.PETROLEUM_FACILITY
        elif self.category == "factory":
            entity = LandInstallationEntity.MAINTENANCE_FACILITY
        elif self.category == "farp":
            entity = LandInstallationEntity.HELICOPTER_LANDING_SITE
        elif self.category == "fuel":
            entity = LandInstallationEntity.WAREHOUSE_STORAGE_FACILITY
        elif self.category == "oil":
            entity = LandInstallationEntity.PETROLEUM_FACILITY
        elif self.category == "power":
            entity = LandInstallationEntity.GENERATION_STATION
        elif self.category == "village":
            entity = LandInstallationEntity.PUBLIC_VENUES_INFRASTRUCTURE
        elif self.category == "ware":
            entity = LandInstallationEntity.WAREHOUSE_STORAGE_FACILITY
        elif self.category == "ww2bunker":
            entity = LandInstallationEntity.MILITARY_BASE
        else:
            raise ValueError(f"Unhandled building category: {self.category}")
        return SymbolSet.LAND_INSTALLATIONS, entity

    @property
    def mark_locations(self) -> Iterator[Point]:
        # Special handling to mark all buildings of the TGO
        for unit in self.strike_targets:
            yield unit.position

    @property
    def warrants_recon(self) -> bool:
        # Strategic infrastructure worth photographing: factories and command
        # posts by category, plus any scenery strike (bridges, dams, etc. — those
        # are modeled as SceneryUnit rather than a dedicated category).
        from .theatergroup import SceneryUnit

        if self.category in {"factory", "commandcenter"}:
            return True
        return any(isinstance(unit, SceneryUnit) for unit in self.units)

    @property
    def is_control_point(self) -> bool:
        return self.is_fob_structure

    @property
    def capturable(self) -> bool:
        return True

    @property
    def purchasable(self) -> bool:
        return False


class NavalGroundObject(TheaterGroundObject, ABC):
    def mission_types(self, for_player: Player) -> Iterator[FlightType]:
        from game.ato import FlightType

        if not self.is_friendly(for_player):
            yield from [
                FlightType.ANTISHIP,
                FlightType.SEAD,
            ]
        yield from super().mission_types(for_player)

    @property
    def capturable(self) -> bool:
        return False

    @property
    def purchasable(self) -> bool:
        return self.control_point.coalition.game.turn == 0

    @property
    def is_iads(self) -> bool:
        return True


class GenericCarrierGroundObject(NavalGroundObject, ABC):
    @property
    def is_control_point(self) -> bool:
        return True

    @property
    def is_naval_control_point(self) -> bool:
        return True


# TODO: Why is this both a CP and a TGO?
class CarrierGroundObject(GenericCarrierGroundObject):
    def __init__(
        self, name: str, location: PresetLocation, control_point: ControlPoint
    ) -> None:
        super().__init__(
            name=name,
            category="CARRIER",
            location=location,
            control_point=control_point,
            sea_object=True,
            task=GroupTask.AIRCRAFT_CARRIER,
        )

    @property
    def symbol_set_and_entity(self) -> tuple[SymbolSet, Entity]:
        return SymbolSet.SEA_SURFACE, SeaSurfaceEntity.CARRIER

    def __str__(self) -> str:
        return f"CV {self.name}"


# TODO: Why is this both a CP and a TGO?
class LhaGroundObject(GenericCarrierGroundObject):
    def __init__(
        self, name: str, location: PresetLocation, control_point: ControlPoint
    ) -> None:
        super().__init__(
            name=name,
            category="LHA",
            location=location,
            control_point=control_point,
            sea_object=True,
            task=GroupTask.HELICOPTER_CARRIER,
        )

    @property
    def symbol_set_and_entity(self) -> tuple[SymbolSet, Entity]:
        return SymbolSet.SEA_SURFACE, SeaSurfaceEntity.AMPHIBIOUS_ASSAULT_SHIP_GENERAL

    def __str__(self) -> str:
        return f"LHA {self.name}"


class MissileSiteGroundObject(TheaterGroundObject):
    def __init__(
        self, name: str, location: PresetLocation, control_point: ControlPoint
    ) -> None:
        super().__init__(
            name=name,
            category="missile",
            location=location,
            control_point=control_point,
            sea_object=False,
            task=GroupTask.MISSILE,
        )

    @property
    def symbol_set_and_entity(self) -> tuple[SymbolSet, Entity]:
        return SymbolSet.LAND_UNIT, LandUnitEntity.MISSILE

    @property
    def capturable(self) -> bool:
        return False

    @property
    def purchasable(self) -> bool:
        return self.control_point.coalition.game.turn == 0

    @property
    def should_head_to_conflict(self) -> bool:
        return True

    def mission_types(self, for_player: Player) -> Iterator[FlightType]:
        from game.ato import FlightType

        if not self.is_friendly(for_player):
            yield FlightType.BAI
        for mission_type in super().mission_types(for_player):
            yield mission_type


class CoastalSiteGroundObject(TheaterGroundObject):
    def __init__(
        self,
        name: str,
        location: PresetLocation,
        control_point: ControlPoint,
    ) -> None:
        super().__init__(
            name=name,
            category="coastal",
            location=location,
            control_point=control_point,
            sea_object=False,
            task=GroupTask.COASTAL,
        )

    @property
    def symbol_set_and_entity(self) -> tuple[SymbolSet, Entity]:
        return SymbolSet.LAND_UNIT, LandUnitEntity.MISSILE

    @property
    def capturable(self) -> bool:
        return False

    @property
    def purchasable(self) -> bool:
        return self.control_point.coalition.game.turn == 0

    @property
    def should_head_to_conflict(self) -> bool:
        return True

    def mission_types(self, for_player: Player) -> Iterator[FlightType]:
        from game.ato import FlightType

        if not self.is_friendly(for_player):
            yield FlightType.BAI
        for mission_type in super().mission_types(for_player):
            yield mission_type


class IadsGroundObject(TheaterGroundObject, ABC):
    def __init__(
        self,
        name: str,
        location: PresetLocation,
        control_point: ControlPoint,
        task: Optional[GroupTask],
        category: str = "aa",
    ) -> None:
        super().__init__(
            name=name,
            category=category,
            location=location,
            control_point=control_point,
            sea_object=False,
            task=task,
        )

    def mission_types(self, for_player: Player) -> Iterator[FlightType]:
        from game.ato import FlightType

        if not self.is_friendly(for_player):
            yield FlightType.DEAD
        yield from super().mission_types(for_player)

    @property
    def should_head_to_conflict(self) -> bool:
        return True

    @property
    def is_iads(self) -> bool:
        return True

    @property
    def warrants_recon(self) -> bool:
        # Air defenses (SAM/IADS/EWR) are prime BDA targets — overfly after the
        # DEAD strikers to confirm the kill.
        return True


# The SamGroundObject represents all type of AA
# The TGO can have multiple types of units (AAA,SAM,Support...)
# Differentiation can be made during generation with the airdefensegroupgenerator
class SamGroundObject(IadsGroundObject):
    def __init__(
        self,
        name: str,
        location: PresetLocation,
        control_point: ControlPoint,
        task: Optional[GroupTask],
    ) -> None:
        super().__init__(
            name=name,
            category="aa",
            location=location,
            control_point=control_point,
            task=task,
        )

    @property
    def sidc_status(self) -> Status:
        return self.sidc_status_for(None)

    def sidc_status_for(self, viewer: Optional[Player] = None) -> Status:
        if self.control_point.captured.is_neutral:
            return Status.PRESENT
        if self.is_dead(viewer):
            return Status.PRESENT_DESTROYED
        elif self.dead_units(viewer):
            if self.max_threat_range(viewer) > meters(0):
                return Status.PRESENT
            else:
                return Status.PRESENT_DAMAGED
        else:
            return Status.PRESENT_FULLY_CAPABLE

    @property
    def symbol_set_and_entity(self) -> tuple[SymbolSet, Entity]:
        return SymbolSet.LAND_UNIT, LandUnitEntity.AIR_DEFENSE

    def mission_types(self, for_player: Player) -> Iterator[FlightType]:
        from game.ato import FlightType

        if not self.is_friendly(for_player):
            yield FlightType.DEAD
            yield FlightType.SEAD
        for mission_type in super().mission_types(for_player):
            # We yielded this ourselves to move it to the top of the list. Don't yield
            # it twice.
            if mission_type is not FlightType.DEAD:
                yield mission_type

    @property
    def capturable(self) -> bool:
        return False

    @property
    def purchasable(self) -> bool:
        return True


class VehicleGroupGroundObject(TheaterGroundObject):
    def __init__(
        self,
        name: str,
        location: PresetLocation,
        control_point: ControlPoint,
        task: Optional[GroupTask],
    ) -> None:
        super().__init__(
            name=name,
            category="armor",
            location=location,
            control_point=control_point,
            sea_object=False,
            task=task,
        )

    @property
    def symbol_set_and_entity(self) -> tuple[SymbolSet, Entity]:
        return (
            SymbolSet.LAND_UNIT,
            LandUnitEntity.ARMOR_ARMORED_MECHANIZED_SELF_PROPELLED_TRACKED,
        )

    @property
    def capturable(self) -> bool:
        return False

    @property
    def purchasable(self) -> bool:
        return True

    @property
    def should_head_to_conflict(self) -> bool:
        return True

    def mission_types(self, for_player: Player) -> Iterator[FlightType]:
        from game.ato import FlightType

        if not self.is_friendly(for_player):
            yield FlightType.BAI
        yield from super().mission_types(for_player)


class DownedSofGroundObject(TheaterGroundObject):
    """A SOF team stranded by a botched SCAR capture, surfaced as a first-class
    recovery objective (SCAR Phase 2c-3).

    Created dynamically each turn from the owning coalition's
    ``pending_csars`` (not authored in the campaign .miz) and attached to a
    friendly control point's ``connected_objectives`` at the strand point. It is
    *our* team, so it is friendly to its owner and offers only a CSAR (helo
    extraction) mission to that side -- the enemy gets no tasking against it. The
    infantry group it carries is the physical team the recovery helo extracts.
    """

    def __init__(
        self,
        name: str,
        location: PresetLocation,
        control_point: ControlPoint,
    ) -> None:
        super().__init__(
            name=name,
            category="downed_team",
            location=location,
            control_point=control_point,
            sea_object=False,
            task=None,
        )

    @property
    def symbol_set_and_entity(self) -> tuple[SymbolSet, Entity]:
        return SymbolSet.LAND_UNIT, LandUnitEntity.UNSPECIFIED

    @property
    def capturable(self) -> bool:
        return False

    @property
    def purchasable(self) -> bool:
        return False

    def mission_types(self, for_player: Player) -> Iterator[FlightType]:
        from game.ato import FlightType

        # Only the owning side, and only with the SCAR commander-capture feature
        # on, can task a recovery. No enemy tasking and no other friendly missions
        # (this is a downed team, not a target). The settings lookup is defensive
        # because some lightweight contexts hold a control point without a
        # coalition.
        if self.is_friendly(for_player):
            try:
                settings = self.control_point.coalition.game.settings
            except (RuntimeError, AttributeError):
                settings = None
            if settings is not None and settings.scar_command_post_intel:
                yield FlightType.CSAR


class EwrGroundObject(IadsGroundObject):
    def __init__(
        self,
        name: str,
        location: PresetLocation,
        control_point: ControlPoint,
    ) -> None:
        super().__init__(
            name=name,
            location=location,
            control_point=control_point,
            category="ewr",
            task=GroupTask.EARLY_WARNING_RADAR,
        )

    @property
    def symbol_set_and_entity(self) -> tuple[SymbolSet, Entity]:
        return SymbolSet.LAND_EQUIPMENT, LandEquipmentEntity.RADAR

    @property
    def capturable(self) -> bool:
        return False

    @property
    def purchasable(self) -> bool:
        return True


class ShipGroundObject(NavalGroundObject):
    def __init__(
        self, name: str, location: PresetLocation, control_point: ControlPoint
    ) -> None:
        super().__init__(
            name=name,
            category="ship",
            location=location,
            control_point=control_point,
            sea_object=True,
            task=GroupTask.NAVY,
        )

    @property
    def symbol_set_and_entity(self) -> tuple[SymbolSet, Entity]:
        return SymbolSet.SEA_SURFACE, SeaSurfaceEntity.SURFACE_COMBATANT_LINE


class IadsBuildingGroundObject(BuildingGroundObject):
    def mission_types(self, for_player: Player) -> Iterator[FlightType]:
        from game.ato import FlightType

        if not self.is_friendly(for_player):
            yield from [FlightType.STRIKE, FlightType.DEAD]
        skippers = [FlightType.STRIKE]  # prevent yielding twice
        for mission_type in super().mission_types(for_player):
            if mission_type not in skippers:
                yield mission_type

    @property
    def is_iads(self) -> bool:
        return True
