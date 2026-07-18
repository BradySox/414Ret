from PySide6.QtGui import QStandardItem

from game.infos.information import Information


class QInfoItem(QStandardItem):
    """One row of the info panel.

    Renders as "[T<turn>] <Title> — <text>" — the game turn, not the wall-clock
    timestamp `Information.__str__` leads with (real-world seconds are noise to
    the player and pushed the actual title off the panel's edge). The full
    message rides the tooltip, since the list view neither wraps nor scrolls
    horizontally, so long campaign events (HVT windows, will movers, SAR
    outcomes) used to be silently clipped (2026-07-18 UI audit).
    """

    def __init__(self, info: Information):
        super(QInfoItem, self).__init__()
        self.info = info
        body = f" — {info.text}" if info.text else ""
        self.setText(f"[T{info.turn}] {info.title}{body}")
        self.setToolTip(f"Turn {info.turn} — {info.title}\n{info.text}".rstrip())
        self.setEditable(False)
