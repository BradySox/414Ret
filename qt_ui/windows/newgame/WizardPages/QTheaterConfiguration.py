from __future__ import unicode_literals, annotations

from datetime import datetime
from typing import List, Optional, Tuple

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
from game.theater.theaterloader import TheaterLoader
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
        self.show_incompatible_campaigns_checkbox.setChecked(False)

        # Filter and Sort Controls
        self.filter_sort_group = QtWidgets.QGroupBox("Filter && Sort Campaigns")
        filter_sort_group = self.filter_sort_group
        filter_sort_layout = QtWidgets.QGridLayout()
        filter_sort_layout.setColumnStretch(1, 1)

        # Get unique values for filters
        all_versions = set()
        all_maps = set()

        for campaign in campaigns:
            all_versions.add(campaign.version)
            all_maps.add(campaign.data.get("theater", ""))

        # Version filter
        filter_sort_layout.addWidget(QtWidgets.QLabel("Version:"), 0, 0)
        self.version_filter = QtWidgets.QComboBox()
        self.version_filter.addItem("All Versions", None)
        for version in sorted(all_versions, reverse=True):  # Newest first
            if version != (0, 0):  # Skip unknown versions
                self.version_filter.addItem(f"v{version[0]}.{version[1]}", version)
        self.version_filter.currentTextChanged.connect(self.on_filter_changed)
        filter_sort_layout.addWidget(self.version_filter, 0, 1)

        # Map filter
        filter_sort_layout.addWidget(QtWidgets.QLabel("Map:"), 1, 0)
        self.map_filter = QtWidgets.QComboBox()
        self.map_filter.addItem("All Maps", "")
        # Label each map with the theater's own name, not the campaign's raw
        # `theater:` key. The key is a directory name, so the list read
        # "MarianaIslands" against "MarianasWWII" -- two maps of the same place,
        # side by side, near-indistinguishable. The item DATA stays the key, which
        # is what currentData() filters on.
        for map_name in sorted(all_maps, key=_map_label):
            if map_name:  # Skip empty map names
                self.map_filter.addItem(_map_label(map_name), map_name)
        self.map_filter.currentTextChanged.connect(self.on_filter_changed)
        filter_sort_layout.addWidget(self.map_filter, 1, 1)

        # Sort option
        filter_sort_layout.addWidget(QtWidgets.QLabel("Sort by:"), 2, 0)
        self.sort_option = QtWidgets.QComboBox()
        self.sort_option.addItems(["Name", "Version", "Performance"])
        self.sort_option.currentTextChanged.connect(self.on_filter_changed)
        filter_sort_layout.addWidget(self.sort_option, 2, 1)

        filter_sort_layout.addWidget(
            self.show_incompatible_campaigns_checkbox, 3, 0, 1, 2
        )

        filter_sort_group.setLayout(filter_sort_layout)

        self.campaignList = QCampaignList(
            campaigns, self.show_incompatible_campaigns_checkbox.isChecked()
        )
        self.show_incompatible_campaigns_checkbox.toggled.connect(
            self.on_filter_changed
        )

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
        layout.addWidget(filter_sort_group, 0, 0, 1, 1)
        layout.addWidget(self.campaignList, 1, 0, 5, 1)
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
        # "Vietnam" card filters the campaign list to era: vietnam; otherwise the
        # full included-campaign list. initializePage fires each time the user
        # arrives from the Introduction page, so changing the radio re-applies the
        # mode.
        wizard = self.wizard()
        vietnam = bool(wizard.field("vietnamMode")) if wizard else False
        self._set_mode(vietnam=vietnam)

    def _set_mode(self, vietnam: bool = False) -> None:
        self._era_filter = "vietnam" if vietnam else None
        if vietnam:
            self.setTitle("Vietnam")
            self.setSubTitle(
                "\nChoose a Vietnam-era campaign. The period mechanics (Arc "
                "Light, AAA flak, era weapons) and recommended factions "
                "pre-load on select."
            )
        else:
            self.setTitle("Theater configuration")
            self.setSubTitle("\nChoose a terrain and time period for this game.")
        # The era shell is just one more filter criterion, so it flows through
        # the same filter/sort pipeline as version/map (upstream #908) rather
        # than a parallel setup_content argument.
        self.on_filter_changed()

    def on_filter_changed(self) -> None:
        """Handle changes in filter or sort options."""
        version_filter = self.version_filter.currentData()
        map_filter = self.map_filter.currentData() or ""
        sort_option = self.sort_option.currentText()

        # Apply filters and sort
        self.campaignList.set_filters(version_filter, map_filter, self._era_filter)
        self.campaignList.set_sort_option(sort_option)
        self.campaignList.setup_content(
            show_incompatible=self.show_incompatible_campaigns_checkbox.isChecked()
        )

    def on_invert_map(self) -> None:
        blue = self.faction_selection.blueFactionSelect.currentIndex()
        red = self.faction_selection.redFactionSelect.currentIndex()
        self.faction_selection.blueFactionSelect.setCurrentIndex(red)
        self.faction_selection.redFactionSelect.setCurrentIndex(blue)
        self.faction_selection.updateUnitRecap()


