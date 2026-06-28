from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtWidgets import QComboBox

from game.ato import FlightType
from game.dcs.aircrafttype import AircraftType
from game.squadrons import Squadron

if TYPE_CHECKING:
    from game.data.doctrine import Doctrine


class PrimaryTaskSelector(QComboBox):
    def __init__(
        self, aircraft: AircraftType | None, doctrine: Optional["Doctrine"] = None
    ) -> None:
        super().__init__()
        self._doctrine = doctrine
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.set_aircraft(aircraft)

    def label_for(self, task: FlightType) -> str:
        """The doctrine display label for a task (the Vietnam rename), else the
        canonical ``FlightType.value``. The item *data* stays the FlightType."""
        if self._doctrine is not None:
            return self._doctrine.display_name_for(task)
        return task.value

    @staticmethod
    def for_squadron(squadron: Squadron) -> PrimaryTaskSelector:
        selector = PrimaryTaskSelector(squadron.aircraft, squadron.coalition.doctrine)
        selector.setCurrentText(selector.label_for(squadron.primary_task))
        return selector

    def set_aircraft(self, aircraft: AircraftType | None) -> None:
        self.clear()
        if aircraft is None:
            self.addItem("Select aircraft type first", None)
            self.setEnabled(False)
            self.update()
            return

        self.setEnabled(True)
        for task in aircraft.iter_task_capabilities():
            self.addItem(self.label_for(task), task)
        self.model().sort(0)
        self.setEnabled(True)
        self.update()

    @property
    def selected_task(self) -> FlightType | None:
        return self.currentData()
