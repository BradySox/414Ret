# Khe Sanh: Operation Niagara — Required Mods & Modules

*The squadron's install list for **Caucasus - Khe Sanh: Operation Niagara**. Read alongside the
[Campaign Briefing](Khe-Sanh-Campaign-Briefing) and [Combat SAR](Combat-SAR).*

Retribution generates **one mission** each turn containing every flight on both sides — yours,
your squadmates', the AI support, and the whole red side. If a unit is in the `.miz`, every
client needs whatever provides it to load the mission, whether or not anyone's actually flying
it.

---

## Install these — free, third-party mods

Everyone on the server needs all of these.

| Mod / pack | Author | What it adds | Download |
|---|---|---|---|
| Vietnam War Vessels (VWV) v3.2.0 | Tetet | Yankee Station ships + period **AI** aircraft (F-8E, A-1H, RF-101B, RA-5C, EC-121D, MiG-17F, MiG-21MF) | [Forum thread](https://forum.dcs.world/topic/338387-tetets-vietnam-war-vessels/) · [GitHub releases](https://github.com/tspindler-cms/tetet-vwv/releases) |
| Russian Military Assets Pack (Russia pack v2.0.1, 2026-03-14) | CurrentHill | NVA ground OOB: `[CH]` T-54 & PT-76 armor, ASU-85, ZSU/AAA guns, SA-2/SA-3 | [currenthill.com/russia](https://www.currenthill.com/russia) |
| OH-6A Cayuse + Vietnam Asset Pack v1.2 | Tobi & EightBall | The OH-6 scout helo, plus the period jeeps/trucks (`vap_*`) that show up even on turns the OH-6 itself isn't flying | [github.com/tobi-be/DCS-OH-6A](https://github.com/tobi-be/DCS-OH-6A) |
| OV-10A Bronco v1.24 | Split-Air Team | FAC(A) "Covey" / light CAS, **flyable** | [Forum thread](https://forum.dcs.world/topic/307951-ov-10a-bronco-mod-by-split-air-teamand-more/) |
| Community A-4E-C Skyhawk v2.3 | Community A-4E Project | Carrier Strike/CAS, **flyable** | [GitHub](https://github.com/Community-A-4E/community-a4e-c) · [releases](https://github.com/heclak/community-a4e-c/releases) |

---

## Official DCS modules in this mission

These are full DCS aircraft (store modules or Heatblur bonus content), not third-party mods.

| Aircraft | Developer | Role at Khe Sanh |
|---|---|---|
| F-4E-45MC Phantom II | Heatblur — paid | Tbilisi Strike / CAS |
| F-100D Super Sabre | Grinnelli Designs — paid | Tbilisi CAS |
| UH-1H Iroquois | Eagle Dynamics — paid | Air Assault / medevac / resupply |
| CH-47F Chinook | Eagle Dynamics — paid, **Early Access** | Combat SAR "Jolly Green" rescuer |
| **DCS: C-130J** | **Airplane Simulation Company — paid, flyable** | Niagara airlift + Combat SAR "King" |
| **A-6E Intruder** | **Heatblur — free, AI-only** | Naval-2 strike |
| Mi-8MTV2 | Eagle Dynamics — paid | NVA red side, AI only |

> ⚠️ **Markup note — C-130J.** This is the full official **DCS: C-130J by Airplane Simulation
> Company** ([e-shop](https://www.digitalcombatsimulator.com/en/shop/modules/c-130j/)) —
> player-flyable with a clickable cockpit, loadmaster mode, the works. It grew out of the older
> Anubis community mod but ships now as a real DCS store module, not a free AI-only forum mod.
> The King seat is a player seat (matches how the squadron already flies it over SRS) — confirm
> the squadron's actually buying this one rather than running a leftover Anubis install.

A paid module a player doesn't own still loads fine for everyone else — it just flies as AI.

> ⚠️ **Markup note — A-6E.** This is **Heatblur's free AI-only Intruder**, confirmed against the
> official DCS changelog ("DCS: A-6E Intruder by Heatblur Simulations"). It is **not** the
> CorsairCat A-6E mod — drop that attribution wherever it still appears. I don't have a clean
> citation for *how* it's obtained (bundled with DCS World, or gated behind owning another
> Heatblur module) — fill that in.

---

## Comes with DCS — nothing to install

**AH-1W SuperCobra** · **CH-53E Super Stallion** · **B-52H Stratofortress** · **KC-135
Stratotanker** · **E-2C Hawkeye** · **Yak-52** · **An-26B** · **An-30M** · **SA342M Gazelle**
(AI only here) — plus the core DCS ground roster (M48 Chaparral, Grad, etc.). Nothing to
download for any of these.

---

## Installing & keeping it tidy

- **Aircraft mods → `Saved Games\DCS\Mods\aircraft\`**; **asset packs → `...\Mods\tech\`** (each
  mod's own readme is authoritative if it differs).
- Use a mod manager (**OvGME** or **DCS-Mod-Manager**) so you can disable the whole Vietnam set
  for other servers and re-enable it for op night. Loose mods left in `Saved Games` can trip the
  integrity check on some MP servers.
- **Match versions across the squadron** — a mismatch shows up as missing or wrong units
  mid-mission.
- **No paid asset packs needed.** The NVA used to pull one half-track from ED's paid WWII Assets
  Pack; it's been swapped for a core-DCS vehicle, so don't buy that pack for this campaign.

---

*Sources: the campaign's own `khe_sanh_niagara.yaml`, the `USA 1970 Vietnam War` / `nva_1970`
faction `requirements`, the fork's bundled mod support (`pydcs_extensions/`), and a direct read
of tonight's generated `.miz` (2026-06-30) cross-checked against the unit roster. If a download
link rots, the mod's name + author is enough to find the current host on the
[ED Forums](https://forum.dcs.world/forum/1155-flyabledrivable-mods-for-dcs-world/).*
