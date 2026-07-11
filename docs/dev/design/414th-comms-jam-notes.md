# 414th — Enemy Comms Jamming (IADS comms nodes) design notes

**Status: LANDED 2026-07-06** (feature §51). Squadron ask (2026-07-06): *"IADS supports
communications nodes — what if we expanded this and allowed red to 'jam' our communications
by flooding SRS channels with audio?"* This note records why the shipped shape is the
in-game radio path, not SRS injection, and the tuning levers for the S4 in-game pass.

## The idea → the shape

The IADS data model already carries communications nodes (`IadsRole.CONNECTION_NODE`,
TGO category `comms`; command centers too) — but their only gameplay was as silent
connection glue for the MANTIS C2-degradation graph. This feature gives them a felt,
in-cockpit effect: while one is alive, the briefed BLUE channels take duty-cycled barrage
noise; kill it (an ordinary IADS strike, with its existing MANTIS consequence) and the
radios clear.

## Why NOT SRS injection (the original framing)

The ask framed the effect as "flooding SRS channels." Injecting audio into the actual SRS
network requires `SRS-ExternalAudio.exe` on the *server host* (MOOSE's MSRS wraps it — the
same dependency TARS's optional `srs` flag accepts), spawns a process per transmission,
and adds a config surface we can't guarantee on every squadron server.

**It also buys nothing.** SRS synchronizes each player's radios *from the cockpit*: a
player on 251.0 in SRS is tuned to 251.0 in the jet. A looping static file transmitted on
that frequency with `trigger.action.radioTransmission` plays through DCS's own radio path
— in the same headset, with **native power/distance falloff** — and is indistinguishable
from the SRS channel being jammed. So the shipped delivery is 100 % in-game, zero external
dependency. (Squadron call 2026-07-06: "drop the SRS part if it can be done natively.")

## Guardrails (the §36 anti-grief bar, applied to audio)

Flooding a human squadron's working voice channels is the *point*, but unbounded it is
grief, not gameplay:

- **Positive target list, built in Python** (`_blue_briefed_frequencies`): intra-flight
  channels (human-crewed flights first, then AI) + blue AWACS. ATC/ATIS/tanker channels
  are never listed by construction; GUARD (243.0/121.5) is defensively filtered on top of
  the registry reserving it. Capped at 10.
- **Duty cycle, never a wall**: ~3 channels per burst (rotating window), 25 s bursts,
  jittered ~90 s+ pauses. Coordination is pressured, never denied — and hopping to a
  channel the jammer isn't currently on is genuine, dynamic comms discipline.
- **The JAM BACKUP channel**: one fresh `RadioRegistry.alloc_uhf()` freq (nothing else
  uses it ⇒ it can never be on the jam list; the planner re-rolls past the freak
  allocator-reuse collision) printed as a `JAM BACKUP` line in the kneeboard **Mission Info
  BLUF**, next to the `PUSH / SUCCESS / ABORT` code words (comms-plan data), and echoed in
  the first-burst cue. Pushing to the backup is a briefed play. *(It formerly rendered in the
  Support Info comms ladder, where the table borrowed the viewing flight's Type/#A/C columns
  and it read as a phantom 4-ship; moved to the BLUF and filtered out of the ladder. The label
  is the shared `JAM_BACKUP_COMM_NAME` constant so the producer `add_comm` and the two kneeboard
  consumers — the BLUF line + the Support-ladder filter — can't drift.)*
- **Startup grace** (240 s): nobody is jammed mid-INS-alignment.
- **Announced, attributable, counterable**: one first-burst cue names the interference and
  points at enemy C2 ("destroy them to silence it"); comms TGOs are visible map objects,
  so the hunt is plannable; a "ceased" cue confirms the kill paid off.

## The intel gate (2026-07-06, squadron call — same day as v1)

*"What if red only jams communications after a blue pilot is shot down and captured? Adds
another reason for search and rescue to be important and it teaches the squadron to rotate
compromised channels."* — adopted as the **default mode** (`comms_jam_requires_capture`,
default ON; turn it off for the v1 ambient always-on-while-node-alive behavior).

The fiction closes perfectly: red can only jam channels it *knows*, and it learns them from
a **captured aircrew's comms plan** — the §15/§21 Combat SAR enemy-capture race that already
exists. Both halves of the loop were already built:

- **In-mission**: the `combatsar` plugin appends every lost capture race to the
  `combat_sar_captures` state global (same mission Lua env). The commsjam plugin, dormant,
  polls it (30 s); on the first blue capture it cues "AIRCREW CAPTURED — assume the comms
  plan is compromised… rotate off them now" and starts the burst loop after an
  **exploitation delay** (`captureReactionS`, 120 s; never before the startup grace).
  **Losing the SAR race now has an immediate, felt cost — and winning it keeps the net
  clean.**
- **Cross-turn**: a POW currently held (`Coalition.pending_pow_recoveries`) means red took
  the comms plan on an earlier turn — `plan_comms_jam` emits `activeFromStart` and the
  jamming runs from the grace with a distinct "COMMS COMPROMISED: enemy interrogation of
  captured aircrew…" story. The compromise is **time-boxed to `COMMS_COMPROMISE_TURNS` (4)**
  off the POW's `captured_turn`: freeing the POW ends it, and so does the window lapsing (the
  squadron *rotates the comms plan*) — so an indefinitely-held POW on a will campaign (the
  2026-07-06 POW rework, §48) doesn't jam the net forever. Both are exactly the "rotate
  compromised channels" lesson, and both fall out of the existing POW machinery.

