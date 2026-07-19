from __future__ import unicode_literals

import logging

from PySide6 import QtGui, QtWidgets

from game.campaignloader.campaign import Campaign
from game.campaignloader.campaignairwingconfig import CampaignAirWingConfig
from game.campaignloader.blanktheatergen import generate_blank_theater
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
            f4e_expanded_weapons=self.field("f4e_expanded_weapons"),
            f22_raptor=self.field("f22_raptor"),
            f111c=self.field("f111c"),
            high_digit_sams=self.field("high_digit_sams"),
            ov10a_bronco=self.field("ov10a_bronco"),
            vietnamwarvessels=self.field("vietnamwarvessels"),
            chinesemilitaryassetspack=self.field("chinesemilitaryassetspack"),
            iranmilitaryassetspack=self.field("iranmilitaryassetspack"),
            russianmilitaryassetspack=self.field("russianmilitaryassetspack"),
            swedishmilitaryassetspack=self.field("swedishmilitaryassetspack"),
            usamilitaryassetspack=self.field("usamilitaryassetspack"),
            ukmilitaryassetspack=self.field("ukmilitaryassetspack"),
            ukrainemilitaryassetspack=self.field("ukrainemilitaryassetspack"),
            fa_18efg=self.field("fa_18efg"),
            fa18ef_tanker=self.field("fa18ef_tanker"),
        )

        blue_faction = self.faction_selection_page.selected_blue_faction
        red_faction = self.faction_selection_page.selected_red_faction

        logging.info("New campaign blue faction: %s", blue_faction.name)
        logging.info("New campaign red faction: %s", red_faction.name)

        blank_canvas = bool(self.field("blankCanvas"))
        if blank_canvas:
            # Campaign maker: ignore the .miz and generate an ALL-NEUTRAL theater of
            # the selected terrain. The player then paints base ownership on the live
            # map and hits "Finalize campaign", which rebuilds from only the painted
            # bases (see finalize_blank_canvas). No air-wing dialog yet — bases aren't
            # owned until finalize.
            theater = generate_blank_theater(
                campaign.data["theater"],
                all_neutral=True,
                advanced_iads=generator_settings.advanced_iads,
            )
            air_wing_config = CampaignAirWingConfig.empty()
            campaign_name = f"Blank canvas — {theater.terrain.name}"
        else:
            theater = campaign.load_theater(generator_settings.advanced_iads)
            air_wing_config = campaign.load_air_wing_config(theater)
            campaign_name = campaign.name

        logging.info("New campaign theater: %s", theater.terrain.name)

        settings = self.settings_page.settings_widget.settings

        generator = GameGenerator(
            blue_faction,
            red_faction,
            theater,
            air_wing_config,
            settings,
            generator_settings,
            mod_settings,
            campaign_name=campaign_name,
        )
        self.generatedGame = generator.generate()

        if blank_canvas:
            self.generatedGame.blank_canvas_setup = True
        else:
            AirWingConfigurationDialog(
                self.generatedGame,
                generator.generator_settings.squadrons_start_full,
                self,
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

        # Campaign type: a prepared campaign vs a blank canvas to build by hand.
        # The blank-canvas radio drives accept()'s branch via the "blankCanvas" field.
        type_group = QtWidgets.QGroupBox("Campaign type")
        self.included_radio = QtWidgets.QRadioButton("Play an included campaign")
        self.included_radio.setChecked(True)
        included_desc = QtWidgets.QLabel(
            "Start from a hand-built campaign with preset front lines, air "
            "defenses, and objectives."
        )
        included_desc.setWordWrap(True)
        included_desc.setIndent(22)

        # The "Vietnam" card: filters the next page's campaign list to era: vietnam
        # and leans on those campaigns' own settings/faction pre-seed. It is still an
        # included-campaign game (accept() takes the normal branch), so the only thing
        # the vietnamMode field changes is which campaigns are shown.
        self.vietnam_radio = QtWidgets.QRadioButton("Vietnam")
        self.registerField("vietnamMode", self.vietnam_radio)
        vietnam_desc = QtWidgets.QLabel(
            "Fly the air war over Vietnam: only Vietnam-era campaigns (1968 Yankee "
            "Station, Velvet Thunder, Red Flag 81-2), with Arc Light, AAA flak, "
            "period weapons, and era taskings (MiGCAP, Alpha Strike, Sandy) "
            "pre-loaded."
        )
        vietnam_desc.setWordWrap(True)
        vietnam_desc.setIndent(22)

        self.blank_canvas_radio = QtWidgets.QRadioButton(
            "Build your own (blank canvas — experimental)"
        )
        self.registerField("blankCanvas", self.blank_canvas_radio)
        blank_desc = QtWidgets.QLabel(
            "Start from an empty map: every airfield on the terrain, split "
            "between sides, with no preset units. You assign ownership and place "
            "SAMs, armor, and strike targets by hand. Pick the terrain on the next "
            "page — the campaign you select there only sets the map."
        )
        blank_desc.setWordWrap(True)
        blank_desc.setIndent(22)

        type_layout = QtWidgets.QVBoxLayout()
        type_layout.addWidget(self.included_radio)
        type_layout.addWidget(included_desc)
        type_layout.addSpacing(10)
        type_layout.addWidget(self.vietnam_radio)
        type_layout.addWidget(vietnam_desc)
        type_layout.addSpacing(10)
        type_layout.addWidget(self.blank_canvas_radio)
        type_layout.addWidget(blank_desc)
        type_group.setLayout(type_layout)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label)
        layout.addSpacing(14)
        layout.addWidget(type_group)
        layout.addStretch(1)
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
