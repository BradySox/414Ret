"""Edit Flight -> DTC tab: the planner's per-flight cartridge controls (§74).

Shown only for DTC-capable airframes (FA-18C, F-16C). Writes
``flight.dtc_options`` live -- the choices pickle with the save and the next
generation's ``DtcGenerator`` honors them. A section that is off is omitted
from the cartridge entirely, leaving the jet's own defaults untouched.
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QLabel,
    QVBoxLayout,
)

from game import Game
from game.ato.flight import Flight

#: (label, DtcOptions field, tooltip) for the section checkboxes.
_SECTIONS = (
    (
        "Comm presets (named channels)",
        "comms",
        "COMM1/COMM2 presets on the same channel numbers as the kneeboard "
        "comm plan, with short names (flight, AWACS, tankers, ATC).",
    ),
    (
        "Route steerpoints + push times",
        "route",
        "The flight's waypoints as named steerpoints with the planned "
        "per-leg speeds and ETAs.",
    ),
    (
        "Recovery aids (TACAN / ICLS / ACLS, home waypoint)",
        "nav_aids",
        "Pre-tunes the recovery TACAN -- the boat's full card on a carrier "
        "flight -- and sets the FPAS home waypoint. Hornet only; the Viper "
        "carries no equivalent cartridge section.",
    ),
    (
        "FLOT + no-strike zones",
        "flot_and_zones",
        "The front line and any ROE no-strike zones on the SA page (Hornet) "
        "or as HSD lines (Viper).",
    ),
    (
        "Friendly CAP + tanker/AWACS orbits",
        "friendly_orbits",
        "Friendly racetracks on the SA page; on the Viper these load as "
        "extra named steerpoints after the route.",
    ),
    (
        "Known enemy SAM rings",
        "threat_rings",
        "Threat rings for enemy air-defense sites your recon has confirmed "
        "(the campaign map's exact sites only -- suspected sites never leak).",
    ),
)


class QFlightDtcTab(QFrame):
    """Per-flight native-DTC cartridge controls."""

    def __init__(self, flight: Flight, game: Game) -> None:
        super().__init__()
        self.flight = flight
        self.game = game

        layout = QVBoxLayout()

        intro = QLabel(
            "This flight's native DCS data cartridge auto-loads at spawn: "
            "comms, route, recovery aids, and the SA picture, straight into "
            "the jet -- multiplayer clients get it with the mission download. "
            "Changes apply the next time the mission is generated."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.mode_selector = QComboBox()
        self.mode_selector.addItem(self._follow_label(), None)
        self.mode_selector.addItem("Always load for this flight", True)
        self.mode_selector.addItem("Never load for this flight", False)
        self.mode_selector.setCurrentIndex(
            {None: 0, True: 1, False: 2}[flight.dtc_options.enabled]
        )
        self.mode_selector.currentIndexChanged.connect(self.on_mode_changed)
        layout.addWidget(self.mode_selector)

        self.contents_group = QGroupBox("Cartridge contents")
        contents_layout = QVBoxLayout()
        self.section_boxes: list[tuple[QCheckBox, str]] = []
        for label, attr, tooltip in _SECTIONS:
            box = QCheckBox(label)
            box.setChecked(getattr(flight.dtc_options, attr))
            box.setToolTip(tooltip)
            box.toggled.connect(self._make_section_writer(attr))
            contents_layout.addWidget(box)
            self.section_boxes.append((box, attr))
        self.contents_group.setLayout(contents_layout)
        layout.addWidget(self.contents_group)

        layout.addStretch()
        self.setLayout(layout)
        self._update_enabled_state()

    def _follow_label(self) -> str:
        state = "on" if self.game.settings.dtc_data_cartridges else "off"
        return f"Follow the campaign setting (currently {state})"

    @property
    def _resolved_enabled(self) -> bool:
        return self.flight.dtc_options.resolve_enabled(
            self.game.settings.dtc_data_cartridges
        )

    def _update_enabled_state(self) -> None:
        self.contents_group.setEnabled(self._resolved_enabled)

    def on_mode_changed(self, index: int) -> None:
        self.flight.dtc_options.enabled = self.mode_selector.itemData(index)
        self._update_enabled_state()

    def _make_section_writer(self, attr: str):  # type: ignore[no-untyped-def]
        def write(checked: bool) -> None:
            setattr(self.flight.dtc_options, attr, checked)

        return write
