"""Dynamic spawn templates (§101): a dynamic-slot jet inherits a player flight.

DCS builds a dynamic spawn of a type at a base from the group its warehouse
entry links to (``linkDynTempl``), if that group is flagged ``dynSpawnTemplate``.
This pass flags one player flight per base and aircraft type and writes the link,
so a pilot who takes a dynamic slot instead of a fragged one gets that flight's
route, comm card, loadout and properties instead of a blank jet.
See docs/dev/design/414th-dynamic-spawn-templates-notes.md.

The template group stays in the slot list (DM, in the editor, 2026-09-15), so
the real flight is marked and nothing is cloned. Only client flights qualify:
the editor clears the flag on an AI group, so an AI donor is untested. The
warehouse entry carries no ``wsType``; whether DCS needs one is row B125.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from dcs.mission import Mission
from dcs.terrain.terrain import Airport
from dcs.unitgroup import FlyingGroup

from game.ato.starttype import StartType

if TYPE_CHECKING:
    from game import Game
    from game.ato.flight import Flight

#: The mission editor's own per-type defaults (``Config/AirportsEquipment.lua``,
#: ``AEDefault.LA``); the airport-level ``unlimitedAircrafts`` stays in charge.
TEMPLATE_ENTRY_INITIAL_AMOUNT = 100

#: Ship and heliport warehouses the generator already emitted, keyed by the
#: control point they belong to. An airfield's link goes on its pydcs Airport.
WarehousesByControlPoint = dict[UUID, list[dict[str, Any]]]


def template_entry(group_id: int) -> dict[str, Any]:
    """The warehouse ``aircrafts.<category>.<type>`` entry that links a template."""
    return {
        "initialAmount": TEMPLATE_ENTRY_INITIAL_AMOUNT,
        "unlimited": False,
        "linkDynTempl": group_id,
    }


class DynamicSpawnTemplateGenerator:
    """Marks one client flight per base and type as that base's dynamic spawn
    template, and writes the airbase link that points at it."""

    def __init__(
        self,
        mission: Mission,
        game: Game,
        warehouses_by_control_point: WarehousesByControlPoint,
    ) -> None:
        self.mission = mission
        self.game = game
        self.warehouses_by_control_point = warehouses_by_control_point
        #: (control point id, DCS type id) -> the template group's id.
        self.links: dict[tuple[UUID, str], int] = {}

    def generate(self) -> None:
        settings = self.game.settings
        if not (settings.dynamic_slots and settings.dynamic_slots_templates):
            return
        for (cp_id, type_id), flight in self._donors().items():
            group = self.mission.find_group_by_id(flight.group_id)
            if not isinstance(group, FlyingGroup):
                logging.warning(
                    "Dynamic spawn template: no group %d for %s at %s",
                    flight.group_id,
                    type_id,
                    flight.departure,
                )
                continue
            targets = self._link_targets(flight)
            if not targets:
                continue
            group.dyn_spawn_template = True
            category = "helicopters" if flight.unit_type.helicopter else "planes"
            for aircrafts in targets:
                aircrafts.setdefault(category, {})[type_id] = template_entry(group.id)
            self.links[(cp_id, type_id)] = group.id

    def _donors(self) -> dict[tuple[UUID, str], Flight]:
        """One client flight per (base, type). A ground start beats an air start
        (the editor's own template picker comments out a parking-only filter, so
        an airborne template is the untested case); otherwise ATO order wins."""
        donors: dict[tuple[UUID, str], Flight] = {}
        for coalition in (self.game.blue, self.game.red):
            for package in coalition.ato.packages:
                for flight in package.flights:
                    if flight.client_count == 0 or flight.group_id == 0:
                        continue
                    key = (flight.departure.id, flight.unit_type.dcs_unit_type.id)
                    current = donors.get(key)
                    if current is None or (
                        current.start_type is StartType.IN_FLIGHT
                        and flight.start_type is not StartType.IN_FLIGHT
                    ):
                        donors[key] = flight
        return donors

    def _link_targets(self, flight: Flight) -> list[dict[str, Any]]:
        """The ``aircrafts`` tables the link is written into: the departure
        airfield's own, or every ship/heliport warehouse of the control point."""
        cp = flight.departure
        airport: Optional[Airport] = getattr(cp, "airport", None)
        if isinstance(airport, Airport):
            mission_airport = self.mission.terrain.airport_by_id(airport.id)
            if mission_airport is None:
                return []
            return [mission_airport.aircrafts]
        return [
            warehouse.setdefault("aircrafts", {})
            for warehouse in self.warehouses_by_control_point.get(cp.id, [])
        ]
