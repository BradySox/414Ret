import logging
import operator
from typing import Optional

from PySide6.QtWidgets import QComboBox, QWidget, QHBoxLayout, QPushButton
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Signal

from game import Game
from game.ato.flight import Flight
from game.ato.flightmember import FlightMember
from game.ato.loadouts import Loadout
from game.data.weapons import Pylon, Weapon
from qt_ui.widgets.dropdownwidth import bound_dropdown_width
from .QWeaponSettingsDialog import QWeaponSettingsDialog


class QPylonEditor(QWidget):
    #: Emitted after this pylon's store changed (the loadout is already updated).
    #: Lets the payload tab refresh derived readouts (the §46 fuel-plan line).
    pylon_changed = Signal()

    #: Width, in characters, a pylon's store dropdown asks for. See
    #: :func:`bound_dropdown_width` -- a full pylon list of un-bounded store names
    #: dragged the Edit Flight dialog past 2000 px wide.
    STORE_NAME_HINT_CHARS = 32

    def __init__(
        self, game: Game, flight: Flight, flight_member: FlightMember, pylon: Pylon
    ) -> None:
        super().__init__()
        self.flight = flight
        self.flight_member = flight_member
        self.pylon = pylon
        self.game = game
        self.has_added_clean_item = False

        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Create combobox for weapon selection
        self.weapon_combo = QComboBox()
        current = self.flight_member.loadout.pylons.get(self.pylon.number)

        self.weapon_combo.addItem("None", None)
        if self.game.settings.restrict_weapons_by_date:
            weapons = pylon.available_on(
                self.game.date, flight.squadron.coalition.faction
            )
        else:
            weapons = pylon.allowed
        allowed = sorted(weapons, key=operator.attrgetter("name"))
        # §54 M2: grey out scarce munitions the departure airfield is out of (guidance;
        # the generator enforces it regardless). Only once stocks are seeded; the
        # currently-selected store is always left selectable so an edit isn't broken.
        stock_gate = self.game.settings.restrict_weapons_by_stock and getattr(
            self.game, "munitions_seeded", False
        )
        munitions = (
            getattr(flight.departure.base, "munitions", {}) if stock_gate else {}
        )
        for i, weapon in enumerate(allowed):
            out_of_stock = False
            if stock_gate and weapon != current:
                family = weapon.weapon_group.scarce_family
                out_of_stock = family is not None and munitions.get(family, 0) <= 0
            label = f"{weapon.name} (out of stock)" if out_of_stock else weapon.name
            self.weapon_combo.addItem(label, weapon)
            if out_of_stock:
                item = self.weapon_combo.model().item(i + 1)
                if item is not None:
                    item.setEnabled(False)
            if current == weapon:
                self.weapon_combo.setCurrentIndex(i + 1)

        bound_dropdown_width(self.weapon_combo, self.STORE_NAME_HINT_CHARS)
        self._update_store_tooltip()

        self.weapon_combo.currentIndexChanged.connect(self.on_pylon_change)
        layout.addWidget(self.weapon_combo, 1)

        # Create settings button (initially hidden)
        self.settings_button = QPushButton()
        self.settings_button.setIcon(QIcon.fromTheme("preferences-system"))
        self.settings_button.setText("⚙")  # Gear emoji as fallback
        self.settings_button.setMaximumWidth(30)
        self.settings_button.setToolTip("Configure weapon settings")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.settings_button.setVisible(False)
        layout.addWidget(self.settings_button)

        self.update_settings_button_visibility()

    def _update_store_tooltip(self) -> None:
        """Show the selected store's full name on hover.

        Store names run well past the dropdown's width cap (see
        :attr:`STORE_NAME_HINT_CHARS`), so the *closed* combo elides them --
        "(Special Weapons Adapter) 2x Mk-20 Rockeye -" with no way to read the rest.
        The open popup keeps its natural width, so this only has to cover the
        closed state.
        """
        self.weapon_combo.setToolTip(self.weapon_combo.currentText())

    def update_settings_button_visibility(self) -> None:
        """Show/hide settings button based on whether current weapon has settings."""
        weapon = self.weapon_combo.currentData()
        if weapon is not None and weapon.has_settings():
            self.settings_button.setVisible(True)
        else:
            self.settings_button.setVisible(False)

    def open_settings_dialog(self) -> None:
        """Open the weapon settings dialog."""
        weapon = self.weapon_combo.currentData()
        if weapon is None:
            return

        current_settings = self.flight_member.loadout.pylon_settings.get(
            self.pylon.number
        )

        dialog = QWeaponSettingsDialog(weapon, current_settings, self)
        if dialog.exec():
            # Save the settings
            settings_dict = dialog.get_settings_dict()
            self.flight_member.loadout.pylon_settings[self.pylon.number] = settings_dict
            logging.info(
                f"Updated settings for pylon {self.pylon.number}: {settings_dict}"
            )

    def on_pylon_change(self) -> None:
        selected: Optional[Weapon] = self.weapon_combo.currentData()
        self.flight_member.loadout.pylons[self.pylon.number] = selected

        # Clear settings when weapon changes
        if self.pylon.number in self.flight_member.loadout.pylon_settings:
            del self.flight_member.loadout.pylon_settings[self.pylon.number]

        self.update_settings_button_visibility()
        self._update_store_tooltip()

        if selected is None:
            logging.debug(f"Pylon {self.pylon.number} emptied")
        else:
            logging.debug(f"Pylon {self.pylon.number} changed to {selected.name}")
        self.pylon_changed.emit()

    def weapon_from_loadout(self, loadout: Loadout) -> Optional[Weapon]:
        weapon = loadout.pylons.get(self.pylon.number)
        if weapon is None:
            return None
        # TODO: Fix pydcs to support the <CLEAN> "weapon".
        # These are not exported in the pydcs weapon map, which causes the pydcs pylon
        # exporter to fail to include them in the supported list. Since they aren't
        # known to be compatible (and we can't show them as compatible for *every*
        # pylon, because they aren't), we won't have populated a "Clean" weapon when
        # creating the selection list, so it's not selectable. To work around this, add
        # the item to the list the first time it's encountered for the pylon.
        #
        # A similar hack exists in Pylon to support forcibly equipping this even when
        # it's not known to be compatible.
        if weapon.clsid == "<CLEAN>":
            if not self.has_added_clean_item:
                self.weapon_combo.addItem("Clean", weapon)
                self.has_added_clean_item = True
        return weapon

    def matching_weapon_name(self, loadout: Loadout) -> str:
        if self.game.settings.restrict_weapons_by_date:
            # Always apply target overrides for AI, only for players if setting is enabled
            should_apply_overrides = (
                not self.flight_member.is_player
                or self.game.settings.apply_target_overrides_to_loadouts
            )
            target = self.flight.package.target if should_apply_overrides else None
            loadout = loadout.degrade_for_date(
                self.flight.unit_type,
                self.game.date,
                self.flight.squadron.coalition.faction,
                target,
            )
        weapon = self.weapon_from_loadout(loadout)
        if weapon is None:
            return "None"
        return weapon.name

    def set_flight_member(self, flight_member: FlightMember) -> None:
        self.flight_member = flight_member
        self.set_from(self.flight_member.loadout)

    def set_from(self, loadout: Loadout) -> None:
        self.weapon_combo.setCurrentText(self.matching_weapon_name(loadout))
        self.update_settings_button_visibility()
        self._update_store_tooltip()
