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
  allocator-reuse collision) printed as a `JAM BACKUP` line on the kneeboard comms ladder
  and echoed in the first-burst cue. Pushing to the backup is a briefed play.
- **Startup grace** (240 s): nobody is jammed mid-INS-alignment.
- **Announced, attributable, counterable**: one first-burst cue names the interference and
  points at enemy C2 ("destroy them to silence it"); comms TGOs are visible map objects,
  so the hunt is plannable; a "ceased" cue confirms the kill paid off.

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
(jittered 0.6–1.4×) · `maxFreqsPerBurst` 3 · `powerW` 100 (the falloff lever — raise if
inaudible at the front, lower if it reaches home plate) · `startGraceS` 240. Python-side:
`MAX_JAMMED_FREQUENCIES` 10 (`commsjamluadata.py`).

## Deferred

- **Symmetric blue comms jamming** — the natural home is the §2 C-130J EW platform
  (a COMMJAM mode next to its radar jamming), not a mirror of this feature.
- **Reactive jamming** (step on a channel *when someone keys up*) — DCS exposes no radio
  transmission event for player voice; not buildable.
- **Datalink/GCI degradation while jammed** — a force-model coupling (e.g. AWACS picture
  quality) was deliberately left out of v1: audio-only keeps the §36/§49 "cosmetic
  pressure, native kills" discipline.

Everything else (files, tests, the emit contract) lives in `docs/dev/414th-features.md`
§51.
