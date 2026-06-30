# Khe Sanh: Operation Niagara — Required Mods & Modules

*The squadron's one-stop install list for **Caucasus - Khe Sanh: Operation Niagara**. Hand this
page to anyone joining op night: it says **what you must install, what you can fly, what's free vs
paid, and exactly where to download it.** Read alongside the [Campaign Briefing](Khe-Sanh-Campaign-Briefing).*

> 🟢 **Provenance — read this.** This list is read **straight from the campaign + faction files**
> (`resources/campaigns/khe_sanh_niagara.yaml`, `resources/factions/USA 1970 Vietnam War.json`,
> `resources/factions/nva_1970.json`). The airframes and packs below are exactly what the campaign
> fields and what its `requirements`/settings flag.

---

## How to read this page

Retribution generates **one mission** each turn that contains **every** flight and unit — yours,
your squadmates', the AI support, and the whole red side. So the rule is simple:

- **If the mission contains it, every client needs the mod.** A free mod that appears anywhere in
  the `.miz` is **required for everyone**, even if you never fly it — without it the mission won't
  load and you'll fail the multiplayer integrity check. **The OV-10 Bronco is a free mod that's in
  the mission, so it's required for the whole squadron, not "only if you fly FAC."**
- **Paid DCS store modules are the one exception.** DCS will load a mission containing a paid
  aircraft you don't own — it just shows up as AI you can't take. So you only need a **paid module**
  to *pilot that seat yourself*.
- **Some airframes ship with DCS** (core AI units) — nothing to download at all.

Three buckets, in order: **§1 install these (required, all free) → §2 what you can fly → §3 comes
with DCS.**

---

## TL;DR — op-night install

