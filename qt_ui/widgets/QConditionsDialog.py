from copy import deepcopy
from datetime import datetime, timedelta
from typing import Optional, Tuple

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from dcs.weather import Wind

from game import Game
from qt_ui.simcontroller import SimController

from game.sim import GameUpdateEvents
from game.weather.clouds import Clouds
from game.weather.wind import WindConditions
from qt_ui.widgets.conditions.QTimeAdjustmentWidget import QTimeAdjustmentWidget
from qt_ui.widgets.conditions.QTimeTurnWidget import QTimeTurnWidget
from qt_ui.widgets.conditions.QWeatherAdjustmentWidget import QWeatherAdjustmentWidget
from qt_ui.widgets.conditions.QWeatherWidget import QWeatherWidget


class QConditionsDialog(QDialog):
    def __init__(self, time_turn: QTimeTurnWidget, weather: QWeatherWidget):
        super().__init__()
        self.time_turn = time_turn
        self.weather = weather
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Time & Weather Conditions")
        self.setMinimumSize(360, 380)

        vbox = QVBoxLayout()

        self.time_adjuster = QTimeAdjustmentWidget(self.time_turn)
        vbox.addWidget(self.time_adjuster, 1)
        self.weather_adjuster = QWeatherAdjustmentWidget(self.weather)
        vbox.addWidget(self.weather_adjuster, 8)

        hbox = QHBoxLayout()
        reject_btn = QPushButton("REJECT")
        reject_btn.setProperty("style", "btn-danger")
        reject_btn.clicked.connect(self.close)
        hbox.addWidget(reject_btn)
        # Re-roll is the explicit, opt-in destructive path: it discards both
        # ATOs and re-plans for the new conditions. Kept separate from ACCEPT so
        # simply changing the clock/weather never wipes a hand-built frag.
        reroll_btn = QPushButton("RE-ROLL TURN")
        reroll_btn.setToolTip(
            "Apply the new conditions and generate a fresh plan for both sides. "
            "Discards the current flight plans."
        )
        reroll_btn.clicked.connect(self.reroll_turn)
        hbox.addWidget(reroll_btn)
        accept_btn = QPushButton("ACCEPT")
        accept_btn.setProperty("style", "btn-success")
        accept_btn.setToolTip(
            "Apply the new conditions and keep the current flight plans "
            "(re-timed to the new mission start)."
        )
        accept_btn.clicked.connect(self.accept_conditions)
        hbox.addWidget(accept_btn)
        vbox.addLayout(hbox, 1)

        self.setLayout(vbox)

    def _apply_clock_and_weather(
        self,
    ) -> Tuple[Game, SimController, datetime, Optional[datetime]]:
        """Push the dialog's date/time/weather onto the game and sim.

        Shared by both ACCEPT and RE-ROLL; leaves the ATO untouched. Returns the
        game, sim controller, the new mission start, and the previous mission
        start (so the caller can decide how to treat the planned flights).
        """
        qdt: datetime = self.time_adjuster.datetime_edit.dateTime().toPython()

        sim = self.time_turn.sim_controller
        current_time = sim.current_time_in_sim_if_game_loaded
        if current_time:
            current_time = deepcopy(current_time)
        sim.game_loop.sim.time = qdt

        game = sim.game_loop.game
        game.date = qdt.date() - timedelta(days=game.turn // 4)
        game.conditions.start_time = qdt
        self.time_turn.set_current_turn(game.turn, game.conditions)

        # TODO: create new weather object

        new_weather_type = self.weather_adjuster.type_selector.currentData()
        new_weather = new_weather_type(
            seasonal_conditions=game.theater.seasonal_conditions,
            day=qdt.date(),
            time_of_day=game.current_turn_time_of_day,
        )

        # self.weather.conditions.weather = WeatherType()
        preset = self.weather_adjuster.preset_selector.currentData()
        new_weather.clouds = Clouds(
            base=self.weather_adjuster.cloud_base.base.value(),
            density=self.weather_adjuster.cloud_density.density.value(),
            thickness=self.weather_adjuster.cloud_thickness.thickness.value(),
            precipitation=self.weather_adjuster.precipitation.selector.currentData(),
            preset=preset,
        )

        def _kts_to_mps(kts: int) -> float:
            return round(kts / 1.944, 1)

        wa = self.weather_adjuster
        new_weather.wind = WindConditions(
            at_0m=Wind(
                speed=_kts_to_mps(wa.wind_gl_speed.value()),
                direction=wa.wind_gl_dir.value(),
            ),
            at_2000m=Wind(
                speed=_kts_to_mps(wa.wind_fl08_speed.value()),
                direction=wa.wind_fl08_dir.value(),
            ),
            at_8000m=Wind(
                speed=_kts_to_mps(wa.wind_fl26_speed.value()),
                direction=wa.wind_fl26_dir.value(),
            ),
        )

        self.weather.conditions.weather = new_weather
        self.weather.update_forecast()

        return game, sim, qdt, current_time

    def accept_conditions(self) -> None:
        """Apply the new conditions and PRESERVE the planned frag.

        A change of mission start would leave every package's absolute TOT stale,
        so the existing plans are re-timed onto the new start (composition,
        rosters, loadouts, and routing are untouched) rather than discarded.
        """
        game, sim, qdt, current_time = self._apply_clock_and_weather()
        if game.turn > 0 and current_time is not None and current_time != qdt:
            delta = qdt - current_time
            game.blue.ato.shift_time(delta)
            game.red.ato.shift_time(delta)
            sim.sim_update.emit(GameUpdateEvents())
        self.accept()

    def reroll_turn(self) -> None:
        """Apply the new conditions and RE-PLAN both sides from scratch."""
        confirm = QMessageBox.question(
            self,
            "Re-roll this turn?",
            (
                "This discards the current flight plans for both sides and "
                "generates a fresh plan for the new conditions.<br />"
                "<br />"
                "Any hand-built frag for this turn will be lost. Continue?"
            ),
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        game, sim, _qdt, _current_time = self._apply_clock_and_weather()
        if game.turn > 0:
            events = GameUpdateEvents()
            game.initialize_turn(events, for_blue=True, for_red=True)
            sim.sim_update.emit(events)
        self.accept()
