from __future__ import unicode_literals

from datetime import timedelta

from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout

from game.campaignloader import Campaign
from game.campaignloader.campaign import DEFAULT_BUDGET
from qt_ui.widgets.spinsliders import CurrencySpinner

DEFAULT_MISSION_LENGTH: timedelta = timedelta(minutes=60)


class BudgetInputs(QtWidgets.QGridLayout):
    def __init__(self, label: str, value: int) -> None:
        super().__init__()
        self.addWidget(QtWidgets.QLabel(label), 0, 0)

        minimum = 0
        maximum = 5000

        slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(minimum)
        slider.setMaximum(maximum)
        slider.setValue(value)
        self.starting_money = CurrencySpinner(minimum, maximum, value)
        slider.valueChanged.connect(lambda x: self.starting_money.setValue(x))
        self.starting_money.valueChanged.connect(lambda x: slider.setValue(x))

        self.addWidget(slider, 1, 0)
        self.addWidget(self.starting_money, 1, 1)


class GeneratorOptions(QtWidgets.QWizardPage):
    def __init__(self, campaign: Campaign, parent=None):
        super().__init__(parent)

        self.setTitle("Generator settings")
        self.setSubTitle("\nOptions affecting the generation of the game.")
        self.setPixmap(
            QtWidgets.QWizard.WizardPixmap.LogoPixmap,
            QtGui.QPixmap("./resources/ui/wizard/logo1.png"),
        )

        # Campaign settings
        generatorSettingsGroup = QtWidgets.QGroupBox("Generator Settings")
        self.no_carrier = QtWidgets.QCheckBox()
        self.registerField("no_carrier", self.no_carrier)
        self.no_lha = QtWidgets.QCheckBox()
        self.registerField("no_lha", self.no_lha)
        self.no_player_navy = QtWidgets.QCheckBox()
        self.registerField("no_player_navy", self.no_player_navy)
        self.no_enemy_navy = QtWidgets.QCheckBox()
        self.registerField("no_enemy_navy", self.no_enemy_navy)
        self.squadrons_start_full = QtWidgets.QCheckBox()
        self.registerField("squadrons_start_full", self.squadrons_start_full)

        generatorLayout = QtWidgets.QGridLayout()
        generatorLayout.addWidget(QtWidgets.QLabel("No Aircraft Carriers"), 1, 0)
        generatorLayout.addWidget(self.no_carrier, 1, 1)
        generatorLayout.addWidget(QtWidgets.QLabel("No LHA"), 2, 0)
        generatorLayout.addWidget(self.no_lha, 2, 1)
        generatorLayout.addWidget(QtWidgets.QLabel("No Player Navy"), 3, 0)
        generatorLayout.addWidget(self.no_player_navy, 3, 1)
        generatorLayout.addWidget(QtWidgets.QLabel("No Enemy Navy"), 4, 0)
        generatorLayout.addWidget(self.no_enemy_navy, 4, 1)

        label = QtWidgets.QLabel("Squadrons start at full capacity")
        label.setToolTip(
            "Campaign will start with all squadrons at full strength "
            "given enough room at the airfield in question.\n"
            "Each squadron's capacity can be defined during Air Wing Configuration."
        )
        generatorLayout.addWidget(label, 5, 0)
        generatorLayout.addWidget(self.squadrons_start_full, 5, 1)
        generatorLayout.addWidget(QtWidgets.QWidget(), 6, 0)

        self.player_budget = BudgetInputs("Player starting budget", DEFAULT_BUDGET)
        self.registerField("starting_money", self.player_budget.starting_money)
        generatorLayout.addLayout(self.player_budget, 7, 0)

        self.enemy_budget = BudgetInputs("Enemy starting budget", DEFAULT_BUDGET)
        self.registerField("enemy_starting_money", self.enemy_budget.starting_money)
        generatorLayout.addLayout(self.enemy_budget, 8, 0)

        generatorSettingsGroup.setLayout(generatorLayout)

        modSettingsGroup = QtWidgets.QGroupBox("Mod Settings")
        self.a4_skyhawk = QtWidgets.QCheckBox()
        self.registerField("a4_skyhawk", self.a4_skyhawk)
        self.chinesemilitaryassetspack = QtWidgets.QCheckBox()
        self.registerField("chinesemilitaryassetspack", self.chinesemilitaryassetspack)
        self.iranmilitaryassetspack = QtWidgets.QCheckBox()
        self.registerField("iranmilitaryassetspack", self.iranmilitaryassetspack)
        self.russianmilitaryassetspack = QtWidgets.QCheckBox()
        self.registerField("russianmilitaryassetspack", self.russianmilitaryassetspack)
        self.swedishmilitaryassetspack = QtWidgets.QCheckBox()
        self.registerField("swedishmilitaryassetspack", self.swedishmilitaryassetspack)
        self.usamilitaryassetspack = QtWidgets.QCheckBox()
        self.registerField("usamilitaryassetspack", self.usamilitaryassetspack)
        self.ukmilitaryassetspack = QtWidgets.QCheckBox()
        self.registerField("ukmilitaryassetspack", self.ukmilitaryassetspack)
        self.ukrainemilitaryassetspack = QtWidgets.QCheckBox()
        self.registerField("ukrainemilitaryassetspack", self.ukrainemilitaryassetspack)
        self.f22_raptor = QtWidgets.QCheckBox()
        self.registerField("f22_raptor", self.f22_raptor)
        self.f111c = QtWidgets.QCheckBox()
        self.registerField("f111c", self.f111c)
        self.high_digit_sams = QtWidgets.QCheckBox()
        self.registerField("high_digit_sams", self.high_digit_sams)
        self.oh_6_vietnamassetpack = QtWidgets.QCheckBox()
        self.registerField("oh_6_vietnamassetpack", self.oh_6_vietnamassetpack)
        self.ov10a_bronco = QtWidgets.QCheckBox()
        self.registerField("ov10a_bronco", self.ov10a_bronco)
        self.vietnamwarvessels = QtWidgets.QCheckBox()
        self.registerField("vietnamwarvessels", self.vietnamwarvessels)
        self.fa_18efg = QtWidgets.QCheckBox()
        self.registerField("fa_18efg", self.fa_18efg)
        self.fa18ef_tanker = QtWidgets.QCheckBox()
        self.registerField("fa18ef_tanker", self.fa18ef_tanker)

        modHelpText = QtWidgets.QLabel(
            "<p>Select the mods you have installed. If your chosen factions support them, you'll be able to use these mods in your campaign.</p>"
        )
        modHelpText.setAlignment(Qt.AlignmentFlag.AlignCenter)

        modLayout = QtWidgets.QGridLayout()
        modLayout_row = 1

        mod_pairs = [
            ("A-4E Skyhawk (v2.2.0)", self.a4_skyhawk),
            (
                "CurrentHill Chinese Military Assets pack (1.1.4)",
                self.chinesemilitaryassetspack,
            ),
            (
                "CurrentHill Iran Military Assets pack (2.0.0)",
                self.iranmilitaryassetspack,
            ),
            (
                "CurrentHill Russian Military Assets pack (2.0.0)",
                self.russianmilitaryassetspack,
            ),
            (
                "CurrentHill Swedish Military Assets pack (1.10)",
                self.swedishmilitaryassetspack,
            ),
            (
                "CurrentHill USA Military Assets pack (1.1.5)",
                self.usamilitaryassetspack,
            ),
            (
                "CurrentHill UK Military Assets pack (1.1.2)",
                self.ukmilitaryassetspack,
            ),
            (
                "CurrentHill Ukraine Military Assets pack (1.1.1)",
                self.ukrainemilitaryassetspack,
            ),
            ("F-22A Raptor (v2.0.0 released May 2025)", self.f22_raptor),
            ("F-111C Aardvark (Warpig Production v2.260208)", self.f111c),
            ("High Digit SAMs (v1.4.0)", self.high_digit_sams),
            ("OH-6 Vietnam Asset Pack (v1.0)", self.oh_6_vietnamassetpack),
            ("OV-10A Bronco", self.ov10a_bronco),
            ("Vietnam War Vessels (v3.0.0 by TeTeT)", self.vietnamwarvessels),
            ("CJS FA-18E/F/G Super Hornet (v2.4)", self.fa_18efg),
            ("CJS FA-18E/F Super Hornet Tanker (v2.4)", self.fa18ef_tanker),
        ]

        for i in range(len(mod_pairs)):
            if i % 15 == 0:
                modLayout_row = 1
            col = 2 * (i // 15)
            if i % 5 == 0:
                # Section break here for readability
                modLayout.addWidget(QtWidgets.QWidget(), modLayout_row, col)
                modLayout_row += 1
            label, cb = mod_pairs[i]
            modLayout.addWidget(QLabel(label), modLayout_row, col)
            modLayout.addWidget(cb, modLayout_row, col + 1)
            modLayout_row += 1

        modSettingsGroup.setLayout(modLayout)

        mlayout = QVBoxLayout()
        mlayout.addWidget(generatorSettingsGroup)
        mlayout.addWidget(modSettingsGroup)
        mlayout.addWidget(modHelpText)
        self.setLayout(mlayout)
        self.update_settings(campaign)

    def update_settings(self, campaign: Campaign) -> None:
        s = campaign.settings

        self.player_budget.starting_money.setValue(campaign.recommended_player_money)
        self.enemy_budget.starting_money.setValue(campaign.recommended_enemy_money)

        self.no_carrier.setChecked(s.get("no_carrier", False))
        self.no_lha.setChecked(s.get("no_lha", False))
        self.no_player_navy.setChecked(s.get("no_player_navy", False))
        self.no_enemy_navy.setChecked(s.get("no_enemy_navy", False))
        self.squadrons_start_full.setChecked(s.get("squadron_start_full", False))

        self.a4_skyhawk.setChecked(s.get("a4_skyhawk", False))
        self.chinesemilitaryassetspack.setChecked(
            s.get("chinesemilitaryassetspack", False)
        )
        self.iranmilitaryassetspack.setChecked(s.get("iranmilitaryassetspack", False))
        self.russianmilitaryassetspack.setChecked(
            s.get("russianmilitaryassetspack", False)
        )
        self.swedishmilitaryassetspack.setChecked(
            s.get("swedishmilitaryassetspack", False)
        )
        self.usamilitaryassetspack.setChecked(s.get("usamilitaryassetspack", False))
        self.ukmilitaryassetspack.setChecked(s.get("ukmilitaryassetspack", False))
        self.ukrainemilitaryassetspack.setChecked(
            s.get("ukrainemilitaryassetspack", False)
        )
        self.f22_raptor.setChecked(s.get("f22_raptor", False))
        self.f111c.setChecked(s.get("f111c", False))
        self.high_digit_sams.setChecked(s.get("high_digit_sams", False))
        self.oh_6_vietnamassetpack.setChecked(s.get("oh_6_vietnamassetpack", False))
        self.ov10a_bronco.setChecked(s.get("ov10a_bronco", False))
        self.vietnamwarvessels.setChecked(s.get("vietnamwarvessels", False))
        self.fa_18efg.setChecked(s.get("fa_18efg", False))
        self.fa18ef_tanker.setChecked(s.get("fa18ef_tanker", False))
