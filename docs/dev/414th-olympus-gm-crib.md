# 414th — Olympus GM crib sheet + Tier-0 compatibility pass

> **Tier 0 green-lit 2026-07-20** (DM call on the exploration note,
> [`docs/dev/design/414th-dcs-olympus-notes.md`](design/414th-dcs-olympus-notes.md) — read
> that first for the full analysis). This page is the operational half: **Part A** is the
> one-page crib for whoever runs Olympus at an event; **Part B** is the compatibility pass
> to fly once on the private-session server before Olympus touches a squadron event.
> Deliberately **no in-game-pass checklist row** — Olympus is not a registered feature and
> the registry test would (rightly) reject the row; this doc carries its own pass card.

---

## Part A — GM crib sheet

Prerequisite: Olympus installed server-side via its Manager (pin the version; v2.0.5 at
time of writing), the squadron connects by browser only. GM role = ground truth;
Blue/Red Commander roles are sensor-fogged.

### The ledger — what counts, campaign-side

- **Anything you spawn is free event content** (the §61 doctrine): red pays nothing for
  it, and its death changes nothing at the turn boundary.
- **Anything your spawns kill is real.** Blue jets, tracked ground units, TGO buildings —
  recorded natively at debrief; front line, economy, will, and pilot rosters all feel it.
  A player killed by your spawn is a real pilot + airframe loss (the
  `invulnerable_player_pilots` setting spares the pilot only).
- **Delete ≠ kill.** An Olympus despawn fires no death event, so the campaign never
  learns: a deleted *tracked* unit is alive again next turn. To make a kill
  campaign-real, kill it (weapons, explosion effects). Use delete only to mean "this
  never happened."
- Effects (explosion/napalm/WP) that kill tracked units are real kills like any other.

### AI reactions to your spawns — know before you spawn

- **The AI QRA reserve will NOT scramble against a GM raid.** The react filter classifies
  raids by the Retribution `{target} {task}|…` group-name format; a name with no `|` is
  non-ATO air and is *never* reacted to (`intercept-config.lua` `qra_group_reacts`,
  documented behavior). If you want ground-alert defenders to meet your raid, spawn and
  steer them yourself.
- **Airborne CAPs fight normally.** BARCAP/TARCAP flights engage anything detected in
  their zones — your raid will get met by whatever is already airborne.
- The player scramble cue (PLAYER_ALERT) is deliberately task-blind and may still cue a
  human alert flight against your raid — **[observe on the pass]**.
- **A GM-spawned SAM fights alone**: vanilla DCS AI, radar always-on, no MANTIS
  EMCON/C2 coupling, no §7 datalink hiding, no campaign-map threat ring, absent from §74
  DTC cartridges. It is a pop-up trap, not an IADS node — good drama, but don't expect
  authored-SAM behavior, and don't "fix" it by touching MANTIS prefixes (see the
  exploration note §3 for why that's wrong).

### Hands-off list — groups the scripts are driving

Re-tasking these is a tug-of-war the plugin wins on its next cadence tick (§49 re-routes
~8 min; COIN re-paths on poll). Steer **your own spawns**; leave these alone unless you
deliberately accept the fight:

- §49 mobile missile batteries (fire-then-scoot choreography);
- COIN movers — HVT convoys, VBIEDs, dispersed cells, infiltrators;
- §50 ambush teams (dug-in, proximity-sprung — moving them breaks the spring);
- Combat SAR actors — survivor, snatch teams, rescue helos mid-pickup (the snatch race
  is ROE-hold *by design*; making them shoot breaks the capture mechanic);
- TIC frontline firefight groups; CTLD sticks;
- anything MANTIS owns (SAM/EWR sites — alarm state/emissions are its to command);
- dispatcher fighters (QRA/CAP AI).

### Seams and switches

- **§59 AI sleep**: rear garrison groups have their controller OFF until an aircraft
  closes ~15 NM or they take a hit — an Olympus order to a slept group does nothing
  until then. For GM-heavy events, either leave `perf_ground_ai_sleep` off or wake
  groups by flying something near them.
- **Anti-grief guarantees bound the automation, not you.** §36 harassment can never
  shell a player ramp; *you* can. Know that you're outside the guardrails.
