"""Stop a combo box from demanding the width of its longest entry.

A ``QComboBox`` hints at the width of its widest item, which is fine for a short
list and ruinous for the long, verbose names this app puts in dropdowns -- store
names ("BRU-42 with 3 x Mk-82 SNAKEYE - 500lb GP Bomb HD"), loadout names,
squadron liveries. A tab full of them asked for over 2000 px of width, more than
a 1440p panel at 150% scaling has, purely so every entry could be read without
opening the list.

Bounding the *hint* costs nothing: the boxes still stretch to fill whatever width
their column has, and the dropdown keeps the width its entries actually need, so
picking an entry is no harder than before. Only the demand goes away.
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox

#: Slack added to a dropdown's measured content width for its frame and scrollbar.
POPUP_CHROME_WIDTH = 40


def natural_content_width(combo: QComboBox) -> int:
    """Width ``combo`` would need to show its longest entry in full.

    Measured from the entries' text rather than asked of the popup view, whose
    own hint is not reliable before the view has ever been shown.
    """
    metrics = combo.fontMetrics()
    if not combo.count():
        return 0
    return max(
        metrics.horizontalAdvance(combo.itemText(i)) for i in range(combo.count())
    )


def bound_dropdown_width(combo: QComboBox, chars: int) -> None:
    """Cap what ``combo`` asks for at roughly ``chars`` characters.

    Call this after the box is populated: the dropdown is pinned to the width its
    current entries need, which is measured here.
    """
    combo.view().setMinimumWidth(natural_content_width(combo) + POPUP_CHROME_WIDTH)
    combo.setSizeAdjustPolicy(
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
    )
    combo.setMinimumContentsLength(chars)
