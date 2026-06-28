"""Combo box for selecting a flight's task type."""

from typing import TYPE_CHECKING, Optional

from PySide6.QtWidgets import QComboBox

from game.ato.flighttype import FlightType
from game.settings.settings import Settings
from game.theater import ConflictTheater, MissionTarget
from game.theater.player import Player

if TYPE_CHECKING:
    from game.data.doctrine import Doctrine


class QFlightTypeComboBox(QComboBox):
    """Combo box for selecting a flight task type."""

    def __init__(
        self,
        theater: ConflictTheater,
        target: MissionTarget,
        settings: Settings,
        is_ownfor: bool,
        doctrine: Optional["Doctrine"] = None,
    ) -> None:
        super().__init__()
        self.theater = theater
        self.target = target
        for mission_type in self.target.mission_types(
            for_player=Player.BLUE if is_ownfor else Player.RED
        ):
            if mission_type == FlightType.AIR_ASSAULT and not settings.plugin_option(
                "ctld"
            ):
                # Only add Air Assault if ctld plugin is enabled
                continue
            # Display the doctrine's tasking label (the Vietnam rename); the userData
            # stays the canonical FlightType, so all selection logic is unaffected.
            label = (
                doctrine.display_name_for(mission_type)
                if doctrine is not None
                else str(mission_type)
            )
            self.addItem(label, userData=mission_type)
