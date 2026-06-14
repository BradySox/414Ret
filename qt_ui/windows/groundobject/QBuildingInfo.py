import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from game.config import REWARDS
from game.theater import Player, TheaterUnit


class QBuildingInfo(QGroupBox):
    def __init__(self, building: TheaterUnit, ground_object, viewer: Player):
        super(QBuildingInfo, self).__init__()
        self.building = building
        self.ground_object = ground_object
        self.viewer = viewer
        self.init_ui()

    def init_ui(self):
        visible_alive = self.building.alive_for_player(self.viewer)
        icon_path = os.path.join(
            "./resources/ui/units/buildings/" + self.building.icon + ".png"
        )
        has_real_icon = self.building.icon != "missing" and os.path.isfile(icon_path)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        if not visible_alive:
            header = QLabel()
            header.setPixmap(QPixmap("./resources/ui/units/buildings/dead.png"))
            layout.addWidget(header)
        elif has_real_icon:
            header = QLabel()
            header.setPixmap(QPixmap(icon_path))
            layout.addWidget(header)

        name_label = QLabel(self.building.short_name_for(self.viewer))
        name_label.setProperty("style", "small")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        if self.ground_object.category in REWARDS:
            income_text = "Value: " + str(REWARDS[self.ground_object.category]) + "M"
            if not visible_alive:
                income_text = "<s>" + income_text + "</s>"
            layout.addWidget(QLabel(income_text))

        self.setLayout(layout)
