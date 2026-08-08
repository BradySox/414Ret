# F-14 — manual page index

Page numbers are **1-based physical PDF pages**. They may not match the
printed page numbers.

Extract a section as text:

```bash
pdftotext -f 63 -l 73 "references/manuals/F-14/<file>.pdf" -
```

The Read tool renders PDF pages as images via `pdftoppm`, which is often not
installed; `pdftotext` is, and text is cheaper. If Read does work, the same
numbers go in its `pages` parameter.

PDFs live in this folder and are gitignored. See [README.md](README.md).

## Chucks Guide.pdf

572 pages · index source: 205 PDF bookmarks

| Section | Pages | Len |
|---|---|---|
| DCS Guide - F-14B Tomcat | 1–1 | 1 |
| Disclaimer | 2–2 | 1 |
| Table of Contents | 3–3 | 1 |
| Part 1 - Introduction & JESTER AI | 4–13 | 10 |
| Part 2 - Controls Setup | 14–22 | 9 |
| Part 3 - Cockpit & Equipment | 23–145 | 123 |
| &nbsp;&nbsp;· Introduction | 23–26 | 4 |
| &nbsp;&nbsp;· Pilot Cockpit | 27–72 | 46 |
| &nbsp;&nbsp;· RIO Cockpit | 73–129 | 57 |
| &nbsp;&nbsp;· Equipment | 130–145 | 16 |
| Part 4 - Start-Up Procedure | 146–175 | 30 |
| &nbsp;&nbsp;· Summary | 146–146 | 1 |
| &nbsp;&nbsp;· 1 - Pilot Pre-Start | 147–150 | 4 |
| &nbsp;&nbsp;· 2 - Pilot Engine Start | 151–156 | 6 |
| &nbsp;&nbsp;· 3 - Pilot Post-Start | 157–163 | 7 |
| &nbsp;&nbsp;· 4 - RIO INS (Inertial Navigation System) Alignment (Shore) | 164–168 | 5 |
| &nbsp;&nbsp;· 5 - RIO INS (Inertial Navigation System) Alignment (Carrier) | 169–171 | 3 |
| &nbsp;&nbsp;· 6 - RIO Post-Alignment | 172–175 | 4 |
| Part 5 - Takeoff | 176–199 | 24 |
| &nbsp;&nbsp;· Shore Takeoff | 176–183 | 8 |
| &nbsp;&nbsp;· Carrier Takeoff | 184–199 | 16 |
| Part 6 - Landing | 200–231 | 32 |
| &nbsp;&nbsp;· Shore Landing (VFR) | 200–205 | 6 |
| &nbsp;&nbsp;· Carrier Landing (Case I Recovery) | 206–226 | 21 |
| &nbsp;&nbsp;· Landing Tips - DLC (Direct Lift Control) | 227–228 | 2 |
| &nbsp;&nbsp;· Landing Tips - Stick & Rudder | 229–231 | 3 |
| Part 7 - Engine Management | 232–239 | 8 |
| Part 8 - Flight & Aerodynamics | 240–246 | 7 |
| Part 9 - Radar & Sensors | 247–349 | 103 |
| &nbsp;&nbsp;· Section Structure | 247–247 | 1 |
| &nbsp;&nbsp;· 1 - Sensors | 248–260 | 13 |
| &nbsp;&nbsp;· 2 - AWG-9 Radar | 261–303 | 43 |
| &nbsp;&nbsp;· 3 - TCS/ALQ-100 (Television Camera Set) | 304–309 | 6 |
| &nbsp;&nbsp;· 4 - LANTIRN Targeting Pod | 310–349 | 40 |
| Part 10 - Offence: Weapons & Armament | 350–426 | 77 |
| &nbsp;&nbsp;· Section Structure | 350–350 | 1 |
| &nbsp;&nbsp;· 1 - Introduction | 351–357 | 7 |
| &nbsp;&nbsp;· 2 - Air-to-Ground Weapons | 358–399 | 42 |
| &nbsp;&nbsp;· 3 - Air-to-Air Weapons | 400–423 | 24 |
| &nbsp;&nbsp;· 4 - Selective Ordnance Jettison | 424–425 | 2 |
| &nbsp;&nbsp;· 5 - Videos | 426–426 | 1 |
| Part 11 - Defence: RWR & Countermeasures | 427–438 | 12 |
| &nbsp;&nbsp;· Introduction | 427–427 | 1 |
| &nbsp;&nbsp;· Countermeasures Control Setup | 428–429 | 2 |
| &nbsp;&nbsp;· AN/ALR-57 RWR (Radar Warning Receiver) | 430–432 | 3 |
| &nbsp;&nbsp;· AN/ALE-39 CMDS (Countermeasures Dispenser System) | 433–437 | 5 |
| &nbsp;&nbsp;· AN/ALQ-126 Deception Jammer (DECM) | 438–438 | 1 |
| Part 12 - Datalink & IFF | 439–452 | 14 |
| &nbsp;&nbsp;· Introduction | 439–439 | 1 |
| &nbsp;&nbsp;· Sensors Integrated View | 440–440 | 1 |
| &nbsp;&nbsp;· TID HAFU Symbology | 441–443 | 3 |
| &nbsp;&nbsp;· Manual IFF Example | 444–445 | 2 |
| &nbsp;&nbsp;· LINK4A (TAC) vs LINK4C (Fighter-to-Fighter) | 446–446 | 1 |
| &nbsp;&nbsp;· Setting up TAC (LINK4A) Datalink - Human RIO | 447–448 | 2 |
| &nbsp;&nbsp;· Setting up AUX (LINK4C) Datalink - Human RIO | 449–450 | 2 |
| &nbsp;&nbsp;· Setting Up Datalink (JESTER) | 451–451 | 1 |
| &nbsp;&nbsp;· Notes on LINK4 Datalink | 452–452 | 1 |
| Part 13 - Radios | 453–459 | 7 |
| Part 14 - Autopilot | 460–465 | 6 |
| Part 15 - Navigation & ACLS Landing | 466–554 | 89 |
| &nbsp;&nbsp;· Navigation Summary | 466–466 | 1 |
| &nbsp;&nbsp;· 1 - Introduction | 467–469 | 3 |
| &nbsp;&nbsp;· 2 - Reference Point Types | 470–471 | 2 |
| &nbsp;&nbsp;· 3 - Waypoint Entry - JESTER | 472–473 | 2 |
| &nbsp;&nbsp;· 4 - Waypoint Entry - RIO | 474–476 | 3 |
| &nbsp;&nbsp;· 5 - Waypoint Navigation - JESTER | 477–478 | 2 |
| &nbsp;&nbsp;· 6 - Waypoint Navigation - RIO | 479–480 | 2 |
| &nbsp;&nbsp;· 7 - TACAN Navigation | 481–486 | 6 |
| &nbsp;&nbsp;· 8 - VOR & ADF Navigation | 487–490 | 4 |
| &nbsp;&nbsp;· 9 - Bullseye & NAVGRID | 491–511 | 21 |
| &nbsp;&nbsp;· 10 - ACLS Carrier Landing Tutorial (Case III Recovery) | 512–532 | 21 |
| &nbsp;&nbsp;· 11 - AN/ASN-92 INS (Inertial Navigation System) | 533–554 | 22 |
| Part 16 - Air-to-Air Refueling | 555–565 | 11 |
| Part 17 - Reference Material & Acronyms | 566–572 | 7 |

