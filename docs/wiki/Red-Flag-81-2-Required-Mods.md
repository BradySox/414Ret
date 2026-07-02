# Red Flag 81-2 — Required Mods & Modules

*The squadron's install list for **Nevada - Red Flag 81-2**. Read alongside the
[Campaign Briefing](Red-Flag-81-2-Campaign-Briefing) and [Combat SAR](Combat-SAR).*

Retribution generates **one mission** each turn containing every flight on both sides — yours,
your squadmates', the AI support, and the whole Red Force. If a unit is in the `.miz`, every
client needs whatever provides it to load the mission, whether or not anyone's flying it.

**You also need the DCS: Nevada Test and Training Range terrain** — the campaign is flown on the
real NTTR map.

---

## Install these — free, third-party mods

Everyone on the server needs both.

| Mod / pack | Author | What it adds here | Download |
|---|---|---|---|
| Vietnam War Vessels (VWV) v3.2.0 | Tetet | The **RF-101B** recon bird + the Constant Peg **MiG-17F / MiG-21MF** (AI) | [Forum thread](https://forum.dcs.world/topic/338387-tetets-vietnam-war-vessels/) · [GitHub releases](https://github.com/tspindler-cms/tetet-vwv/releases) |
| OV-10A Bronco v1.24 | Split-Air Team | FAC(A) / light CAS, **flyable** | [Forum thread](https://forum.dcs.world/topic/307951-ov-10a-bronco-mod-by-split-air-teamand-more/) |
| High Digit SAMs — Ultimate Compilation v1.4.3+ | dcs-sams | The Red Force's period **P-37 "Bar Lock" EWR** — the GCI eyes behind the ambush (the campaign ships `high_digit_sams: true`) | [GitHub](https://github.com/dcs-sams/HighDigitSAMs-Ultimate-Compilation) |

*(No CurrentHill packs, no Community A-4E, no OH-6 for this one — the 1981 factions are built on
vanilla + the three mods above.)*

---

## Official DCS modules in this mission

| Aircraft | Developer | Role at Red Flag |
|---|---|---|
| **F-4E-45MC Phantom II** | Heatblur — paid, **flyable** | The 336th TFS — Strike + MiGCAP. The campaign's seat. |
| **A-10A Thunderbolt II** | ED (Flaming Cliffs) — paid, **flyable** | BAI / the trail war |
| **UH-1H Iroquois** | ED — paid, **flyable** | Air Assault / Mercury lift |
| **DCS: C-130J** | Airplane Simulation Company — paid, **flyable** | Transport + the Combat SAR "King" |
| **CH-47F Chinook** | ED — paid, Early Access | Combat SAR pickup (if flown player-side) |
| **F-5E Tiger II** | ED — the AI (FC) version flies red | The 64th/65th Aggressors — you fight it, you don't fly it (unless you start the campaign **inverted**) |
| **MiG-21bis** | Magnitude 3 — paid | The 4477th's Fishbeds — AI red |
| **Mi-8MTV2** | ED — paid | Red lift, AI only |

A paid module a player doesn't own still loads fine for everyone else — it just flies as AI.

---

## Comes with DCS — nothing to install

**B-52H Stratofortress** · **KC-135 Stratotanker** · **E-3A Sentry** · **AH-1W SuperCobra** ·
**CH-47D** · **An-26B** — plus the whole ground threat array (SA-2/SA-3, ZSU-23-4, Hawk, Vulcan,
the armor). Nothing to download.

---

## Installing & keeping it tidy

- **Aircraft mods → `Saved Games\DCS\Mods\aircraft\`**; asset packs → `...\Mods\tech\` (each
  mod's own readme is authoritative if it differs).
- Use a mod manager (**OvGME** / **DCS-Mod-Manager**) so the Vietnam-era set can be toggled per
  server. Match versions across the squadron.
- Running the squadron's **Khe Sanh / Yankee Station install set already?** You're covered — this
  campaign uses a *subset* (VWV + OV-10; no CurrentHill, no A-4E, no OH-6 required).

---

*Sources: the campaign's own `red_flag_81_2.yaml` settings block and the
`usa_red_flag_1981` / `red_force_aggressors_1981` faction files. If a download link rots, the
mod's name + author will find the current host on the
[ED Forums](https://forum.dcs.world/forum/1155-flyabledrivable-mods-for-dcs-world/).*
