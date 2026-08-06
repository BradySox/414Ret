# Operation Enduring Resolve (COIN) — Campaign Briefing

**Afghanistan - Operation Enduring Resolve (COIN)** is the 414th's counter-insurgency campaign:
Helmand and Uruzgan provinces, **April 2006**, on the **DCS Afghanistan** map. It is a fork of
Starfire's *Operation Shattered Dagger* laydown, rebuilt as a **living insurgency**: the enemy
regrows from its ammo caches, resupplies down a real ratline, and can't be beaten by body
count.

This is not a front-line war. There are **no front lines** at all — it's strongholds, towns,
caches, convoys, and a clock.

> **The one-paragraph version:** find and destroy the **ammo caches** that feed each stronghold's
> regeneration, interdict the **ratline convoys**, and take the strongholds with **air assaults**
> — then *hold* them, or the insurgency walks back in. Killing fighters wins you almost nothing.
> Killing their supply wins the war.

---

## What you need

| Requirement | Detail |
|---|---|
| **DCS Afghanistan map** | Required — the whole laydown sits on real-world Helmand/Uruzgan coordinates. |
| **High Digit SAMs (Ultimate Compilation)** | Recommended — the insurgent ZU-23 technicals/emplacements are HDS content. Without the mod they drop silently (the campaign still plays, with less AAA texture). |
| **A NEW game** | The campaign, factions, and `.miz` are current-build content — start fresh, don't load an old save. |

The campaign pre-seeds its own toggles (the COIN stack, convoy interdiction, airbase
harassment, carrier ops, HDS) — select it in the New Game wizard and it lights up correctly out
of the box.

---

## The situation

The insurgency holds **13 strongholds** across Helmand, Farah, and Uruzgan — 11 seized forward
FOBs plus the Farah and Tarinkot airfield anchors. Its life-support is on the ground next to
them: **28 ammo caches** (2 per FOB, 3 at each airfield) and a **9-corridor ratline** of real
driveable roads — Highway 1 (the Ring Road), Route 611 up the Helmand valley, and the Uruzgan
road — moving genuine reinforcement columns between strongholds.

Nine **population centers** — Lashkar Gah, Gereshk, Sangin, Musa Qala, Now Zad, Kajaki, Marjah,
Delaram, Tarin Kowt — were authored as permanent no-strike rings. The ROE layer that enforced
them was removed on 2026-07-21, so nothing in the game prices a careless shot any more; half the
cells and caches still sit in and around the towns, and digging them out cleanly is now a matter
of your own discipline rather than a scored one.

