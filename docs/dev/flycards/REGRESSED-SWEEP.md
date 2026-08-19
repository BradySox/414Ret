# Fly card — clear the regressed rows on one Starfire campaign

## Start: `operation_desert_trident` (Syria)

Starfire's, and the campaign behind the DM's own working save
(`Saved Games\DCS\Retribution\Saves\brady.retribution`). Nothing to add to the `.miz` — it
already carries everything below.

| It has | Which clears |
|---|---|
| **Stennis** (a `NIMITZ_DECK_HULLS` member) | B49, C9 |
| LHA Tarawa + USS Arleigh Burke IIa | B48 |
| **3 × `Scud_B`** | S2 |

**B39 is dropped from this sweep.** It needs an anti-ship *engagement*, and no Starfire campaign
has a red navy — all fifteen with a Nimitz hull are blue-navy-only. It stays regressed until
either a campaign with an opposing fleet is used or hulls are added, and neither is worth doing
to close one row.

Also ruled out, so nobody retries them: **Marianas 2027** cannot test S2 (its PLARF launchers are
`CH_CJ10`, listed in §49's `IMMOBILE_UNIT_IDS` and deliberately never routed), and **Red Tide**
has no carrier at all.

---

## Settings

| Where | Setting | Why |
|---|---|---|
| Mission Generation → Carrier | `carrier_deck_decorations` | main gate |
| Mission Generation → Carrier | `carrier_deck_decorations_recovery` | **B49**, default OFF |
| — | `mobile_missile_relocation` + `mobilemissiles` plugin | **S2** — confirm both, Starfire campaigns do not preseed them |

Leave recon fog on (default). Tacview on.

---

## One mission, four rows

Fly or watch a carrier turn long enough for **two ~8-minute relocation intervals** — roughly 20
minutes. You do not need to attack the Scuds; you need them to fire and then move.

### B49 — carrier recovery deck dressing · ✗ REGRESSED

- **Pass:** nothing on the bow at mission start. When the launch set is struck below, 3–9 pieces
  of gear appear forward on the **starboard bow** and **ride the deck** — still in place, still
  square to the ship, after the boat has steamed a few miles.
- **Fail — three signatures, they mean different things:**
  1. **Nothing appears** → MOOSE absent or `SPAWNSTATIC` errored. Grep `DECKDECOR|` in `dcs.log`;
     the spawn is `pcall`-wrapped and logs a count, so a **0 is diagnostic**.
  2. **Gear appears, boat sails out from under it** → the link failed, statics are
     world-anchored. Kills the tier as designed.
  3. **A jet spawns into the new gear** → bow spots 11/12/13 are unmeasured. Known risk, and the
     reason this ships default-OFF.
- Three further 2026-08-17 changes ride this same re-fly; if the row passes they pass with it.
- **Bonus if it flies clean:** Tacview the deck at t=0 on a full cold spawn and **count the bow
  spots** — that closes the 11-vs-16 gap and is the gate on ever making this default-ON.

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
