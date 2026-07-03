# Combat SAR

Combat SAR (combat search and rescue) makes a downed pilot worth flying for. In stock
Retribution an ejection is a flat loss: the airframe is gone and the aviator is written off.
This fork turns that moment into a mission. When a **human** pilot ejects in the operating
area, you can launch a rescue — a CH-47 goes in, lands at the survivor, picks them up, and
flies them home. Deliver them to any friendly field and the campaign **spares that aviator at
debrief**: you still lose the jet, but the experienced pilot returns to the squadron instead of
being killed off.

It is a bespoke flight type (`FlightType.COMBAT_SAR`) driven by the plugin's **survivor
ledger** runtime. Since the 2026-07-03 rescope it is a **normal, standing task**: the AI plans
the rescue package automatically by default (see the standing alert below), and a captured
pilot is a held POW — there is no separate recovery-raid mission (see [SCAR](SCAR) for the
capture → POW consequence).

> **In-game-pass status:** the core loop is **flown and verified** — AI rescues credit the
> spare-pilot scoring by real identity and AI ejections are capturable → POW (checklist
> G11/G20, 2026-06-30). Still open: the King TACAN beacon re-fly (G10) and the newest
> AI-rescue/Sandy retasking fixes (G21/G23 — G23 is frozen pass-or-delete).

---

## The rescue package: Jolly Green, King, and Sandy

Combat SAR is flown as a three-part package, modeled on real combat-SAR doctrine. The rescuer
(Jolly Green) and the King are the Combat SAR flight types below; the **Sandy** escort is
`FlightType.SCAR` — see [SCAR](SCAR) for how Sandy is flown.

| Element | Airframe | Role |
|---|---|---|
| **Jolly Green** (rescuer) | **CH-47Fbl1** (the player-flyable ED Chinook) | Flies in, lands, boards the survivor, and delivers them to any friendly field or FARP. Carries a door-gun fit (port + starboard M60D) for self-protection on the ingress. |
| **King** | **C-130J-30** | Flies the overhead **HC-130 "King"** on-scene-command orbit: lights the homing beacon and runs the survivor locator. It never lands at a crash site. |
| **Sandy** ×2–4 | **A-10C / AH-64D** | RESCAP escort (`FlightType.SCAR`): protect the survivor, suppress the threats around them, walk Jolly in. See [SCAR](SCAR). |

The rescuer holds **near the FLOT**, not at AWACS depth — its racetrack sits just outside FLOT
SHORAD/MANPAD reach (a short ~15 NM threat buffer) on a tight helo-sized orbit, so a slow helo is
actually within reach of an ejection instead of 80 NM back. (Earlier builds parked it at the
tanker/AWACS standoff; that was fixed so the rescue can reach a deep ejection in time.) Its loiter
altitude is clamped to the campaign's helicopter combat altitude automatically — you do not tune
it.

An AI **CH-47D** is the fallback rescuer (no weapon stations). The King is *overhead presence and
command*, **not** a tanker — the C-130 cannot act as a DCS aerial-refueling tanker, and the
Chinook couldn't take fuel from it anyway, so the King role is deliberately never wired into the
refueling system.

---

## How a rescue works, step by step

![The rescue-helo Combat SAR kneeboard page: ROLE, HOW IT WORKS, PICKUP, and a KING BEACON block telling the crew to home on the HC-130 King's TACAN to find the rescue area](https://raw.githubusercontent.com/bradyccox/414Ret/main/docs/wiki/img/kneeboard-combat-sar.png)

*The rescue helo's kneeboard page: how the pickup works and the **King beacon** block — home on the HC-130 "King" TACAN to find the survivor's area.*

1. A **human** pilot ejects in the area. The MOOSE CSAR engine catches the ejection event and
   spawns the downed pilot on the ground with a beacon. (It only reacts to **human** ejections
   and only to **ejections** — not AI, not ordinary crashes — unless the AI standing alert is
   on; see below.)
2. The **King** lights an **air-tracking TACAN** beacon. This is the single homing solution: it
   follows the King's moving orbit, and every rescue helo carries a TACAN receiver. (An ADF
   radio beacon was considered and deliberately dropped — MOOSE's radio beacon is fixed-point,
   so chasing a moving King with it would buy nothing over the TACAN.)
3. The King's crew can press an F10 **Combat SAR → LARS — Locate Survivors** button. LARS reads
   the live downed-pilot table and reports each active survivor nearest-first: position, plus
   bearing and range **from the King** — exactly the readout the crew relays to the helo.
4. The **CH-47** homes on the King's TACAN, flies to the survivor, lands (or hovers at the
   pickup height), boards them, and delivers them to a friendly field/FARP.

The whole pickup is driven through the helo's own F10 **CSAR** menu, which MOOSE adds to any
human helo in the mission. Plugin options let you tune the feel:

| Plugin option | Default | Effect |
|---|---|---|
| `autosmoke` | off | Auto-pop smoke at the survivor |
| `loadDistance` | 75 m | How close the helo must be to board the survivor |
| `rescueHoverHeight` | 20 m | Hover height that counts as a pickup if you don't land |
| `messageTime` | 15 s | How long CSAR radio messages stay on screen |

