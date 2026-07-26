# 414th — Jack Ryan-era campaign ideas (design brainstorm)

**Status: ideas only — nothing built, nothing preseeded, no code touched.** This is the
expanded shortlist requested 2026-07-26: DCS campaigns and missions drawn from **Tom Clancy's
original Jack Ryan novels** (the Ryan Sr. line — *not* the Jack Ryan Jr. books), plus the two
Ryan-universe prequels that share the same cast. The brief was the **era** as much as the
plots: roughly **1982 → 2005**, the late-Cold-War-into-post-Cold-War window the books live in.

Each entry is written so it can be handed straight to a campaign build: map, factions that
already exist in `resources/factions/`, a laydown sketch, a 3-phase arc, which 414th features
it exercises, and an honest build cost.

> **Not covered here:** submarines (DCS has none playable), CT/ground-team ops (*Rainbow Six*),
> and anything set after ~2010. See §5 for what was considered and set aside.

---

## 0. Why this era fits this fork

The Ryan novels sit almost exactly on top of the hardware the 414th already ships content for,
and — unusually — on maps DCS actually sells.

**Factions already in the repo that cover the era with no authoring at all:**

| Story window | Blue | Red |
|---|---|---|
| 1982–88 late Cold War | `usn_1985`, `usa_1975`, `bluefor_coldwar`, `blufor_late_coldwar` | `russia_1980`, `russia_1980_red_tide`, `russia_1975 (Mi-24P)` |
| 1988–91 Gulf | `NATO_Desert_Storm`, `usa_1990`, `usn_1985` | `iran_1988`, `iraq_1991` |
| 1994–2000 | `usa_1990`, `usn_2005`, `usa_2005` | `japan_2005`, `iran_2015`, `russia_1990` |
| Irregular / cartel / mujahideen | `oef_coalition_2006`, `usa_1975` | `insurgents`, `insurgents_hard`, `peru_1995`, `taliban_2001` |

**Features that make the era *play* like the books rather than just look like them:**

- **§3 recon fog + TARPS** — the Ryan novels are intelligence stories. A campaign where you
  cannot see the enemy order of battle until someone flies the film back is the single closest
  mechanical analogue to the source material this fork owns.
- **§70 COMINT + §51 comms jamming** — the signals-intelligence half of the same idea.
- **§49 mobile missile relocation** — the SCUD/theatre-ballistic hunt, straight out of
  *Executive Orders*.
- **§21 CSAR / POW arc** — *Clear and Present Danger* and *Without Remorse* are both, at their
  core, "we left people behind and we are going to go get them."
- **§62 modex / §65 carrier comms / §72 deck dressing** — the 1980s CVW is the Ryan visual
  signature; these three are what make a Nimitz deck read as 1985 rather than generic.
- **§79 decoy zones / §17 planner unpredictability** — deception and an enemy that does not
  hit the same targets every turn.

**Deliberate non-duplication:** *Red Storm Rising* is not a Ryan novel (Ryan does not appear),
and the fork's **Red Tide** already occupies that exact ground — Fulda Gap, 1988, Soviet
combined-arms offensive. Nothing below overlaps it.

---

## 1. Shared building blocks

Worth authoring **once** and reusing across whichever of these get built:

1. **The 1985 CVW air wing preset** — F-14A, A-6E, A-7E (or F/A-18A), EA-6B, E-2C, S-3B,
   KA-6D. `usn_1985` already fields most of it; the value-add is a squadron block with real
   1980s squadron identities (the §23 country/nickname machinery + the Desert Storm campaign's
   "every squadron is its real unit" precedent).
2. **A Soviet PVO/GCI doctrine profile** — the Vietnam layer proved a doctrine can carry an
   era (`VIETNAM_AIR_DEFENSE_DOCTRINE`, `gci_ambush`, era engagement ranges). A
   `SOVIET_PVO_DOCTRINE` — rigid ground control, late scramble, narrow tasking whitelist —
   would serve Red October, Cardinal, and any 1980s red side, and is reusable far beyond
   these campaigns.
