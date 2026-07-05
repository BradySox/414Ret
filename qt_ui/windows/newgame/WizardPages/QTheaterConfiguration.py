from __future__ import unicode_literals, annotations

from datetime import datetime
from typing import List, Optional

from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Signal, QDate, QPoint, QItemSelectionModel, Qt, QModelIndex
from PySide6.QtGui import QStandardItem, QPixmap, QStandardItemModel
from PySide6.QtWidgets import (
    QCheckBox,
    QTextBrowser,
    QTextEdit,
    QLabel,
    QListView,
    QAbstractItemView,
)

from game.campaignloader import Campaign
from game.campaignloader.campaign import DEFAULT_BUDGET
from qt_ui.liberation_install import get_dcs_install_directory
from qt_ui.widgets.QLiberationCalendar import QLiberationCalendar
from qt_ui.widgets.spinsliders import CurrencySpinner
from qt_ui.windows.newgame.WizardPages.QFactionSelection import FactionSelection
from qt_ui.windows.newgame.jinja_env import jinja_env

"""
Possible time periods for new games

    `Name`: daytime(day, month, year),

`Identifier` is the name that will appear in the menu
The object is a python datetime object
"""
TIME_PERIODS = {
    # Chronological, era seasons and historical scenarios interleaved.
    "WW2 - Winter [1944]": datetime(1944, 1, 1),
    "WW2 - Spring [1944]": datetime(1944, 4, 1),
    "WW2 - Summer [1944]": datetime(1944, 6, 1),
    "WW2 - Fall [1944]": datetime(1944, 10, 1),
    "Arab-Israeli War [1948]": datetime(1948, 5, 15),
    "Early Cold War - Winter [1952]": datetime(1952, 1, 1),
    "Early Cold War - Spring [1952]": datetime(1952, 4, 1),
    "Early Cold War - Summer [1952]": datetime(1952, 6, 1),
    "Early Cold War - Fall [1952]": datetime(1952, 10, 1),
    "6 days war [1967]": datetime(1967, 6, 5),
    "Cold War - Winter [1970]": datetime(1970, 1, 1),
    "Cold War - Spring [1970]": datetime(1970, 4, 1),
    "Cold War - Summer [1970]": datetime(1970, 6, 1),
    "Cold War - Fall [1970]": datetime(1970, 10, 1),
    "Yom Kippour War [1973]": datetime(1973, 10, 6),
    "First Lebanon War [1982]": datetime(1982, 6, 6),
    "Late Cold War - Winter [1985]": datetime(1985, 1, 1),
    "Late Cold War - Spring [1985]": datetime(1985, 4, 1),
    "Late Cold War - Summer [1985]": datetime(1985, 6, 1),
    "Late Cold War - Fall [1985]": datetime(1985, 10, 1),
    "Gulf War - Winter [1990]": datetime(1990, 1, 1),
    "Gulf War - Spring [1990]": datetime(1990, 4, 1),
    "Gulf War - Summer [1990]": datetime(1990, 6, 1),
    "Gulf War - Fall [1990]": datetime(1990, 10, 1),
    "Mid-90s - Winter [1995]": datetime(1995, 1, 1),
    "Mid-90s - Spring [1995]": datetime(1995, 4, 1),
    "Mid-90s - Summer [1995]": datetime(1995, 6, 1),
    "Mid-90s - Fall [1995]": datetime(1995, 10, 1),
    "Georgian War [2008]": datetime(2008, 8, 7),
    "Modern - Winter [2010]": datetime(2010, 1, 1),
    "Modern - Spring [2010]": datetime(2010, 4, 1),
    "Modern - Summer [2010]": datetime(2010, 6, 1),
    "Modern - Fall [2010]": datetime(2010, 10, 1),
    "Syrian War [2011]": datetime(2011, 3, 15),
}

#: The preset selected when no campaign recommends a date. By name, not a brittle
#: positional index into the (now chronologically sorted) table.
DEFAULT_TIME_PERIOD = "Mid-90s - Summer [1995]"


class BudgetInputs(QtWidgets.QGridLayout):
    """A labelled slider + spinner pair for a starting budget."""

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


