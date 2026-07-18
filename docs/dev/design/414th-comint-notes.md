# 414th — COMINT: blue-side communications intelligence (design)

**Status: C0 + C1 LANDED 2026-07-18 (feature §70 — Feature A, the campaign take, checklist
B22; and Feature B1, the audible UHF red net + `rednet` plugin, checklist B23; see
`docs/dev/414th-features.md` §70). C2 (the clandestine transmitter + the active-nets
listing) not started.**
Squadron ask (2026-07-18): *"Such a large part of real warfare is communications
intercepts. Currently DCS has no way to do that — what options do we have?"* Scope call
(same day, option 1 of the survey): build **Feature A (campaign-layer COMINT take)** and
**Feature B (in-cockpit red net + DF hunts)** together. The in-mission "COMINT FLASH" cue
layer (option 2) is deferred until A defines the gating; the survey's other options are
recorded in **Deliberately out** below.

This is the blue-side mirror of §51: the fork already models the enemy exploiting a
captured aircrew's comms plan (`comms_jam_requires_capture` — red COMINT against blue).
This note gives blue its own collection against red.

---

## The hard constraint — every intercept is fabricated

Three facts, all previously established:

1. **AI "radio traffic" isn't RF.** The canned AI voice lines are client-side audio; the
   scripting sandbox cannot observe them and they carry no frequency/position to collect
   against.
2. **No transmission event exists** — for AI *or* player voice. Already recorded as "not
   buildable" in `414th-comms-jam-notes.md` (the reactive-jamming deferred item). SRS
   voice lives entirely outside the sandbox.
3. **The one real radio primitive is `trigger.action.radioTransmission`** — transmits an
   audio file from a world position on a frequency with genuine power/distance falloff,
   heard through cockpit radios (and therefore through SRS, which syncs from the cockpit).
   Named transmissions can be stopped (`stopRadioTransmission`), and a **looped**
   transmission can be genuinely direction-found by any airframe with an ADF. Proven
   end-to-end by §51.

Therefore: COMINT in DCS is a **presentation-and-gating layer over ground truth the
engine already knows** — exactly the §3 recon-fog shape (the engine knows everything; the
player is sold a degraded view, and flying collection earns a better one). Feature A is
that layer at the campaign scale. Feature B is the one place DCS lets the intercept be
*physically real*: an actual transmission in the world, tunable and homeable.

Lessons inherited from §51/§58 (do not relearn): `powerW` is **range, not loudness**
(loudness = the clip's RMS; normalize to ~−4 dBFS); in-miz sounds resolve **only** via
their `l10n/DEFAULT/` archive path (a bare basename fails silently); audio assets must be
**original** (synthesized or self-recorded — never lifted from paid campaigns).

---

## One node set, four features (the tap-vs-bomb dilemma)

Red `comms` / `commandcenter` TGOs already serve three systems. This design adds two
more consumers of the same objects — and the dilemma emerges without a line of
special-case code (the §HVT/CDE precedent: the engine prices the choice, the player makes
it):

| Red comms/CC node | §51 comms jam | §52 planning | A — COMINT take | B — red net |
|---|---|---|---|---|
| **alive** | can jam blue (when the comms plan is compromised) | red plans well | product flows | audible, DF-able |
| **dead** | silenced | red degrades | take dries up | goes quiet |

Killing the node is still an ordinary IADS strike with its MANTIS consequence — nothing
here owns kills or force-model changes (the §36/§49/§51 discipline: cosmetic/intel
pressure, native kills).

**Sources on campaigns with no authored C2** (the COIN problem — insurgents field no
IADS comms): concealed COIN-spawned TGOs (cells, IED teams, the HVT convoy) are
**intrinsically comms-active** — an insurgency runs on radios. `_comint_sources(game)`
= alive red `comms`/`commandcenter` TGOs ∪ alive concealed COIN-spawned TGOs. Regulars
whose C2 dies go landline/courier (take dries up); an insurgency can't (its chatter *is*
the take), which is historically honest.

---

## Feature A — the COMINT take (turn model, pure Python)

### Tiers

- **Tier 0 — no alive sources**: no product. One SITREP line: *"Enemy C2 net silent — no
  COMINT take."* (Legibility: the player learns the silence is a consequence, not a bug.)