3. **An escalation-ladder victory profile** — several of these stories are about *not* going
   to war, or about stopping one. §75 custom victory conditions already support
   "destroy_targets", "lose_cps", "min_turn"; a campaign whose win condition is
   *survive N turns without losing X* is authorable today with no engine work.

---

## 2. Tier 1 — campaign-scale, canonical map fits

### 1. *Debt of Honor* — "Operation Dateline" (Marianas, 1996) ⭐ recommended first build

**Source.** Japan's zaibatsu conspiracy seizes the Marianas after crippling two US carriers;
the US counteroffensive kills the E-767 AWACS picket, sinks the Aegis destroyer screen, and
retakes the islands. It is the only Ryan story whose geography **ships in DCS, island for
island**.

**Map.** `MarianaIslands`. Existing laydowns to crib from: `pacific_repartee` (US Navy 2005 vs
China 2010 — nearly the right structural shape already), `marianas_guam_barrigada`,
`marianas_guam_landing_at_agat`, `operation_velvet_thunder`.

**Sides.**
- **Blue:** `usn_2005` trimmed back to mid-90s (F-14D, F/A-18C, EA-6B, E-2C, S-3B) off a CVN,
  plus land-based F-15C / B-1B out of Andersen.
- **Red:** `japan_2005` is the ready-made starting point — fork it to `Japan 1996 (Dateline)`
  and trim to F-15J, F-2/F-1, E-767 (E-3 stand-in), Kongo-class Aegis (Burke hull), Patriot
  and Hawk belts, Type-81/Type-11 SHORAD.

**Laydown sketch.**
- RED holds **Saipan** (the anchor — Patriot + the E-767 orbit) and **Tinian** (the second
  field, the resupply node).
- BLUE holds **Andersen AFB, Guam** as the land anchor plus the CVN off the east.
- No land front line — this is an island/naval campaign, so the "front" is the sea lane
  between Guam and Saipan. That makes it a natural fit for §78 sea-supply convoys and the
  front-less-laydown features (§36 stronghold-proximity harassment, §50 ambient convoys).

**Phase arc.**
1. **Blind them** — kill the E-767 orbit and the island EWR chain. Long-range Tomcat/AMRAAM
   work against a defended AWACS; forces real SEAD sequencing (§69) because the Patriot rings
   cover the orbit.
2. **Sink the screen** — the Kongo-class Aegis pickets. Harpoon/SLAM-ER packages, Tomahawk
   raids off the escorts (§63), and the first real test of §78 coastal batteries.
3. **Retake the rocks** — CAS/BAI onto Saipan and Tinian, interdict the inter-island resupply
   (§78 convoys running the gauntlet), amphibious support.

**Feature wiring.** §63 cruise raids · §78 sea convoys + coastal engagement · §69 SEAD-before-strike ·
§60 SAM redundancy (Patriot already fields two STRs) · §65/§72 carrier comms + deck dressing ·
§62 modex · §3 recon fog (island target sets are perfect for TARPS).

**Build cost.** ~1–2 sessions for a design note + laydown; the `.miz` is the ME work
(decorate-a-base pattern like Inherent Resolve). No new engine features required.

**Risks / open calls.**
- Blue-hardware-on-both-sides is the selling point *and* the risk: red F-15Js are as good as
  blue F-15Cs, so the campaign is hard by construction. Wants a difficulty pass.
- Whether Guam is contested or a safe rear anchor is a **design choice**, not a canon lookup —
  recommend safe rear anchor so the player always has a field.

---

### 2. *Executive Orders* — "The United Islamic Republic" (Persian Gulf, ~1996)

**Source.** Iran absorbs a shattered Iraq into the United Islamic Republic and drives on Saudi
Arabia and Kuwait; the book's climax is the annihilation of a road-bound UIR armoured corps by
air power and a US armoured cavalry regiment.

