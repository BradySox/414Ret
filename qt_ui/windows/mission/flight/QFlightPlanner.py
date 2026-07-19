from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import QTabWidget

from game.ato.flight import Flight
from game.missiongenerator.dtc import CARTRIDGE_BUILDERS
from qt_ui.models import PackageModel, GameModel
from qt_ui.windows.mission.flight.QFlightDtcTab import QFlightDtcTab
from qt_ui.windows.mission.flight.payload.QFlightPayloadTab import QFlightPayloadTab
from qt_ui.windows.mission.flight.settings.QGeneralFlightSettingsTab import (
    QGeneralFlightSettingsTab,
)
from qt_ui.windows.mission.flight.waypoints.QFlightWaypointTab import QFlightWaypointTab


class QFlightPlanner(QTabWidget):
    squadron_changed = Signal(Flight)

    def __init__(self, package_model: PackageModel, flight: Flight, gm: GameModel):
        super().__init__()

        self.payload_tab = QFlightPayloadTab(flight, gm.game)

        self.waypoint_tab = QFlightWaypointTab(gm.game, package_model.package, flight)
        self.waypoint_tab.loadout_changed.connect(self.payload_tab.reload_from_flight)

        self.general_settings_tab = QGeneralFlightSettingsTab(
            gm,
            package_model,
            flight,
            self.waypoint_tab.flight_waypoint_list,
            self.payload_tab,
        )
        self.general_settings_tab.flight_size_changed.connect(
            self.payload_tab.resize_for_flight
        )
        self.general_settings_tab.squadron_changed.connect(self.squadron_changed)
        self.addTab(self.general_settings_tab, "General Flight settings")
        self.addTab(self.payload_tab, "Payload")
        self.addTab(self.waypoint_tab, "Waypoints")
        # Native DTC cartridge controls (§74) -- only for airframes with DCS
        # DTC support, where the generator can actually build a cartridge.
        if flight.unit_type.dcs_unit_type.id in CARTRIDGE_BUILDERS:
            self.dtc_tab = QFlightDtcTab(flight, gm.game)
            self.addTab(self.dtc_tab, "DTC")
        self.setCurrentIndex(0)

    def sizeHint(self) -> QSize:
        """Size to the page on screen, not to the tallest page.

        QTabWidget's own hint expands over *every* page, so the dialog opened
        sized for its tallest hidden page: the General tab (~856 px) rendered in
        a window sized for the hidden Payload tab (~1080 px), leaving a ~260 px
        band of dead space under the form. Setting the hidden pages'
        size policy to Ignored does not help -- QTabWidget::sizeHint expands
        over the pages regardless of policy -- so substitute the current page's
        height, keeping the base width and the tab bar/frame chrome.

        Only the hint changes. Nothing forces a resize, so switching tabs leaves
        a window the user (or the screen-fit clamp) has already sized alone; a
        taller page simply uses the space it has.
        """
        base = super().sizeHint()
        current = self.currentWidget()
        if current is None or not self.count():
            return base
        tallest = max(self.widget(i).sizeHint().height() for i in range(self.count()))
        chrome = base.height() - tallest
        return QSize(base.width(), current.sizeHint().height() + chrome)