Dependency worth knowing: live captures require the Combat SAR capture race to be running
(a blue rescue helo emitted — `auto_combat_sar` default ON makes this the norm). A mission
with no CombatSAR node can still be jammed via the POW path. The C2 node is still the
*transmitter* in every mode: no alive comms/command-center node ⇒ no jamming, and killing
it still silences the net regardless of what red knows.

## Death detection = the MANTIS convention, on purpose

Comms/CC nodes are placed statics (`<name> object`) or destructible scenery —
`Group.getByName` never finds them, and a naive nil-check reads every scenery node as
dead at mission start (the exact bug MANTIS's `node_dead` fixed). The plugin reuses that
convention verbatim: dead only on positive evidence (existed-and-destroyed static, or the
`dead_events` ledger, bare-name matched). Corollary: a **culled**/never-spawned node reads
alive and jams all mission unkillably — accepted deliberately, since the standing pressure
is what motivates fragging a strike at it next turn (which un-culls it).

## Tuning levers (for the S4 pass)

All plugin options (`dcsRetribution.plugins.commsjam`): `burstSec` 25 · `intervalSec` 90
(jittered 0.6–1.4×) · `maxFreqsPerBurst` 3 · `maxChannels` 10 · `powerW` 100 (the falloff
lever — raise if inaudible at the front, lower if it reaches home plate) · `startGraceS`
240 · `captureReactionS` 120 (live capture → first burst). Python-side:
`MAX_JAMMED_FREQUENCIES` 10 (`commsjamluadata.py`, the *emit* ceiling); the capture-watch
poll cadence is a plugin constant (`CAPTURE_POLL` 30 s).

**Continuous-vs-scattered feel.** Two independent axes: *how much* is jammed (`maxChannels`
caps the total distinct channels — the Lua keeps the first N of the priority-ordered emit,
so N=3 pins the top three high-priority nets and leaves the rest clean) and *how continuous*
(`burstSec` up + `intervalSec` down → less duty-cycling; `burstSec` 120 / `intervalSec` 10 ≈
90 % on-air). `maxFreqsPerBurst` should be ≥ `maxChannels` so every capped channel is stepped
on each burst rather than round-robined. Red Tide preseeds `burstSec 120 / intervalSec 10 /
maxChannels 3` — near-continuous pressure on the human flights' + AWACS channels.

## Deferred

- **Symmetric blue comms jamming** — the natural home is the §2 C-130J EW platform
  (a COMMJAM mode next to its radar jamming), not a mirror of this feature.
- **Reactive jamming** (step on a channel *when someone keys up*) — DCS exposes no radio
  transmission event for player voice; not buildable.
- **Datalink/GCI degradation while jammed** — a force-model coupling (e.g. AWACS picture
  quality) was deliberately left out of v1: audio-only keeps the §36/§49 "cosmetic
  pressure, native kills" discipline.
- **A real comms-plan rotation after a compromise** — the "rotated after `COMMS_COMPROMISE_TURNS`"
  story is fiction riding the compromise window: squadrons with authored `radio_presets` keep
  the same intra-flight channel across turns, so red "losing" the freqs when the window lapses
  is a gameplay abstraction, not simulation. Actually re-rolling the compromised presets on the
  turn after a capture would make the lesson literal; deferred. (The POW-side rework — status,
  visibility, indefinite hold, Homecoming — landed 2026-07-06; see `414th-csar-notes.md`.)

Everything else (files, tests, the emit contract) lives in `docs/dev/414th-features.md`
§51.