- **Mod units**: Olympus spawns vanilla + whatever mods it's configured for; the fork's
  mod fleet (HDS etc.) needs Olympus-side configuration **[verify at install]**.
- **SRS voice** (needs the HTTPS server config): transmit as the enemy on the §70
  red-net UHF frequencies (players see discovered ones on the COMINT kneeboard block),
  taunt on JAM BACKUP, run downed-pilot drama — or loudspeaker-assign to units for local
  color.
- **After the mission: nothing to clean up.** The debrief reads only DCS events; there
  is no Olympus-side state. For the first few events, sanity-scan the debrief anyway.

---

## Part B — Tier-0 compatibility pass card

Run **once on the private-session server** before Olympus touches a squadron event.
Fly it twice: once on a **heavy laydown** (Red Tide, or 1968 Yankee Station — the §59
measured stress case) and once on a **COIN campaign** (Enduring/Inherent Resolve — the
mover-dense case). Record results in the box at the bottom; fold `[verify]` answers back
into this doc and the exploration note.

| # | Step | PASS looks like | FAIL signature |
|---|---|---|---|
| 1 | Generate + load a current-build mission with Olympus running; connect a GM browser. | All plugin banners in dcs.log (`BRIEFING\|`, `REDSCRAMBLE\|`, MANTIS init, TARS/TIC late-init); Olympus map live. | Missing banners; sandbox errors mentioning Olympus. |
| 2 | Ingress toward a red SAM belt (or watch AI do it). | MANTIS EMCON intact: sites dark until cued, light per range-mode. | Every radar radiating from T0 (set filters broken). |
| 3 | Spawn a red 2-ship at a red field; waypoint it at blue. | It flies your orders. AI QRA does **not** scramble (non-ATO name, by design); any airborne BARCAP engages normally. Note whether a player alert flight gets the PLAYER_ALERT cue. | AI QRA scrambling against it (filter regression); the spawn refusing tasking. |
| 4 | Spawn an SA-6/8 near the ingress. | Fights vanilla-and-alone: radar on, engages in range; no MANTIS log adoption; no campaign-map marker. | MANTIS claiming it; it holding fire inexplicably (would suggest something managed it dark). |
| 5 | Spawn junk; exercise every Olympus delete flavor. Then delete ONE tracked rear red unit deliberately; end mission. | Debrief: the deleted tracked unit is NOT a loss and survives next turn ("despawn = erase" confirmed). Record which flavor, if any, fires a real death event. | The despawned unit recorded as killed (would change the crib's ledger rules). |
| 6 | Kill one tracked red unit with a GM spawn or effect. | Debrief shows the loss; next-turn campaign state reflects it. | The kill missing from the debrief. |
| 7 | Watch a §49 battery or COIN mover with the Olympus map; optionally re-task one. | The script re-asserts on its next cadence (evidence for the hands-off rule). | The mover permanently hijacked (would mean the cadence re-push broke). |
| 8 | Heavy laydown, `perf_ground_ai_sleep` ON: order a slept garrison group; then fly near it and re-order. | Nothing happens while slept; wakes on approach; then obeys. | A slept group obeying (sleep broken) or never waking. |
| 9 | Perf: note server FPS/frametime with Olympus idle vs GM map active, heavy laydown. | No meaningful delta; no ANTIFREEZE log events that don't occur without Olympus. | ANTIFREEZE onset correlated with Olympus. |
| 10 | (If HTTPS configured) transmit on a §70 red-net frequency. | Players tuned there hear the GM. | — (feature simply unavailable without HTTPS). |
| 11 | Full turn close-out. | Debrief/`state.json` parse clean; §66 mission archive intact; next turn processes normally. | Debrief poll errors; archive missing. |

**Also record while you're in there** (the exploration note's `[verify]` items): the
actual group names Olympus assigns to spawns · which ME drawing layers (FLOT, §40
zones, §45 orbit capsules) render on the Olympus map · `autoexec.cfg` surviving a DCS
update · the delete-flavor semantics from step 5.

### Results

| Date | Campaign | Build | Olympus ver | Steps passed | Notes |
|---|---|---|---|---|---|
| — | — | — | — | — | not yet flown |
