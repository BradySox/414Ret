# Kneeboards

414Ret generates the kneeboard deck a pilot actually briefs off in the cockpit. The deck is
**upstream's page set**, with the fork's additions folded into those pages rather than bolted on as
new ones — plus you can **import your own kneeboard images** per campaign.

In DCS, kneeboards are scoped **per airframe**: every pilot flying a given type sees all of that
type's flight decks stacked together. The fork's layout is built around that fact.

---

## What's in the deck

Pages are generated per client flight, in this order. Only the first two are unconditional — the
rest appear when they have something to say, or when their setting is on.

| # | Page | When |
|---|---|---|
| 1 | **Mission Info** | always — the BLUF, flight plan, bullseye, weather |
| 2 | **Support Info** | always — package flights, radios, AWACS/tanker/JTAC, code words, airfields |
| 3 | **SITREP — Turn N** | previous turn had news, and `generate_sitrep_kneeboard` is on |
| 4 | **Notes** | the campaign has notes |
| 5 | **Task page** (e.g. SEAD/Strike Target Info) | the task has one, and it isn't superseded by the recon detail page |
| 6 | **Threat Intel Brief** | `generate_threat_intel_kneeboard` **(default ON)** and enemy air defenses exist |
| 7 | **Recon** overview / detail / airfield-departure | `generate_target_recon_kneeboard` |
| 8 | **Friendly Packages** + targets map | `generate_all_packages_kneeboard` |

A **flight index** is prepended when 2+ client flights share the airframe — see below.

### Mission Info — the BLUF

The lead page opens with a **BLUF** block that answers "what am I doing and what will kill me"
before the flight plan:

- **THREATS AIR / SAM** — compact one-line summaries of what is up and what is emitting.
- **LOADOUT** — a one-line summary of what you are actually carrying.
- **SAR** — the if-down drill, written to match the real Combat SAR model: evade toward friendly
  lines, capture risk climbs the deeper you went down, rescue tracks your last known position.
- **JAM BACKUP** — when enemy comms jamming is active, the clean backup UHF channel, printed next
  to the PUSH / SUCCESS / ABORT code words.

