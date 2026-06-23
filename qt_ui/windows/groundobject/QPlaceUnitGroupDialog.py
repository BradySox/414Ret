"""Drop-spawn dialog: lets the user place a new unit group anywhere on the map."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QMessageBox,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from game.armedforces.armedforces import ArmedForces
from game.armedforces.forcegroup import ForceGroup
from game.data.groups import GroupRole, GroupTask
from game.layout.layout import LayoutException, TgoLayout
from game.server import EventStream
from game.sim import GameUpdateEvents
from game.theater.theatergroundobject import TheaterGroundObject
from game.theater.unitplacement import PlacementSelection, place_unit_group
from qt_ui.models import GameModel
from qt_ui.windows.groundobject.QGroundObjectBuyMenu import (
    QTgoLayout,
    QTgoLayoutGroupRow,
)

logger = logging.getLogger(__name__)

# Category entries shown in the dropdown:  (label, role_or_tasks)
# role_or_tasks is a GroupRole (for broad categories) or a list[GroupTask] (narrow).
_CATEGORIES: list[tuple[str, GroupRole | list[GroupTask]]] = [
    ("Ground Force (Armor / Infantry)", GroupRole.GROUND_FORCE),
    (
        "Air Defense — SAM / AAA",
        [
            GroupTask.LORAD,
            GroupTask.MERAD,
            GroupTask.SHORAD,
            GroupTask.AAA,
            GroupTask.POINT_DEFENSE,
        ],
    ),
    ("Air Defense — EWR", [GroupTask.EARLY_WARNING_RADAR]),
    ("Navy", GroupRole.NAVAL),
    ("Missile / Coastal", GroupRole.DEFENSES),
]


def _groups_for_category(
    armed_forces: ArmedForces,
    category_data: GroupRole | list[GroupTask],
) -> list[ForceGroup]:
    if isinstance(category_data, GroupRole):
        tasks = category_data.tasks
    else:
        tasks = category_data
    groups = armed_forces.groups_for_tasks(tasks)
    return groups


class QPlaceUnitGroupDialog(QDialog):
    """Dialog to configure and confirm a drop-spawn unit placement."""

    def __init__(
        self,
        parent: QWidget,
        lat: float,
        lng: float,
        game_model: GameModel,
    ) -> None:
        super().__init__(parent)
        self.lat = lat
        self.lng = lng
        self.game_model = game_model
        self.game = game_model.game
        assert self.game is not None

        self.setWindowTitle("Place Unit Group")
        self.setMinimumWidth(420)

        self._layout_model: Optional[QTgoLayout] = None
        self._armed_forces: Optional[ArmedForces] = None

        root = QVBoxLayout()
        self.setLayout(root)

        # --- Position ---
        root.addWidget(QLabel(f"<b>Position:</b> {lat:.4f}°, {lng:.4f}°"))

        # --- Coalition ---
        coalition_box = QGroupBox("Coalition")
        cbox_layout = QVBoxLayout()
        coalition_box.setLayout(cbox_layout)
        self._coalition_group = QButtonGroup(self)
        self._blue_radio = QRadioButton("Blue")
        self._red_radio = QRadioButton("Red")
        self._coalition_group.addButton(self._blue_radio)
        self._coalition_group.addButton(self._red_radio)
        self._blue_radio.setChecked(True)
        if not self.game.settings.enable_enemy_buy_sell:
            self._red_radio.setEnabled(False)
            self._red_radio.setToolTip(
                "Enable 'Enemy Buy/Sell' cheat to place red units."
            )
        cbox_layout.addWidget(self._blue_radio)
        cbox_layout.addWidget(self._red_radio)
        root.addWidget(coalition_box)

        # --- Category ---
        root.addWidget(QLabel("Category:"))
        self._category_combo = QComboBox()
        for label, _ in _CATEGORIES:
            self._category_combo.addItem(label)
        root.addWidget(self._category_combo)

        # --- Force Group ---
        root.addWidget(QLabel("Group type:"))
        self._fg_combo = QComboBox()
        self._fg_combo.setMinimumWidth(300)
        root.addWidget(self._fg_combo)

        # --- Layout ---
        root.addWidget(QLabel("Layout:"))
        self._layout_combo = QComboBox()
        root.addWidget(self._layout_combo)

        # --- Unit rows (scrollable) ---
        self._units_box = QGroupBox("Units")
        self._units_layout = QVBoxLayout()
        self._units_box.setLayout(self._units_layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._units_box)
        scroll.setMinimumHeight(150)
        root.addWidget(scroll)

        # --- Deploy timing ---
        timing_box = QGroupBox("Deploy timing")
        timing_layout = QVBoxLayout()
        timing_box.setLayout(timing_layout)
        self._timing_group = QButtonGroup(self)
        self._spawn_now = QRadioButton("Spawn now")
        self._spawn_next = QRadioButton("Deploy next turn")
        self._timing_group.addButton(self._spawn_now)
        self._timing_group.addButton(self._spawn_next)
        self._spawn_now.setChecked(True)
        timing_layout.addWidget(self._spawn_now)
        timing_layout.addWidget(self._spawn_next)
        root.addWidget(timing_box)

        # --- Respawn ---
        self._respawn_check = QCheckBox(
            "Auto-respawn if destroyed (costs budget each turn)"
        )
        root.addWidget(self._respawn_check)

        # --- Cost / budget ---
        self._cost_label = QLabel()
        root.addWidget(self._cost_label)

        # --- Buttons ---
        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Place")
        self._buttons.accepted.connect(self._on_confirm)
        self._buttons.rejected.connect(self.reject)
        root.addWidget(self._buttons)

        # Wire change signals
        self._blue_radio.toggled.connect(self._on_coalition_changed)
        self._category_combo.currentIndexChanged.connect(self._on_category_changed)
        self._fg_combo.currentIndexChanged.connect(self._on_fg_changed)
        self._layout_combo.currentIndexChanged.connect(self._on_layout_changed)

        # Populate initial state
        self._on_coalition_changed()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def _coalition(self):
        return self.game.blue if self._blue_radio.isChecked() else self.game.red

    def _current_category_data(self) -> GroupRole | list[GroupTask] | None:
        idx = self._category_combo.currentIndex()
        if idx < 0:
            return None
        return _CATEGORIES[idx][1]

    def _current_force_group(self) -> Optional[ForceGroup]:
        return self._fg_combo.currentData()

    def _current_layout(self) -> Optional[TgoLayout]:
        return self._layout_combo.currentData()

    def _is_free(self) -> bool:
        return self.game.settings.enable_free_unit_placement

    # ------------------------------------------------------------------
    # Cascade repopulation
    # ------------------------------------------------------------------

    def _on_coalition_changed(self) -> None:
        self._armed_forces = ArmedForces(self._coalition.faction)
        self._on_category_changed()

    def _on_category_changed(self) -> None:
        cat = self._current_category_data()
        self._fg_combo.blockSignals(True)
        self._fg_combo.clear()
        if cat is not None and self._armed_forces is not None:
            for fg in _groups_for_category(self._armed_forces, cat):
                self._fg_combo.addItem(fg.name, userData=fg)
        self._fg_combo.blockSignals(False)
        self._on_fg_changed()

    def _on_fg_changed(self) -> None:
        fg = self._current_force_group()
        self._layout_combo.blockSignals(True)
        self._layout_combo.clear()
        if fg is not None:
            faction = self._coalition.faction
            for layout in fg.layouts:
                if layout.usable_by_faction(faction):
                    self._layout_combo.addItem(layout.name, userData=layout)
        self._layout_combo.blockSignals(False)
        self._on_layout_changed()

    def _on_layout_changed(self) -> None:
        # Clear existing unit rows
        while self._units_layout.count():
            item = self._units_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        fg = self._current_force_group()
        layout = self._current_layout()
        if fg is None or layout is None:
            self._update_cost()
            return

        self._layout_model = QTgoLayout(layout=layout, force_group=fg)
        self._layout_model.groups = defaultdict(list)

        for tgo_group in layout.groups:
            group_box = QGroupBox(tgo_group.group_name)
            group_vbox = QVBoxLayout()
            for unit_group in tgo_group.unit_groups:
                try:
                    row = QTgoLayoutGroupRow(fg, unit_group)
                except LayoutException:
                    continue
                self._layout_model.groups[tgo_group.group_name].append(row.group_layout)
                row.group_template_changed.connect(self._update_cost)
                group_vbox.addWidget(row)
            group_box.setLayout(group_vbox)
            self._units_layout.addWidget(group_box)

        self._update_cost()

    def _update_cost(self) -> None:
        if self._layout_model is None:
            cost = 0
        else:
            cost = self._layout_model.price

        budget = self._coalition.budget
        free = self._is_free()

        if free:
            self._cost_label.setText(f"Cost: FREE | Budget: ${budget:.0f}M")
        else:
            self._cost_label.setText(f"Cost: ${cost}M | Budget: ${budget:.0f}M")

        ok_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setEnabled(free or cost <= budget or self.game.turn == 0)

    # ------------------------------------------------------------------
    # Confirm
    # ------------------------------------------------------------------

    def _on_confirm(self) -> None:
        fg = self._current_force_group()
        layout = self._current_layout()
        if fg is None or layout is None:
            QMessageBox.warning(
                self, "No selection", "Please select a group type and layout."
            )
            return

        if self._layout_model is None:
            QMessageBox.warning(self, "No units", "No units configured.")
            return

        # Build PlacementSelection list from active rows
        selections: list[PlacementSelection] = []
        for group_name, row_list in self._layout_model.groups.items():
            for row in row_list:
                if not row.enabled:
                    continue
                dcs_group_name = f"{layout.name} ({group_name})"
                selections.append(
                    PlacementSelection(
                        unit_group=row.layout,
                        dcs_group_name=dcs_group_name,
                        unit_type=row.dcs_unit_type,
                        count=row.amount,
                    )
                )

        if not selections:
            QMessageBox.warning(self, "No units", "Enable at least one unit group.")
            return

        coalition = self._coalition
        free = self._is_free()
        deploy_next = self._spawn_next.isChecked()
        respawn = self._respawn_check.isChecked()

        # Deduct budget now (for both spawn-now and deploy-next-turn).
        cost = self._layout_model.price
        if not free and self.game.turn > 0:
            if cost > coalition.budget:
                QMessageBox.warning(
                    self,
                    "Insufficient budget",
                    f"Need ${cost}M, have ${coalition.budget:.0f}M.",
                )
                return
            coalition.budget -= cost

        try:
            result = place_unit_group(
                self.game,
                coalition,
                self.lat,
                self.lng,
                fg,
                layout,
                selections,
                free=free,
                deploy_next_turn=deploy_next,
                respawn=respawn,
            )
        except ValueError as exc:
            # Refund the budget deduction we just made
            if not free and self.game.turn > 0:
                coalition.budget += cost
            QMessageBox.warning(self, "Placement error", str(exc))
            return

        # Push the new TGO to the React map immediately (spawn-now path only).
        if isinstance(result, TheaterGroundObject):
            events = GameUpdateEvents()
            events.update_tgo(result)
            EventStream.put_nowait(events)

        self.accept()
