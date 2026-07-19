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
from dcs import lua

from game import Game
from game.ato.flight import Flight
from game.ato.flightmember import FlightMember
from game.data.weapons import Pylon
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

    def _backup_payloads(self) -> None:
        ac_id = self.flight.unit_type.dcs_unit_type.id
        payload_file = payloads_dir() / f"{ac_id}.lua"
        if not payload_file.exists():
            return
        backup_folder = payloads_dir(backup=True)
        backup_file = backup_folder / f"{ac_id}.lua"
        copyfile(payload_file, backup_file)
        QMessageBox.information(
            QWidget(),
            "Backup Payload",
            f"Payload file for {self.flight.unit_type.dcs_unit_type.id} was backed up successfully.\n"
            f"Location: {backup_file}",
        )

    def _save_payload(self) -> None:
        payload_name_input = self._create_input_dialog()
        if not payload_name_input.exec_():
            return
        payload_name = payload_name_input.textValue()
        ac_type = self.flight.unit_type.dcs_unit_type
        ac_id = ac_type.id
        payloads_folder = payloads_dir()
        payload_file = payloads_folder / f"{ac_id}.lua"
        ac_type.payloads[payload_name] = DcsPayload.from_flight_member(
            self.flight_member, payload_name
        ).to_dict()
        if payload_file.exists():
            self._create_backup_if_needed(ac_id)
            with payload_file.open("r", encoding="utf-8") as f:
                payloads = lua.loads(f.read())
            if payloads:
                pdict = payloads["unitPayloads"]["payloads"]
                next_key = len(pdict) + 1
                for p in pdict:
                    if pdict[p]["name"] == payload_name:
                        next_key = p
                pdict[next_key] = DcsPayload.from_flight_member(
                    self.flight_member, payload_name
                ).to_dict()
                with payload_file.open("w", encoding="utf-8") as f:
                    f.write("local unitPayloads = ")
                    f.write(lua.dumps(payloads["unitPayloads"], indent=1))
                    f.write("\nreturn unitPayloads")
        else:
            with payload_file.open("w", encoding="utf-8") as f:
                payloads = {
                    "name": f"{self.flight.unit_type.dcs_unit_type.id}",
                    "payloads": {
                        1: DcsPayload.from_flight_member(
                            self.flight_member, payload_name
                        ).to_dict(),
                    },
                    "unitType": f"{self.flight.unit_type.dcs_unit_type.id}",
                }
                f.write("local unitPayloads = ")
                f.write(lua.dumps(payloads, indent=1))
                f.write("\nreturn unitPayloads")
            self.flight.unit_type.dcs_unit_type.add_to_payload_cache(payload_file)
        self.saved.emit(payload_name)
        QMessageBox.information(
            QWidget(),
            "Payload Saved",
            f"Payload for {self.flight.unit_type.dcs_unit_type.id} was successfully saved.\n"
            f"Location: {payload_file}",
        )

    def _create_backup_if_needed(self, ac_id):
        backup_file = payloads_dir(backup=True) / f"{ac_id}.lua"
        if not backup_file.exists():
            self._backup_payloads()

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
