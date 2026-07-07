"""Drop-spawn dialog: lets the user place a new unit group anywhere on the map."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Optional

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

from game.armedforces.forcegroup import ForceGroup
from game.data.groups import GroupRole, GroupTask
from game.layout import LAYOUTS
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

# Category entries: (display label, set of matching GroupTasks).
# The dialog enumerates LAYOUTS directly for each category so every named
# layout usable by the faction is available — not just what the faction
# happens to auto-spawn via ArmedForces.
_CATEGORIES: list[tuple[str, set[GroupTask]]] = [
    (
        "Air Defense — SAM / AAA",
        {
            GroupTask.LORAD,
            GroupTask.MERAD,
            GroupTask.SHORAD,
            GroupTask.AAA,
            GroupTask.POINT_DEFENSE,
        },
    ),
    ("Air Defense — EWR", {GroupTask.EARLY_WARNING_RADAR}),
    ("Coastal / Missile Defense", {GroupTask.COASTAL, GroupTask.MISSILE}),
    ("Ground Force (Armor / Infantry)", set(GroupRole.GROUND_FORCE.tasks)),
    ("Navy", set(GroupRole.NAVAL.tasks)),
]


def _layouts_for_category(
    faction,
    tasks: set[GroupTask],
) -> list[tuple[str, ForceGroup, TgoLayout]]:
    """Return (display_name, ForceGroup, TgoLayout) for every layout that:
    - has at least one matching task
    - is usable by the faction (has accessible units for all non-optional groups)
    Sorted alphabetically by display name.
    """
    results: list[tuple[str, ForceGroup, TgoLayout]] = []
    for layout in LAYOUTS.layouts:
        if not any(t in tasks for t in layout.tasks):
            continue
        if not layout.usable_by_faction(faction):
            continue
        try:
            fg = ForceGroup.for_layout(layout, faction)
        except Exception:
            continue
        if not fg.units and not fg.statics:
            continue
        results.append((layout.name, fg, layout))
    results.sort(key=lambda x: x[0])
    return results


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
        self.setMinimumWidth(440)

        self._layout_model: Optional[QTgoLayout] = None

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

        # --- Unit type (layout) — single picker replacing the old Force Group + Layout cascade ---
        root.addWidget(QLabel("Unit type:"))
        self._unit_type_combo = QComboBox()
        self._unit_type_combo.setMinimumWidth(320)
        root.addWidget(self._unit_type_combo)

        # --- Unit rows (scrollable) ---
        self._units_box = QGroupBox("Units")
        self._units_layout = QVBoxLayout()
        self._units_box.setLayout(self._units_layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._units_box)
        scroll.setMinimumHeight(160)
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
        self._unit_type_combo.currentIndexChanged.connect(self._on_unit_type_changed)

        # Populate initial state
        self._on_coalition_changed()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def _coalition(self):
        return self.game.blue if self._blue_radio.isChecked() else self.game.red

    def _current_tasks(self) -> set[GroupTask]:
        idx = self._category_combo.currentIndex()
        if idx < 0:
            return set()
        return _CATEGORIES[idx][1]

    def _current_fg_and_layout(
        self,
    ) -> Optional[tuple[ForceGroup, TgoLayout]]:
        return self._unit_type_combo.currentData()

    def _is_free(self) -> bool:
        return self.game.settings.enable_free_unit_placement

    # ------------------------------------------------------------------
    # Cascade repopulation
    # ------------------------------------------------------------------

    def _on_coalition_changed(self) -> None:
        self._on_category_changed()

    def _on_category_changed(self) -> None:
        tasks = self._current_tasks()
        faction = self._coalition.faction
        entries = _layouts_for_category(faction, tasks)

        self._unit_type_combo.blockSignals(True)
        self._unit_type_combo.clear()
        if entries:
            for name, fg, layout in entries:
                self._unit_type_combo.addItem(name, userData=(fg, layout))
        else:
            self._unit_type_combo.addItem("(no compatible units for this faction)")
        self._unit_type_combo.blockSignals(False)
        self._on_unit_type_changed()

    def _on_unit_type_changed(self) -> None:
        # Clear existing unit rows
        while self._units_layout.count():
            item = self._units_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        pair = self._current_fg_and_layout()
        if pair is None:
            self._update_cost()
            return

        fg, layout = pair
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
        cost = self._layout_model.price if self._layout_model is not None else 0
        budget = self._coalition.budget
        free = self._is_free()

        if free:
            self._cost_label.setText(f"Cost: FREE | Budget: ${budget:.0f}M")
        else:
            self._cost_label.setText(f"Cost: ${cost}M | Budget: ${budget:.0f}M")

        ok_btn = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setEnabled(
            self._current_fg_and_layout() is not None
            and (free or cost <= budget or self.game.turn == 0)
        )

    # ------------------------------------------------------------------
    # Confirm
    # ------------------------------------------------------------------

    def _on_confirm(self) -> None:
        pair = self._current_fg_and_layout()
        if pair is None or self._layout_model is None:
            QMessageBox.warning(self, "No selection", "Please select a unit type.")
            return

        fg, layout = pair

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
                # So a discarded deploy-next-turn placement can be refunded.
                cost=0.0 if (free or self.game.turn == 0) else cost,
            )
        except ValueError as exc:
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