The flight plan below it carries a **Fuel** column — planned fuel remaining at each steerpoint —
and a one-line **RTB margin** call-out, amber when the margin goes negative. A patrol flight also
gets an **on-station endurance** line ("On station 45 min planned; fuel supports ~50 min before
bingo"), because the planned dwell is doctrine and the gas is the real answer.

Reference steerpoints (divert, bullseye) print no Time/GSPD — a chained ETA past the landing point
is noise, not information.

![The Mission Info kneeboard page: a BLUF block listing task, code words, jam-backup channel, air and SAM threats, loadout and the SAR drill, above the airfield table and a flight plan whose right-hand column shows planned fuel at each steerpoint](https://raw.githubusercontent.com/BradySox/414Ret/main/docs/wiki/img/kneeboard-mission-info-bluf.png)

*A real generated Mission Info page (Baltic Fury, an F/A-18F on OCA/Runway). The BLUF answers the
brief before the flight plan starts; the plan's right-hand **Fuel** column and the **RTB margin**
line below it are the retired Fuel Ladder page, folded in where you actually read it.*

### Support Info — comms and the code words

Package flights, the radio ladder, AWACS/tanker/JTAC, and the departure/arrival airfield rows. The
colour-keyed **code words** block rides here.

The top row of that table is **your own flight on its intra-flight channel** — the people directly
flying with you — which is why it reads **`Flight`** rather than a callsign, and why it sits on a
different channel (COMM1) from the rest of the package (COMM2). Give the flight a **custom name**
in the ATO and that name replaces `Flight` here.

![The Support Info kneeboard page: the package's flights with callsigns, tasks, types and radio channels, a colour-keyed code-words block, then AEW&C and tanker tables with frequencies, TACAN and time on station](https://raw.githubusercontent.com/BradySox/414Ret/main/docs/wiki/img/kneeboard-support-info.png)

*The same flight's Support Info page. Every other flight in the package with its channel, the
code words colour-keyed (blue push, green success, red abort — "(you)" marks your own call), then
the AEW&C and tanker ladders with TACAN and time on station.*

### The threat cards

The enemy air-defense dossier: one card per system with guidance, band, range and ceiling,
**recon-fog aware** — you get cards for what you have actually scouted, not the ground truth. This
is on by default and is the single most useful page in the deck for a SEAD or strike crew.

### Shared-airframe flight index

DCS stacks every deck for an airframe together, so a four-flight Hornet mission is a wall of pages.
When 2+ client flights share a type, the generator keeps each flight's pages in a contiguous,
callsign-sorted block and prepends a one-page **index** — callsign, task, start page — so you can
find yours. A lone flight skips it.

### Layout

Sparse pages (Combat SAR, Support Info, Mission Info) use a light heading + underline-rule layout
that fills the page instead of boxing content into a corner, and long friendly-package lists flow
into two columns. Tables measure their rendered width and word-wrap the widest column rather than
running off the right edge. A theme-aware four-colour scheme — blue nav/comms, amber threats/fuel,
green success, red abort — runs across the pages that use it.

---

## Campaign SITREP page

After a turn is resolved, the next mission's deck carries a **"SITREP — Turn N"** page: a cockpit
intel brief of what happened last turn — per-side losses, base captures, Combat SAR rescues, MIA
evaders and POWs. Enemy losses are framed as **"claimed"** to respect the recon-fog model (you
don't get perfect BDA for free). It is absent on turn 1, on a quiet turn, or when the toggle is
off.

It sits on **its own page** rather than at the bottom of Mission Info: a busy turn's POW/MIA list
clipped at the page edge (found on a flown deck, 2026-07-19).

---

## Custom kneeboard import

You can add your own kneeboard pages per campaign — a squadron SPINS card, a target photo, a comms
ladder, anything:

1. Open the **Kneeboards** toolbar action (`QCustomKneeboardsWindow`).
2. Import an image once. It's stored **in the campaign save** (name + PNG + optional airframe), so it
   travels with the campaign and never leaks across campaigns the way the global `Kneeboards/` folder
   does.
3. At generation it's injected into **every client flight** (or just one airframe, if you scoped it).

Old saves migrate automatically (no custom kneeboards until you add them).

---

## Settings reference

All five live on the **Kneeboards** settings page.

| Setting | Default | Effect |
|---|---|---|
| `generate_threat_intel_kneeboard` | **ON** | The enemy air-defense dossier page (recon-fog aware) |
| `generate_sitrep_kneeboard` | **ON** | The previous-turn SITREP page |
| `generate_target_recon_kneeboard` | OFF | Recon overview / detail / airfield-departure pages |
| `generate_all_packages_kneeboard` | OFF | Friendly-packages list + targets map |
| `generate_dark_kneeboard` | OFF | Dark theme, for night flying |
| `target_recon_extra_threat_search_nmi` | 0 | Widen the recon page's threat search beyond the target area |
| Custom kneeboards | — | *Kneeboards* toolbar action — per-campaign images injected into client flights |

---

## Not in the deck

The cover page, compact deck and Brief Sheet were removed in the 2026-07-13 pass.
The deck opens on Mission Info; there is no cover page, no compact 3-4 page mode, and no separate
Brief Sheet or brevity card. Fuel is the **Fuel** column on the flight plan plus its RTB margin
call-out, not its own page. Code words live on Support Info.

---

## See also

- [Getting Started](Getting-Started) — opening the kneeboard in the cockpit
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance) — approximate-mode kneeboard pages
- [Mission Planning](Mission-planning) — packages, comms, and code words that feed the deck
- [Combat SAR](Combat-SAR) — the Combat SAR kneeboard page
