"""Manage player-imported custom kneeboard pages for the campaign.

Lets the campaign owner add an image once and have it injected into every client
flight's kneeboard at mission generation — optionally scoped to a single airframe —
instead of hand-editing each flight's mission. The images are stored in the campaign
save (`game.custom_kneeboards`); injection happens in `KneeboardGenerator.generate`.
"""

from __future__ import annotations

import io

from PIL import Image
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

import qt_ui.uiconstants as CONST
from game.customkneeboard import CustomKneeboard
from game.dcs.aircrafttype import AircraftType
from game.game import Game

#: File types the import picker accepts.
_IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
#: Combo label for the "applies to every flight" scope.
_ALL_FLIGHTS = "All flights"


class QCustomKneeboardsWindow(QDialog):
    def __init__(self, game: Game):
        super().__init__()
        self.game = game
        # Lazily migrate a pre-feature save the moment it is edited.
        if not hasattr(self.game, "custom_kneeboards"):
            self.game.custom_kneeboards = []

        self.setWindowTitle("Custom Kneeboards")
        self.setWindowIcon(CONST.ICONS["Notes"])
        self.setMinimumSize(480, 320)

        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(
            QLabel(
                "Imported images are added to every client flight's kneeboard at "
                "mission generation (or scoped to one airframe). Stored in the "
                "campaign save."
            )
        )

        self.list_widget = QListWidget(self)
        layout.addWidget(self.list_widget)

        button_row = QHBoxLayout()
        layout.addLayout(button_row)

        self.add_button = QPushButton("ADD…", self)
        self.add_button.setProperty("style", "btn-success")
        self.add_button.clicked.connect(self.add_kneeboard)
        button_row.addWidget(self.add_button)

        self.remove_button = QPushButton("REMOVE", self)
        self.remove_button.setProperty("style", "btn-danger")
        self.remove_button.clicked.connect(self.remove_selected)
        button_row.addWidget(self.remove_button)

        self.close_button = QPushButton("CLOSE", self)
        self.close_button.setProperty("style", "btn-primary")
        self.close_button.clicked.connect(self.accept)
        button_row.addWidget(self.close_button)

        self.refresh_list()

    def refresh_list(self) -> None:
        self.list_widget.clear()
        for kneeboard in self.game.custom_kneeboards:
            self.list_widget.addItem(f"{kneeboard.name}  —  {kneeboard.scope_label}")

    def _airframe_choices(self) -> dict[str, str | None]:
        """Map scope label -> airframe id (None = all flights), sorted by name."""
        choices: dict[str, str | None] = {_ALL_FLIGHTS: None}
        airframes: set[AircraftType] = set(self.game.blue.air_wing.squadrons.keys())
        for aircraft in sorted(airframes, key=str):
            choices[str(aircraft)] = aircraft.dcs_unit_type.id
        return choices

    def add_kneeboard(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select kneeboard image", "", _IMAGE_FILTER
        )
        if not path:
            return

        # Normalise to PNG bytes so the generator can always write a .png, and so
        # the bytes are self-contained in the save (no path dependency).
        try:
            with Image.open(path) as image:
                buffer = io.BytesIO()
                image.convert("RGB").save(buffer, format="PNG")
                data = buffer.getvalue()
        except (OSError, ValueError) as exc:
            QMessageBox.warning(
                self, "Could not load image", f"Failed to read the image:\n{exc}"
            )
            return

        choices = self._airframe_choices()
        label, ok = QInputDialog.getItem(
            self,
            "Apply to",
            "Add this kneeboard to:",
            list(choices.keys()),
            0,
            False,
        )
        if not ok:
            return

        name = path.replace("\\", "/").rsplit("/", 1)[-1]
        self.game.custom_kneeboards.append(
            CustomKneeboard(name=name, image=data, airframe_id=choices[label])
        )
        self.refresh_list()

    def remove_selected(self) -> None:
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.game.custom_kneeboards):
            del self.game.custom_kneeboards[row]
            self.refresh_list()