def _map_label(theater_key: str) -> str:
    """The theater's display name, falling back to the raw key if it has no
    descriptor (a campaign naming a theater this build does not ship)."""
    if not theater_key:
        return ""
    try:
        return TheaterLoader(theater_key.lower()).display_name
    except (OSError, KeyError):
        return theater_key


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

        # Filter and sort settings
        self.current_version_filter: Optional[Tuple[int, int]] = None
        self.current_map_filter = ""
        self.current_era_filter: Optional[str] = None
        self.current_sort_option = "Name"

        self.setup_content(show_incompatible)

    @property
    def selected_campaign(self) -> Optional[Campaign]:
        return self.currentIndex().data(QCampaignList.CampaignRole)

    def set_filters(
        self,
        version_filter: Optional[Tuple[int, int]] = None,
        map_filter: str = "",
        era: Optional[str] = None,
    ) -> None:
        """Set the filter criteria for campaigns."""
        self.current_version_filter = version_filter
        self.current_map_filter = map_filter
        self.current_era_filter = era

    def set_sort_option(self, sort_option: str) -> None:
        """Set the sort option for campaigns."""
        self.current_sort_option = sort_option

    def _filter_campaign(self, campaign: Campaign) -> bool:
        """Check if a campaign passes all current filters."""
        if (
            self.current_version_filter is not None
            and campaign.version != self.current_version_filter
        ):
            return False

        if self.current_map_filter and self.current_map_filter != campaign.data.get(
            "theater", ""
        ):
            return False

        # The era shell (the Intro page's "Vietnam" card) is just another filter.
        if not campaign.matches_era(self.current_era_filter):
            return False

        return True

    def _sort_campaigns(self, campaigns: list[Campaign]) -> list[Campaign]:
        """Sort campaigns based on current sort option."""
        if self.current_sort_option == "Name":
            return sorted(campaigns, key=lambda c: c.name.lower())
        elif self.current_sort_option == "Version":
            return sorted(
                campaigns, key=lambda c: c.version, reverse=True
            )  # Newest first
        elif self.current_sort_option == "Performance":
            return sorted(campaigns, key=lambda c: c.performance)
        else:
            return campaigns

    def setup_content(self, show_incompatible: bool = False) -> None:
        self.selectionModel().blockSignals(True)
        try:
            self.campaign_model.clear()

            # Filter campaigns
            filtered_campaigns = []
            for campaign in self.campaigns:
                if (
                    show_incompatible or campaign.is_compatible
                ) and self._filter_campaign(campaign):
                    filtered_campaigns.append(campaign)

            # Sort campaigns
            sorted_campaigns = self._sort_campaigns(filtered_campaigns)

            # Add to model
            for campaign in sorted_campaigns:
                item = QCampaignItem(campaign)
                self.campaign_model.appendRow(item)
        finally:
            self.selectionModel().blockSignals(False)

        # Select first item if available
        if self.campaign_model.rowCount() > 0:
            self.selectionModel().setCurrentIndex(
                self.campaign_model.index(0, 0, QModelIndex()),
                QItemSelectionModel.SelectionFlag.Select,
            )
