# Fly card — clear the regressed rows on one Starfire campaign

## Start: `operation_desert_trident` (Syria)

Starfire's, and the campaign behind the DM's own working save
(`Saved Games\DCS\Retribution\Saves\brady.retribution`). Nothing to add to the `.miz` — it
already carries everything below.

| It has | Which clears |
|---|---|
| **Stennis** (a `NIMITZ_DECK_HULLS` member) | C9 |
| LHA Tarawa + USS Arleigh Burke IIa | B48 |
| **3 × `Scud_B`** | S2 |

**B39 is dropped from this sweep — but it is no longer blocked.** It needs an anti-ship
*engagement*, which `operation_desert_trident` cannot stage. The claim that no Starfire campaign
has a red navy was **wrong**: `operation_vectrons_claw` (Caucasus, USA 2005 vs Russia 2010) fields
a Kuznetsov, a Slava and two escort groups against a CVN-71 CSG. It was flown 2026-08-19 and B39
is now ◐ PARTIAL — fly **that** campaign for B39, not this one.

Also ruled out, so nobody retries them: **Marianas 2027** cannot test S2 (its PLARF launchers are
`CH_CJ10`, listed in §49's `IMMOBILE_UNIT_IDS` and deliberately never routed), and **Red Tide**
has no carrier at all.

---

## Settings

| Where | Setting | Why |
|---|---|---|
| — | `mobile_missile_relocation` + `mobilemissiles` plugin | **S2** — confirm both, Starfire campaigns do not preseed them |

Leave recon fog on (default). Tacview on.

---

## One mission, three rows

Fly or watch a carrier turn long enough for **two ~8-minute relocation intervals** — roughly 20
minutes. You do not need to attack the Scuds; you need them to fire and then move.

**B49 is off this card — CLOSED 2026-08-20.** The recovery-phase deck dressing it covered was
removed along with the launch-phase E-2C and the `deckdecor` plugin.

### C9 — carrier-recovery stagger · ◐ PARTIAL · free, same recovery

- **Pass:** arrivals reach the overhead **one package at a time** — no two packages' flights
  co-altitude within ~1 NM in Tacview.
- **Fail:** two AI packages converging co-altitude in the overhead within a minute of each other.

### B48 — ships hold station · ◐ PARTIAL · free, same fleet

- **Pass:** the boats stay on their assigned racetrack instead of sliding off it over the mission.

### S2 — mobile missile sites relocate · ✗ REGRESSED

- **Pass:** every site with a forwarded fire mission launches on schedule **and relocates
  afterwards**, moving to a fresh spot within the scoot radius. No `giving up on` line in the log
  for a battery that fired.
- **Fail:**
  - A **fired** battery still on its launch point at mission end, or
    `giving up on ... (no movement across 2 route pushes)` naming it. **This is the exact
    regression fixed 2026-08-18** — if it recurs, the controller reset was not the cause and the
    next lever is post-salvo launcher state.
  - Launchers showing a single position record in Tacview despite the armed line — the 2-waypoint
    route did not take.
  - **A SAM site moves.** That is the category filter broken and matters more than S2 itself:
    MANTIS/IADS depends on emitter positions holding still.

---

## Recording it

Write each row's status the **same turn you fly it**, with the session id — results get clobbered
otherwise. `☑ VERIFIED` means "I watched for the fail signature and it did not occur", with a
Tacview or log reference and a date.

Rows live in [414th-ingame-pass-checklist.md](../414th-ingame-pass-checklist.md).

## Free while you are in there

[WATCH.md](WATCH.md) — B23, the red C2 net being audible and DF-able. Tune the red UHF net near a
live enemy command post; a bearing swing as you fly past is the confirmation.

[LOCAL.md](LOCAL.md) needs arranging on purpose — do not treat those rows as opportunistic.