**Map.** `Persian Gulf`. Existing laydowns: `tanker_war_1988` (already US Navy 1985 vs Iran
1988 — the closest structural sibling in the repo), `battle_of_abu_dhabi`, `WRL_PG_Wargames`.

**Sides.**
- **Blue:** `usa_1990` / `NATO_Desert_Storm` + `usn_1985` for the boat — F-15C/E, F-16C,
  A-10A, F-14B, F/A-18C, E-8 JSTARS stand-in (E-3 or a recon platform).
- **Red:** fork `iran_1988` forward to ~1996 and graft the surviving `iraq_1991` armour and
  Scud batteries — **`United Islamic Republic 1996`**. The set piece writes itself: **Iranian
  F-14A against US F-14B**, the only place in DCS where that fight is era-honest.

**Laydown sketch.**
- RED: Bandar Abbas / Shiraz / Bushehr as the Iranian rear, a captured Iraqi-analogue forward
  belt, and a **single armoured axis** down the coast highway toward the Saudi border — the
  book's road-bound corps, expressed as a supply-route corridor plus §56 motorpool depots.
- BLUE: Saudi/UAE fields + a CVN in the Gulf.
- One front, one highway. The campaign's whole tension is *stop the column before it arrives*.

**Phase arc.**
1. **The bio-attack turn** — campaign opens with blue restricted and reacting (a low
   opening-package cap, hostile weather); red has the initiative.
2. **Break the Scud threat** — §49 mobile missile relocation makes this a genuine hunt rather
   than a target list.
3. **Kill the column** — the interdiction massacre. §35/§50 convoy interdiction + §56
   motorpools + §67 weather-aware planning (the sandstorm that grounds the low-level attack).

**Feature wiring.** §49 SCUD hunt (the marquee) · §56 motorpools · §35/§50 convoy interdiction ·
§67 weather-aware planning · §63 Tomahawk opening night · §52 C2 decapitation (the UIR command
network) · §75 victory: *hold the border* as a loss condition rather than a territory win.

**Build cost.** ~1–2 sessions. Cheapest of the Tier 1 three because the roster, the map and a
sibling campaign (`tanker_war_1988`) all already exist.

**Risks / open calls.**
- Needs a faction fork (`iran_1988` → 1996) — an era audit like the Red Tide one, not free.
- The "annihilate a column" climax is only satisfying if the column is *big*; check the §50
  ambient-convoy caps and the §35 concurrent-convoy budget before promising it.

---

### 3. *The Cardinal of the Kremlin* — Afghanistan, 1985 (fly for the Soviets)

**Source.** The novel's Afghan arc: the Archer, Stinger missiles arriving in-country, and — as
the climax — a mujahideen strike on the Soviet ground-based laser complex at Dushanbe. It is
the Ryan book with the most *air* in it that nobody builds.

**Map.** `Afghanistan`. Existing laydowns to fork: `coin_enduring_resolve` (the fork's own COIN
stack, tuned), `graveyard_of_empires`, `operation_shattered_dagger`.

**The twist.** **Blue = the Soviet 40th Army.** Su-25, Mi-24P (`russia_1975 (Mi-24P)` exists
precisely for this), MiG-23, An-26, Mi-8. **Red = the mujahideen** (`insurgents` /
`insurgents_hard` / `taliban_2001` retimed) whose one decisive weapon is the Stinger.

This is the cheapest Tier 1 build by a wide margin, because it is a **reskin of the existing
Enduring Resolve COIN stack to 1985** rather than a new system.

**Laydown sketch.**
- BLUE (Soviet): Bagram as the main base, Kandahar and Jalalabad forward, Kabul as the rear.
- RED: the existing ER stronghold pattern — valley strongholds, ammo caches, the ratline over
  the Pakistan border.
- The caches are the campaign: shut them down and the insurgency throttles (§C1 regen), leave
  them and it regenerates forever.

