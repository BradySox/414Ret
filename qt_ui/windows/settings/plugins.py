from typing import Dict, List

from PySide6.QtCore import Qt, QLocale
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
    QSpinBox,
)

from game.plugins import LuaPlugin, LuaPluginManager
from game.plugins.luaplugin import plugin_option_is_enabled
from game.settings import Settings
from game.settings.ISettingsContainer import SettingsContainer


class PluginsBox(QGroupBox):
    def __init__(self) -> None:
        super().__init__("Plugins")

        layout = QGridLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)

        self.plugin_map: Dict[str, QCheckBox] = {}

        for row, plugin in enumerate(LuaPluginManager.plugins()):
            if not plugin.show_in_ui:
                continue

            layout.addWidget(QLabel(plugin.name), row, 0)

            checkbox = QCheckBox()
            checkbox.setChecked(plugin.get_value)
            checkbox.toggled.connect(plugin.set_value)
            layout.addWidget(checkbox, row, 1)
            self.plugin_map[plugin.identifier] = checkbox

    def update_from_settings(self, settings: Settings):
        for identifier, enabled in settings.plugins.items():
            if identifier in self.plugin_map:
                self.plugin_map[identifier].setChecked(enabled)


class PluginsPage(QWidget):
    def __init__(self, sc: SettingsContainer) -> None:
        super().__init__()

        self.sc = sc

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)

        self.plugins_box = PluginsBox()
        layout.addWidget(self.plugins_box)

    def update_from_settings(self):
        self.plugins_box.update_from_settings(self.sc.settings)


class PluginOptionsBox(QGroupBox):
    def __init__(self, plugin: LuaPlugin) -> None:
        super().__init__(plugin.name)

        layout = QGridLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)

        self.widgets: Dict[str, QWidget] = {}
        #: identifier -> its label, so a dependency greys the whole row and not
        #: just the control (a lit label beside a dead spinbox reads as a bug).
        self.labels: Dict[str, QLabel] = {}
        self.plugin = plugin

        row = 0
        if plugin.description:
            description = QLabel(plugin.description)
            description.setWordWrap(True)
            font = description.font()
            font.setItalic(True)
            description.setFont(font)
            description.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            layout.addWidget(description, row, 0, 1, 2)
            row += 1

        for option in plugin.options:
            label = QLabel(option.name)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(label, row, 0)
            self.labels[option.identifier] = label

            val = option.get_value
            # Pick the widget from the option's *declared default* type, not the
            # currently-stored value's type. A decimal option (default 0.75) whose
            # value was ever written as an int (e.g. 1, from an older build or a
            # round-trip) would otherwise get an integer QSpinBox and silently round
            # 0.75 -> 1, making the fractional value unreachable from the UI. Keying
            # on the default keeps a float option a QDoubleSpinBox regardless of what
            # value happens to be stored.
            default = option.value
            if type(default) == bool:
                checkbox = QCheckBox()
                checkbox.setChecked(val)
                checkbox.toggled.connect(option.set_value)
                # A master's own control must refresh the box AFTER the new value
                # is stored, so connect the refresh second -- Qt fires slots in
                # connection order, and refreshing first would read the old value.
                checkbox.toggled.connect(lambda _: self.refresh_enabled_states())
                layout.addWidget(checkbox, row, 1)
                self.widgets[option.identifier] = checkbox
            elif type(default) == float or type(default) == int:
                if type(default) == float:
                    spinbox = QDoubleSpinBox()
                    spinbox.setSingleStep(0.01)
                    spinbox.setLocale(QLocale.Language.English)
                else:
                    spinbox = QSpinBox()
                spinbox.setMinimum(option.min)
                spinbox.setMaximum(option.max)
                # Coerce the stored value to the field's type: a QSpinBox rejects a
                # float in PySide6, and a mistyped stored value must not break the
                # whole options page.
                spinbox.setValue(float(val) if type(default) == float else int(val))
                spinbox.valueChanged.connect(option.set_value)
                spinbox.valueChanged.connect(lambda _: self.refresh_enabled_states())
                layout.addWidget(spinbox, row, 1)
                self.widgets[option.identifier] = spinbox
            else:
                # A string option. Without this branch the loop added the label and
                # then no widget at all, so all seven the fork ships (frequencies,
                # weapon-pattern lists, the FAC type, the scramble spawn mode) sat in
                # the page next to an empty cell and could not be edited.
                if option.choices:
                    combo = QComboBox()
                    combo.addItems(option.choices)
                    combo.setCurrentText(str(val))
                    combo.currentTextChanged.connect(option.set_value)
                    combo.currentTextChanged.connect(
                        lambda _: self.refresh_enabled_states()
                    )
                    layout.addWidget(combo, row, 1)
                    self.widgets[option.identifier] = combo
                else:
                    line = QLineEdit(str(val))
                    line.textChanged.connect(option.set_value)
                    line.textChanged.connect(lambda _: self.refresh_enabled_states())
                    layout.addWidget(line, row, 1)
                    self.widgets[option.identifier] = line

            row += 1

        self.refresh_enabled_states()

    def refresh_enabled_states(self) -> None:
        """Grey out every option whose master option doesn't match.

        Greying is presentation only: the stored value is untouched and still
        goes into the mission's Lua data table. The plugin scripts already guard
        on their own master option, so this tells the reader what is inert
        instead of changing what runs.
        """
        for option in self.plugin.options:
            if option.enabled_when is None:
                continue
            enabled = plugin_option_is_enabled(option, self.plugin.settings)
            widget = self.widgets.get(option.identifier)
            if widget is not None:
                widget.setEnabled(enabled)
            label = self.labels.get(option.identifier)
            if label is not None:
                label.setEnabled(enabled)

    def update_from_settings(self, settings: Settings) -> None:
        for identifier in self.widgets:
            value = settings.plugin_option(identifier)
            w = self.widgets[identifier]
            if isinstance(w, QCheckBox):
                w.setChecked(value)
            elif isinstance(w, QDoubleSpinBox):
                w.setValue(float(value))
            elif isinstance(w, QSpinBox):
                w.setValue(int(value))
        self.refresh_enabled_states()


class PluginOptionsPage(QWidget):
    def __init__(self, sc: SettingsContainer) -> None:
        super().__init__()

        self.sc = sc

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)

        self.pobs: List[PluginOptionsBox] = []

        for plugin in LuaPluginManager.plugins():
            if plugin.options:
                pob = PluginOptionsBox(plugin)
                layout.addWidget(pob)
                self.pobs.append(pob)

    def update_from_settings(self):
        for pob in self.pobs:
            pob.update_from_settings(self.sc.settings)
