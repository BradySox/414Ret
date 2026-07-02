# Combat SAR as a normal, two-sided auto-task (design / scoping)

**Status (updated 2026-07-01):** the **Route 1 survivor-ledger core (below) HAS SHIPPED** —
`resources/plugins/combatsar/combatsar-config.lua` is that ledger. AI rescues now credit by real
identity (`creditRescue` from `dispatchAIRescue`; verified in-game 2026-06-30, 3 credited rescues in
`state.json` / `game.last_sitrep.pilots_recovered=3`, checklist G11), AI ejections are capturable →
POW (a captured A-1H pilot in the same session, G20), and the runtime is coalition-generic (would
consume `dcsRetribution.CombatSAR.red`). So the "AICSAR anonymous-clone / uncredited AI rescue"
problem this note diagnoses is **already fixed** — do NOT re-implement the ledger.
**Phase 3 (symmetric red) is REJECTED — squadron call 2026-07-01: red flies NO CSAR.** Red combat-SAR
planning briefly existed via the coalition-generic `combat_sar_targets` seeding and produced exactly
the noise this note worried about: red rescue packages burning airframes and a **BLUE snatch party
spawning to race every red ejection**. The seeding is now BLUE-gated (`theaterstate.py`), the
generator **never emits the `red` Lua node** (`luagenerator._generate_combat_sar`), and the plugin's
red path stays dormant capability only. Do not re-enable without a fresh squadron call. What remains
design-only from this note is just Phase 1 (blue default-on; `auto_combat_sar` still defaults OFF).
· **Date:** 2026-06-27 (status refreshed 2026-07-01)
**Related:** [`414th-combat-sar-spec.md`](414th-combat-sar-spec.md) (the shipped blue feature),
`414th-scar-rescue-rework-notes.md` (Sandy/POW/capture rework), CLAUDE.md §21 (Combat SAR) +
§15 (SCAR "Sandy"). In-game-pass rows: **G8–G14**.

## LOCKED 2026-06-28 — Route 1: one owned survivor ledger (supersedes the two-engine split)

**User picked route 1.** Replace the two disjoint MOOSE engines — player-only `CSAR`
(owns scoring + the capture race) and AI-only `AICSAR` (anonymous clones) — with **one
plugin-owned survivor ledger** that is the single source of truth, coalition-generic, with
**player and AI rescues judged by the SAME geometry logic**. This fixes the root cause
diagnosed in the 2026-06-28 Vietnam test: the campaign-meaningful machinery (rescue credit,
capture→POW) was bolted onto the human-only engine, so AI losses — the common case —
produced nothing.

### Why the two-engine split fails (evidence, 2026-06-28)
- Capture race iterates `csar.downedPilots`; `csar.enableForAI=false` ⇒ AI ejections never
  enter it ⇒ **AI can never be captured** (`combatsar-config.lua:99/204/215`).
- AI rescues run on `AICSAR`, which spawns an **anonymous clone** and never fires CSAR's
  `OnAfterRescued` ⇒ **AI rescues are uncredited** (`:294`, `:430`).
- Net in the test: 5 AI pilots ejected, AICSAR flew, but `combat_sar_captures=[]` and
  `combat_sar_rescues=[]` ⇒ nothing reached the turn processor ⇒ no POW, no spared pilots.

### The ledger (Lua, in-mission — single source of truth)
`survivors[id] = { unit=<orig airframe unit name>, coalition="blue"|"red",`
`group=<downed-pilot group name>, coord=<vec2>, state="down"|"boarding"|"rescued"|`
`"captured"|"dead", party=<snatch group|nil>, dwell=<s>, t0=<time> }`

- **Register** on `S_EVENT_EJECTION` for **either** coalition (one world event handler —
  already prototyped as the AI eject bridge). Spawn a downed-pilot group from that
  coalition's template; record the real `unit` name + coalition + coord.
- **Rescue judging (engine-agnostic, identical for player & AI):** poll — a *friendly* helo
  (human- or AI-crewed) within `loadDistance` of a `down` survivor for `boardDwell`s ⇒
  `boarding` (pilot attached to that helo); that helo lands at / reaches a friendly
  airfield/FARP ⇒ `rescued` ⇒ append the real `unit` to `combat_sar_rescues`. Helo
  destroyed with the pilot aboard ⇒ survivor returns to `down`.
- **AI dispatch:** spawn a rescue helo from the survivor's coalition's nearest friendly
  field and route it to the survivor (reuse the existing FARP/route plumbing). **No anonymous
  clone** — the ledger holds identity, so the AI rescue credits exactly like the player path.
- **Capture race:** same logic, but reads the **ledger** (not `csar.downedPilots`); snatch
  party = the **opposing** coalition; on capture append `{unit,x,y,coalition}` to
  `combat_sar_captures`.
