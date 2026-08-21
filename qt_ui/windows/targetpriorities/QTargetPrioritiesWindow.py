"""Target priorities (§93) — how hard the auto-planner chases each kind of target.

The second axis beside per-control-point region priorities. A family is a group of
target categories the player thinks about together; per-CATEGORY control was
rejected as twenty combo rows, and the fine grain lives on the per-target override
in the ground-object dialog instead.

IGNORED here is absolute: no per-target override reopens a family the player has
switched off. The count column is the point of the window -- a priority means
nothing until you can see how many targets it moves.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

import qt_ui.uiconstants as CONST
from game.fourteenth.region_priorities import (
    TARGET_FAMILIES,
    RegionPriority,
    family_priority,
)
from game.game import Game


class QTargetPrioritiesWindow(QDialog):
    def __init__(self, game: Game, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.game = game

        self.setWindowTitle("Target Priorities")
        self.setWindowIcon(CONST.ICONS["Generator"])
        self.setMinimumWidth(520)

        layout = QVBoxLayout()
        self.setLayout(layout)

        intro = QLabel(
            "How hard the auto-planner chases each kind of enemy target. Emphasized "
            "ranks a family closer than it is, deprioritized ranks it further, and "
            "ignored leaves it to packages you build by hand.\n\n"
            "This multiplies with a base's own region priority, and it wins: a family "
            "set to ignored is never auto-planned, even at an emphasized base. To spare "
            "one target, set its own priority in the target's dialog instead."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        if not game.settings.region_priorities:
            warning = QLabel(
                "<b>Region priorities are off</b>, so nothing here reaches the "
                "planner yet. Settings → 414th Features → Region priorities."
            )
            warning.setWordWrap(True)
            layout.addWidget(warning)

        grid = QGridLayout()
        layout.addLayout(grid)
        grid.addWidget(QLabel("<b>Target family</b>"), 0, 0)
        grid.addWidget(QLabel("<b>Priority</b>"), 0, 1)
        grid.addWidget(QLabel("<b>In this theater</b>"), 0, 2)

        counts = self.enemy_target_counts()
        self.combos: dict[str, QComboBox] = {}
        for row, family in enumerate(TARGET_FAMILIES, start=1):
            grid.addWidget(QLabel(family), row, 0)

            combo = QComboBox()
            for priority in RegionPriority:
                combo.addItem(priority.value.capitalize(), priority)
            combo.setCurrentIndex(
                list(RegionPriority).index(family_priority(family, game.settings))
            )
            combo.currentIndexChanged.connect(
                lambda _index, f=family: self.on_changed(f)
            )
            grid.addWidget(combo, row, 1)
            self.combos[family] = combo

            count = counts.get(family, 0)
            label = QLabel(str(count) if count else "—")
            if not count:
                label.setToolTip("No enemy target of this kind on this map.")
            grid.addWidget(label, row, 2)

    def enemy_target_counts(self) -> dict[str, int]:
        """Live enemy targets per family, so a priority is not set blind."""
        from game.fourteenth.region_priorities import family_of

        counts: dict[str, int] = {}
        for control_point in self.game.theater.controlpoints:
            if control_point.captured.is_blue:
                continue
            for tgo in control_point.ground_objects:
                if tgo.is_dead():
                    continue
                family = family_of(tgo)
                if family is not None:
                    counts[family] = counts.get(family, 0) + 1
        return counts

    def on_changed(self, family: str) -> None:
        combo = self.combos[family]
        priority = combo.itemData(combo.currentIndex())
        self.game.settings.blue_target_family_priorities[family] = priority.value
