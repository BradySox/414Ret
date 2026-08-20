# FA-18C — manual page index

Page numbers are **1-based physical PDF pages**. They may not match the
printed page numbers.

Extract a section as text:

```bash
pdftotext -f 63 -l 73 "references/manuals/FA-18C/<file>.pdf" -
```

The Read tool renders PDF pages as images via `pdftoppm`, which is often not
installed; `pdftotext` is, and text is cheaper. If Read does work, the same
numbers go in its `pages` parameter.

PDFs live in this folder and are gitignored. See [README.md](../README.md).

## DCS FA-18C Early Access Guide EN.pdf

424 pages · index source: 412 PDF bookmarks

| Section | Pages | Len |
|---|---|---|
| Introduction | 2–2 | 1 |
| Table of Contents | 3–10 | 8 |
| Latest Changes | 11–12 | 2 |
| DCS: WORLD FUNDAMENTALS | 13–23 | 11 |
| THE F/A-18C | 24–91 | 68 |
| &nbsp;&nbsp;· Aircraft History | 25–29 | 5 |
| &nbsp;&nbsp;· Weapons & Munitions | 30–37 | 8 |
| &nbsp;&nbsp;· Cockpit Overview | 38–70 | 33 |
| &nbsp;&nbsp;· Control Stick & Throttles | 71–76 | 6 |
| &nbsp;&nbsp;· Heads-Up Display (HUD) | 77–78 | 2 |
| &nbsp;&nbsp;· Digital Display Indicator (DDI) & Advanced Multi-Purpose Color Display (AMPCD) Pages | 79–91 | 13 |
| PROCEDURES | 92–113 | 22 |
| &nbsp;&nbsp;· Cold Start | 93–98 | 6 |
| &nbsp;&nbsp;· Airfield Taxi | 99–99 | 1 |
| &nbsp;&nbsp;· Airfield Takeoff | 100–100 | 1 |
| &nbsp;&nbsp;· Airfield VFR Landing | 101–103 | 3 |
| &nbsp;&nbsp;· Aircraft Carrier Taxi | 104–106 | 3 |
| &nbsp;&nbsp;· Aircraft Carrier Launch | 107–107 | 1 |
| &nbsp;&nbsp;· Case 1 Carrier Recovery | 108–113 | 6 |
| NAVIGATION | 114–151 | 38 |
| &nbsp;&nbsp;· Navigation | 115–120 | 6 |
| &nbsp;&nbsp;· Waypoint Navigation | 121–135 | 15 |
| &nbsp;&nbsp;· TACAN Navigation | 136–138 | 3 |
| &nbsp;&nbsp;· DATA Option Sublevel | 139–142 | 4 |
| &nbsp;&nbsp;· Automatic Direction Finder (ADF) Navigation | 143–143 | 1 |
| &nbsp;&nbsp;· Additional HSI Symbology | 144–145 | 2 |
| &nbsp;&nbsp;· Autopilot Relief Modes | 146–149 | 4 |
| &nbsp;&nbsp;· Instrument Carrier Landing System (ICLS) | 150–151 | 2 |
| RADIO COMMUNICATIONS | 152–155 | 4 |
| APG-73 FIRE CONTROL RADAR | 156–198 | 43 |
| &nbsp;&nbsp;· Air-to-Air Radar | 157–179 | 23 |
| &nbsp;&nbsp;· AZ/EL Format | 180–185 | 6 |
| &nbsp;&nbsp;· Air-to-Ground Radar | 186–198 | 13 |
| TACTICAL DATALINK | 199–215 | 17 |
| &nbsp;&nbsp;· Tactical Net Datalink (TNDL) | 200–203 | 4 |
| &nbsp;&nbsp;· Situational Awareness (SA) Page | 204–215 | 12 |
| ADVANCED TARGETING FORWARD LOOKING INFRARED POD | 216–232 | 17 |
| &nbsp;&nbsp;· AN/ASQ-228 ATFLIR | 217–219 | 3 |
| &nbsp;&nbsp;· Air-to-Ground Mode | 220–230 | 11 |
| &nbsp;&nbsp;· Air-to-Air Mode | 231–232 | 2 |
| LITENING II TARGETING POD | 233–246 | 14 |
| &nbsp;&nbsp;· AN/AAQ-28 Litening II | 234–236 | 3 |
| &nbsp;&nbsp;· Air-to-Ground (A/G) Mode | 237–243 | 7 |
| &nbsp;&nbsp;· Air to Air (AA) Page | 244–246 | 3 |
| JOINT HELMET-MOUNTED CUEING SYSTEM | 247–259 | 13 |
| &nbsp;&nbsp;· Helmet Mounted Display (HMD) | 248–259 | 12 |
| AIR-TO-AIR EMPLOYMENT | 260–297 | 38 |
| &nbsp;&nbsp;· Air-to-Air Master Mode | 261–261 | 1 |
| &nbsp;&nbsp;· M61A1 Gun, Air-to-Air Mode (A/A GUNS) | 262–270 | 9 |
| &nbsp;&nbsp;· AIM-9 Sidewinder Air-to-Air Missile | 271–278 | 8 |
| &nbsp;&nbsp;· AIM-7 Sparrow Air-to-Air Missile | 279–287 | 9 |
| &nbsp;&nbsp;· AIM-120 Advanced Medium Range Air-to-Air Missile (AMRAAM) | 288–297 | 10 |
| AIR-TO-GROUND EMPLOYMENT | 298–405 | 108 |
| &nbsp;&nbsp;· Air-to-Ground Master Mode | 299–299 | 1 |
| &nbsp;&nbsp;· Air-to-Ground Markpoints | 300–302 | 3 |
| &nbsp;&nbsp;· Air-to-Ground SMS Bombing Page | 303–306 | 4 |
| &nbsp;&nbsp;· Air-to-Ground Bombing HUD | 307–317 | 11 |
| &nbsp;&nbsp;· JHMCS Air-to-Ground Mode | 318–320 | 3 |
| &nbsp;&nbsp;· Laser-Guided Bombing | 321–328 | 8 |
| &nbsp;&nbsp;· INS/GPS-Guided Weapons | 329–341 | 13 |
| &nbsp;&nbsp;· Air-to-Ground Gun and Rockets | 342–346 | 5 |
| &nbsp;&nbsp;· AGM-65 Maverick | 347–360 | 14 |
| &nbsp;&nbsp;· AGM-88 HARM | 361–375 | 15 |
| &nbsp;&nbsp;· AGM-84D Harpoon | 376–380 | 5 |
| &nbsp;&nbsp;· AGM-84E Stand-Off Land Attack Missile (SLAM) | 381–394 | 14 |
| &nbsp;&nbsp;· AGM-84H SLAM-ER (Expanded Response) | 395–398 | 4 |
| &nbsp;&nbsp;· AGM-62 Walleye II ER/DL with AWW-13 Datalink Pod | 399–405 | 7 |
| DEFENSIVE SYSTEMS | 406–418 | 13 |
| &nbsp;&nbsp;· Integrated Countermeasures Control Panel (ICMCP) | 407–408 | 2 |
| &nbsp;&nbsp;· EW Page | 409–411 | 3 |
| &nbsp;&nbsp;· ALR-67(V) Azimuth Indicator | 412–414 | 3 |
| &nbsp;&nbsp;· Airborne Self-Protection Jammer (ASPJ) | 415–417 | 3 |
| &nbsp;&nbsp;· HOTAS Controls | 418–418 | 1 |
| APPENDICES | 419–424 | 6 |
