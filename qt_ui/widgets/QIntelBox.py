from typing import Optional

from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
)

from game import Game
from game.income import Income
from game.theater import Player
from qt_ui.windows.intel import IntelWindow


class QIntelBox(QGroupBox):
    def __init__(self, game: Game) -> None:
        super().__init__("Intel")
        self.setProperty("style", "IntelSummary")

        self.game = game

        columns = QHBoxLayout()
        self.setLayout(columns)

        summary = QGridLayout()
        summary.setContentsMargins(5, 5, 5, 5)
        # A gutter column separating the two label/value column groups below.
        summary.setColumnMinimumWidth(2, 12)

        # Left column group: the force & economy balance (upstream rows).
        air_superiority = QLabel("Air superiority:")
        summary.addWidget(air_superiority, 0, 0)
        self.air_strength = QLabel()
        summary.addWidget(self.air_strength, 0, 1)

        front_line = QLabel("Front line:")
        summary.addWidget(front_line, 1, 0)
        self.ground_strength = QLabel()
        summary.addWidget(self.ground_strength, 1, 1)

        economy = QLabel("Economic strength:")
        summary.addWidget(economy, 2, 0)
        self.economic_strength = QLabel()
        summary.addWidget(self.economic_strength, 2, 1)

        # Right column group: campaign phase (§40) + political will (Vietnam /
        # COIN campaign layer). Placed *beside* the force rows, not stacked
        # beneath them, so the box stays three rows tall and fits the 70px
        # top-panel cap even when both are active -- five stacked rows overflowed
        # the cap and painted over each other. Each row still hides entirely
        # when its feature is off, so a stock campaign's box is unchanged.
        self._will_title = QLabel("Political will:")
        summary.addWidget(self._will_title, 1, 3)
        self.political_will = QLabel()
        summary.addWidget(self.political_will, 1, 4)

        self.details = QPushButton()
        self.details.setMinimumHeight(50)
        self.details.setMinimumWidth(210)
        self.details.setLayout(summary)
        columns.addWidget(self.details)
        self.details.clicked.connect(self.open_details_window)
        self.details.setEnabled(False)

        self.update_summary()

        self.details_window: Optional[IntelWindow] = None

    def set_game(self, game: Optional[Game]) -> None:
        self.game = game
        self.details.setEnabled(True)
        self.update_summary()

    @staticmethod
    def forces_strength_text(own: int, enemy: int) -> str:
        if not enemy:
            return "enemy eliminated"

        ratio = own / enemy
        if ratio < 0.6:
            return "outnumbered"
        if ratio < 0.8:
            return "slightly outnumbered"
        if ratio < 1.2:
            return "evenly matched"
        if ratio < 1.4:
            return "slight advantage"
        return "strong advantage"

    def economic_strength_text(self) -> str:
        assert self.game is not None
        own = Income(self.game, player=Player.BLUE).total
        enemy = Income(self.game, player=Player.RED).total

        if not enemy:
            return "enemy economy ruined"

        ratio = own / enemy
        if ratio < 0.6:
            return "strong disadvantage"
        if ratio < 0.8:
            return "slight disadvantage"
        if ratio < 1.2:
            return "evenly matched"
        if ratio < 1.4:
            return "slight advantage"
        return "strong advantage"

    def update_summary(self) -> None:
        if self.game is None or not self.game.game_stats.data_per_turn:
            # A blank-canvas setup game has not run begin_turn_0 yet, so there
            # are no per-turn stats to summarise. Show a neutral placeholder
            # instead of indexing an empty list.
            self.air_strength.setText("no data")
            self.ground_strength.setText("no data")
            self.economic_strength.setText("no data")
            self._update_campaign_rows()
            return

        data = self.game.game_stats.data_per_turn[-1]

        self.air_strength.setText(
            self.forces_strength_text(
                data.allied_units.aircraft_count, data.enemy_units.aircraft_count
            )
        )
        self.ground_strength.setText(
            self.forces_strength_text(
                data.allied_units.vehicles_count, data.enemy_units.vehicles_count
            )
        )
        self.economic_strength.setText(self.economic_strength_text())

        if self.game.turn == 0:
            self.air_strength.setText("gathering intel")
            self.ground_strength.setText("gathering intel")

        self._update_campaign_rows()

    def _update_campaign_rows(self) -> None:
        """The political-will (Vietnam) row.

        The row shows only when its feature is live for this game; the full
        legibility "why" string rides on the tooltip so the box stays compact.
        """
        show_will = self.game is not None and getattr(
            self.game.settings, "vietnam_political_will", False
        )
        self._will_title.setVisible(show_will)
        self.political_will.setVisible(show_will)
        if show_will and self.game is not None:
            blue = getattr(self.game.blue, "political_will", None)
            red = getattr(self.game.red, "political_will", None)
            if blue is not None and red is not None:
                from game.fourteenth.political_will import will_profile_for

                profile = will_profile_for(self.game)
                self.political_will.setText(f"{blue:.0f}% vs resolve {red:.0f}%")
                self.political_will.setToolTip(
                    f"{profile.blue.label} vs {profile.red.label}. Either side "
                    "hitting zero ends the war at the negotiating table."
                )

    def open_details_window(self) -> None:
        self.details_window = IntelWindow(self.game)
        self.details_window.show()
