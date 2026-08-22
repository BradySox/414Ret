"""Edit Flight -> DTC tab: the planner's per-flight cartridge controls (§74).

Shown only for DTC-capable airframes (FA-18C, F-16C, F-14B(U)). Writes
``flight.dtc_options`` live -- the choices pickle with the save and the next
generation's ``DtcGenerator`` honors them. A section that is off leaves the
jet's own defaults untouched: omitted from the Hornet and Viper cartridges,
written as the editor's reset state on the Tomcat, whose descriptor cannot
take a partial cartridge.
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
        "comm plan, with short names (flight, AWACS, tankers, ATC). Hornet "
        "only -- the Viper's presets come from the mission itself. On the "
        "F-14B(U) this switch carries the TIS send-to list instead.",
    ),
    (
        "Route steerpoints + push times",
        "route",
        "The flight's waypoints as named steerpoints with the planned "
        "per-leg speeds and ETAs. On the F-14B(U) the route goes on flight "
        "plan 2 -- plan 1 is the mission editor's own -- and the bullseye and "
        "divert become reference points.",
    ),
    (
        "Recovery aids (TACAN / ICLS / ACLS, home waypoint)",
        "nav_aids",
        "Pre-tunes the recovery TACAN -- the boat's full card on a carrier "
        "flight -- sets the FPAS home waypoint, and designates the bullseye as "
        "the air-to-air waypoint. Hornet only; the Viper carries no equivalent "
        "cartridge section.",
    ),
    (
        "Front line (FLOT)",
        "flot_and_zones",
        "The front line on the SA page (Hornet), as HSD lines (Viper) or as "
        "a plot line (F-14B(U)).",
    ),
    (
        "Own orbit + tanker/AWACS orbits",
        "friendly_orbits",
        "This flight's own orbit first -- its patrol track, or its hold point "
        "when it flies no track -- then the tanker and AWACS orbits. Never "
        "another flight's CAP station. Racetracks on the Hornet's SA page, "
        "extra named steerpoints after the route on the Viper, reference "
        "points on the F-14B(U).",
    ),
    (
        "Known enemy SAM rings",
        "threat_rings",
        "Threat rings for enemy air-defense sites your recon has confirmed "
        "(the campaign map's exact sites only -- suspected sites never leak). "
        "Rings on the Hornet and Viper; named reference points on the "
        "F-14B(U).",
    ),
    (
        "Pre-planned target points",
        "jdam_targets",
        "The flight's targets as pre-planned aimpoints on every weapon "
        "station, with the run-in heading and release parameters. F-14B(U) "
        "only; the other jets carry no equivalent cartridge section.",
    ),
    (
        "Recovery fields + the target airfield",
        "destinations",
        "Friendly airfields and boats as Destination steerpoints, the briefed "
        "divert first and the enemy field you are working over right after "
        "it. Viper only; the other jets carry no equivalent section.",
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
            "comms, route, recovery aids, the SA picture and, on the F-14B(U), "
            "pre-planned JDAM points -- straight into the jet, and multiplayer "
            "clients get it with the mission download. Radio presets and the "
            "route reach the jet through the mission anyway; the cartridge adds "
            "the rest. Changes apply the next time the mission is generated."
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
