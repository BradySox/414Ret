from PySide6.QtWidgets import QDialog, QGridLayout, QTabWidget

import qt_ui.uiconstants as CONST
from game.game import Game
from qt_ui.windows.stats.QAircraftChart import QAircraftChart
from qt_ui.windows.stats.QArmorChart import QArmorChart
from qt_ui.windows.stats.QWillChart import QWillChart


class QStatsWindow(QDialog):
    def __init__(self, game: Game):
        super(QStatsWindow, self).__init__()

        self.game = game
        self.setModal(True)
        self.setWindowTitle("Stats")
        self.setWindowIcon(CONST.ICONS["Statistics"])
        self.setMinimumSize(600, 300)

        self.layout = QGridLayout()
        self.aircraft_charts = QAircraftChart(self.game)
        self.armor_charts = QArmorChart(self.game)
        self.tabview = QTabWidget()
        self.tabview.addTab(self.aircraft_charts, "Aircraft")
        self.tabview.addTab(self.armor_charts, "Armor")
        # Vietnam campaign layer: the negotiation meters trend in the same
        # window as the force counts. Tab only exists when the campaign tracks
        # will, so stock campaigns see the stock two-tab window.
        if getattr(game.settings, "vietnam_political_will", False):
            self.tabview.addTab(QWillChart(self.game), "Political will")
        self.layout.addWidget(self.tabview, 0, 0)
        self.setLayout(self.layout)