- **Player drop-in:** any human-crewed friendly helo satisfies the same proximity rule ⇒
  identical credit. The King LARS F10 locator stays.
- **Tradeoff:** we drop MOOSE CSAR's radio-menu pickup UX (request-smoke, "wounded runs to
  helo", board countdown) for the simpler land-near-survivor geometry. Revisit if players
  miss it; the locator + smoke-on-spawn cover "find the pilot".

### Coalition-generic data contract (Python → Lua)
Generator emits both sides (e.g. `dcsRetribution.CombatSAR.red = { pilotTemplate,
rescueHelos[], kings[], farp }` mirroring blue). Planner frags both. `record_pow_captures`
/ `pow_recovery` / `pow_objectives` / `Coalition.end_turn` handle the **capturing** coalition
generically (captured red pilot held at a blue field, recoverable by red, and vice-versa).

### Build order (each independently shippable; blue-first verify → red)
1. **Lua ledger core** — replace CSAR+AICSAR with the ledger (blue wired live, code written
   coalition-generic). Capture + AI dispatch + player pickup + scoring all read the ledger.
   → **in-game pass G8/G9/G11**. *(Drafted in scratchpad, swapped in only when complete, so
   the live plugin never sits half-rewritten.)*
2. **Python coalition-generic emit + scoring** — red template/helos/king; both-sided
   `record_pow_captures`. Verifiable via pytest; inert until the Lua red path is on.
3. **Enable red** — drop the blue filters in the plugin + the `player.is_blue` planner gate.
4. **Default ON + save migration + docs** — only after the blue in-game pass passes.

## Vision (user's words, locked 2026-06-27)

> I want the system to work where it's auto-fragged for AI to go pick up AIs (hopefully with red
> too) and players can drop in if they wish. Just a normal task.

So Combat SAR should behave like BARCAP/SEAD: the commander frags a standing rescue capability
**every turn, for both sides**, the AI actually flies the rescues (including for downed **AI**
pilots), and a human can slot in to fly it if they want — no special opt-in ritual.

## Where we are today (the honest baseline)

Most of the **blue** half already exists, behind `Settings.auto_combat_sar` (**default OFF**, and
**never flown** — checklist G9 is UNTESTED). With it on:

- `PlanCombatSar` (`game/commander/tasks/primitive/combatsar.py`) auto-frags a standing package
  each turn — King (C-130) + Jolly Green (rescue helo) + 1 Sandy (SCAR) — air-started ASAP.
- The MOOSE **`AICSAR`** engine (`resources/plugins/combatsar/combatsar-config.lua`) flies the AI
  rescue: it spawns its own rescue helo from the alert FARP and recovers survivors, **including AI
  ejections**, delivering to a `ZONE_AIRBASE`.
- `AICSAR` `autoonoff` **stands down** when a human crews a rescue helo, so the player-flown path
  (`enableForAI=false` MOOSE `CSAR`) never competes — i.e. a human can already take over.

### The gaps between that and the vision

1. **Default OFF.** "Just a normal task" ⇒ default ON. One field flip + save migration — but do
   **not** default-on a feature that has never had its in-game pass (see Phase 0).
2. **Blue-only — the big one.** Everything is hardcoded to blue:
   - planner: `combat_sar_targets` is populated only `if game.settings.auto_combat_sar and
     player.is_blue` (`game/commander/theaterstate.py:305`; the non-blue branch at :334 skips it).
   - generator: `_emit_combat_sar` (`game/missiongenerator/luagenerator.py:336`) filters
     `flight.friendly.is_blue` and early-returns if there is no blue rescue **helo**.
   - plugin: `CSAR:New("blue", …)`, `SET_GROUP:FilterCoalitions("blue")`, and the `AICSAR`
     instance are all blue.
   - POW path: `record_pow_captures` creates `PendingPowRecovery` on the **blue** coalition only;
     the capture race spawns **CJTF_RED** snatch parties against **blue** survivors only.
3. **AI-rescue scoring is cosmetic.** An `AICSAR` pickup spawns an **anonymous pilot clone**, so
   the original ejected unit name is lost and the spare-the-aviator credit (`combat_sar_rescues`
   → `commit_air_losses`) never applies. "AI picks up AIs" currently changes nothing in the
   campaign model. (Known v1 limitation, §21.)
4. **Drop-in is partial.** A human who *frags or crews their own* rescue helo works (AI yields).
   But the **auto-alert flights themselves are AI** (no client slots), so you can't slot straight
   into the standing alert without editing the flight. True "drop in" wants client slots on the
   alert (or a per-flight toggle).

## Target end-state