1. **Install every mod in [§1](#1--required-mods--everyone-installs-all-of-these).** All free, all
   mandatory for everyone — the mission is built from them.
2. **To fly a fast-mover or the Huey, also buy its [paid module](#2--what-you-can-fly--player-seats)**
   (F-4E, F-100D, or UH-1H). The only two **free** flyable seats — OV-10A and A-4E — are already
   covered by §1; every other mod aircraft in the campaign is **AI-only**.
3. **Match versions** across the squadron and load mods with a mod manager (see [§4](#4--installing--keeping-it-tidy)).

> 💡 **No paid *asset* packs needed.** Khe Sanh's required content is 100% free mods + core DCS. The
> NVA used to pull one half-track from ED's **paid** WWII Assets Pack; it's been swapped for a
> core-DCS vehicle, so **the WWII Assets Pack is no longer required — don't buy it for this campaign.**

---

## 1 · Required mods — *everyone installs all of these*

Every player on the server needs **all** of these. They're free, and they're in the generated
mission — a missing one means the mission won't load / you fail the integrity check.

| Mod / pack | What it adds to Khe Sanh | Download |
|---|---|---|
| **Vietnam War Vessels (VWV) v2.3.0** — Tetet | Yankee Station ships **+** the period **AI** aircraft (F-8E, A-1H, RF-101B, RA-5C, EC-121D, MiG-17F — see [§3](#whats-inside-vwv)) | [Forum thread](https://forum.dcs.world/topic/338387-tetets-vietnam-war-vessels/) · [GitHub releases](https://github.com/tspindler-cms/tetet-vwv/releases) |
| **Russian Military Assets Pack** — CurrentHill | The NVA ground OOB: `[CH]` T-54 & PT-76 armor, ASU-85, ZSU/AAA guns, SA-2/SA-3 | [currenthill.com/russia](https://www.currenthill.com/russia) |
| **OH-6A Cayuse + Vietnam Asset Pack** — tobi-be | The OH-6 scout helo and its bundled period assets | [github.com/tobi-be/DCS-OH-6A](https://github.com/tobi-be/DCS-OH-6A) |
| **OV-10A Bronco** — Split-Air team | The FAC(A) "Covey" bird (a **flyable** seat — see §2) | [Forum thread](https://forum.dcs.world/topic/307951-ov-10a-bronco-mod-by-split-air-teamand-more/) |
| **Community A-4E-C Skyhawk** | The carrier Skyhawk (a **flyable** seat — see §2) | [GitHub](https://github.com/Community-A-4E/community-a4e-c) · [releases](https://heclak.github.io/community-a4e-c/) |
| **A-6E Intruder** — CorsairCat | The Naval-2 anti-armor Strike bird (**AI** — see §3) | [github.com/CorsairCat/DCS-A-6E-Intruder](https://github.com/CorsairCat/DCS-A-6E-Intruder) |
| **C-130J-30 Super Hercules** — Anubis | The Niagara airlift lifeline (**AI** — see §3) | [Forum thread](https://forum.dcs.world/topic/252075-dcs-super-hercules-mod-by-anubis/) |

> ℹ️ All of the above install into `Saved Games\DCS\Mods\aircraft\` (aircraft) or `...\Mods\tech\`
> (asset packs) — follow each mod's own readme if it differs.

---

## 2 · What you can fly — *player seats*

These are the seats a human can actually take in this campaign. Everything else the mission spawns
is **AI** (see §3 and the VWV note below).

| Seat | Role at Khe Sanh | What you need to fly it |
|---|---|---|
| **OV-10A Bronco** | FAC(A) "Covey" / light CAS | **Free mod** — the OV-10A mod (already in §1) |
| **A-4E Skyhawk** | Carrier Strike / CAS | **Free mod** — Community A-4E-C (already in §1) |
| **F-4E-45MC Phantom II** | Tbilisi Strike | **Paid module** — [DCS: F-4E Phantom II](https://www.digitalcombatsimulator.com/en/products/planes/phantom/) (Heatblur) |
| **F-100D Super Sabre** | Tbilisi CAS | **Paid module** — [DCS: F-100D Super Sabre](https://www.digitalcombatsimulator.com/en/products/planes/f-100d/) (Grinnelli Designs) |
| **UH-1H Iroquois** | Air Assault / medevac / resupply | **Paid module** — [DCS: UH-1H Huey](https://www.digitalcombatsimulator.com/en/products/helicopters/uh-1h/) (Eagle Dynamics) |

> Only **two** of the campaign's mod aircraft are genuinely **player-flyable** — the **OV-10A** and
> the **A-4E-C** (both free, already in §1). The three fast/rotary seats below them are full **paid
> DCS store modules** — and you only need the module to pilot that seat yourself; AI and other
> players' copies load fine for everyone. **Every other mod aircraft in this campaign is AI-only**
> (see §3) — the A-6E, C-130 and all the VWV birds are mods you *install* but don't *fly*.

---

## 3 · Comes with DCS / AI-only — *no action*

**Core DCS AI units (ship with the base sim — nothing to download):**
**AH-1W SuperCobra** · **CH-53E Super Stallion** · **B-52H Stratofortress** · **KC-135
Stratotanker** · **E-2C Hawkeye**. These are AI stand-ins — not pilotable.

<a name="whats-inside-vwv"></a>
**Inside Vietnam War Vessels (installed in §1 — AI-only, don't go hunting for separate mods):**
the **F-8E Crusader**, **A-1H Skyraider**, **RF-101B Voodoo** & **RA-5C Vigilante** (recon),
**EC-121D Warning Star** (AEW&C), **MiG-17F Fresco-C** (red fighters), plus L-1049 Constellation,
O-1 Bird Dog, CH-46D Sea Knight and SH-2F Seasprite. They populate the war as **AI** — you don't
fly these in this campaign even though they appear on the role cards as *roles*.

**Other AI mod aircraft (installed in §1, but AI-only — not player seats):** the **A-6E Intruder**
(CorsairCat) and **C-130J-30** (Anubis). You install these as required mods because the mission
spawns them, but they fly as **AI** — there's no cockpit to take in this campaign.

**Red side (NVA) is all AI:** the **Mi-8MTV2** (a paid ED module, but red AI here — blue players
never need to own it) and the VWV **MiG-17F**.

> Several airframes are deliberate **modern stand-ins** for the period type (AH-1W for AH-1G, A-6E
> for A-6A, F-4E for F-4B/C, CH-53E for CH-53) — see the
> [briefing's module note](Khe-Sanh-Campaign-Briefing#1--campaign-at-a-glance).

---

## 4 · Installing & keeping it tidy

- **Aircraft mods → `Saved Games\DCS\Mods\aircraft\`**; **asset packs → `...\Mods\tech\`** (each
  mod's readme is authoritative if it differs).
- Use a mod manager (**OvGME** or **DCS-Mod-Manager**) so you can disable the whole Vietnam set when
  you play other servers and re-enable it for op night. Loose mods left in `Saved Games` can trip
  the integrity check on some MP servers.
- **Match versions across the squadron.** Everyone runs the **same VWV / CurrentHill / mod
  versions** — a mismatch shows up as missing or wrong units mid-mission. Pin the versions in your
  squadron's pre-op post.
- Launch **Retribution before DCS**, then generate and fly the mission as normal
  (see [Getting Started](Getting-Started)).

---

## 5 · Quick "what do I need?" by role

**Everyone:** install all of [§1](#1--required-mods--everyone-installs-all-of-these) first — that's non-negotiable.

| If you're flying… | On top of §1, you also need… |
|---|---|
| **FAC(A)** (OV-10A) | nothing — free mod, already in §1 |
| **Carrier Strike / CAS** (A-4E) | nothing — free mod, already in §1 |
| **Tbilisi Strike** (F-4E-45MC) | the **paid** Heatblur **F-4E** module |
| **Tbilisi CAS** (F-100D) | the **paid** Grinnelli **F-100D** module |
| **Air Assault / medevac** (UH-1H) | the **paid** ED **UH-1H Huey** module |

> Many roles on the kneeboard cards are flown by **AI** in this campaign — there's no player seat to
> grab and nothing extra to install beyond §1: **Sandy A-1H**, **BARCAP F-8E**, **photo-recon
> RF-101B/RA-5C** (VWV birds), plus **Naval-2 strike A-6E** and **airlift C-130J-30** (AI mods). The
> only player seats are the five in §2.

---

*Sources for this page: the campaign's own `khe_sanh_niagara.yaml` (squadrons + settings flags),
the `USA 1970 Vietnam War` / `nva_1970` faction `requirements`, and the fork's bundled mod support
(`pydcs_extensions/`). If a download link rots, the mod's name + author is enough to find the
current host on the [ED Forums](https://forum.dcs.world/forum/1155-flyabledrivable-mods-for-dcs-world/).*