- **Tier 1 — ambient (sources alive)**: the national/theater-collection fiction — someone
  is always listening, poorly. Product: **(a)** the §55 red-posture *detail* line becomes
  COMINT-attributed ("COMINT assesses: Surging (all-in) — ground 4.0x…") — when this
  feature is ON, that intel is *earned* by red having an emitting net; **(b)** the
  **active-nets listing** (each alive net's frequency + coarse area, e.g. "enemy C2 net,
  271.25 AM — Haina area") — the findability hook for Feature B's hunts (§37/§38 lesson:
  an unfindable feature reads half-baked).
- **Tier 2 — collected (a collector flew last mission)**: Tier 1 **plus** the tasking
  leak and one concealed-TGO reveal (below).

### The collector

**RESOLVED 2026-07-18 (squadron call #3): both.** A blue **`FlightType.JAMMING`** flight
(the §2 C-130J platform) **or a blue drone flight** (`UAV_DCS_IDS` — the §3 "a drone is
always filming" rule extends to *always listening*), player- or AI-crewed, that flew
last mission and was not lost — recorded at debrief commit (`MissionResultsProcessor`,
the §29 SITREP hook pattern) as `game.comint_collected_turn`. A shot-down collector
collects nothing (the `airecon` one-shot precedent). Era self-limits: a campaign that
fields no drones (Red Tide, the Vietnam set) earns Tier 2 only via the Herc, so drone
SIGINT never leaks into eras that predate it; OIR's standing Predator orbits will hold
Tier 2 most turns — acceptable on COIN, where the drone war *is* the intel war.

### The tasking leak (Tier 2)

Red's ATO for the mission being generated is fully planned by kneeboard time, so the
leak warns of **what red flies today**: pick the most threatening red offensive package
(Strike/BAI/OCA/anti-ship against blue assets), **deterministically** (seeded off turn +
target id — regeneration must not reroll it; the §3 jitter discipline) and **coarsened**:
task class + size band + target area name + TOT ± 30 min. Rendered as a short **COMINT
block folded into the Mission Info page** next to the SITREP band (the §30 rule: no new
kneeboard pages). Python-only, no client rebuild (the §55 surfacing pattern); a client
intel surface is deferred.

**Zero planner coupling, by design.** The blue AI planner already operates on ground
truth (§3 `viewer=None` discipline) — the leak informs the *human* only. Feature A is
100 % presentation; if it's off, nothing anywhere changes.

### The reveal (Tier 2)

At `initialize_turn` (after red plans), snap **one** eligible concealed enemy TGO to its
exact symbol via the existing discovery path (`known_for`) — eligible = `concealed`,
within `COMINT_REVEAL_RANGE_KM` (60, constant) of an alive source, deterministic pick.
**`map_hidden` TGOs are NEVER eligible** — the §50 ambush teams stay untelegraphed
unconditionally (that feature's core rule). **RESOLVED 2026-07-18 (squadron call #2):
full snap** — the reveal reuses the shipped discovery machinery; the shrink variant and
its new per-TGO uncertainty state are dropped.

### Settings & preseeds

`comint_collection` — Campaign Management → "Campaign features", default **OFF** until
the app/in-game pass. BLUE-only product (players are blue; red's version already exists
as §51's capture gate). **No Red Tide preseed** — the feature lock took effect Friday
night 2026-07-17. Post-M2 candidates: Red Tide (the 9-node destroyable C2 net §52 keys
on is the perfect source set) and both COIN campaigns (insurgent chatter).

### Files & tests

`game/fourteenth/comint.py` (tiering, sources, leak pick, reveal) + hooks in
`initialize_turn` / `MissionResultsProcessor.commit` / the kneeboard Mission Info block;
`tests/fourteenth/test_comint.py` — tier gating (no sources ⇒ nothing; sources ⇒
ambient; collector ⇒ leak + reveal), the `map_hidden` exclusion, determinism across
regeneration, OFF ⇒ exact no-op.

---

## Feature B — the red net (in-mission audio + DF hunts)

### B1 — ambient net

Each alive red comms/CC node **transmits**: a named `radioTransmission` on an assigned
frequency, in **windows** (traffic patterns, not a 24/7 wall — schedule jittered per
node, loop=true *within* a window so ADF needles can home, stopped between via
`stopRadioTransmission`). Node starts staggered across the first interval (the §49
same-frame lesson). Node death mid-mission stops the transmission — the audible kill
confirmation is a feature — via the vendored MANTIS `node_dead` positive-evidence
convention (§51 vendors it too; plugins are standalone by design).

**Frequency plan — who can actually hunt (module audit 2026-07-18, resolving squadron
call #4).** The squadron hunch "most jets in DCS can track ADF" **checked out** for the
fleet that matters — the DF-capable set is far larger than the helo trio the (stale)
MOOSE `Core.Beacon` docs claim ("only Mi-8/Huey/Gazelle"; that note predates the
fast-jet ADF implementations). Audited against the Airgoons radio/nav reference + the
Heatblur manuals:

- **UHF/V-UHF DF — the fast jets**: **F/A-18C** (UFC ADF off COMM 1/2, 108.0–400.0 MHz,
  HSI bearing circle), **F-14** (ARC-182 "V/UHF 2" DF mode + ARA-50, AM/FM — the modeled
  ARC-159's ADF position is non-functional, and the needle drops during own
  transmissions), **F-4E** (ARC-164 COMM/AUX ADF modes onto the HSI/BDI — the Heatblur
  manual itself documents the "continuously transmitting ME station" setup this feature
  is), **F-5E** (radio 1 UHF DF).
- **LF/MF ADF — helos, trainers, classics**: UH-1H (190–1750 kHz), Mi-8 (ARK-9
  150–1290 kHz + ARK-UD), Ka-50 (ARK-22), SA342, L-39, C-101CC, F-86F, MiG-15/19/21,
  Yak-52. (AH-64D/Mi-24/CH-47F/OH-58D postdate the audited table — verify in the pass.)
- **VHF-FM homing**: UH-1H ARC-131 (30–76 FM), OH-58D FM1, Mi-8 R-828.
- **Listen-only (no DF)**: A-10C/II, F-16C, AV-8B, AJS-37, JF-17, M-2000C (TACAN only),
  the FC3 fleet — for them the hunt is the intel circle plus eyeballs.

So the **UHF 225–400 AM "C2/air net" is the primary DF band**
(Hornet/Tomcat/Phantom/Tiger all home on it) and builds first; the **LF/MF "agent net"**
(~300–1200 kHz AM, numbers-station CW for the helos/trainers) and the **VHF-FM "ground
net"** (30–76 FM, Huey/Kiowa homing) follow. The audit is documentation, not a flight
test — per-module needle behavior against scripted transmissions stays the in-game-pass
criterion.

**The one hard guardrail**: Python assigns net frequencies and validates them against
the mission's allocated blue comms plan (`RadioRegistry`) so a red net can **never** land
on a briefed blue channel — the §51 positive-list discipline, inverted into a hard
exclusion. GUARD is excluded by construction. No other anti-grief is needed: nothing
here targets blue's radios; hearing the enemy requires deliberately tuning off-plan.

**Audio — RESOLVED 2026-07-18 (squadron call #5): synthesized CW/beeps on every net**,
a distinct rhythm per net so they're tellable apart by ear; voice chatter is a deferred
expansion. Original assets only (§58 precedent); RMS-normalized (~−4 dBFS, the §51
lesson); bundled via plugin `otherResourceFiles` so they ride `l10n/DEFAULT/`.

**Emit contract**: `game/missiongenerator/rednetluadata.py` → `dcsRetribution.redNet` —
one record per alive source: `{ name, x, y, freqHz, modulation, powerW, windowSec,
gapSec, clip }`; empty/absent node ⇒ the plugin no-ops. Plugin:
`resources/plugins/rednet/` (options: window/gap/power/clip-set; plugin `defaultValue`
**ON** so the Python setting is the only gate — the §36 saved-default-off lesson).

### B2 — the clandestine transmitter (the DF hunt)

A **normal `comms`-category TGO authored off-base** — a field site (comms truck +
antenna mast + generator + a 2-man security team, vanilla units/statics), `concealed`
(§3 dashed circle). It joins the B1 net with a **distinctive schedule**: short windows,
long gaps — you DF it while it's up or you wait. Because it is *just a comms TGO*,
everything composes for free: killing it is a native kill that reduces red's source set
(§51 jam capacity, §52 planning where it's a CC, Feature A's take), and the §3
concealment circle is the search area the DF work shrinks. The Tier-1 active-nets
listing is how the hunt is briefed.

v1 placement is campaign-authored (the existing comms-TGO authoring path). v2: COIN
dynamic spawns — the cells/IED teams themselves transmit on the ground net during their
fuse windows, making the §P4 IED hunt a genuine DF problem (rides
`coin.spawn_red_ground_at`; movement/consequence stay in the turn model as always).

### Settings

`red_comms_net` — Mission Generation → Battlefield life, default **OFF** until flown.
Independent of `comint_collection` but designed to pair (A lists the nets B transmits;
either degrades gracefully alone).

### Files & tests

Emitter tests `tests/missiongenerator/test_rednetluadata.py` (source walk, frequency
exclusion vs the registry, no-sources ⇒ no node); harness tests
`tests/lua/test_rednet_runtime.py` (window schedule, stagger, stop-on-death via
`dead_events`, no transmission before grace). The DF experience itself (needle behavior
per module, audibility at range) is DCS-only — checklist row at landing, criteria: tune
each band from a front-area cockpit, hear the net, home an ADF needle to overhead the
site; kill the node and confirm silence.

---

## Deliberately out (with reasons)

- **SRS / ExternalAudio / gRPC TTS injection** — evaluated and rejected for §51
  (server-host dependency, buys nothing over the native path). Identical verdict.
- **Anything reacting to real player voice** — no API (comms-jam note: "not buildable").
- **In-mission "COMINT FLASH" cues** (survey option 2 — delayed intercept warnings off
  live red events: §61 scrambles, §63 launches, VBIED departures) — deferred; a cheap
  rider once A's gating (collector airborne + source alive + in range) exists in Lua.
- **Blue jamming red's net** — the §2 C-130J EW platform's lane (a COMMJAM mode is
  already the comms-jam note's deferred item), not this design.
- **Deceptive/false intercepts** — a v2 knob at most; v1 product is honest-but-coarse
  (the §5 approximate-precision precedent).
- **Force-model coupling of listening** (AWACS picture quality, detection buffs) — the
  take is intel/audio only; kills and combat stay native.
- **A C-130J COMINT sensor mode** (survey option 4, the scripts-layer twin) — clean fit
  for the ELINT track/triangulate pipeline, but that script has its own HANDOFF
  constraints and repo layer; separate effort if wanted.
- **DM-voiced red net over SRS** (survey option 5) — zero code, works today for events;
  nothing to build, just publish (or hide) a freq.

## Delivery

One PR per testable phase (the house norm):

- **C0 — Feature A core** (**LANDED 2026-07-18** as feature §70): `comint.py` + setting +
  kneeboard block + tests. Pure Python, headless-verifiable end-to-end; no DCS runtime
  risk. In-app pass = checklist B22.
- **C1 — Feature B1 ambient net** (**LANDED 2026-07-18**, same day as C0): emitter
  (`rednetluadata.py` — deterministic x.500 MHz off-grid freqs, registry-reserved) +
  `rednet` plugin (windowed/staggered looped CW, `node_dead`) + the synthesized
  `rednet-cw.wav` + harness tests. **UHF net first** (the fast-jet DF band per the
  call-#4 audit) — the LF/MF + FM nets remain future work with C2+. In-game pass =
  checklist B23 (audibility + per-module needle behavior).
- **C2 — B2 clandestine TX** + the A↔B findability tie (active-nets listing names the
  hunt) + first campaign authoring.
- **Later**: COIN dynamic transmitters, voice-chatter asset expansion, client intel
  surface, the FLASH cue layer.

## Squadron calls (all RESOLVED 2026-07-18, same day as the note)

1. **Tier-1 ambient take with no collector** — **keep.** The national-collection fiction
   stands: A works on all 67 campaigns and the C-130 *upgrade* is still felt.
2. **Tier-2 reveal strength** — **full snap** of one concealed circle; shrink-only
   dropped.
3. **Collector eligibility** — **both**: JAMMING flights and drones (see The collector).
4. **DF bands** — settled by the module audit (see the frequency plan): the squadron's
   "most jets can track ADF" hunch checked out for the fleet that matters —
   Hornet/Tomcat/Phantom/Tiger all DF UHF — so the **UHF net builds first**;
   F-16/A-10/Harrier/Viggen/JF-17/Mirage stay listen-only.
5. **Audio v1** — **CW/beeps only**, every net; voice chatter deferred.