---

## The enemy capture race

A rescue is a race, not a milk run. When a pilot goes down, the enemy may send a **snatch party**
to seize the survivor before you can pull them out:

1. On a downed-pilot spawn there's a chance an enemy infantry party appears a short distance away
   (**red smoke** + a **MAYDAY** cue) and walks straight at the survivor. The King smokes/marks and
   calls it so the **Sandy** escort can engage.
2. **Kill the party** and the pilot is safe for pickup as normal.
3. **Let it reach the survivor** and dwell there un-rescued, and the pilot is **CAPTURED** — taken
   off the rescue board and held as a **POW**.

Plugin tunables control the race (`captureEnabled` / `captureChance` / `captureSpawnDistanceNm` /
`captureRangeFt` / `captureDwell` / `capturePartySize` / `captureTeams` — distances in NM/ft), so you
can dial how often and how aggressive the snatch attempts are.

### If captured: the held POW

A captured pilot is **not killed at debrief** — they become a POW held at the **nearest enemy
airfield**. The capture is the campaign consequence for losing the rescue fight:

- **Recapture the holding airfield** with the ground war and the POW walks free (they stay in
  the squadron).
- Every turn they are held **drains your side's political will** (on campaigns with the will
  economy).
- A POW left too long is on a **4-turn clock** — abandon them past it and the aviator is
  **killed for good**.

(The earlier dedicated "CSAR raid" mission against the holding field was shelved in the
2026-07-03 rescope — win the fight at the survivor, or win the field back.)

## Rescue scoring — the payoff

The point of a rescue is to save the pilot, so the loop closes inside the campaign model:

- When the helo **boards** a survivor, the engine records that pilot's **original ejected
  aircraft** (by the exact unit name DCS reports in its crash/kill event).
- On a successful **delivery to a friendly field**, those pilots are credited.
- At debrief, each credited pilot's loss is resolved so the **airframe is still attrited but the
  aviator survives** — the kill on that pilot is skipped.

Two properties make this safe:

- **You have to actually bring them home.** A rescue helo shot down with survivors aboard never
  reaches the delivery, so those pilots are never credited.
- **Fail-safe.** If nothing is rescued, the result is identical to today's behavior — the pilot
  dies. An empty rescue list is exactly the pre-scoring outcome.

See [Squadrons and Pilots](Squadrons-and-Pilots) for why keeping an experienced aviator matters
over a campaign.

---

## AI standing alert (default ON)

Rescue is a normal, standing task: the **`auto_combat_sar`** setting (HQ automation page,
**default ON** since the 2026-07-03 rescope — existing campaigns keep their saved choice; turn
it OFF to only fly rescues manually). With it on:

- the planner auto-plans the package per turn for blue — **King + Jolly Green + 1 Sandy** — so the
  escorted alert is up before the first losses; and
- the rescue helo **air-starts on station** near the FLOT (a slow helo spooling up from a rear
  field never reaches a deep ejection in time); and
- the AI rescue is dispatched by the plugin's own **survivor ledger** — it prefers to
  **commandeer the on-station rescue helo** (never a player's) and only clones a fresh helo from
  the alert's home FARP when every planned helo is dead or busy. A player crewing a rescue helo
  always takes precedence — the AI never competes with the player-flown path.

Airframe scarcity self-limits the alert: no rescue helo available, no orbit planned. Combat SAR is
**blue-only** — the engine is built for blue, so a red Combat SAR would just fly an inert orbit
and is never auto-tasked.

> **Update (2026-06-30, survivor-ledger rework):** the old v1 limitations are fixed — player
> and AI rescues are judged by the same ledger, an AI auto-rescue **does** credit the
> spare-pilot scoring by the pilot's real identity (verified in-game, checklist G11), and one
> ledger owns every ejection so nothing is double-handled.

---

## Settings reference

| Setting / option | Default | Effect |
|---|---|---|
| `FlightType.COMBAT_SAR` | player-selectable | Plan a rescuer (CH-47) or King (C-130) orbit by hand |
| `auto_combat_sar` | OFF | AI standing alert: auto-plans a Combat SAR orbit per turn and makes AI ejections rescuable |
| King beacon | TACAN-only | Air-tracking TACAN the helo homes on; F10 LARS reports survivor positions |
| `loadDistance` / `rescueHoverHeight` / `autosmoke` / `messageTime` | 75 m / 20 m / off / 15 s | CSAR pickup feel (plugin options) |

## Tips

- **Put a King up if you can.** The helo can be rescued without one, but the TACAN homing and
  LARS readout make finding the survivor far less of a needle-in-a-haystack.
- **Bring escorts.** The rescuer orbits behind the rings but the pickup itself often pushes
  toward the fight; the door guns are for self-defense, not for clearing a hot LZ.
- **Deliver to the nearest friendly field or FARP** — `allowFARPRescue` is on, so you do not
  need a dedicated MASH; any friendly airfield/FARP scores the save.

## See also

- [SCAR](SCAR)
- [Squadrons and Pilots](Squadrons-and-Pilots)
- [Air Defense and the Air War](Air-Defense-and-the-Air-War)
- [Mission planning](Mission-planning)
