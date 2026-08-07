# CSAR — survivor ADF beacon (design proposal)

> **STATUS: PROPOSAL — NOT BUILT.** Nothing in this document is implemented. It specifies a
> new addition to §21 Combat SAR. The authoritative CSAR doc is
> [`414th-csar-notes.md`](414th-csar-notes.md); fold this in when the feature lands and delete
> the standalone file.
>
> **Date:** 2026-08-07 · **Feature:** §21 Combat SAR (addition) · **Plugin:** `combatsar`

## The idea

The downed pilot's survival radio keys a homing signal from where they are sitting. Any
rescue aircraft with a direction-finder gets a needle to the survivor instead of a text
readout of their coordinates.

## Why this is not the King ADF that was already dropped

An ADF beacon for the C-130 "King" was specced and deliberately dropped on 2026-06-25
(`414th-combat-sar-spec.md:86-96`, restated player-facing at `docs/wiki/Combat-SAR.md:58-61`).
The recorded reason: MOOSE's radio-beacon path is fixed-point, the King orbits, and following
a moving King would need a position-refresh loop for no gain over the air-tracking TACAN that
already tracks the orbit.

That reason is specific to the King. The survivor does not move. Fixed-point is the correct
model for them, not a limitation to work around.

Two things have also changed since that call:

- §70 COMINT proved the mechanism end-to-end in this fork. A looped
  `trigger.action.radioTransmission` from a world position is genuinely direction-findable
  (`414th-comint-notes.md:36`, `:264-268`).
- The COMINT module audit produced an airframe-by-airframe DF capability table
  (`414th-comint-notes.md:160-176`), so the band choice below rests on audited data rather
  than a guess.

## Mechanism — `radioTransmission`, not the beacon command

Use `trigger.action.radioTransmission`, the same call §70 keys the red net with
(`resources/plugins/rednet/rednet-config.lua:158-167`).

Do **not** use MOOSE `BEACON` or the raw `ActivateBeacon` controller command. Three reasons:

1. The bundled `Moose.lua` `BEACON` class implements only `ActivateTACAN`, `ActivateICLS` and
   `ActivateLink4` (`resources/plugins/base/Moose.lua:6177`, `:6204`, `:6214`). There is no NDB
   or homer activator to call.
2. `ActivateBeacon` is the exact command family behind the 2026-06-25 King CTD — an
   `AI::Controller` discrete command that produced a hard `ACCESS_VIOLATION` in DCS's command
   executor. The fork's response was to fence it to AI-only units
   (`combatsar-config.lua:1232-1243`). A new feature should not reopen that path.
3. `radioTransmission` takes a world position, not a unit. No controller, no discrete command
   queue, no exposure to that crash class at all. The survivor group can stay exactly what it is.

This also means the beacon works for a survivor whose group failed to spawn, since the ledger
already carries `entry.coord` independently of the group (`combatsar-config.lua:745-763`).

## Band plan — one carrier, VHF-FM

**Decision (2026-08-07): VHF-FM only.** One carrier, 30.000–59.975 MHz, the overlap of UH-1H
ARC-131 (30–76 MHz) and Mi-8 R-828. No UHF carrier.

Combat SAR-capable airframes are the eight yamls carrying the task: `C-130J-30`, `CH-47D`,
`CH-47Fbl1`, `CH-53E`, `Mi-8MT`, `UH-1H`, `UH-60A`, `UH-60L`. The Sandy is the `SCAR` task,
defined in code as the A-10 / Apache rescue escort (`game/ato/flight.py:69`,
`game/ato/flighttype.py:72`).

What that fleet can do with an FM carrier, from the DF audit at `414th-comint-notes.md:167-176`:

| Airframe | Role | FM homing | Gets |
|---|---|---|---|
| UH-1H | rescue helo (flyable) | ARC-131, 30–76 MHz | needle |
| Mi-8MT | rescue helo (flyable) | R-828 | needle |
| CH-47D / CH-47Fbl1 | rescue helo (flyable) | postdates the audit — **verify** | unknown |
| CH-53E, UH-60A/L | rescue helo | AI-only, no cockpit | nothing — irrelevant |
| A-10C / AH-64D | Sandy (§15) | not in the audited DF set | audio only |
| C-130J-30 | King | not audited | audio only |