**Phase arc.**
1. **Before the Stinger** — Hinds work low and with impunity. Establish the rhythm.
2. **The Stingers arrive** — MANPADS seed into the red roster mid-campaign. Low-level flight
   becomes lethal; the player has to re-learn the war from medium altitude.
3. **The convoy war / the laser** — protect the Salang-corridor convoys (§50 ambush is
   *literally* this), and optionally a one-off deep strike on the SDI laser complex as the
   campaign's capstone.

**Feature wiring.** The whole COIN suite (§C1 regen, §C1.5 re-infiltration, §IED, §HVT, §C4
dispersed cells, concealment circles) · §36 airbase harassment (Bagram under rocket fire is
canon, not flavour) · §50 convoy ambush · §70 COMINT · §79 decoy zones.

**Build cost.** ~1 session for the design note; the laydown is a retime of an existing one.
The main real work is the **mid-campaign Stinger introduction** — check whether the date-gate
machinery (§24 / weapon date restriction) can express "MANPADS appear at turn N", or whether
it needs a phase-style toggle.

**Risks / open calls.**
- Playing the Soviets is a **taste call** — some squadrons love it, some will not fly it.
  A blue-side "CIA-supported" variant is possible but has much less DCS-flyable hardware.
- The Stinger step-change is the design's entire spine. If it cannot be scheduled, the
  campaign is just another COIN map.

---

## 3. Tier 2 — strong stories, stand-in geography

### 4. *The Hunt for Red October* — Kola / Norwegian Sea, November 1984

**Source.** The entire Soviet Northern Fleet surges into the Atlantic to hunt one defecting
submarine; the USN shadows, and for most of the story **nobody is allowed to shoot**.

**Map.** `Kola`. Existing: `operation_frostbite` (test build), `northern_russia`. The Kola
laydown gives you Severomorsk, Olenya, Monchegorsk — the real Northern Fleet air estate.

**Sides.** Blue `usn_1985` (F-14A with Phoenix, A-6E, S-3B, E-2C, KA-6D) plus RAF/Norwegian
land-based air; red `russia_1980` (Tu-95/Tu-142 Bears, Tu-22M Backfires, MiG-31, Su-27,
Kirov/Slava/Udaloy surface groups, the Kola SAM belt).

**What makes it different from every other DCS campaign.** It is an **intelligence and
escalation** campaign, not an attrition one:
- **Phase 1 — Shadow.** Intercept and *photograph* Bears (§3 TARPS is the mission, not a
  side-task). Nobody shoots. Victory is measured in what you found out, not what you killed.
- **Phase 2 — Posture.** Backfire regiments range on the battle group; you must break up raids
  before they launch, which is a timing and geometry problem, not a dogfight.
- **Phase 3 — The one that goes loud.** A surface action group has to be dealt with. §63
  Tomahawks, A-6E Harpoons, and the first genuine losses of the campaign.

**Feature wiring.** §3 recon fog (the campaign's whole point) · §70 COMINT (finding the fleet
by its emissions) · §1 QRA forward defense + a Soviet GCI doctrine · §47 continuous clock (the
Arctic winter night — this is the campaign that would sell §47) · §63 cruise raids · §78
coastal batteries · §75 victory-by-condition rather than by territory.

**Build cost.** ~2 sessions. The laydown is straightforward; the **doctrine and victory
profile are the real work**, and both are reusable.

**Risk.** The "shadow, don't shoot" phase is either the most atmospheric thing the fork has
ever shipped or it is boring. Prototype Phase 1 as a single mission before committing.

---

### 5. *Clear and Present Danger* — "Operation Reciprocity", 1989

**Source.** Deniable US strikes on cartel infrastructure — an LGB through a cartel leadership
meeting, gunship attacks on airstrips and processing labs — and then the light-infantry teams
inserted into the mountains are politically abandoned. The back half of the book is a rescue.

