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

## Band plan

What the actual Combat SAR fleet can direction-find, from the audit at
`414th-comint-notes.md:167-176`:

| Airframe | Role | UHF DF | VHF-FM homing | LF/MF ADF |
|---|---|---|---|---|
| UH-1H | rescue helo (flyable) | no | ARC-131, 30–76 MHz | ARN-83, 190–1750 kHz |
| Mi-8MT | rescue helo (flyable) | no | R-828 | ARK-9, 150–1290 kHz |
| CH-47D / CH-47Fbl1 | rescue helo | postdates the audit — verify | postdates the audit | postdates the audit |
| CH-53E, UH-60A/L | rescue helo | AI-only, no cockpit — irrelevant | — | — |
| F/A-18C, F-14, F-4E, F-5E | Sandy (§15) | yes (audited) | — | varies |
| C-130J-30 | King | not audited | — | — |

Combat SAR-capable airframes are the eight yamls carrying the task: `C-130J-30`, `CH-47D`,
`CH-47Fbl1`, `CH-53E`, `Mi-8MT`, `UH-1H`, `UH-60A`, `UH-60L`.

The finding that drives the design: **neither flyable rescue helo direction-finds UHF, and the
Sandy fast jets do.** One band cannot serve both. So key two carriers:

- **UHF AM — primary.** Serves the Sandy, whose whole job under §15 is to find the survivor and
  shepherd the rescue. This is the proven path; §70 flies it today.
- **VHF-FM — secondary, for the helo.** UH-1H ARC-131 and Mi-8 R-828 overlap at
  **30.000–59.975 MHz**. Unproven through `radioTransmission` — this is the in-game-pass risk.

**LF/MF is not proposed.** It is the band an ADF set is actually built for, but it is also the
least likely to work through `radioTransmission`, and FM homing already covers both flyable
helos. Hold it as the fallback if FM fails the pass.

## Battery life

The beacon is finite. This is the design element that makes the feature more than a convenience.

- The beacon lights when the survivor registers (`registerSurvivor`, `combatsar-config.lua:736`),
  after the same grace the MAYDAY call uses.
- It keys in **windows**, not as a continuous carrier — reuse the §70 window/gap loop
  (`rednet-config.lua:141-177`). In fiction the survivor is conserving the battery and not
  holding the transmit key down in hostile territory. In engine it is the machinery that already
  exists.
- Total **battery life is capped** (proposed default 45 minutes of mission time). When it expires
  the beacon goes silent permanently. The survivor is still rescuable — smoke, LARS, an F10 mark —
  just no longer homeable.
- The beacon stops immediately when the survivor resolves, at all three existing ledger
  transitions: `creditRescue` (`:431`), `recordCapture` (`:454`), and the killed-on-the-ground
  reap in `tick` (`:1057`).
- A persistent evader re-spawning from `persistentSurvivors` (`:881-910`) gets a **fresh
  battery** — they have been hiding with the radio off.

## One carrier at a time

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
  assignment (`NET_GUARD_HZ`, `NET_GRID_HZ`), so nothing allocated later parks a briefed channel
  a detent away from the beacon.
- **Never 243.0.** `rednetluadata.py:76-78` already skips Guard's whole-MHz slot; the same
  exclusion applies here, and more strongly — a continuous carrier on the emergency channel is
  the one thing not to ship.
- The inversion: unlike the red net, this frequency **is briefed**. It goes on the CSAR
  kneeboard card and in the flight briefing, because the rescue package needs to tune it
  deliberately.
- Two allocations per mission (one UHF, one FM), made once, not per survivor.

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

Plugin options, in the units the squadron flies (`combatsar-config.lua:47-49`):

| Option | Default | What |
|---|---|---|
| `beaconEnabled` | on | master switch for the survivor beacon |
| `beaconBatteryMin` | 45 | minutes of battery before the beacon dies for good |
| `beaconWindowSec` | 60 | transmission length per window |
| `beaconGapSec` | 120 | mean silence between windows, jittered |
| `beaconPowerW` | 1000 | range, **not** loudness — a handheld survival radio, so well below the red net's 10000 |
| `beaconFm` | on | also key the VHF-FM carrier for the helo |

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
- **Python**: frequency allocation lands in band, the guard band is reserved, 243.0 is never
  chosen, the kneeboard line renders.

In-game pass rows, for `414th-ingame-pass-checklist.md` when the feature lands:

- Sandy fast jet DFs the UHF carrier to overhead the survivor. Fail signature: needle inert or
  parked at a fixed bearing.
- UH-1H and Mi-8MT home the FM carrier. **This is the risk row** — if `radioTransmission` does
  not drive an FM homing needle, fall back to LF/MF and re-fly.
- Beacon audibly dies at battery expiry and never returns.

## Open calls

1. Battery life — 45 minutes is a guess. It should be short enough to create pressure and long
   enough that a helo launched on the AI dispatch delay can still get there.
2. Whether the beacon should be **on by default** for new campaigns, or opt-in like the §15
   command-post intel was at first.
3. Whether a persistent evader really gets a full fresh battery every mission, or a reduced one
   that runs the survivor down over successive turns.