## F-14 Manual.pdf

1156 pages · index source: 1967 PDF bookmarks

| Section | Pages | Len |
|---|---|---|
| F-14 Tomcat Manual | 1–2 | 2 |
| Introduction | 3–9 | 7 |
| Technical Specifications | 10–11 | 2 |
| Variants | 12–13 | 2 |
| Definitions | 14–14 | 1 |
| F-14A/B | 15–15 | 1 |
| Cockpit Overview | 16–16 | 1 |
| Pilot Cockpit Overview | 17–18 | 2 |
| Left Side Console | 19–37 | 19 |
| &nbsp;&nbsp;· G-valve Button | 19–19 | 1 |
| &nbsp;&nbsp;· Oxygen-Vent Airflow Control Panel | 20–20 | 1 |
| &nbsp;&nbsp;· Volume/TACAN Command Panel | 21–22 | 2 |
| &nbsp;&nbsp;· TACAN Control Panel | 23–23 | 1 |
| &nbsp;&nbsp;· ICS Control Panel | 24–25 | 2 |
| &nbsp;&nbsp;· AFCS Control Panel | 26–27 | 2 |
| &nbsp;&nbsp;· UHF 1 (AN/ARC-159) Radio | 28–29 | 2 |
| &nbsp;&nbsp;· ASYM Limiter/Engine Mode Select (F-14B only) | 30–30 | 1 |
| &nbsp;&nbsp;· Target Designate Switch | 31–31 | 1 |
| &nbsp;&nbsp;· Inlet Ramps/Throttle Control Panel | 32–33 | 2 |
| &nbsp;&nbsp;· Throttle | 34–35 | 2 |
| &nbsp;&nbsp;· Throttle Quadrant | 36–36 | 1 |
| &nbsp;&nbsp;· Hydraulic Hand Pump | 37–37 | 1 |
| Left Vertical Console | 38–46 | 9 |
| Left Knee Panel | 47–50 | 4 |
| Left Instrument Panel | 51–59 | 9 |
| Left Windshield Frame | 60–63 | 4 |
| Center Panel | 64–78 | 15 |
| &nbsp;&nbsp;· Heads-Up Display | 64–64 | 1 |
| &nbsp;&nbsp;· Cockpit Television Sensor (CTVS) | 65–65 | 1 |
| &nbsp;&nbsp;· Air Combat Maneuver Panel | 66–68 | 3 |
| &nbsp;&nbsp;· Vertical Display Indicator (VDI) | 69–71 | 3 |
| &nbsp;&nbsp;· Horizontal Situation Display Indicator (HSD) | 72–73 | 2 |
| &nbsp;&nbsp;· Cabin Pressure Altimeter | 74–74 | 1 |
| &nbsp;&nbsp;· Emergency Brake Pressure Indicator | 75–75 | 1 |
| &nbsp;&nbsp;· Control Stick | 76–78 | 3 |
| Right Windshield Frame | 79–81 | 3 |
| Right Instrument Panel | 82–90 | 9 |
| Right Knee Panel | 91–94 | 4 |
| Right Vertical Console | 95–100 | 6 |
| Right Side Console | 101–119 | 19 |
| &nbsp;&nbsp;· Spoiler Failure Override | 101–101 | 1 |
| &nbsp;&nbsp;· Liquid Oxygen Quantity Indicator | 102–103 | 2 |
| &nbsp;&nbsp;· Compass Control Panel | 102–103 | 2 |
| &nbsp;&nbsp;· ARA-63 Control Panel | 104–104 | 1 |
| &nbsp;&nbsp;· Caution - Advisory Indicator | 105–108 | 4 |
| &nbsp;&nbsp;· Master Generator Control Panel | 109–109 | 1 |
| &nbsp;&nbsp;· Master Light Control Panel | 110–112 | 3 |
| &nbsp;&nbsp;· Air Conditioning Control Panel | 113–114 | 2 |
| &nbsp;&nbsp;· Master Test Panel | 115–115 | 1 |
| &nbsp;&nbsp;· External Environmental Control Panel | 116–116 | 1 |
| &nbsp;&nbsp;· Hydraulic Transfer Pump Switch | 117–117 | 1 |
| &nbsp;&nbsp;· HUD - Video Control Panel | 118–118 | 1 |
| &nbsp;&nbsp;· Canopy Defog / Cabin Air Lever | 119–119 | 1 |
| Canopy Control Handle | 120–120 | 1 |
| RIO Cockpit Overview | 121–122 | 2 |
| Left Side Console | 123–140 | 18 |
| &nbsp;&nbsp;· G-Valve Button | 123–123 | 1 |
| &nbsp;&nbsp;· Oxygen-Vent Airflow Control Panel | 124–124 | 1 |
| &nbsp;&nbsp;· Data Stowage Compartment | 125–125 | 1 |
| &nbsp;&nbsp;· TACAN Control Panel | 126–126 | 1 |
| &nbsp;&nbsp;· Communication / TACAN Command Panel | 127–128 | 2 |
| &nbsp;&nbsp;· V/UHF 2 (AN/ARC-182) Radio | 129–129 | 1 |
| &nbsp;&nbsp;· KY-28 Control Panel | 130–130 | 1 |
| &nbsp;&nbsp;· Radar Beacon Control Panel | 131–131 | 1 |
| &nbsp;&nbsp;· Liquid Cooling Control Panel | 132–133 | 2 |
| &nbsp;&nbsp;· ICS Control Panel | 132–133 | 2 |
| &nbsp;&nbsp;· Eject Command Lever | 134–134 | 1 |
| &nbsp;&nbsp;· Sensor Control Panel | 135–137 | 3 |
| &nbsp;&nbsp;· Computer Address Panel (CAP) | 138–140 | 3 |
| Left Vertical Console | 141–145 | 5 |
| Left Instrument Panel | 146–151 | 6 |
| Center Panel | 152–157 | 6 |
| Center Console | 158–163 | 6 |
| Footwells | 164–165 | 2 |
| Right Instrument Panel | 166–176 | 11 |
| Right Knee Panel | 177–180 | 4 |
| Right Vertical Console | 181–181 | 1 |
| Right Side Console | 182–205 | 24 |
| &nbsp;&nbsp;· Radar Warning Receiver Panel | 182–183 | 2 |
| &nbsp;&nbsp;· Digital Data Indicator (DDI) | 184–186 | 3 |
| &nbsp;&nbsp;· DECM Control Panel | 187–187 | 1 |
| &nbsp;&nbsp;· Data Link Control Panel | 188–188 | 1 |
| &nbsp;&nbsp;· Data Link Reply and Antenna Control Panel | 189–190 | 2 |
| &nbsp;&nbsp;· AN/ALE-39 Control Panel | 191–192 | 2 |
| &nbsp;&nbsp;· AA1 Control Panel | 193–193 | 1 |
| &nbsp;&nbsp;· AN/ALE-39 Programmer | 194–195 | 2 |
| &nbsp;&nbsp;· Interior Light Control Panel | 196–196 | 1 |
| &nbsp;&nbsp;· Data / ADF Switch | 197–197 | 1 |
| &nbsp;&nbsp;· IFF Transponder Control Panel | 198–200 | 3 |
| &nbsp;&nbsp;· IFF Antenna Control / Test Panel | 201–201 | 1 |
| &nbsp;&nbsp;· Mid Compression Bypass Test Panel (F-14A only) | 202–202 | 1 |
| &nbsp;&nbsp;· Electrical Power System Test Panel | 203–204 | 2 |
| &nbsp;&nbsp;· Canopy Defog / Cabin Air Lever | 205–205 | 1 |
| Canopy Control Handle | 206–206 | 1 |
| Systems Overview | 207–207 | 1 |
| Flight Controls and Gear | 208–208 | 1 |
| Central Air Data Computer (CADC) | 209–209 | 1 |
| Flight Controls & AFCS | 210–215 | 6 |
| Wing-Sweep System | 216–221 | 6 |
| Landing Gear System & GroundHandling | 222–226 | 5 |
| Engines & Fuel Systems | 227–227 | 1 |
| Engines | 228–239 | 12 |
| &nbsp;&nbsp;· Throttle Controls | 230–231 | 2 |
| &nbsp;&nbsp;· Engine and Throttle Control Switches and Indicators | 232–235 | 4 |
| &nbsp;&nbsp;· Engine Instrument Group (EIG), Related Indicatorsand Caution Lights | 236–239 | 4 |
| Fuel System | 240–245 | 6 |
| Navigation & Communication | 246–247 | 2 |
| Navigation System | 248–272 | 25 |
| &nbsp;&nbsp;· WCS Computer | 248–248 | 1 |
| &nbsp;&nbsp;· IMU Platform Alignment | 248–248 | 1 |
| &nbsp;&nbsp;· Navigation Modes | 249–249 | 1 |
| &nbsp;&nbsp;· Navigation Computations | 250–255 | 6 |
| &nbsp;&nbsp;· Displays | 250–255 | 6 |
| &nbsp;&nbsp;· Radar Altimeter System (AN/APN-194) | 256–256 | 1 |
| &nbsp;&nbsp;· Navigation System Integration | 257–272 | 16 |
| Inertial Navigation System (INS) | 273–294 | 22 |
| &nbsp;&nbsp;· Inertial Measurement Unit | 273–276 | 4 |
| &nbsp;&nbsp;· INS Alignment Modes | 277–278 | 2 |
| &nbsp;&nbsp;· Non-SAT Alignments | 279–286 | 8 |
| &nbsp;&nbsp;· Stored Heading Alignment | 287–288 | 2 |
| &nbsp;&nbsp;· Catapult Alignment | 289–289 | 1 |
| &nbsp;&nbsp;· Navigation Fix Update | 289–289 | 1 |
| &nbsp;&nbsp;· Radar Update | 290–290 | 1 |
| &nbsp;&nbsp;· TACAN Update | 291–291 | 1 |
| &nbsp;&nbsp;· Visual Update | 292–292 | 1 |
| &nbsp;&nbsp;· Data Link Update | 292–292 | 1 |
| &nbsp;&nbsp;· Fighter-to-Fighter Navigation Update | 293–294 | 2 |
| &nbsp;&nbsp;· Position Marking | 293–294 | 2 |
| Attitude and Heading Reference Set(AHRS) | 295–297 | 3 |
| TACAN System (AN/ARN-84) | 298–300 | 3 |
| Bearing Distance and HeadingIndicator (BDHI) | 301–301 | 1 |
| Communications Systems | 302–306 | 5 |
| ICS - Intercommunications System | 307–309 | 3 |
| TSEC/KY-28 Voice Security Equipment | 310–312 | 3 |
| AN/ARC-159 (UHF 1) Radio | 313–316 | 4 |
| AN/ARC-182 (V/UHF 2) Radio | 317–320 | 4 |
| Link 4A & C Data Link | 321–324 | 4 |
| Identification Systems | 325–327 | 3 |
| Hydraulics | 328–331 | 4 |
| Environmental Control System | 332–335 | 4 |
| Utility | 336–338 | 3 |
| Electrical Power System | 339–341 | 3 |
| Lighting System | 342–343 | 2 |
| AN/AWG-9 Radar | 344–344 | 1 |
| Radar Interface | 345–386 | 42 |
| &nbsp;&nbsp;· Detail Data Display (DDD) and Panel | 345–346 | 2 |
| &nbsp;&nbsp;· Radar and Missile Frequency Selectors | 347–349 | 3 |
| &nbsp;&nbsp;· Detail Data Display | 350–351 | 2 |
| &nbsp;&nbsp;· Tactical Information Display (TID) and AssociatedControls | 352–365 | 14 |
| &nbsp;&nbsp;· Navigation Command and Control Grid (NAV GRID) | 366–367 | 2 |
| &nbsp;&nbsp;· Operation | 368–369 | 2 |
| &nbsp;&nbsp;· Hand Control Unit (HCU) | 370–376 | 7 |
| &nbsp;&nbsp;· CAP Message Matrix Indicator Drum and buttons | 377–384 | 8 |
| &nbsp;&nbsp;· Sensor Control Panel | 385–386 | 2 |
| General Radar Operation | 387–399 | 13 |
| &nbsp;&nbsp;· Pulse Mode | 388–390 | 3 |
| &nbsp;&nbsp;· Pulse Doppler Mode | 391–397 | 7 |
| &nbsp;&nbsp;· HCU Stick in Radar Mode | 398–398 | 1 |
| &nbsp;&nbsp;· Transitional Modes | 398–398 | 1 |
| &nbsp;&nbsp;· TWS STT Acquisition | 399–399 | 1 |
| ACM Modes | 400–404 | 5 |
| AN/AXX-1 TCS | 405–413 | 9 |
| LANTIRN | 414–422 | 9 |
| Modes | 423–425 | 3 |
| Defensive Systems | 426–426 | 1 |
| Countermeasures | 427–427 | 1 |
| AN/ALE-39 CountermeasuresDispensing Set | 428–434 | 7 |
| LAU-138 | 435–435 | 1 |
| Radar Warning Receiver | 436–436 | 1 |
| AN/ALR-67 RWR | 437–448 | 12 |
| &nbsp;&nbsp;· Controls | 438–439 | 2 |
| &nbsp;&nbsp;· Displays | 440–441 | 2 |
| &nbsp;&nbsp;· Warning Lights | 442–442 | 1 |
| &nbsp;&nbsp;· Threat Indication Alert Tones | 443–443 | 1 |
| &nbsp;&nbsp;· BIT | 444–448 | 5 |
| ALR-45/50 (F-14A Early) | 449–456 | 8 |
| Electronic Countermeasures - AN/ALQ-100 & 126 DECM (Defensive ElectronicCounterMeasures) | 457–458 | 2 |
| Emergency | 459–462 | 4 |
| Weapons & Stores | 463–465 | 3 |
| M-61 Vulcan Six-Barreled GatlingCannon | 466–475 | 10 |
| Air to Air | 476–478 | 3 |
| AIM-54 Phoenix | 479–486 | 8 |
| AIM-7 Sparrow | 487–490 | 4 |
| AIM-9 Sidewinder | 491–494 | 4 |
| Air to Ground | 495–495 | 1 |
| Air-to-Ground Weapon Settings | 496–497 | 2 |
| Air-to-Ground Weapon Delivery | 498–503 | 6 |
| Zuni Rockets | 504–504 | 1 |
| Mk-81, 82, 83, and 84 GP Bombs | 505–506 | 2 |
| GBU-10, 12, 16, and 24 | 507–508 | 2 |
| Mk-20 Rockeye | 509–509 | 1 |
| BDU-33 Practice Bombs | 510–510 | 1 |
| ADM-141 TALD | 511–511 | 1 |
| LUU-2 Parachute Flare | 512–512 | 1 |
| Smokewinder | 513–513 | 1 |
| Pods | 514–515 | 2 |
| Tanks | 516–516 | 1 |
| Jester & Iceman | 517–522 | 6 |
| Normal Procedures | 523–523 | 1 |
| Interior Inspection | 524–529 | 6 |
| Pre-Start | 530–533 | 4 |
| Engine Start | 534–536 | 3 |
| Post-Start | 537–544 | 8 |
| Emergency Procedures | 545–547 | 3 |
| DCS | 548–548 | 1 |
| Special Options | 549–549 | 1 |
| Mission Editor | 550–551 | 2 |
| F-14B Upgrade | 552–552 | 1 |
| Cockpit Overview | 553–553 | 1 |
| Pilot Cockpit Overview | 554–554 | 1 |
| Left Side Console | 555–575 | 21 |
| &nbsp;&nbsp;· G-valve Button | 557–557 | 1 |
| &nbsp;&nbsp;· Oxygen-Vent Airflow Control Panel | 558–559 | 2 |
| &nbsp;&nbsp;· Volume/TACAN Command Panel | 560–561 | 2 |
| &nbsp;&nbsp;· TACAN Control Panel | 560–561 | 2 |
| &nbsp;&nbsp;· ICS Control Panel | 562–562 | 1 |
| &nbsp;&nbsp;· DFCS Control Panel | 563–565 | 3 |
| &nbsp;&nbsp;· UHF 1 (AN/ARC-159) Radio | 566–567 | 2 |
| &nbsp;&nbsp;· ASYM Limiter/Engine Mode Select | 568–568 | 1 |
| &nbsp;&nbsp;· Target Designate Switch | 569–569 | 1 |
| &nbsp;&nbsp;· Inlet Ramps/Throttle Control Panel | 570–571 | 2 |
| &nbsp;&nbsp;· Throttle | 572–573 | 2 |
| &nbsp;&nbsp;· Throttle Quadrant | 574–574 | 1 |
| &nbsp;&nbsp;· Hydraulic Hand Pump | 575–575 | 1 |
| Left Vertical Console | 576–587 | 12 |
| &nbsp;&nbsp;· Fuel Management Panel | 578–580 | 3 |
| &nbsp;&nbsp;· Control Surface Pos Indicator | 581–581 | 1 |
| &nbsp;&nbsp;· Launch Bar Abort Panel | 582–582 | 1 |
| &nbsp;&nbsp;· Landing Gear Control Panel | 583–587 | 5 |
| Left Knee Panel | 588–591 | 4 |
| Left Instrument Panel | 592–601 | 10 |
| Left Windshield Frame | 602–606 | 5 |
| Center Panel | 607–627 | 21 |
| &nbsp;&nbsp;· Vertical Display Indicator Group - Replacement | 608–609 | 2 |
| &nbsp;&nbsp;· Heads-Up Display | 610–612 | 3 |
| &nbsp;&nbsp;· Vertical Display Indicator (VDI) | 613–615 | 3 |
| &nbsp;&nbsp;· VDI Specific Displays | 616–617 | 2 |
| &nbsp;&nbsp;· Air Combat Maneuver Panel | 618–620 | 3 |
| &nbsp;&nbsp;· Horizontal Situation Display Indicator (HSD) | 621–622 | 2 |
| &nbsp;&nbsp;· Cabin Pressure Altimeter | 623–623 | 1 |
| &nbsp;&nbsp;· Emergency Brake Pressure Indicator | 624–624 | 1 |
| &nbsp;&nbsp;· Control Stick | 625–627 | 3 |
| Right Windshield Frame | 628–629 | 2 |
| Right Instrument Panel | 630–639 | 10 |
| Right Knee Panel | 640–643 | 4 |
| Right Vertical Console | 644–649 | 6 |
| Right Side Console | 650–669 | 20 |
| &nbsp;&nbsp;· Liquid Oxygen Quantity Indicator | 652–653 | 2 |
| &nbsp;&nbsp;· Compass Control Panel | 652–653 | 2 |
| &nbsp;&nbsp;· ARA-63 Control Panel | 654–654 | 1 |
| &nbsp;&nbsp;· Caution - Advisory Indicator | 655–657 | 3 |
| &nbsp;&nbsp;· Master Generator Control Panel | 658–659 | 2 |
| &nbsp;&nbsp;· Master Light Control Panel | 660–663 | 4 |
| &nbsp;&nbsp;· Air Conditioning Control Panel | 664–665 | 2 |
| &nbsp;&nbsp;· Master Test Panel | 666–666 | 1 |
| &nbsp;&nbsp;· External Environmental Control Panel | 667–667 | 1 |
| &nbsp;&nbsp;· Hydraulic Transfer Pump Switch | 668–668 | 1 |
| &nbsp;&nbsp;· Canopy Defog / Cabin Air Lever | 669–669 | 1 |
| Canopy Control Handle | 670–670 | 1 |
| RIO Cockpit Overview | 671–671 | 1 |
| Left Side Console | 672–692 | 21 |
| &nbsp;&nbsp;· Sensor Control Panel | 674–676 | 3 |
| &nbsp;&nbsp;· Control Display Navigation Unit (CDNU) | 677–679 | 3 |
| &nbsp;&nbsp;· LANTIRN Control Panel (LCP) | 680–682 | 3 |
| &nbsp;&nbsp;· Computer Address Panel (CAP) | 683–685 | 3 |
| &nbsp;&nbsp;· Communication / TACAN Command Panel | 686–686 | 1 |
| &nbsp;&nbsp;· Radar Beacon Control Panel | 687–687 | 1 |
| &nbsp;&nbsp;· Power System Test Panel | 688–688 | 1 |
| &nbsp;&nbsp;· KY-28 Control Panel | 689–689 | 1 |
| &nbsp;&nbsp;· Oxygen-Vent Airflow Control Panel | 689–689 | 1 |
| &nbsp;&nbsp;· G-Valve Button | 690–690 | 1 |
| &nbsp;&nbsp;· Liquid Cooling Control Panel | 691–691 | 1 |
| &nbsp;&nbsp;· Eject Command Lever | 692–692 | 1 |
| Left Vertical Console | 693–697 | 5 |
| Left Instrument Panel | 698–704 | 7 |
| Center Panel | 705–710 | 6 |
| Center Console | 711–718 | 8 |
| Footwells | 719–724 | 6 |
| Right Instrument Panel | 725–732 | 8 |
| Right Vertical Console | 733–734 | 2 |
| Right Side Console | 735–763 | 29 |
| &nbsp;&nbsp;· ECM Display Control Panel | 737–737 | 1 |
| &nbsp;&nbsp;· Radar Warning Receiver Panel | 738–739 | 2 |
| &nbsp;&nbsp;· UHF 2 Control Panel | 740–740 | 1 |
| &nbsp;&nbsp;· ICS Control Panel | 741–741 | 1 |
| &nbsp;&nbsp;· AN/ALE-47 Digital Control Display Unit (DCDU) | 742–746 | 5 |
| &nbsp;&nbsp;· AN/ALE-47 Programmer | 747–749 | 3 |
| &nbsp;&nbsp;· Digital Data Indicator (DDI) | 747–749 | 3 |
| &nbsp;&nbsp;· The Fast Tactical Imaging Control Panel | 750–750 | 1 |
| &nbsp;&nbsp;· Data Link Control Panel | 751–751 | 1 |
| &nbsp;&nbsp;· Data Link Reply and Antenna Control Panel | 752–753 | 2 |
| &nbsp;&nbsp;· AA1 Control Panel | 754–754 | 1 |
| &nbsp;&nbsp;· Interior Light Control Panel | 755–756 | 2 |
| &nbsp;&nbsp;· IFF Transponder Control Panel | 757–758 | 2 |
| &nbsp;&nbsp;· DECM Control Panel | 759–760 | 2 |
| &nbsp;&nbsp;· IFF Antenna Control / Test Panel | 761–761 | 1 |
| &nbsp;&nbsp;· Canopy Defog / Cabin Air Lever | 762–763 | 2 |
| Canopy Control Handle | 764–764 | 1 |
| Systems Overview | 765–765 | 1 |
| Navigation & Communication | 766–766 | 1 |
| NAVIGATION CONTROLS ANDDISPLAYS | 767–781 | 15 |
| &nbsp;&nbsp;· Pilot | 768–768 | 1 |
| &nbsp;&nbsp;· RIO | 769–769 | 1 |
| &nbsp;&nbsp;· System Architecture and Terminology | 770–771 | 2 |
| &nbsp;&nbsp;· Navigation Display Matrix | 772–772 | 1 |
| &nbsp;&nbsp;· Steering Select Sources | 773–776 | 4 |
| &nbsp;&nbsp;· EGI vs DEST Steering mode use-case examples | 777–781 | 5 |
| Introduction | 782–804 | 23 |
| &nbsp;&nbsp;· Embedded GPS/INS (EGI) | 782–783 | 2 |
| &nbsp;&nbsp;· EGI MODES OF OPERATION | 784–785 | 2 |
| &nbsp;&nbsp;· Navigation System Caution and AdvisoryLights/Legends | 786–787 | 2 |
| &nbsp;&nbsp;· EGI ALIGNMENT MODES | 788–794 | 7 |
| &nbsp;&nbsp;· Transition to NAV Mode | 795–795 | 1 |
| &nbsp;&nbsp;· GPS | 796–796 | 1 |
| &nbsp;&nbsp;· Stationary Alignments | 797–798 | 2 |
| &nbsp;&nbsp;· In-Motion Alignments | 799–802 | 4 |
| &nbsp;&nbsp;· In-Flight Alignments | 803–804 | 2 |
| CONTROL DISPLAY NAVIGATION UNIT | 805–807 | 3 |
| THE CDNU | 808–873 | 66 |
| &nbsp;&nbsp;· CDNU Display | 808–809 | 2 |
| &nbsp;&nbsp;· Line Select Keys | 810–811 | 2 |
| &nbsp;&nbsp;· Alphanumeric Keys | 810–811 | 2 |
| &nbsp;&nbsp;· Function Keys | 810–811 | 2 |
| &nbsp;&nbsp;· Dedicated Select Keys | 812–812 | 1 |
| &nbsp;&nbsp;· Scratchpad | 813–813 | 1 |
| &nbsp;&nbsp;· Page Scrolling | 813–813 | 1 |
| &nbsp;&nbsp;· Clear Key | 813–813 | 1 |
| &nbsp;&nbsp;· Common Symbology | 814–814 | 1 |
| &nbsp;&nbsp;· The CDNU flight plan and Steering sources | 815–816 | 2 |
| &nbsp;&nbsp;· Data Entry | 817–820 | 4 |
| &nbsp;&nbsp;· CDNU Pages | 821–873 | 53 |
| Bearing Distance Heading Indicator | 874–877 | 4 |
| Fast Tactical Imaging System | 878–896 | 19 |
| &nbsp;&nbsp;· Remote Control Unit (RCU) | 879–879 | 1 |
| &nbsp;&nbsp;· Image Transceiver | 879–879 | 1 |
| &nbsp;&nbsp;· Airborne Video Tape Recorder (AVTR) | 880–881 | 2 |
| &nbsp;&nbsp;· OPERATING INSTRUCTIONS | 882–883 | 2 |
| &nbsp;&nbsp;· SETTINGS MENUS | 884–890 | 7 |
| &nbsp;&nbsp;· CAPTURING/COMPRESSING/SAVING/TRANSMITTING/RECEIVING IMAGES | 891–893 | 3 |
| &nbsp;&nbsp;· VIEWING IMAGES | 894–894 | 1 |
| &nbsp;&nbsp;· CONTROLLING VTR FUNCTIONS | 895–896 | 2 |
| Programmable Tactical InformationDisplay | 897–898 | 2 |
| Programmable Tactical InformationDisplay | 899–928 | 30 |
| &nbsp;&nbsp;· Waypoints | 901–902 | 2 |
| &nbsp;&nbsp;· Tactical Page | 903–904 | 2 |
| &nbsp;&nbsp;· Menu Page | 905–906 | 2 |
| &nbsp;&nbsp;· Navigation Data Plot Line (NVD PLT) Page | 907–907 | 1 |
| &nbsp;&nbsp;· Plot Lines | 908–911 | 4 |
| &nbsp;&nbsp;· Navigation Data Waypoint Page (NVD WP) Page | 912–912 | 1 |
| &nbsp;&nbsp;· Bullseye | 913–915 | 3 |
| &nbsp;&nbsp;· Nav Grid | 916–916 | 1 |
| &nbsp;&nbsp;· All Weather Landing (AWL) Page | 917–918 | 2 |
| &nbsp;&nbsp;· JDAM Mission (JMSN) Page | 919–920 | 2 |
| &nbsp;&nbsp;· Stores Management Page (SMS) Page | 921–922 | 2 |
| &nbsp;&nbsp;· PTID Steering | 923–928 | 6 |
| Vertical Display Indicator GroupReplacement | 929–930 | 2 |
| Vertical Display Indicator Group-Replacement | 931–959 | 29 |
| &nbsp;&nbsp;· Symbology Common To All Display Modes | 934–943 | 10 |
| &nbsp;&nbsp;· Takeoff | 944–945 | 2 |
| &nbsp;&nbsp;· Cruise | 946–947 | 2 |
| &nbsp;&nbsp;· Air-To-Air | 948–955 | 8 |
| &nbsp;&nbsp;· Air-To-Ground | 956–956 | 1 |
| &nbsp;&nbsp;· Landing | 957–959 | 3 |
| Programmable Multiple DisplayIndicator Group | 960–960 | 1 |
| Programmable Multiple DisplayIndicator Group | 961–976 | 16 |
| &nbsp;&nbsp;· Pilot Horizontal Situation Display | 961–961 | 1 |
| &nbsp;&nbsp;· RIO Electronic Countermeasure Display | 962–963 | 2 |
| &nbsp;&nbsp;· PMDIG Modes | 964–976 | 13 |
| AN/ASQ-215 Mission Data Loader | 977–977 | 1 |
| Mission Data Loader | 978–984 | 7 |
| Defensive Systems | 985–985 | 1 |
| AN/ALE-47 CountermeasuresDispensing Set | 986–994 | 9 |
| LAU-138 | 995–996 | 2 |
| LANTIRN TARGETING SYSTEM | 997–997 | 1 |
| LANTIRN | 998–1005 | 8 |
| DIGITAL FLIGHT CONTROL SYSTEM | 1006–1006 | 1 |
| The Digital Flight Control System | 1007–1010 | 4 |
| F-14B Upgrade Weapons Employment | 1011–1015 | 5 |
| Air To Air Weapons Employment | 1016–1017 | 2 |
| Vertical Display Indicator GroupReplacement A/A | 1018–1037 | 20 |
| &nbsp;&nbsp;· VDIG-R Symbology common to all A/A formats | 1018–1037 | 20 |
| Programmable Tactical InformationDisplay | 1038–1045 | 8 |
| Air To Ground Weapons Employment | 1046–1046 | 1 |
| GPS Guided Weapons Employment | 1047–1068 | 22 |
| &nbsp;&nbsp;· Pre-Planned Missions | 1047–1047 | 1 |
| &nbsp;&nbsp;· ACP Attack Mode Steering Options | 1047–1047 | 1 |
| &nbsp;&nbsp;· Pre-Planned Launch Acceptability Region | 1048–1048 | 1 |
| &nbsp;&nbsp;· Pre-Planned Launch Point Cue | 1048–1048 | 1 |
| &nbsp;&nbsp;· Bearing to Launch Point Cue | 1049–1049 | 1 |
| &nbsp;&nbsp;· GGW Target Cue | 1049–1049 | 1 |
| &nbsp;&nbsp;· GGW Terminal Heading Cue | 1050–1051 | 2 |
| &nbsp;&nbsp;· ROPT Release Strobe | 1050–1051 | 2 |
| &nbsp;&nbsp;· Primary Release Modes | 1050–1051 | 2 |
| &nbsp;&nbsp;· Typical PTID Tac Page Cues for JDAM releases | 1052–1057 | 6 |
| &nbsp;&nbsp;· Typical VDIG-R A/G Cues for JDAM releases | 1058–1060 | 3 |
| &nbsp;&nbsp;· JDAM Mission Page (JMSN) | 1061–1062 | 2 |
| &nbsp;&nbsp;· Pre-Planned JDAM Employment | 1063–1066 | 4 |
| &nbsp;&nbsp;· Target Of Opportunity JDAM Employment | 1067–1067 | 1 |
| &nbsp;&nbsp;· Pre-Planned JDAM tutorial by Baltic Dragon | 1068–1068 | 1 |
| Joint Direct Attack Munition | 1069–1072 | 4 |
| Enhanced Paveway™ III Dual ModeGPS/Laser Guided Bomb | 1073–1074 | 2 |
| Laser Guided Bombs | 1075–1080 | 6 |
| Unguided Weapons Employment | 1081–1086 | 6 |
| Normal Procedures | 1087–1087 | 1 |
| Checklists | 1088–1088 | 1 |
| Preparation for Flight and InteriorInspection | 1089–1094 | 6 |
| Engine Startup | 1095–1096 | 2 |
| Post Start | 1097–1100 | 4 |
| Quick Start Field | 1101–1102 | 2 |
| Quick Start CV | 1103–1104 | 2 |
| Jester | 1105–1105 | 1 |
| DCS | 1106–1106 | 1 |
| Special Options | 1107–1107 | 1 |
| Mission Editor | 1108–1108 | 1 |
| Grease Pencil | 1109–1110 | 2 |
| Instant Camera | 1111–1112 | 2 |
| Laser Pointer Designator | 1113–1114 | 2 |
| JESTER / ICEMAN SET COMMANDS | 1115–1126 | 12 |
| &nbsp;&nbsp;· General / Pilot Commands | 1115–1115 | 1 |
| &nbsp;&nbsp;· Jester LANTIRN / Targeting | 1116–1117 | 2 |
| &nbsp;&nbsp;· Radio / Navigation | 1118–1118 | 1 |
| &nbsp;&nbsp;· Jester Systems | 1119–1119 | 1 |
| &nbsp;&nbsp;· Jester Radar / Air-to-Air | 1120–1120 | 1 |
| &nbsp;&nbsp;· Jester Weapons | 1121–1121 | 1 |
| &nbsp;&nbsp;· Jester LANTIRN Zoom | 1122–1122 | 1 |
| &nbsp;&nbsp;· Jester Backup (BU) Waypoint / Nav Commands | 1123–1124 | 2 |
| &nbsp;&nbsp;· Iceman (AI Pilot) Commands | 1125–1125 | 1 |
| &nbsp;&nbsp;· Sentinel | 1126–1126 | 1 |
| Bombing Tool | 1127–1129 | 3 |
| Kneeboard | 1130–1132 | 3 |
| Embedded Manual | 1133–1134 | 2 |
| Training Missions | 1135–1135 | 1 |
| Acronyms and Abbreviations | 1136–1146 | 11 |
| Tutorials | 1147–1154 | 8 |
| Imprint | 1155–1156 | 2 |