**Map.** No Colombia in DCS. Two workable stand-ins:
- **`MarianaIslands`** — jungle, mountain spine, small airstrips, coastline. Visually closest.
- **`Syria`** or **`Sinai`** southern sectors — easier to author, less atmospheric.

**Sides.** Blue: a small, deniable package — F-15E-analog, an AC-130 stand-in, MH-53/MH-60,
plus a drone (the fork auto-fields one, §3). Red: `peru_1995` is the ready-made cartel-era
Latin American roster; trim to technicals, ZU-23, a handful of SA-7/SA-16, and an airstrip +
lab network as the strike target set.

**Phase arc.**
1. **SHOWBOAT** — insert and support the ground teams; interdict the airstrips. Small
   packages, no AWACS, no tanker — the deniability *is* the difficulty.
2. **RECIPROCITY** — the leadership strike. One target, one bomb, hard ROE.
3. **Abandoned** — support is withdrawn; the teams are compromised (§50 ambush), people go
   MIA (§21), and the campaign's win condition becomes **getting them out**.

**Feature wiring.** This is the campaign that shows off **§21 CSAR/POW as a story** rather than
a system — MIA evaders, the depth-weighted capture roll, the recovery surge — plus §75 custom
victory (`destroy_targets` = the labs; losing the teams is the defeat condition), §3
concealment, and the drone-JTAC path.

**Build cost.** ~1 session. Smallest footprint of anything here — few control points, small
air wing, short arc. **The best candidate if the goal is "something flyable soon."**

---

## 4. Tier 3 — standalone missions / mini-arcs

Each is one to three missions, not a campaign. All are cheap.

### 6. *Patriot Games* — the ULA camp strike (North Africa, 1987)
One package, no escort, no tanker, no AWACS, watched from a satellite feed. **Map:** `Sinai` or
`Syria` desert south. **The design point:** total intelligence asymmetry — the player has
perfect pre-strike imagery of a camp that has *no* air defence, and the entire mission is about
positive identification and not hitting the wrong tents. §3 fog off, §5 approximate-target-
location on, tight ROE. A 20-minute mission that is entirely about restraint.

### 7. *The Sum of All Fears* — the lost bomb (Sinai/Golan, October 1973)
The novel opens with an Israeli A-4 Skyhawk carrying a nuclear weapon being shot down during
the Yom Kippur war; the bomb is never recovered. **Ready-made in this repo:**
`operation_gazelle` (Sinai, Israel 1973 vs Egypt 1973) and `golan_heights_lite`, plus the
`israel_1973` / `syria_1973` / `egypt_1973` factions. Fly the strike; get shot down; that is
the mission. A dark, memorable one-off with **zero authoring cost beyond the mission itself**.

### 8. *The Sum of All Fears* — "Broken Arrow" escalation (Med/Gulf, 1991)
After the detonation, US and Soviet forces stand at DEFCON 2 and every contact risks the war
nobody wants. **The mechanic is the point:** a short campaign where the victory condition is
**de-escalation** — survive N turns without losing a capital asset, with every engagement
raising the stakes. §75 supports this today (`min_turn` guard + loss conditions, no win
condition beyond survival). Pairs naturally with the Red October doctrine work.

### 9. *Without Remorse* — Operation BOXWOOD GREEN (Vietnam, 1970)
Ryan-universe prequel (John Kelly / John Clark). A Son Tay-style raid on the SENDER GREEN POW
camp: A-1 Sandys, helicopter insert, flak suppression, and an extraction under time pressure.
**Ready-made in this repo:** `1968_Yankee_Station` + the whole Vietnam Ops suite (§32–§39) +
the §21 POW machinery. Arguably the cheapest single mission on this list with the highest
production value, because every system it needs already flew.