| Axis | Today | Target |
|---|---|---|
| Default | OFF, opt-in | **ON** (after Phase 0 verification) |
| Coalitions | blue only | **blue + red**, symmetric |
| AI rescues AI | yes (blue), but uncredited | yes (both), **credited** where it should count |
| Player drop-in | frag/crew your own; AI yields | same **plus** joinable alert slots |
| POW / capture | blue survivors → red snatch → blue POW | **both directions** |

## The work, by layer

### Phase 0 — Verify blue first (gate; no code) — *this is option 1*
Fly the rescue test with `auto_combat_sar` **ON** and confirm in the cockpit that `AICSAR`
actually launches and completes an AI→AI rescue (closes **G9**), the King TACAN/LARS work
(**G10**), and the capture race → POW carryover works (**G8**). **Do not build red or flip the
default on top of an unverified engine.**

### Phase 1 — "Normal task" for blue
- Flip `auto_combat_sar` **default ON** (`game/settings/settings.py`); add a `__setstate__`
  migration note so existing saves keep their stored value (only *new* campaigns default on).
- Decide drop-in: generate the alert with **client slots** (preferred) vs. leave frag-your-own.
  If client slots: the alert flight needs a client count and a sane start (the AI air-starts on
  station; a client likely starts cold/at a field — confirm the forward-hold plan still works).

### Phase 2 — AI-rescue scoring (make AI→AI matter)
- Carry the **original ejected unit name** through `AICSAR` so a completed AI rescue appends to
  `combat_sar_rescues` (or an equivalent), and `commit_air_losses` spares that pilot — same as the
  player path. If AICSAR can't preserve the name, score it from the Python side off the
  ejection/recovery events instead. Open question: do we credit **red** AI rescues too (does red
  pilot experience matter in the campaign model? — see Open questions).

### Phase 3 — Symmetric red (the big one)
- **Planner:** populate `combat_sar_targets` for red too (drop the `player.is_blue` gate;
  generalise the :334 branch). `PlanCombatSar` already proposes King/Jolly/Sandy generically.
- **Generator:** emit a red `CombatSAR` data table (red rescue helos / king / template), not just
  blue. Generalise `_emit_combat_sar` over both coalitions.
- **Plugin:** stand up a **second CSAR + AICSAR instance for red** (`CSAR:New("red", …)`,
  `FilterCoalitions("red")`), parameterised so the two coalitions share one code path. Watch the
  `FilterPrefixes` match-all sentinel per side.
- **Capture race:** spawn the **opposing** coalition's snatch party per survivor (CJTF_BLUE vs a
  red survivor; CJTF_RED vs a blue survivor).
- **POW path:** `record_pow_captures` / `pow_objectives` / `surviving_pows` must handle **both**
  coalitions (a captured red pilot held at a blue field, recoverable by red, and vice-versa).

## Open questions / risks

1. **Does red CSAR matter to the player?** Symmetric immersion vs. "red rescuing its own AI pilots"
   having little gameplay weight. Minimum viable red = red *tries* to rescue (immersion) even if we
   don't fully wire red pilot-experience scoring.
2. **Two CSAR/AICSAR engines = performance.** Two full MOOSE CSAR FSMs + capture polls every tick.
   Profile on a heavy map; the capture poll is already pcall-guarded.
3. **AICSAR per-coalition behaviour** — confirm `AICSAR` (and its FARP/ZONE_AIRBASE assumptions)
   works for red FARPs/airbases the same way it does for blue.
4. **Save migration of the default flip** — must not silently turn it on for in-progress campaigns.
5. **Balance** — a standing rescue package every turn for both sides consumes airframes; confirm it
   doesn't starve other tasks (airframe scarcity already self-limits the blue alert).

## Sequence

**Phase 0 (verify blue) → Phase 1 (blue default-on + drop-in) → Phase 2 (scoring) → Phase 3 (red).**
Each phase is independently shippable and testable; red rides on a *proven* engine, not a hopeful one.

## File map (touch-points)

- Planner: `game/commander/theaterstate.py`, `game/commander/tasks/primitive/combatsar.py`
- Settings: `game/settings/settings.py` (`auto_combat_sar` default + migration)
- Generator: `game/missiongenerator/luagenerator.py` (`_emit_combat_sar`)
- Plugin: `resources/plugins/combatsar/combatsar-config.lua`, `plugin.json`
- POW / capture / scoring: `game/sim/missionresultsprocessor.py`, `game/pow_recovery.py`,
  `game/pow_objectives.py`, `game/debriefing.py`, `resources/plugins/base/dcs_retribution.lua`
- Docs on landing: README.md, `docs/dev/414th-features.md` §21, the feature registry/index, the
  in-game-pass checklist (G8–G14), and the wiki (`docs/wiki/Combat-SAR.md`).