**Tuning is not homing, and the spec should not pretend otherwise.** Most of the fleet can
*receive* 30–60 MHz. Under the fork's own audit exactly three DCS airframes *home* it — UH-1H,
Mi-8, OH-58D. So the honest contract is: **the two flyable rescue helos get a needle to the
survivor; everyone else in the package gets an audible carrier and no bearing.**

Those are the aircraft that matter, and the reasons to accept the trade:

- The helo is the one that lands and picks the survivor up.
- The Sandy already gets the survivor's position through LARS and the F10 mark.
- One carrier drops the two-carrier bookkeeping and the second frequency allocation.
- It also drops any shared-band contention with the §70 red net, which lives on UHF.

**LF/MF is the fallback, and it is now the only fallback.** With no UHF carrier, if FM homing
fails the in-game pass the feature has nothing left to fall back to in code. Expose the band as
the `beaconBand` option below so the fallback is a config change and a re-fly, not a rewrite.

## Battery life

The beacon is finite. This is the design element that makes the feature more than a convenience.

- The beacon lights when the survivor registers (`registerSurvivor`, `combatsar-config.lua:736`),
  after the same grace the MAYDAY call uses.
- It keys in **windows**, not as a continuous carrier — reuse the §70 window/gap loop
  (`rednet-config.lua:141-177`). In fiction the survivor is conserving the battery and not
  holding the transmit key down in hostile territory. In engine it is the machinery that already
  exists.
- Total **battery life is capped** (proposed default 45 minutes). When it expires the beacon goes
  silent permanently. The survivor is still rescuable — smoke, LARS, an F10 mark — just no longer
  homeable.
- **The battery drains on transmit time, not wall clock.** This matters because of the
  one-survivor-at-a-time rule below: a queued survivor who never holds the net would otherwise
  burn their whole battery in silence and be un-homeable the moment they get it. Count only the
  seconds actually radiated.
- The beacon stops immediately when the survivor resolves, at all three existing ledger
  transitions: `creditRescue` (`combatsar-config.lua:428`), `recordCapture` (`:443`), and the
  killed-on-the-ground reap in `tick` (`:1057`).
- A persistent evader re-spawning from `persistentSurvivors` (`:881-910`) gets a **fresh
  battery** — they have been hiding with the radio off.

## One survivor on the air at a time

Real survival radios all sit on the same guard channel, and the fork already has a rule about
not filling a band with carriers (`rednetluadata.py:90-92`: "the band is shared").

- **One shared blue SAR frequency per mission**, not one per survivor.
- Only the **most recent un-resolved survivor** radiates. Everyone else holds. A fresh ejection
  is the live emergency and takes the net.
- That caps concurrent carriers at exactly one per band, regardless of how many evaders the
  campaign is carrying.
- The King gets an F10 **`Combat SAR → Beacon — next survivor`** command to hand the net to
  another survivor. It sits next to the existing LARS button
  (`combatsar-config.lua:1245-1246`) and composes with it: LARS lists who is out there, the
  beacon command puts one of them on the air.

## Frequency allocation (Python)

Reuse the discipline in `game/missiongenerator/rednetluadata.py:202-264`, with one inversion.

- Allocate from the mission `RadioRegistry` and reserve the 100 kHz guard band around the
  assignment (`NET_GUARD_HZ`, `NET_GRID_HZ` — both band-agnostic; the 25 kHz grid is the FM
  tuning grid too), so nothing allocated later parks a briefed channel a detent away from the
  beacon.
- **The band constants do not carry over.** `UHF_NET_FIRST_SLOT_MHZ` / `UHF_NET_LAST_SLOT_MHZ`
  (225–399) and the `GUARD_SLOT_MHZ` 243.0 exclusion are UHF-specific and are **not** reused —
  there is no emergency channel inside 30.000–59.975. Allocate against the FM band bounds
  instead, and keep clear of any FM channel the mission's own ground/FAC plan has taken.
- The inversion: unlike the red net, this frequency **is briefed**. It goes on the CSAR
  kneeboard card and in the flight briefing, because the rescue package needs to tune it
  deliberately.
- **One allocation per mission**, made once, not per survivor.

## Files touched

