"""SP Pilot Mode -- the pre-turn card and the aircraft-first sortie board.

Opened straight after the player accepts mission results, so the single-player
loop goes debrief -> next briefing without a detour through the map and the
ATO. The dialog is a thin shell over two pure-Python cores that carry all the
logic and all the tests:

* ``game.fourteenth.pre_turn_briefing`` -- why this turn matters, from state the
  campaign already computed (evaders and their capture odds, enemy command
  damage the player caused, victory progress, scheduled arrivals, open loops).
* ``game.fourteenth.sp_pilot_mode`` -- step 1 the airframe, step 2 the sortie.

Nothing here decides anything: the widgets read the cores and call ``take_seat``.
Closing the dialog at any point leaves the turn exactly as ``pass_turn`` left it,
so the player can always fall back to the normal map/ATO planning path.
"""

from __future__ import annotations

import logging
from typing import Callable, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from game import Game
from game.fourteenth.pre_turn_briefing import URGENT, build_pre_turn_briefing
from game.fourteenth.sp_pilot_mode import (
    AirframeOption,
    SortieOption,
    airframe_options,
    sortie_options,
    take_seat,
)


class QSpPilotModeDialog(QDialog):
    """Pick tonight's jet, then tonight's sortie."""

    def __init__(
        self,
        game: Game,
        parent: Optional[QDialog] = None,
        launch: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.game = game
        self._launch = launch
        self._seated = False
        self._airframes: List[AirframeOption] = []
        self._sorties: List[SortieOption] = []

        self.setWindowTitle(f"Fly turn {game.turn}")
        self.setMinimumWidth(720)

        layout = QVBoxLayout()
        layout.addWidget(self._build_briefing())
        layout.addWidget(self._build_board())
        layout.addLayout(self._build_buttons())
        self.setLayout(layout)

        self._load_airframes()

    # ------------------------------------------------------------- briefing

    def _build_briefing(self) -> QFrame:
        """The reasons to fly, shown BEFORE the commitment -- the whole point."""
        frame = QFrame()
        box = QVBoxLayout()

        heading = QLabel(f"<b>Turn {self.game.turn} — why it matters</b>")
        box.addWidget(heading)

        try:
            briefing = build_pre_turn_briefing(self.game)
        except Exception:
            logging.exception("SP Pilot Mode: could not build the pre-turn briefing")
            briefing = None

        if briefing is None or briefing.is_empty:
            quiet = QLabel("A quiet turn — nothing outstanding. Pick a jet and fly.")
            quiet.setWordWrap(True)
            box.addWidget(quiet)
        else:
            for item in briefing.ordered():
                label = QLabel(("• " if item.urgency < URGENT else "‼ ") + item.text)
                label.setWordWrap(True)
                if item.urgency >= URGENT:
                    label.setProperty("style", "warning")
                box.addWidget(label)

        frame.setLayout(box)
        return frame

    # ---------------------------------------------------------------- board

    def _build_board(self) -> QFrame:
        frame = QFrame()
        columns = QHBoxLayout()

        left = QVBoxLayout()
        left.addWidget(QLabel("<b>1. What do you want to fly?</b>"))
        self.airframe_list = QListWidget()
        self.airframe_list.currentRowChanged.connect(self._on_airframe_changed)
        left.addWidget(self.airframe_list)
        columns.addLayout(left)

        right = QVBoxLayout()
        right.addWidget(QLabel("<b>2. Which sortie?</b>"))
        self.sortie_list = QListWidget()
        self.sortie_list.currentRowChanged.connect(self._on_sortie_changed)
        right.addWidget(self.sortie_list)
        self.sortie_hint = QLabel("")
        self.sortie_hint.setWordWrap(True)
        right.addWidget(self.sortie_hint)
        columns.addLayout(right)

        frame.setLayout(columns)
        return frame

    def _load_airframes(self) -> None:
        try:
            self._airframes = airframe_options(self.game)
        except Exception:
            logging.exception("SP Pilot Mode: could not list airframes")
            self._airframes = []

        self.airframe_list.clear()
        for option in self._airframes:
            bases = ", ".join(option.bases) or "no base"
            text = f"{option.name} — {option.ready_airframes} ready · {bases}"
            entry = QListWidgetItem(text)
            if not option.has_spare_airframes:
                entry.setForeground(Qt.GlobalColor.gray)
            self.airframe_list.addItem(entry)
        if self._airframes:
            self.airframe_list.setCurrentRow(0)

    def _on_airframe_changed(self, row: int) -> None:
        self.sortie_list.clear()
        self._sorties = []
        if row < 0 or row >= len(self._airframes):
            self._update_buttons()
            return

        try:
            self._sorties = sortie_options(self.game, self._airframes[row].aircraft)
        except Exception:
            logging.exception("SP Pilot Mode: could not list sorties")
            self._sorties = []

        for option in self._sorties:
            self.sortie_list.addItem(QListWidgetItem(option.description))
        if self._sorties:
            self.sortie_list.setCurrentRow(0)
        else:
            self.sortie_hint.setText(
                "No sortie in this type this turn — the commander did not frag one "
                "and there is no package it could join. Pick another jet, or close "
                "and plan it yourself on the map."
            )
        self._update_buttons()

    def _on_sortie_changed(self, row: int) -> None:
        if 0 <= row < len(self._sorties):
            option = self._sorties[row]
            summary = option.package_summary or "standalone"
            joining = (
                "You are adding a flight to a package that is already going."
                if option.rung == 2
                else "You are taking a seat in a flight the commander planned."
            )
            self.sortie_hint.setText(f"{summary}. {joining}")
        self._update_buttons()

    # -------------------------------------------------------------- buttons

    def _build_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.fly = QPushButton("Take this sortie")
        self.fly.setProperty("style", "btn-primary")
        self.fly.clicked.connect(self._take_sortie)
        row.addWidget(self.fly)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.buttons.rejected.connect(self.reject)
        row.addWidget(self.buttons)
        return row

    def _update_buttons(self) -> None:
        selected = self.sortie_list.currentRow()
        self.fly.setEnabled(0 <= selected < len(self._sorties) and not self._seated)

    @property
    def seated(self) -> bool:
        """Whether the player took a seat (the caller may then launch)."""
        return self._seated

    def _take_sortie(self) -> None:
        row = self.sortie_list.currentRow()
        if not (0 <= row < len(self._sorties)):
            return
        option = self._sorties[row]

        if option.rung != 1:
            # Joining a package builds a new flight, which is the ATO's own
            # add-flight path rather than anything this dialog should invent.
            # Until that is wired, say so plainly instead of failing silently.
            self.sortie_hint.setText(
                "Joining an existing package is not wired up yet — pick a sortie "
                "the commander already planned, or close and add the flight from "
                "the package on the map."
            )
            return

        seated = take_seat(self.game, option)
        if seated is None:
            self.sortie_hint.setText(
                "No player pilot free in that squadron — pick another sortie, or "
                "free a pilot in the Air Wing dialog."
            )
            return

        self._seated = True
        self._update_buttons()
        if self._launch is not None:
            self.accept()
            self._launch()
        else:
            self.sortie_hint.setText(
                f"You are flying {option.description}. Close this and press "
                f"Take off."
            )