**The coalition** flies from Kandahar and Camp Bastion, with a carrier — **CVN-74 John C.
Stennis** — holding station in the Gulf of Oman, ~400+ NM from the AO, flying the real OEF
Arabian-Sea cycle (see [the carrier's war](#the-carriers-war) below).

## Victory — how the campaign ends

> **Changed 2026-07-21.** This campaign was originally won or lost on a **political-will
> economy** — a Coalition mandate that drained from casualties and collateral damage against
> an insurgent momentum meter — with a negotiated ending. **That economy was removed**, along
> with the kill-box / population-ring ROE layer that priced your shots into it.

The campaign currently ends on Retribution's **standard territorial rules**: hold the map,
take the enemy's bases. It does **not** author a custom `victory:` block, so there is no
insurgency-specific win condition today — clearing and *holding* the strongholds is the
practical objective, and the §C1.5 re-infiltration mechanic is what makes "holding" cost
something.

Play it as a campaign you grind down rather than one you win on points: kill the ammo caches
to throttle regeneration, hold what you clear, and hunt the leadership and the cells before
they mature.

## The living insurgency

What makes this campaign different from a stronghold shooting gallery
(*toggle: `coin_insurgency`, pre-seeded on*):

- **Cells regenerate.** Every insurgent stronghold refills its garrison each turn toward its
  turn-0 strength — real units revived in place, never phantom spawns, and never *growing* past
  where the campaign started. Clear a position and leave it alone, and it comes back.
- **Caches are the throttle.** Each stronghold's regen rate scales with its surviving ammo
  caches. Kill them all and the trickle collapses to a **25% residual floor** — infiltration
  never fully stops; it's the will economy that ends the war. Each cache kill is also a direct
  momentum hit (the double lever, worth ~4 points).
- **Your recon picture can lie.** Revived units **don't update your last recon snapshot** — a
  position you photographed dead last week is shooting again until you re-fly the recon. "We
  cleared that ridge already" is exactly the war this is modelling.
- **Only insurgent kit comes back** — infantry, technicals, light guns, MANPADS. Nothing
  armored, nothing radar-guided ever regenerates.
- **The ratline feeds the anchors.** Real convoys (up to ~10 vehicles, several concurrent, on
  distinct roads) run the 9 corridors, framed as external logistics from over the border. A
  convoy killed on the trail is a real loss and a momentum hit; one that arrives is real
  reinforcement. In Phase 2 the network **surges the trail** — the convoy budget doubles.

Turning `coin_insurgency` off reverts the campaign to a static one-shot clearance.

## The three-act shape

The campaign was authored as a three-act arc — **Disrupt the Network → Clear and Hold →
Break the Momentum** — and the laydown still reflects it, but the `phases:` machinery that
drove it (with its ROE kill boxes and objective ticks) was removed on 2026-07-21. Treat the
acts as **narrative guidance for how to sequence your war**, not as anything the game tracks:

1. **Disrupt** — map the insurgency before fighting it. Recon the Route-611 green zone and the
   Highway-1 corridor; find the caches and the cells before committing ground.
2. **Clear and Hold** — take the strongholds and *garrison* them. The trail surges here (the
   red tempo schedule doubles the convoy budget), so interdiction matters most in this act.
3. **Break the Momentum** — hunt the leadership and the dispersed cells, and keep the caches
   dead so the regeneration you shut off stays off.

## Your forces

| Base | Squadrons |
|---|---|
| **Kandahar** | A-10C ×4 (CAS) · RNLAF 322 Sqn F-16CM ×4 (BAI) · RAF IV(AC) Sqn AV-8B ×4 (CAS) · 391st FS F-15E ×4 (Strike) · B-1B ×2 (Strike) · KC-135 ×2 · C-130J ×4 |
| **Kandahar Heliport** | UH-60A ×4 (Air Assault) · 1-17 CAV OH-58D ×4 (CAS) |
| **Camp Bastion** | AV-8B Night Attack ×4 (BAI) · E-3A ×1 (AEW&C) |
| **Camp Bastion Heliport** | 12th CAB AH-64D ×4 (CAS) · CH-47F ×4 (Transport) |
| **CVN-74 John C. Stennis** *(Gulf of Oman)* | VFA-113 F/A-18C ×6 (BAI) · VA-165 A-6E tankers ×3 · E-2C ×1 |

A deliberately air-assault-heavy mix: the UH-60s/CH-47s and their Apache/Kiowa escorts are how
you take strongholds; the fast air is how you make that survivable.

## The enemy

**No aircraft. No armor.** The insurgency's teeth are era-honest:

- **AAA everywhere** — ZU-23 emplacements and technicals at all 13 strongholds, plus MANPADS.
  Low is where it hurts; treat every stronghold as a flak trap for anything below ~10k.
- **SA-9/SA-8/SA-13/SA-15 SHORAD** at 7 strongholds.
- A thin **radar-SAM crust at the three anchors** — an SA-6 battery at Farah, SA-3 at Tarinkot,
  and a second SA-6 at FOB Frontenac. A real (small) SEAD/DEAD job, and deliberately **never
  inside a town ring**, so the suppression war stays AI-plannable.
- The economy behind it: a small income trickle plus the regen/ratline machinery above.

## The carrier's war

*Toggle: `long_range_carrier_ops` — pre-seeded on; new in this campaign.*

The Stennis holds ~400+ NM out — far beyond the stock planner's range gate, which would normally
leave the whole air wing on deck. With carrier ops on, the boat fights anyway:

- **One deterministic carrier package a turn**: a 2-ship Hornet **strike** (preferring ammo
  caches — thematically the carrier's job, and always ROE-legal), an **A-6E buddy tanker**
  holding a real orbit off the boat for launch/recovery gas, and an **E-2C** on station.
- The commander flies the boat's **spare Hornets on SEAD** against the radar crust — and any
  carrier flight in a tanker-less package is automatically routed to tank from the boat's own
  A-6 on its way in and out.

Expect Navy jets over Helmand every turn, properly tanked, without you fragging any of it.

## How to fight it — the priorities

1. **Recon first.** The fog model is the campaign. Fly TARPS/recon over strongholds to find the
   caches — and **re-fly** positions you cleared, because your old photos go stale as cells
   regenerate.
2. **Kill caches.** The single best target class in the campaign — it throttles regeneration at
   the source. The carrier's daily strike helps; deliberate Strike/BAI packages do the heavy
   lifting.
3. **Work the ratline.** Right-click an enemy supply route to frag an Armed Recon sweep down
   the road. Every convoy killed is real reinforcement denied. During the trail surge this is a
   target-rich environment — and ignoring it feeds the strongholds.
4. **Assault and hold.** Air Assault is the territorial lever — Frontenac, then Hadrian, then
   Tarinkot. A stronghold flipped blue stops regenerating, but an ungarrisoned one gets
   re-infiltrated over about four announced turns: taking ground is the easy half.

## Status

The whole COIN stack — regen and revival, the cache throttle to the 25% floor, the inverted will
profile, the 3-phase arc, kill-box geometry, the carrier package — is engine-verified and
CI-locked, but the campaign **has not yet had its played in-game pass** (checklist P1/P2). Feel,
pacing, and the flown carrier cycle are exactly what the first campaign through it will be
testing. Fly it and report.

## See also

- **[Vietnam Ops § Convoy interdiction](Vietnam-Ops#4--convoy-interdiction-steel-tiger)** — the
  trail-convoy mechanics the ratline rides on.
- **[Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)** — why your recon picture
  goes stale.
- **[Custom Campaigns](Custom-Campaigns)** — how the campaign's YAML (settings preseeds,
  supply corridors, squadrons) is authored.
