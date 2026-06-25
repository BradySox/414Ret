# SCAR — Strike Coordination and Reconnaissance

SCAR is a player-flown hunt. You work a defined area to find and kill a moving high-value
target (HVT) that is hidden among look-alike decoys and clutter, before it reaches safety. It
is the air-to-ground answer to "the target is out there moving — go find the real one and
prosecute it," and it rewards reading the picture over trusting a single pin on the map.

`FlightType.SCAR` is **player-selectable** when you build a package. The auto-planner does not
frag it by default (see auto-planning below). BAI remains the AI's anti-armor/convoy task —
SCAR is the human discrimination puzzle.

## The core loop

When you fly a SCAR sortie, the area is populated at mission start with:

- The **real HVT** — a signature convoy (or a real ground object, see below).
- **Partial-signature decoys** that look almost right.
- **Plain-truck clutter** and a light threat laydown (AAA).

The whole picture is **parked** when you arrive, so the discrimination puzzle is always
present. The columns only **bug out once your strike package crosses the activation ring**
(50 NM, counting only human-flown aircraft, so a transiting AI tanker or AWACS cannot start
the chase before you get there). The fail clock starts on that activation, not at mission
start — the target is moving as you arrive, but it can never be "long gone" before slow jets
reach it.

Outcomes:

- **Success** — you kill the HVT.
- **Fail** — the HVT reaches the nearest enemy-held city, **or** (for a SCUD) reaches its
  firing position and launches, **or** the window expires.

The F10 / briefing cues give you the target signature, no-strike and firing-position marks,
and a decoy warning. The target mark points at the **search-area center**, not the exact HVT
unit — combined with spawn-time decoys and the HVT moving off its start point, you have to
reconnoiter to identify it.

## Three target types

| Variant | What it is | Win / lose |
|---|---|---|
| **spawn** (generic convoy) | A fully scripted ground picture: HVT signature convoy + partial decoys + plain clutter + light threats | Win = HVT killed; lose = it reaches the city or the window expires |
| **armor** (real, fully-mobile group) | Binds a **real** mobile vehicle group as the HVT and mixes in decoys derived from its live composition | Same; groups containing towed/static units (e.g. a KS-19 flak gun) fall back to the spawn picture so nothing is stranded |
| **missile** (real SCUD site) | The launcher races to a firing position and actually **launches** at its target city on arrival | The launch is the fail |

So real armor and missile sites on the map can themselves become the SCAR objective, not just
abstract convoys.

## Mis-ID penalty — discrimination has a cost

Because the decoys look almost right, destroying the wrong convoy has to hurt — otherwise you
would just shoot everything. Killing one of the area's decoy/clutter columns on a SCAR sortie
**debits budget**. The charge applies only when the prosecuting (SCAR) side gets the kill.

The amount is the **`scar_misid_penalty`** setting (Campaign Doctrine, default **8** — about
the cost of one SOF team). Set it to **0** to disable the budget hit (mis-IDs are then only
logged). The Lua side of this still wants an in-game pass.

## Commander capture (experimental)

SCAR also drives an experimental commander-capture path. It is gated by the
**`scar_command_post_intel`** setting (Campaign Doctrine, **default ON for new campaigns**
while it is playtested; existing saves keep their stored value).

When it is on:

- Enemy **command posts are hidden entirely** from your map until revealed.
- You can buy finite, dedicated **SOF teams** (a distinct, priced inventory unit, kept out of
  front-line deployment ratios and combat-strength scoring).
- A **C-130 SOF insert** (`FlightType.SOF`, flown by fixed-wing transports — helos are reserved
  for recovery) drops the capture team at the ambush point along the HVT's route. If you do not
  fly the insert, a scripted fallback team is spawned.
- If the un-killed command vehicle drives into the capture radius **and your SOF team is still
  alive**, you get a **clean capture**: the enemy command posts are revealed (permanently, with
  exact coordinates), and the team escapes with the prisoner. The kill-priority order is
  killed > captured > escaped/timeout.
- A **botched grab strands the team** — surfaced next turn as a first-class "downed SOF team"
  objective that you recover with a helo. See the recovery loop below.

The economy is debit-on-frag: one bought team per fragged insert. A clean capture **refunds**
the team (it got out); a botch **strands** it.

> Note: the EW (C-130J) plugin is correctly skipped on the SOF insert C-130, so you cannot fly
> the EW jet and run a SOF insert in the same mission.

## The CSAR recovery loop

A stranded SOF team becomes a friendly "downed SOF team" ground object at the strand point,
anchored to the nearest friendly control point. It offers only `FlightType.CSAR` (helo-only)
to your side. The team ages out after a few turns (default 3) or if its anchor base is overrun.

You recover it two ways, and either one refunds the bought team (it only refunds once):

1. A dedicated **`FlightType.CSAR`** helo air-assault flown at the objective that survives the
   sortie.
2. A **Combat SAR** flight extracting the team in-mission (MOOSE CASEVAC) — see
   [Combat SAR](Combat-SAR).

This SCAR SOF-recovery CSAR is **distinct** from the Combat SAR pilot-rescue flight type,
though Combat SAR can service both.

## Auto-planning (off by default)

`PlanScarHunts` can frag **one** player-flyable SCAR package per turn against the
highest-priority enemy battle position. It is gated by the **`scar_autoplan`** setting (default
**OFF**) and is **blue-only by design** — the AI keeps using BAI for anti-armor and never frags
SCAR for itself. It is left off until the in-mission Lua has had a full cockpit pass; flip it on
once you are comfortable flying SCAR by hand.

## In-game pass status

The SCAR planner, scenario bridge, command-post fog, capture loop, and SOF EW de-conflict have
been verified in-game (the HVT drives/flees on activation; posts hide; the capture loop and the
overview toggle work). Still owing a pass: the **mis-ID budget penalty** Lua (checklist F5) and
the full capture → permanent-reveal carryover across turns (checklist F2). Until those are
cleared, treat the commander-capture path as experimental.

## See also

- [Combat SAR](Combat-SAR)
- [Mission planning](Mission-planning)
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance)