class TheaterConfiguration(QtWidgets.QWizardPage):
    campaign_selected = Signal(Campaign)

    def __init__(
        self,
        campaigns: List[Campaign],
        faction_selection: FactionSelection,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.faction_selection = faction_selection

        # The active era-shell filter (set from the Intro "Vietnam" card via the
        # vietnamMode field in initializePage); None lists every campaign.
        self._era_filter: Optional[str] = None

        self.setTitle("Theater configuration")
        self.setSubTitle("\nChoose a terrain and time period for this game.")
        self.setPixmap(
            QtWidgets.QWizard.WizardPixmap.LogoPixmap,
            QtGui.QPixmap("./resources/ui/wizard/logo1.png"),
        )

        self.setPixmap(
            QtWidgets.QWizard.WizardPixmap.WatermarkPixmap,
            QtGui.QPixmap("./resources/ui/wizard/watermark3.png"),
        )

        # List of campaigns
        self.show_incompatible_campaigns_checkbox = QCheckBox(
            text="Show incompatible campaigns"
        )
        show_incompatible_campaigns_checkbox = self.show_incompatible_campaigns_checkbox
        show_incompatible_campaigns_checkbox.setChecked(False)
        self.campaignList = QCampaignList(
            campaigns, show_incompatible_campaigns_checkbox.isChecked()
        )
        show_incompatible_campaigns_checkbox.toggled.connect(
            lambda checked: self.campaignList.setup_content(
                show_incompatible=checked, era=self._era_filter
            )
        )
        self.registerField("selectedCampaign", self.campaignList)

        # Faction description
        self.campaignMapDescription = QTextBrowser()
        self.campaignMapDescription.setReadOnly(True)
        self.campaignMapDescription.setOpenExternalLinks(True)
        self.campaignMapDescription.setMaximumHeight(200)

        self.performanceText = QTextEdit("")
        self.performanceText.setReadOnly(True)
        self.performanceText.setMaximumHeight(90)

        # Campaign settings
        mapSettingsGroup = QtWidgets.QGroupBox("Map Settings")
        mapSettingsLayout = QtWidgets.QGridLayout()
        self.invertMap = QtWidgets.QCheckBox()
        self.invertMap.stateChanged.connect(self.on_invert_map)
        self.registerField("invertMap", self.invertMap)
        mapSettingsLayout.addWidget(QtWidgets.QLabel("Invert Map"), 0, 0)
        mapSettingsLayout.addWidget(self.invertMap, 0, 1)
        self.advanced_iads = QtWidgets.QCheckBox()
        self.registerField("advanced_iads", self.advanced_iads)
        self.iads_label = QtWidgets.QLabel("Advanced IADS (MANTIS)")
        mapSettingsLayout.addWidget(self.iads_label, 1, 0)
        mapSettingsLayout.addWidget(self.advanced_iads, 1, 1)
        mapSettingsGroup.setLayout(mapSettingsLayout)

        # Forces & budget (moved here from the old Generator page: everything that
        # shapes the world being built belongs on the page where you pick it. The
        # values re-seed from each campaign's settings/recommendations on select.)
        forcesGroup = QtWidgets.QGroupBox("Forces && Budget")
        forcesLayout = QtWidgets.QGridLayout()
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

        forcesLayout.addWidget(QtWidgets.QLabel("No Aircraft Carriers"), 0, 0)
        forcesLayout.addWidget(self.no_carrier, 0, 1)
        forcesLayout.addWidget(QtWidgets.QLabel("No LHA"), 1, 0)
        forcesLayout.addWidget(self.no_lha, 1, 1)
        forcesLayout.addWidget(QtWidgets.QLabel("No Player Navy"), 0, 2)
        forcesLayout.addWidget(self.no_player_navy, 0, 3)
        forcesLayout.addWidget(QtWidgets.QLabel("No Enemy Navy"), 1, 2)
        forcesLayout.addWidget(self.no_enemy_navy, 1, 3)
        squadrons_label = QtWidgets.QLabel("Squadrons start at full capacity")
        squadrons_label.setToolTip(
            "Campaign will start with all squadrons at full strength "
            "given enough room at the airfield in question.\n"
            "Each squadron's capacity can be defined during Air Wing Configuration."
        )
        forcesLayout.addWidget(squadrons_label, 2, 0)
        forcesLayout.addWidget(self.squadrons_start_full, 2, 1)

        self.player_budget = BudgetInputs("Player starting budget", DEFAULT_BUDGET)
        self.registerField("starting_money", self.player_budget.starting_money)
        forcesLayout.addLayout(self.player_budget, 3, 0, 1, 2)
        self.enemy_budget = BudgetInputs("Enemy starting budget", DEFAULT_BUDGET)
        self.registerField("enemy_starting_money", self.enemy_budget.starting_money)
        forcesLayout.addLayout(self.enemy_budget, 3, 2, 1, 2)
        forcesGroup.setLayout(forcesLayout)

        # Time Period
        timeGroup = QtWidgets.QGroupBox("Time Period")
        timePeriod = QtWidgets.QLabel("Start date :")
        timePeriodSelect = QtWidgets.QComboBox()
        timePeriodPresetLabel = QLabel("Use preset :")
        timePeriodPreset = QtWidgets.QCheckBox()
        timePeriodPreset.setChecked(True)
        self.calendar = QLiberationCalendar()
        self.calendar.setSelectedDate(QDate())
        self.calendar.setDisabled(True)

        def onTimePeriodChanged():
            self.calendar.setSelectedDate(
                list(TIME_PERIODS.values())[timePeriodSelect.currentIndex()]
            )

        timePeriodSelect.currentTextChanged.connect(onTimePeriodChanged)

        for r in TIME_PERIODS:
            timePeriodSelect.addItem(r)
        timePeriod.setBuddy(timePeriodSelect)
        timePeriodSelect.setCurrentText(DEFAULT_TIME_PERIOD)

        def onTimePeriodCheckboxChanged():
            if timePeriodPreset.isChecked():
                self.calendar.setDisabled(True)
                timePeriodSelect.setDisabled(False)
                onTimePeriodChanged()
            else:
                self.calendar.setDisabled(False)
                timePeriodSelect.setDisabled(True)

        timePeriodPreset.stateChanged.connect(onTimePeriodCheckboxChanged)

        # Bind selection method for campaign selection
        def on_campaign_selected():
            template = jinja_env.get_template("campaigntemplate_EN.j2")
            template_perf = jinja_env.get_template(
                "campaign_performance_template_EN.j2"
            )
            campaign = self.campaignList.selected_campaign
            self.setField("selectedCampaign", campaign)
            if campaign is None:
                self.campaignMapDescription.setText("No campaign selected")
                self.performanceText.setText("No campaign selected")
                return

            self.campaignMapDescription.setText(template.render({"campaign": campaign}))
            self.faction_selection.setDefaultFactions(campaign)
            if self.invertMap.isChecked():
                self.on_invert_map()
            self.performanceText.setText(
                template_perf.render({"performance": campaign.performance})
            )

            # Re-seed the forces/budget group from the selected campaign.
            s = campaign.settings
            self.no_carrier.setChecked(s.get("no_carrier", False))
            self.no_lha.setChecked(s.get("no_lha", False))
            self.no_player_navy.setChecked(s.get("no_player_navy", False))
            self.no_enemy_navy.setChecked(s.get("no_enemy_navy", False))
            self.squadrons_start_full.setChecked(s.get("squadron_start_full", False))
            self.player_budget.starting_money.setValue(
                campaign.recommended_player_money
            )
            self.enemy_budget.starting_money.setValue(campaign.recommended_enemy_money)

            if (start_date := campaign.recommended_start_date) is not None:
                self.calendar.setSelectedDate(
                    QDate(start_date.year, start_date.month, start_date.day)
                )
                timePeriodPreset.setChecked(False)
            else:
                timePeriodPreset.setChecked(True)
            self.advanced_iads.setEnabled(campaign.advanced_iads)
            self.iads_label.setEnabled(campaign.advanced_iads)
            self.advanced_iads.setChecked(campaign.advanced_iads)
            if not campaign.advanced_iads:
                self.advanced_iads.setToolTip(
                    "Advanced IADS is not supported by this campaign"
                )
            else:
                self.advanced_iads.setToolTip(
                    "Networked air defenses driven by the MANTIS IADS engine: SAM "
                    "sites hold dark until cued by EWR/AWACS, and killing a base's "
                    "C2/comms/power degrades its net."
                )

            self.campaign_selected.emit(campaign)

        self.campaignList.selectionModel().setCurrentIndex(
            self.campaignList.indexAt(QPoint(1, 1)),
            QItemSelectionModel.SelectionFlag.Rows,
        )

        self.campaignList.selectionModel().selectionChanged.connect(
            on_campaign_selected
        )
        on_campaign_selected()

        docsText = QtWidgets.QLabel(
            "<p>Campaign briefings and handbooks live on the "
            '<a href="https://github.com/bradyccox/414Ret/wiki"><span style="color:#FFFFFF;">414th wiki</span></a>. '
            "Want more? "
            '<a href="https://github.com/dcs-retribution/dcs-retribution/wiki/Community-campaigns"><span style="color:#FFFFFF;">Play a community campaign</span></a> '
            'or <a href="https://github.com/dcs-retribution/dcs-retribution/wiki/Custom-Campaigns"><span style="color:#FFFFFF;">create your own</span></a>.'
            "</p>"
        )
        docsText.setAlignment(Qt.AlignmentFlag.AlignCenter)
        docsText.setOpenExternalLinks(True)

        # Register fields
        self.registerField("timePeriod", timePeriodSelect)
        self.registerField("usePreset", timePeriodPreset)

        timeGroupLayout = QtWidgets.QGridLayout()
        timeGroupLayout.addWidget(timePeriodPresetLabel, 0, 0)
        timeGroupLayout.addWidget(timePeriodPreset, 0, 1)
        timeGroupLayout.addWidget(timePeriod, 1, 0)
        timeGroupLayout.addWidget(timePeriodSelect, 1, 1)
        timeGroupLayout.addWidget(self.calendar, 0, 2, 3, 1)
        timeGroup.setLayout(timeGroupLayout)

        layout = QtWidgets.QGridLayout()
        layout.setColumnMinimumWidth(0, 20)
        layout.addWidget(self.campaignList, 0, 0, 5, 1)
        layout.addWidget(show_incompatible_campaigns_checkbox, 5, 0, 1, 1)
        layout.addWidget(docsText, 6, 0, 1, 1)
        layout.addWidget(self.campaignMapDescription, 0, 1, 1, 1)
        layout.addWidget(self.performanceText, 1, 1, 1, 1)
        layout.addWidget(mapSettingsGroup, 2, 1, 1, 1)
        layout.addWidget(forcesGroup, 3, 1, 1, 1)
        layout.addWidget(timeGroup, 4, 1, 3, 1)
        self.setLayout(layout)

    def initializePage(self) -> None:
        super().initializePage()
        # The Intro page's "Campaign type" card drives which list we present. The
        # blank-canvas (campaign maker) path only uses the selected campaign for its
        # terrain, so it gets a clean terrain picker; the "Vietnam" card filters the
        # campaign list to era: vietnam; otherwise the full included-campaign list.
        # initializePage fires each time the user arrives from the Introduction page,
        # so changing the radio re-applies the mode.
        wizard = self.wizard()
        terrain_only = bool(wizard.field("blankCanvas")) if wizard else False
        vietnam = bool(wizard.field("vietnamMode")) if wizard else False
        self._set_mode(terrain_only=terrain_only, vietnam=vietnam)

    def _set_mode(self, terrain_only: bool, vietnam: bool = False) -> None:
        self._era_filter = "vietnam" if (vietnam and not terrain_only) else None
        if terrain_only:
            self.setTitle("Theater")
            self.setSubTitle(
                "\nPick a terrain. Every airfield starts neutral — you'll paint "
                "ownership and place defenses on the map yourself."
            )
            self.campaignList.setup_terrain_content()
        elif vietnam:
            self.setTitle("Vietnam")
            self.setSubTitle(
                "\nChoose a Vietnam-era campaign. The period mechanics (Arc Light, "
                "AAA flak, era weapons) and recommended factions pre-load on select."
            )
            self.campaignList.setup_content(
                self.show_incompatible_campaigns_checkbox.isChecked(), era="vietnam"
            )
        else:
            self.setTitle("Theater configuration")
            self.setSubTitle("\nChoose a terrain and time period for this game.")
            self.campaignList.setup_content(
                self.show_incompatible_campaigns_checkbox.isChecked()
            )
        # Campaign-specific panels are meaningless for a blank canvas.
        self.campaignMapDescription.setVisible(not terrain_only)
        self.performanceText.setVisible(not terrain_only)
        self.show_incompatible_campaigns_checkbox.setVisible(not terrain_only)

    def on_invert_map(self) -> None:
        blue = self.faction_selection.blueFactionSelect.currentIndex()
        red = self.faction_selection.redFactionSelect.currentIndex()
        self.faction_selection.blueFactionSelect.setCurrentIndex(red)
        self.faction_selection.redFactionSelect.setCurrentIndex(blue)
        self.faction_selection.updateUnitRecap()


class QCampaignItem(QStandardItem):
    def __init__(self, campaign: Campaign) -> None:
        super(QCampaignItem, self).__init__()
        self.setData(campaign, QCampaignList.CampaignRole)

        # Define terrain icon path from the DCS installation directory by default
        dcs_path = get_dcs_install_directory()
        icon_path = dcs_path / campaign.menu_thumbnail_dcs_relative_path

        # If the path does not exist (user does not have the terrain installed),
        # use the old icons as fallback to avoid an ugly campaign list with missing icons
        if not icon_path.exists():
            icon_path = campaign.fallback_icon_path

        self.setIcon(QtGui.QIcon(QPixmap(str(icon_path))))
        self.setEditable(False)
        if campaign.is_compatible:
            name = campaign.name
        else:
            name = f"[INCOMPATIBLE] {campaign.name}"
        self.setText(name)


class QCampaignList(QListView):
    CampaignRole = Qt.ItemDataRole.UserRole

    def __init__(self, campaigns: list[Campaign], show_incompatible: bool) -> None:
        super(QCampaignList, self).__init__()
        self.campaign_model = QStandardItemModel(self)
        self.setModel(self.campaign_model)
        self.setMinimumWidth(250)
        self.setMinimumHeight(350)
        self.campaigns = campaigns
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setup_content(show_incompatible)

    @property
    def selected_campaign(self) -> Optional[Campaign]:
        return self.currentIndex().data(QCampaignList.CampaignRole)

    def setup_content(self, show_incompatible: bool, era: Optional[str] = None) -> None:
        self.selectionModel().blockSignals(True)
        try:
            self.campaign_model.clear()
            for campaign in self.campaigns:
                if not campaign.matches_era(era):
                    continue
                if show_incompatible or campaign.is_compatible:
                    item = QCampaignItem(campaign)
                    self.campaign_model.appendRow(item)
        finally:
            self.selectionModel().blockSignals(False)

        self.selectionModel().setCurrentIndex(
            self.campaign_model.index(0, 0, QModelIndex()),
            QItemSelectionModel.SelectionFlag.Select,
        )

    def setup_terrain_content(self) -> None:
        """Populate one row per unique terrain for the blank-canvas terrain picker.

        Each row carries a representative compatible campaign for that terrain (the
        blank-canvas flow only uses it for ``data["theater"]`` + default factions)
        but is labelled by the terrain name, so the user picks a map rather than a
        hand-built campaign.
        """
        self.selectionModel().blockSignals(True)
        try:
            self.campaign_model.clear()
            seen: set[str] = set()
            for campaign in self.campaigns:
                if not campaign.is_compatible:
                    continue
                terrain = campaign.data.get("theater")
                if not terrain or terrain in seen:
                    continue
                seen.add(terrain)
                item = QCampaignItem(campaign)
                item.setText(terrain)
                self.campaign_model.appendRow(item)
        finally:
            self.selectionModel().blockSignals(False)

        self.selectionModel().setCurrentIndex(
            self.campaign_model.index(0, 0, QModelIndex()),
            QItemSelectionModel.SelectionFlag.Select,
        )
