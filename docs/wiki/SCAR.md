# SCAR — Strike Coordination and Reconnaissance

SCAR is a player-flown hunt. You work a defined area to find and kill a moving high-value target
(HVT) hidden among look-alike decoys and clutter, before it reaches safety. It is the air-to-
ground answer to "the target is out there moving — go find the real one and prosecute it," and it
rewards reading the picture over trusting a single pin on the map. SCAR sits between
[CAS](Mission-planning) (needs troops in contact), BAI (a known, fixed group), and Armed Recon
(small-radius targets of opportunity): the skill it tests is **discrimination**, not a free-fire
sweep.

`FlightType.SCAR` is **player-selectable** when you build a package. The auto-planner does not
frag it by default (see [auto-planning](#auto-planning-off-by-default)). BAI remains the AI's
anti-armor/convoy task — SCAR is the human discrimination puzzle, not an AI behavior.

> **In-game-pass status:** the planner, scenario bridge, command-post fog, and capture loop are
> verified in-game. Still owing a cockpit pass: the **mis-ID budget penalty** Lua (checklist F5)
> and the capture → permanent-reveal carryover across turns (F2).

---

## The core loop

When you fly a SCAR sortie, the search area is populated at mission start with:

- the **real HVT** — a signature convoy (or a real ground object; see
  [target types](#three-target-types) below);
- **partial-signature decoys** that look almost right; and
- **plain-truck clutter** and a light threat laydown (AAA).

The whole picture is **parked** when you arrive, so the discrimination puzzle is always there to
solve. The columns only **bug out once your strike package crosses the activation ring** — 50 NM,
counting only **human-flown** aircraft, so a transiting AI tanker or AWACS can't start the chase
before you get there. The fail clock starts on that activation, not at mission start: the target
is already moving as you arrive, but it can never be "long gone" before slow jets reach the area.

**Outcomes:**

- **Success** — you identify and kill the HVT.
- **Fail** — the HVT reaches the nearest enemy-held city, **or** (for a SCUD) reaches its firing
  position and launches, **or** the window expires.

---

## Reading the picture

This is the heart of SCAR, so it's worth being explicit about what you're given and what you're
not:

- The **target mark points at the search-area center**, not the HVT. Combined with spawn-time
  decoys and the HVT moving off its start point, the mark is a starting place to look, never the
  answer.
- The **briefing and F10 cues** give you the **target signature** (the specific mix of vehicles
  that make up the real HVT — e.g. a SAM TEL plus a command vehicle plus two support trucks), the
  **no-strike / firing-position marks**, and a **decoy warning**.
- The decoys carry a **partial** signature — close, but missing a piece — and the clutter is
  plain trucks. Your job is to **reconnoiter the convoys and match the full signature** before you
  release.

Practical technique: get eyes on each candidate column before committing. Read the composition
against the briefed signature, watch which column is making for the city (or, for a SCUD, the
firing position), and prosecute only when the picture matches. You can pass talk-ons to other
flights in your package — coordination across aircraft is player-run, which is the "coordination"
in Strike Coordination and Reconnaissance.

---

## Three target types

| Variant | What it is | Win / lose |
|---|---|---|
| **spawn** (generic convoy) | A fully scripted ground picture: HVT signature convoy + partial decoys + plain clutter + light threats | Win = HVT killed; lose = it reaches the city or the window expires |
| **armor** (real, fully-mobile group) | Binds a **real** mobile vehicle group on the map as the HVT and mixes in decoys derived from its live composition | Same; a group containing towed/static units (e.g. a KS-19 flak gun) falls back to the spawn picture so nothing is stranded |
| **missile** (real SCUD site) | The launcher races to a firing position and actually **launches** at its target city on arrival | The launch is the fail — stop it before it shoots |

So real armor and missile sites already on the map can themselves become the SCAR objective, not
just abstract convoys.

---

## Mis-ID penalty — discrimination has a cost

Because the decoys look almost right, destroying the wrong convoy has to hurt — otherwise you'd
just shoot everything in the box. Killing one of the area's decoy/clutter columns on a SCAR
sortie **debits budget**. The charge applies only when the prosecuting (SCAR) side gets the kill.

The amount is the **`scar_misid_penalty`** setting (Campaign Doctrine, **default 8** — about the
cost of one SOF team). Set it to **0** to disable the budget hit, in which case mis-IDs are only
logged. (The Lua side of this still wants an in-game pass — checklist F5.)

---

## Commander capture (experimental)

SCAR also drives an experimental **commander-capture** path: rather than killing the HVT, you can
capture the enemy commander alive with a finite, purchased special-operations team — a clean grab
permanently reveals the enemy command network, and a botched grab strands your team and starts a
rescue subplot. It is gated by the **`scar_command_post_intel`** setting (Campaign Doctrine,
**default ON for new campaigns** while it is playtested).

This is a whole campaign-layer loop of its own — buying SOF teams, the C-130 insert, the capture
geometry, and the multi-turn CSAR recovery if a team is stranded. It has its own page:

> **→ [SOF and Commander Capture](SOF-and-Commander-Capture)** for the full economy, the insert,
> capture outcomes, and the recovery loop.

---

## Auto-planning (off by default)

`PlanScarHunts` can frag **one** player-flyable SCAR package per turn against the highest-priority
enemy battle position. It is gated by the **`scar_autoplan`** setting (**default OFF**) and is
**blue-only by design** — the AI keeps using BAI for anti-armor and never frags SCAR for itself.
It's left off until the in-mission Lua has had a full cockpit pass; flip it on once you're
comfortable flying SCAR by hand.

## Settings reference

| Setting | Default | Effect |
|---|---|---|
| `FlightType.SCAR` | player-selectable | Build a SCAR hunt by hand |
| `scar_misid_penalty` | 8 | Budget cost per wrong convoy prosecuted (0 disables) |
| `scar_command_post_intel` | ON (new campaigns) | Enables the SOF commander-capture loop and hides enemy command posts |
| `scar_autoplan` | OFF | Auto-frag one blue SCAR package per turn |

## See also

- [SOF and Commander Capture](SOF-and-Commander-Capture)
- [Combat SAR](Combat-SAR)
- [TARPS Reconnaissance](TARPS-Reconnaissance)
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
- [Mission planning](Mission-planning)
