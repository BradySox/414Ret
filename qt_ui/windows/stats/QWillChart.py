from PySide6 import QtCharts
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QFrame, QGridLayout

from game import Game


class QWillChart(QFrame):
    """Political Will vs Regime Resolve over time (Vietnam campaign layer W1).

    Reads the same per-turn series as the other stats tabs
    (FactionTurnMetadata.political_will); the tab is only added when the
    campaign tracks will, so this never charts an empty series by design.
    """

    def __init__(self, game: Game):
        super(QWillChart, self).__init__()
        self.game = game
        self.initUi()

    def initUi(self):
        self.layout = QGridLayout()
        self.generateWillChart()
        self.setLayout(self.layout)

    def generateWillChart(self):
        # (turn index, blue, red) for every turn that carries will data. Pre-
        # feature turns (or a mid-campaign toggle) simply contribute no point.
        points = [
            (turn, blue, red)
            for turn, data in enumerate(self.game.game_stats.data_per_turn)
            if (blue := getattr(data.allied_units, "political_will", None)) is not None
            and (red := getattr(data.enemy_units, "political_will", None)) is not None
        ]

        blueSerie = QtCharts.QLineSeries()
        blueSerie.setName("Political Will (Washington)")
        redSerie = QtCharts.QLineSeries()
        redSerie.setColor(Qt.GlobalColor.red)
        redSerie.setName("Regime Resolve (Hanoi)")
        for turn, blue, red in points:
            blueSerie.append(QPointF(turn, blue))
            redSerie.append(QPointF(turn, red))

        self.chart = QtCharts.QChart()
        self.chart.addSeries(blueSerie)
        self.chart.addSeries(redSerie)
        self.chart.setTitle("Political will over time (0 ends the war)")

        self.chart.createDefaultAxes()
        self.chart.axisX().setTitleText("Turn")
        self.chart.axisX().setLabelFormat("%i")
        self.chart.axisX().setRange(0, max((t for t, _, _ in points), default=1))
        self.chart.axisX().applyNiceNumbers()

        self.chart.axisY().setLabelFormat("%i")
        self.chart.axisY().setRange(0, 100)

        self.chartView = QtCharts.QChartView(self.chart)
        self.chartView.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.layout.addWidget(self.chartView, 0, 0)