### 10. *Red Rabbit* — the Budapest exfil (Central Europe, 1982)
The covert exfiltration of a KGB defector out of Hungary. Almost no air combat — a night
transport or helicopter run, a border crossing, and the threat of being intercepted rather
than the certainty. **Map:** `GermanyCW` or `Caucasus` as a stand-in. **The design point:** a
mission with no weapons employment where success is *not being noticed*. Would need a small
amount of scripting (a detection/alert state), so it is the least "free" of the Tier 3 set —
but it is also the only one that would feel genuinely new.

---

## 5. Considered and set aside

| Story | Why not (yet) |
|---|---|
| *The Bear and the Dragon* (2000) | China invades Russian Siberia. **No map** — no Siberia, no Amur. Caucasus/Kola stand-ins lose everything that makes it distinctive. Revisit if a suitable terrain ships. |
| *Rainbow Six* (1998) | Counter-terrorist ground ops. Almost no air component; the one helicopter insert does not carry a campaign. |
| *Red Storm Rising* (1986) | Not a Ryan novel, **and Red Tide already owns this ground** (Fulda Gap 1988). Deliberately excluded to avoid duplicating a locked campaign. |
| Amazon *Jack Ryan* series | It *is* Ryan Sr., so it is in scope by the letter of the brief — but S1 (Syria, 2018) and S3 (Czechia, 2020s) sit **outside the 1982–2005 era window** the brief actually asked for. S1's ISIS-analogue arc is also near-identical to the fork's existing Inherent Resolve. |
| *Red October* submarine gameplay | DCS has no playable submarine and no meaningful ASW. Handled above by abstracting the hunt into recon/intel. |

---

## 6. Build-cost summary and suggested order

| # | Idea | Map | Scale | Cost | New engine work? |
|---|---|---|---|---|---|
| 5 | Clear and Present Danger | Marianas / Syria | Mini-campaign | **Lowest** | None |
| 9 | Without Remorse (BOXWOOD GREEN) | Caucasus (Vietnam) | 1 mission | **Lowest** | None |
| 7 | Sum of All Fears (1973 opening) | Sinai | 1 mission | **Lowest** | None |
| 3 | Cardinal of the Kremlin | Afghanistan | Campaign | Low | Mid-campaign MANPADS gate |
| 2 | Executive Orders | Persian Gulf | Campaign | Medium | Faction fork (Iran 1996) |
| 1 | **Debt of Honor** | Marianas | Campaign | Medium | None (difficulty pass) |
| 8 | Sum of All Fears (Broken Arrow) | Persian Gulf / Med | Mini-campaign | Medium | Victory profile only |
| 4 | Hunt for Red October | Kola | Campaign | High | Soviet PVO doctrine, shadow phase |
| 6 | Patriot Games | Sinai / Syria | 1 mission | Low | None |
| 10 | Red Rabbit | GermanyCW | 1 mission | Medium | Detection/alert scripting |

**Suggested order if the goal is momentum:** #5 or #9 first (something flyable in a session),
then **#1 Debt of Honor** as the flagship campaign, with #3 Cardinal as the cheap second
campaign because it rides the COIN stack.

**Suggested order if the goal is the flagship:** #1 Debt of Honor straight away — it is the
only Ryan story whose map DCS actually sells, and that will never be truer than it is now.

---

## 7. Open calls for the DM

1. **Soviet-side play** (idea #3) — is flying for the 40th Army acceptable to the squadron, or
   should every campaign put the player on the NATO/US side?
2. **Colombia stand-in** (idea #5) — Marianas for the jungle look, or Syria/Sinai for the
   cheaper build?
3. **The shadow phase** (idea #4) — is a no-shooting intelligence phase something the squadron
   would fly, or is it a design that reads better than it plays?
4. **Naming** — do these ship under their book titles, or under invented operation names with
   the source acknowledged only in the design notes?

---

*Nothing in this document is registered in `game/fourteenth/features.py`, preseeded into any
campaign, or reflected in the in-game-pass checklist. It becomes real work only when one of
these is picked up and given its own design note.*
