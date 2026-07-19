from collections.abc import Iterator
from dataclasses import dataclass
from shutil import copyfile
from typing import Dict, Union, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QPushButton,
    QInputDialog,
    QMessageBox,
    QWidget,
)
from game import Game
from game.ato.flight import Flight
from game.ato.flightmember import FlightMember
from game.data.weapons import Pylon
from game.fourteenth import loadout_defaults
from game.persistency import payloads_dir
from qt_ui.blocksignals import block_signals
from qt_ui.windows.mission.flight.payload.QPylonEditor import QPylonEditor


class QLoadoutEditor(QGroupBox):
    saved = Signal(str)

    def __init__(self, flight: Flight, flight_member: FlightMember, game: Game) -> None:
        super().__init__("Use custom loadout")
        self.flight = flight
        self.flight_member = flight_member
        self.game = game
        self.setCheckable(True)
        self.setChecked(flight_member.loadout.is_custom)

        vbox = QVBoxLayout(self)

        pylon_grid = QGridLayout()
        for i, pylon in enumerate(Pylon.iter_pylons(self.flight.unit_type)):
            label = QLabel(f"<b>{pylon.number}</b>")
            label.setSizePolicy(
                QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            )
            pylon_grid.addWidget(label, i, 0)
            pylon_grid.addWidget(QPylonEditor(game, flight, flight_member, pylon), i, 1)

        # The pylon list scrolls rather than shrinking its rows when the window
        # cannot be tall enough for every station. Without the scroll the list's
        # full height was also its *minimum*, so the screen-fit clamp (which
        # relaxes a minimum to get a window on screen) squeezed the rows until
        # their text clipped: 19 pylons on an F-15E ask for more height than a
        # 1440p panel at 150% scaling has.
        #
        # It still *shows* every station, because the payload tab gives this
        # widget its whole column to stretch into. That is load-bearing, and the
        # reason an earlier attempt at a scroll here was reverted for "opening
        # showing only a few rows": QScrollArea::sizeHint is hard-capped at 24
        # font-heights (~360 px), so a scroll can never ask for a tall list no
        # matter its size-adjust policy -- it can only grow into space something
        # else has claimed. AdjustToContents keeps the hint tracking the content
        # up to that cap; the column stretch does the rest.
        pylon_content = QWidget()
        pylon_content.setLayout(pylon_grid)
        pylon_scroll = QScrollArea()
        pylon_scroll.setWidget(pylon_content)
        pylon_scroll.setWidgetResizable(True)
        pylon_scroll.setFrameShape(QFrame.Shape.NoFrame)
        pylon_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        pylon_scroll.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents
        )
        vbox.addWidget(pylon_scroll, stretch=1)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Save Payload")
        save_btn.setProperty("style", "btn-danger")
        save_btn.setMaximumWidth(250)
        save_btn.clicked.connect(self._save_payload)
        buttons.addWidget(save_btn)

        purge_btn = QPushButton("Create Backup")
        purge_btn.setProperty("style", "btn-success")
        purge_btn.setMaximumWidth(250)
        purge_btn.clicked.connect(self._backup_payloads)
        buttons.addWidget(purge_btn)
        vbox.addLayout(buttons)

        # 414th (§73): make this loadout the one every future flight of this
        # airframe+task is planned with, by writing it into the payload name the
        # planner resolves. Mirrors the "Save as default" pair on the aircraft
        # settings box, which covers fuel + cockpit properties.
        vbox.addLayout(self._build_default_loadout_row())

        self.setLayout(vbox)

        for pylon_editor in self.iter_pylon_editors():
            pylon_editor.set_from(self.flight_member.loadout)

    def iter_pylon_editors(self) -> Iterator[QPylonEditor]:
        yield from self.findChildren(QPylonEditor)

    def set_flight_member(self, flight_member: FlightMember) -> None:
        self.flight_member = flight_member
        with block_signals(self):
            self.setChecked(self.flight_member.use_custom_loadout)
        for pylon_editor in self.iter_pylon_editors():
            pylon_editor.set_flight_member(flight_member)

    def _build_default_loadout_row(self) -> QHBoxLayout:
        task = self.flight.flight_type
        aircraft = self.flight.unit_type

        row = QHBoxLayout()
        row.addWidget(QLabel(f"Default {task.value} loadout:"))
        row.addStretch(1)

        self.set_default_btn = QPushButton(f"Set as default for {task.value}")
        self.set_default_btn.setToolTip(
            f"Plan every future {aircraft.display_name} {task.value} flight with "
            f"this loadout, by saving it as the payload the planner resolves for "
            f"that task. Applies to both coalitions and every campaign."
        )
        self.set_default_btn.clicked.connect(self._on_set_default_loadout)
        row.addWidget(self.set_default_btn)

        self.clear_default_btn = QPushButton("Clear default")
        self.clear_default_btn.setToolTip(
            f"Drop your saved {task.value} loadout for the "
            f"{aircraft.display_name} and go back to Retribution's built-in fit."
        )
        self.clear_default_btn.clicked.connect(self._on_clear_default_loadout)
        self.clear_default_btn.setEnabled(self._has_default_loadout_override())
        row.addWidget(self.clear_default_btn)
        return row

    def _default_loadout_name(self) -> str:
        return loadout_defaults.override_name_for(
            self.flight.flight_type, self.flight.unit_type.dcs_unit_type
        )

    def _has_default_loadout_override(self) -> bool:
        return loadout_defaults.has_override_for(
            self.flight.unit_type.dcs_unit_type, self._default_loadout_name()
        )

    def _on_set_default_loadout(self) -> None:
        task = self.flight.flight_type
        aircraft = self.flight.unit_type
        name = self._default_loadout_name()
        if (
            QMessageBox.question(
                self,
                f"Set the default {task.value} loadout?",
                f"Every {aircraft.display_name} planned as {task.value} will be "
                f"given this loadout from now on.\n\n"
                f'It is saved to your DCS user payloads as "{name}", which takes '
                f"precedence over Retribution's built-in fit. So it applies:\n\n"
                f"• to both coalitions — enemy {aircraft.display_name} "
                f"{task.value} flights get it too\n"
                f"• in every campaign, until you clear it\n"
                f"• to newly planned flights only — flights already in "
                f"the ATO keep the loadout they have",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        if not self._write_payload(name):
            return
        self.clear_default_btn.setEnabled(True)
        QMessageBox.information(
            self,
            "Default loadout set",
            f"New {aircraft.display_name} {task.value} flights will now be planned "
            f'with this loadout (saved as "{name}").',
        )

    def _on_clear_default_loadout(self) -> None:
        task = self.flight.flight_type
        aircraft = self.flight.unit_type
        name = self._default_loadout_name()
        if (
            QMessageBox.question(
                self,
                f"Clear the default {task.value} loadout?",
                f'This removes your saved "{name}" payload for the '
                f"{aircraft.display_name}. New {task.value} flights will go back to "
                f"Retribution's built-in fit.\n\n"
                f"A backup of the payload file is kept in "
                f'"{payloads_dir(backup=True)}".',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        removed = loadout_defaults.remove_payload_entry(
            self.flight.unit_type.dcs_unit_type, name
        )
        self.clear_default_btn.setEnabled(self._has_default_loadout_override())
        QMessageBox.information(
            self,
            "Default loadout cleared" if removed else "No saved default",
            (
                (
                    f"New {aircraft.display_name} {task.value} flights will use "
                    f"Retribution's built-in loadout again."
                )
                if removed
                else (
                    f'No saved "{name}" payload was found for the '
                    f"{aircraft.display_name}; nothing was changed."
                )
            ),
        )

    def _backup_payloads(self) -> None:
        ac_id = self.flight.unit_type.dcs_unit_type.id
        payload_file = payloads_dir() / f"{ac_id}.lua"
        if not payload_file.exists():
            return
        backup_folder = payloads_dir(backup=True)
        backup_file = backup_folder / f"{ac_id}.lua"
        copyfile(payload_file, backup_file)
        QMessageBox.information(
            self,
            "Backup Payload",
            f"Payload file for {ac_id} was backed up successfully.\n"
            f"Location: {backup_file}",
        )

    def _write_payload(self, payload_name: str) -> bool:
        """Persist the current loadout under ``payload_name``. False if it wasn't."""
        ac_type = self.flight.unit_type.dcs_unit_type
        payload = DcsPayload.from_flight_member(
            self.flight_member, payload_name
        ).to_dict()
        if not loadout_defaults.write_payload_entry(ac_type, payload_name, payload):
            QMessageBox.warning(
                self,
                "Payload not saved",
                f"The existing payload file for {ac_type.id} could not be read, so "
                f"it was left untouched rather than risk losing the payloads "
                f"already saved in it.\n\n"
                f"Location: {loadout_defaults.user_payload_file(ac_type.id)}",
            )
            return False
        self.saved.emit(payload_name)
        return True

    def _save_payload(self) -> None:
        payload_name_input = self._create_input_dialog()
        if not payload_name_input.exec_():
            return
        payload_name = payload_name_input.textValue()
        ac_type = self.flight.unit_type.dcs_unit_type
        if not self._write_payload(payload_name):
            return
        self.clear_default_btn.setEnabled(self._has_default_loadout_override())
        QMessageBox.information(
            self,
            "Payload Saved",
            f"Payload for {ac_type.id} was successfully saved.\n"
            f"Location: {loadout_defaults.user_payload_file(ac_type.id)}",
        )

    def _create_input_dialog(self):
        payload_name_input = QInputDialog()
        payload_name_input.setWindowTitle("Save payload")
        payload_name_input.setLabelText("Enter a name for the payload to be saved:")
        payload_name_input.setTextValue(f"Custom {self.flight.flight_type.name}")
        payload_name_input.setFixedWidth(500)
        return payload_name_input

    def reset_pylons(self) -> None:
        self.flight_member.use_custom_loadout = self.isChecked()
        if not self.isChecked():
            for pylon_editor in self.iter_pylon_editors():
                pylon_editor.set_from(self.flight_member.loadout)


@dataclass
class DcsPayload:
    displayName: str
    name: str
    pylons: Dict[int, Dict[str, Union[str, int, Dict[str, Any]]]]
    tasks: Dict[int, int]

    @classmethod
    def from_flight_member(cls, member: FlightMember, payload_name: str):
        pylons = {}
        for i, nr in enumerate(member.loadout.pylons, 1):
            wpn = member.loadout.pylons[nr]
            clsid = wpn.clsid if wpn else "<CLEAN>"
            pylon_dict: Dict[str, Union[str, int, Dict[str, Any]]] = {
                "CLSID": clsid,
                "num": nr,
            }

            # Add weapon settings if present
            if nr in member.loadout.pylon_settings:
                settings = member.loadout.pylon_settings[nr]
                if settings:  # Only add if settings dict is non-empty
                    pylon_dict["settings"] = settings

            pylons[i] = pylon_dict

        return DcsPayload(
            f"{payload_name}",
            f"{payload_name}",
            pylons=pylons,
            tasks={1: 31},
        )

    def to_dict(self):
        return {
            "displayName": self.displayName,
            "name": self.name,
            "pylons": self.pylons,
            "tasks": self.tasks,
        }
