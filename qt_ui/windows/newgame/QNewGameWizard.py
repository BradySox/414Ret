from __future__ import unicode_literals

import logging

from PySide6 import QtGui, QtWidgets

from game.campaignloader.campaign import Campaign
from game.theater.start_generator import GameGenerator, GeneratorSettings, ModSettings
from qt_ui.windows.AirWingConfigurationDialog import AirWingConfigurationDialog
from qt_ui.windows.newgame.WizardPages.QFactionSelection import FactionSelection
from qt_ui.windows.newgame.WizardPages.QGeneratorSettings import GeneratorOptions
from qt_ui.windows.newgame.WizardPages.QNewGameSettings import NewGameSettings
from qt_ui.windows.newgame.WizardPages.QTheaterConfiguration import (
    TheaterConfiguration,
    TIME_PERIODS,
)


class NewGameWizard(QtWidgets.QWizard):
    def __init__(self, parent=None):
        super(NewGameWizard, self).__init__(parent)
        self.setOption(QtWidgets.QWizard.WizardOption.IndependentPages)

        self.campaigns = list(sorted(Campaign.load_each(), key=lambda x: x.name))

        self.faction_selection_page = FactionSelection(self)
        self.addPage(IntroPage(self))
        self.theater_page = TheaterConfiguration(
            self.campaigns, self.faction_selection_page, self
        )
        self.addPage(self.theater_page)
        self.addPage(self.faction_selection_page)
        self.go_page = GeneratorOptions(self.campaigns[0], self)
        self.addPage(self.go_page)
        self.settings_page = NewGameSettings(self.campaigns[0], self)

        # Update difficulty page on campaign select
        self.theater_page.campaign_selected.connect(lambda c: self.update_settings(c))
        self.addPage(self.settings_page)
        self.addPage(ConclusionPage(self))

        self.setPixmap(
            QtWidgets.QWizard.WizardPixmap.WatermarkPixmap,
            QtGui.QPixmap("./resources/ui/wizard/watermark1.png"),
        )
        self.setWizardStyle(QtWidgets.QWizard.WizardStyle.ModernStyle)

        self.setWindowTitle("New Game")
        self.generatedGame = None

    def accept(self):
        logging.info("New Game Wizard accept")
        logging.info("======================")

        campaign = self.field("selectedCampaign")
        if campaign is None:
            campaign = self.theater_page.campaignList.selected_campaign
        if campaign is None:
            campaign = self.campaigns[0]

        logging.info("New campaign selected: %s", campaign.name)

        if self.field("usePreset"):
            start_date = TIME_PERIODS[
                list(TIME_PERIODS.keys())[self.field("timePeriod")]
            ]
        else:
            start_date = self.theater_page.calendar.selectedDate().toPython()

        logging.info("New campaign start date: %s", start_date.strftime("%m/%d/%Y"))

        generator_settings = GeneratorSettings(
            start_date=start_date,
            start_time=campaign.recommended_start_time,
            player_budget=int(self.field("starting_money")),
            enemy_budget=int(self.field("enemy_starting_money")),
            # QSlider forces integers, so we use 1 to 50 and divide by 10 to
            # give 0.1 to 5.0.
            inverted=self.field("invertMap"),
            advanced_iads=self.field("advanced_iads"),
            no_carrier=self.field("no_carrier"),
            no_lha=self.field("no_lha"),
            no_player_navy=self.field("no_player_navy"),
            no_enemy_navy=self.field("no_enemy_navy"),
            tgo_config=campaign.load_ground_forces_config(),
            carrier_config=campaign.load_carrier_config(),
            squadrons_start_full=self.field("squadrons_start_full"),
        )
        mod_settings = ModSettings(
            a4_skyhawk=self.field("a4_skyhawk"),
            f22_raptor=self.field("f22_raptor"),
            f111c=self.field("f111c"),
            high_digit_sams=self.field("high_digit_sams"),
            oh_6_vietnamassetpack=self.field("oh_6_vietnamassetpack"),
            ov10a_bronco=self.field("ov10a_bronco"),
            vietnamwarvessels=self.field("vietnamwarvessels"),
            chinesemilitaryassetspack=self.field("chinesemilitaryassetspack"),
            iranmilitaryassetspack=self.field("iranmilitaryassetspack"),
            russianmilitaryassetspack=self.field("russianmilitaryassetspack"),
            swedishmilitaryassetspack=self.field("swedishmilitaryassetspack"),
            usamilitaryassetspack=self.field("usamilitaryassetspack"),
            ukmilitaryassetspack=self.field("ukmilitaryassetspack"),
            ukrainemilitaryassetspack=self.field("ukrainemilitaryassetspack"),
        )

        blue_faction = self.faction_selection_page.selected_blue_faction
        red_faction = self.faction_selection_page.selected_red_faction

        logging.info("New campaign blue faction: %s", blue_faction.name)
        logging.info("New campaign red faction: %s", red_faction.name)

        theater = campaign.load_theater(generator_settings.advanced_iads)

        logging.info("New campaign theater: %s", theater.terrain.name)

        settings = self.settings_page.settings_widget.settings

        generator = GameGenerator(
            blue_faction,
            red_faction,
            theater,
            campaign.load_air_wing_config(theater),
            settings,
            generator_settings,
            mod_settings,
            campaign_name=campaign.name,
        )
        self.generatedGame = generator.generate()

        AirWingConfigurationDialog(
            self.generatedGame, generator.generator_settings.squadrons_start_full, self
        ).exec_()

        self.generatedGame.begin_turn_0(
            squadrons_start_full=generator_settings.squadrons_start_full
        )

        super(NewGameWizard, self).accept()

    def update_settings(self, campaign: Campaign) -> None:
        self.settings_page.set_campaign_values(campaign)
        self.go_page.update_settings(campaign)


class IntroPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super(IntroPage, self).__init__(parent)

        self.setTitle("Introduction")
        self.setPixmap(
            QtWidgets.QWizard.WizardPixmap.WatermarkPixmap,
            QtGui.QPixmap("./resources/ui/wizard/watermark1.png"),
        )

        label = QtWidgets.QLabel(
            "This wizard will help you setup a new game.\n\n"
            "Please make sure you saved and backed up your previous game before going through."
        )
        label.setWordWrap(True)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class ConclusionPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super(ConclusionPage, self).__init__(parent)

        self.setTitle("Conclusion")
        self.setSubTitle("\n\n")
        self.setPixmap(
            QtWidgets.QWizard.WizardPixmap.WatermarkPixmap,
            QtGui.QPixmap("./resources/ui/wizard/watermark2.png"),
        )

        self.label = QtWidgets.QLabel(
            "Click 'Finish' to generate and start the new game."
        )
        self.label.setWordWrap(True)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)
