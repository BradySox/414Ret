from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QScrollArea, QVBoxLayout, QWidget

from game.dcs.groundunittype import GroundUnitType
from game.purchaseadapter import GroundUnitPurchaseAdapter
from game.theater import ControlPoint
from game.theater.player import Player
from qt_ui.models import GameModel
from qt_ui.windows.basemenu.UnitTransactionFrame import UnitTransactionFrame


class QArmorRecruitmentMenu(UnitTransactionFrame[GroundUnitType]):
    def __init__(self, cp: ControlPoint, game_model: GameModel):
        super().__init__(
            game_model,
            GroundUnitPurchaseAdapter(
                cp, game_model.game.coalition_for(cp.captured), game_model.game
            ),
        )
        self.cp = cp
        self.game_model = game_model
        self.purchase_groups = {}
        self.bought_amount_labels = {}
        self.existing_units_labels = {}

        main_layout = QVBoxLayout()

        scroll_content = QWidget()
        task_box_layout = QGridLayout()
        scroll_content.setLayout(task_box_layout)
        row = 0

        unit_types = set(
            self.game_model.game.faction_for(player=Player.BLUE).ground_units
        )
        # Phase 2c: the dedicated SOF team is buyable when the SCAR commander-capture
        # feature is on. It isn't in any faction's frontline_units, so the AI never
        # buys it and the ground planner never deploys it (INFANTRY class) — this menu
        # is the player-only acquisition path. can_buy is affordability-only.
        if self.game_model.game.settings.scar_command_post_intel:
            from game.scar_rescue import SCAR_SOF_UNIT_BLUE

            try:
                unit_types.add(GroundUnitType.named(SCAR_SOF_UNIT_BLUE))
            except KeyError:
                pass
        unit_types = list(unit_types)
        unit_types.sort(key=lambda u: u.display_name)
        for row, unit_type in enumerate(unit_types):
            self.add_purchase_row(unit_type, task_box_layout, row)
        stretch = QVBoxLayout()
        stretch.addStretch()
        task_box_layout.addLayout(stretch, row, 0)

        scroll_content.setLayout(task_box_layout)
        scroll = QScrollArea()
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