| File | Change |
|---|---|
| `resources/plugins/combatsar/combatsar-config.lua` | beacon window loop, battery timer, net-holder selection, stop hooks at the three resolve points, King F10 command |
| `resources/plugins/combatsar/plugin.json` | new `specificOptions` entries + `otherResourceFiles` for the tone |
| `resources/plugins/combatsar/csar-beacon.wav` | new — the swept survival-radio tone (`rednet-cw.wav` is the shipping precedent, `rednet/plugin.json:50`) |
| `game/missiongenerator/luagenerator.py` | emit `survivorBeacon` on the CombatSAR node in `_emit_combat_sar_side` (`:584`) |
| new: `game/missiongenerator/csarbeaconluadata.py` | frequency allocation + guard band, modelled on `rednetluadata.py` |
| `game/missiongenerator/kneeboard.py` | beacon frequencies on the Combat SAR card |
| `game/settings/settings.py` | campaign toggle |
| `game/fourteenth/features.py` | registry entry (CI fails without it) |

## Options

Plugin options, in the units the squadron flies (`combatsar-config.lua:45-49`):

| Option | Default | What |
|---|---|---|
| `beaconEnabled` | on | master switch for the survivor beacon |
| `beaconBatteryMin` | 45 | minutes of battery before the beacon dies for good |
| `beaconWindowSec` | 60 | transmission length per window |
| `beaconGapSec` | 120 | mean silence between windows, jittered |
| `beaconPowerW` | 1000 | range, **not** loudness — a handheld survival radio, so well below the red net's 10000 (`rednet-config.lua:51`) |
| `beaconBand` | `fm` | `fm` \| `lfmf` — the fallback lever if FM homing fails the in-game pass |

`beaconPowerW` carries the standing constraint in its label, the way `rednet/plugin.json` does:
`powerW` is range, not loudness (§51, §70).

## What this deliberately does not do

- **No enemy DF.** Red does not get a homing bonus onto the survivor. The capture race is
  already tuned — 0.75 NM spawn, roughly a 4-minute march, explicitly retuned from 2 NM to make
  capture a real but occasional outcome (`combatsar-config.lua:69-73`). Handing red a needle
  re-opens that tuning. Deferred, not rejected.
- **No gameplay model change.** Audio and geometry only, the same contract §70 holds
  (`rednet-config.lua:25-26`). No kills, no scoring, no change to who gets rescued.
- **Does not replace LARS or smoke.** Both stay. The beacon is a third finding aid, and the only
  one that works with no King up.

## Test plan

Headless, in the normal pytest run:

- **Lua harness** (`tests/lua/`, the §82/`414th-lua-plugin-harness-notes.md` rig — the existing
  `test_combatsar_ledger.py` is the model): beacon starts after grace; battery expiry silences it
  permanently; each of the three resolve transitions stops it; exactly one survivor on the air at
  a time; the King F10 command hands the net over.
- **Python**: the allocation lands inside 30.000–59.975, the 100 kHz guard band is reserved
  against every already-allocated mission frequency, exactly one allocation is made per mission
  regardless of survivor count, and the kneeboard line renders.

In-game pass rows, for `414th-ingame-pass-checklist.md` when the feature lands:

- **UH-1H and Mi-8MT home the FM carrier. This is the gate row, not a risk row** — with UHF
  dropped there is no second carrier behind it. Fail signature: needle inert or parked at a fixed
  bearing. On failure, flip `beaconBand` to `lfmf` and re-fly.
- CH-47D / CH-47Fbl1 FM homing — **unverified in the audit**, and both carry the Combat SAR task.
  Confirm in the same pass; a silent no-needle on two of the eight carriers is the quiet failure.
- Beacon audibly dies at battery expiry and never returns.

## Open calls

1. Battery life — 45 minutes is a guess. It should be short enough to create pressure and long
   enough that a helo launched on the AI dispatch delay can still get there. Now measured in
   transmit seconds, so 45 minutes of battery against a 60 s / 120 s duty cycle is roughly a
   2¼-hour wall-clock life — probably too long. Either shorten the battery or lengthen the gap.
2. Whether the beacon should be **on by default** for new campaigns, or opt-in like the §15
   command-post intel was at first.
3. Whether a persistent evader really gets a full fresh battery every mission, or a reduced one
   that runs the survivor down over successive turns.
4. Whether the Sandy is worth serving at all. Under the audit the A-10 / Apache have no DF in any
   band, so no single-carrier choice reaches them; they work off LARS and the F10 mark as they do
   today. Adding a second UHF carrier for a Hornet or Tomcat flying an off-doctrine Sandy is
   possible but was rejected here as bookkeeping for an edge case.
