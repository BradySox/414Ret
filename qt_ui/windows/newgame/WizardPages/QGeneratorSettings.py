"""The New Game wizard's Mods page.

Historically this page mixed the world-shaping generator options (carriers, navies,
budgets) with the installed-mods checklist; the generator options now live on the
Theater page (everything that shapes the world being built sits where you pick it),
leaving this page a single job: declare which mods this group's DCS installs carry.

Only mods the fork's factions actually consume are listed (ModSettings knows ~50;
the rest are deliberately retired/scrubbed content and stay permanently off).
Field names are unchanged, so the wizard's accept() reads the same fields.
"""

from __future__ import unicode_literals

from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Qt

from game.campaignloader import Campaign


class GeneratorOptions(QtWidgets.QWizardPage):
    def __init__(self, campaign: Campaign, parent=None):
        super().__init__(parent)

        self.setTitle("Mods")
        self.setSubTitle(
            "\nSelect the mods installed in your group's DCS. If your chosen "
            "factions carry their units, they'll appear in the campaign."
        )
        self.setPixmap(
            QtWidgets.QWizard.WizardPixmap.LogoPixmap,
            QtGui.QPixmap("./resources/ui/wizard/logo1.png"),
        )

        # --- Aircraft modules -----------------------------------------------------
        self.a4_skyhawk = QtWidgets.QCheckBox()
        self.registerField("a4_skyhawk", self.a4_skyhawk)
        self.fa_18efg = QtWidgets.QCheckBox()
        self.registerField("fa_18efg", self.fa_18efg)
        self.fa18ef_tanker = QtWidgets.QCheckBox()
        self.registerField("fa18ef_tanker", self.fa18ef_tanker)
        self.f22_raptor = QtWidgets.QCheckBox()
        self.registerField("f22_raptor", self.f22_raptor)
        self.f111c = QtWidgets.QCheckBox()
        self.registerField("f111c", self.f111c)
        self.ov10a_bronco = QtWidgets.QCheckBox()
        self.registerField("ov10a_bronco", self.ov10a_bronco)
        self.f4e_expanded_weapons = QtWidgets.QCheckBox()
        self.f4e_expanded_weapons.setToolTip(
            "Requires DSplayer's “Expanded F-4E Weapons Pack” mod (DCS user "
            "files) installed in the group's DCS.\n\n"
            "Adds AGM-78 Standard ARM and AGM-88C HARM stations to the Heatblur "
            "F-4E; with this on, the Phantom's auto-selected SEAD loadouts carry "
            "AGM-78B Standards instead of Shrikes, and a 4x HARM fit is one "
            "click away in the payload editor. Weapons pack only — the F-4E "
            "module itself is unaffected.\n\n"
            "https://www.digitalcombatsimulator.com/en/files/3338686/"
        )
        self.registerField("f4e_expanded_weapons", self.f4e_expanded_weapons)

        aircraft_pairs = [
            ("A-4E-C Skyhawk (v2.3.0)", self.a4_skyhawk),
            ("CJS FA-18E/F/G Super Hornet (v2.4.5.260501.RC1)", self.fa_18efg),
            (
                "CJS FA-18E/F Super Hornet Tanker (v2.4.5.260501.RC1)",
                self.fa18ef_tanker,
            ),
            (
                "Expanded F-4E Weapons Pack (DSplayer v1.0.11+)",
                self.f4e_expanded_weapons,
            ),
            ("F-22A Raptor (v2.0.0)", self.f22_raptor),
            ("F-111C Aardvark (Warpig Production v2.260208)", self.f111c),
            ("OV-10A Bronco", self.ov10a_bronco),
        ]

        # --- Asset packs ----------------------------------------------------------
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
        self.oh_6_vietnamassetpack = QtWidgets.QCheckBox()
        self.oh_6_vietnamassetpack.setToolTip(
            "Ground objects only (hooches, watchtowers, VC bunkers, bicycle "
            "logistics, gun trucks). The OH-6A helicopter itself is no longer "
            "carried by any faction."
        )
        self.registerField("oh_6_vietnamassetpack", self.oh_6_vietnamassetpack)
        self.vietnamwarvessels = QtWidgets.QCheckBox()
        self.registerField("vietnamwarvessels", self.vietnamwarvessels)

        pack_pairs = [
            (
                "CurrentHill Chinese Military Assets (1.1.4)",
                self.chinesemilitaryassetspack,
            ),
            ("CurrentHill Iran Military Assets (2.0.0)", self.iranmilitaryassetspack),
            (
                "CurrentHill Russian Military Assets (2.0.1)",
                self.russianmilitaryassetspack,
            ),
            (
                "CurrentHill Swedish Military Assets (1.10)",
                self.swedishmilitaryassetspack,
            ),
            ("CurrentHill UK Military Assets (1.1.2)", self.ukmilitaryassetspack),
            (
                "CurrentHill Ukraine Military Assets (1.1.1)",
                self.ukrainemilitaryassetspack,
            ),
            ("CurrentHill USA Military Assets (1.5.0)", self.usamilitaryassetspack),
            (
                "OH-6 Vietnam Asset Pack — ground objects (v1.2)",
                self.oh_6_vietnamassetpack,
            ),
            ("Vietnam War Vessels (v3.2.0 by TeTeT)", self.vietnamwarvessels),
        ]

        # --- Air defense ----------------------------------------------------------
        self.high_digit_sams = QtWidgets.QCheckBox()
        self.high_digit_sams.setToolTip(
            "Requires the High Digit SAMs — Ultimate Compilation (dcs-sams), "
            "v1.4.3 or newer.\n\n"
            "This is NOT the original Auranis HighDigitSAMs or other forks — they "
            "rename units (e.g. the S-300PS radars), so a mismatched build makes SAM "
            "sites spawn without their radars, with no error.\n\n"
            "https://github.com/dcs-sams/HighDigitSAMs-Ultimate-Compilation"
        )
        self.registerField("high_digit_sams", self.high_digit_sams)

        ad_pairs = [
            ("High Digit SAMs — Ultimate Compilation (v1.4.3+)", self.high_digit_sams),
        ]

        def group(title: str, pairs) -> QtWidgets.QGroupBox:
            box = QtWidgets.QGroupBox(title)
            grid = QtWidgets.QGridLayout()
            for row, (label, cb) in enumerate(pairs):
                label_widget = QtWidgets.QLabel(label)
                if cb.toolTip():
                    label_widget.setToolTip(cb.toolTip())
                grid.addWidget(label_widget, row, 0)
                grid.addWidget(cb, row, 1)
            grid.setColumnStretch(0, 1)
            box.setLayout(grid)
            return box

        hdsNote = QtWidgets.QLabel(
            "<p><b>High Digit SAMs</b> must be the dcs-sams "
            "“Ultimate Compilation” build (v1.4.3+). The original Auranis "
            "mod and other forks rename units (e.g. the S-300 radars) and will not "
            "work with these campaigns.</p>"
        )
        hdsNote.setWordWrap(True)
        hdsNote.setAlignment(Qt.AlignmentFlag.AlignCenter)

        left = QtWidgets.QVBoxLayout()
        left.addWidget(group("Aircraft modules", aircraft_pairs))
        left.addWidget(group("Air defense", ad_pairs))
        left.addStretch(1)
        right = QtWidgets.QVBoxLayout()
        right.addWidget(group("Asset packs", pack_pairs))
        right.addStretch(1)
        columns = QtWidgets.QHBoxLayout()
        columns.addLayout(left, 1)
        columns.addLayout(right, 1)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(columns)
        layout.addWidget(hdsNote)
        layout.addStretch(1)
        self.setLayout(layout)
        self.update_settings(campaign)

    def update_settings(self, campaign: Campaign) -> None:
        """Re-seed the mod checkboxes from the selected campaign's settings block."""
        s = campaign.settings
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
        self.f4e_expanded_weapons.setChecked(s.get("f4e_expanded_weapons", False))
        self.high_digit_sams.setChecked(s.get("high_digit_sams", False))
        self.oh_6_vietnamassetpack.setChecked(s.get("oh_6_vietnamassetpack", False))
        self.ov10a_bronco.setChecked(s.get("ov10a_bronco", False))
        self.vietnamwarvessels.setChecked(s.get("vietnamwarvessels", False))
        self.fa_18efg.setChecked(s.get("fa_18efg", False))
        self.fa18ef_tanker.setChecked(s.get("fa18ef_tanker", False))
