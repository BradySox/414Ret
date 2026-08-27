# 414th — what recon does now that engaging is the only reveal

Status: **candidate A is BUILT** (2026-08-18, same day — see
[414th-features.md §3](../414th-features.md), "Recon's one remaining job"). B and C remain
scoping only. Written immediately after the §3 recon rework left `FlightType.TARPS` and the
`recon` plugin mechanically inert. **The plugin was deleted 2026-08-20** (§12); neither B
nor C would have used its capture ledger, so nothing here is blocked by that.

## The constraint any new job must satisfy

Engaging a site reveals it **completely and permanently**. So recon cannot:

- reveal an un-engaged site's composition — that is "hidden until scouted", the rule the
  rework removed;
- confirm anything about an engaged site — that is the BDA damage lag, also removed.

Whatever recon does, it has to answer a question that engaging the site does not already
answer, about something engagement cannot settle.

## Candidate A — recon finds what is hidden outright — **BUILT 2026-08-18**

**This closed a hole the rework opened.** Implemented as
`MissionResultsProcessor.reveal_scouted_command_posts`: a surviving TARPS flight reveals any
hidden enemy command post within `TARPS_POD_RADIUS_NM` (3 NM) of its package target. Checklist
row **G40**. The analysis that led there is kept below.

Enemy **command posts** are hidden from the player's map entirely — no marker, not
right-clickable, not plannable (`hidden_on_player_map`, gated `scar_command_post_intel`,
default ON). They are revealed by `_command_post_revealed()`, which is
`captured_commander or discovered_by_player`.

Both keys are now dead ends for a player who plans by hand:

- `captured_commander` is **never set True anywhere in the tree** — the commander-capture
  mechanic was removed 2026-07-01 and only the flag survives.
- `discovered_by_player` is now set only by engagement, and you cannot frag a package at a
  target that is not on your map.

The one remaining path is the **auto-planner**, which enumerates strike targets on ground
truth (`ObjectiveFinder.strike_targets`, `viewer=None`) and will happily frag a package at a
command post the player cannot see. Once that package flies, `attacked_tgos_this_turn`
reveals the site. So the feature is reachable *only* by delegating planning — a hand-planner
can never map the command network.

Before the rework, recon was the intended path; the wiki said so in as many words.

**Shape:** a recon sortie whose route passes within some radius of a hidden command post
reveals it (marker + exact coordinates), and nothing else. Ordinary sites are unaffected
because they are already on the map. §50 ambush teams stay excluded — their whole point is
that the first sign of them is the in-mission TROOPS IN CONTACT call.

**Size:** small. The reveal path (`discovered_by_player = True`) already exists; this is a
geometric proximity check in `missionresultsprocessor` plus a gate so it only applies to
`hidden_on_player_map` sites.

## The remaining leak: the auto-planner (OPEN, undecided)

Three blue-side systems pick targets automatically off ground truth and could therefore
name a command post the player cannot see. Two are now gated (2026-08-18):

| Picker | Status |
|---|---|
| §63 auto cruise raids (`_enemy_raid_targets`) | **Gated.** Was the worst: `commandcenter` is priority 0, so the first raid of a campaign went straight at the un-found HQ |
| §44 long-range carrier strike (`_nearest_legal_strike_target`) | **Gated** |
| Upstream auto-planner (`ObjectiveFinder.strike_targets`) | **Not gated** |

The third is a real decision, not an oversight. `strike_targets` enumerates every enemy
`BuildingGroundObject` on ground truth, and a command post is one — so a player who
delegates planning still gets HQs fragged for free, and G40 only bites for a hand-planner.

Both readings are defensible:

- **Gate it.** The fog should mean the same thing however the player plans. Otherwise
  "auto-plan the turn" is a cheat code for the command network.
- **Leave it.** The auto-planner is the player's staff, and upstream's whole model is that
  the planner uses truth while the *map* is fogged. Gating it is a fork divergence in
  upstream code, and it makes auto-planned campaigns strictly worse at a job they used to
  do.

Not decided. Do not gate it without an explicit call — it changes what the auto-planner
does for every campaign, not just the fogged ones.

## Candidate B — recon tracks what moves

Fleet control points genuinely relocate between turns: `ControlPoint.process_turn` sets
`self.position = self.target_position` and shifts every linked
`GenericCarrierGroundObject` by the same delta (`controlpoint.py:1174`). An enemy carrier
group you found last turn is somewhere else this turn, and nothing tells you where.

**Shape:** an enemy naval group's *position* on the player map is its last observed position,
not its live one, and a recon pass re-fixes it. Composition stays fully known (it was engaged)
— only the fix goes stale. This does not reintroduce a lag, because the thing going stale is
a coordinate that actually changed, not a fact about damage.

**Size:** medium. Needs a per-TGO "last observed position" field, a save migration, and the
map/DTC/kneeboard consumers pointed at it.

**⚠️ The mobile-missile version of this does NOT work today.** §49 relocation is
**in-mission Lua only** (`resources/plugins/mobilemissiles/mobilemissiles-config.lua`, fed by
`game/missiongenerator/mobilemissileluadata.py`). There is no Python-side position writeback,
so a launcher's campaign coordinate never moves — which is what the Marianas note already
recorded ("once photographed the coordinate stays good"). Extending B to §49 means building
the writeback first. Do not propose "recon re-fixes a scooted SCUD" without that.

## Candidate C — recon produces an intel product, not campaign state

Recon stops touching the fog entirely and instead produces something you read: a per-target
imagery card on the kneeboard — individual unit positions inside the site, revetment layout,
an aimpoint list, approach notes. You always know *what* is at an engaged site; recon tells
you *how to hit it*.

**Shape:** the recon kneeboard machinery already exists (`game/missiongenerator/kneeboard_recon/`)
and ships default-off pending an in-game pass on the tile alignment fix. This would give it a
reason to be on.

**Size:** medium, and it is the only candidate that is purely additive — it can never
conflict with the reveal rule because it never writes campaign state.

### C.1 — the recon bird gets the target card — **BUILT 2026-08-26**

**The hole nobody had noticed.** `_FLIGHT_TYPES_WITH_RECON`
(`kneeboard_recon/pages.py`) held nine air-to-ground types and **not `TARPS`**. The
recon bird rides the strike package and shares its target, so it reached the
dispatcher with everything a page needs — it was simply never in the set. The one
pilot whose entire sortie is imagery was the only member of the package flying
without the target card. Its aimpoint list doubles as the shot list.

One line plus its contract test. The contract test's docstring cited a
"Spec design doc table" in `414th-tars-recon-notes.md`, **deleted 2026-08-20 (#922)** —
a dead citation, now replaced with the rule stated in place and a pointer here.

**Why this became worth doing on 2026-08-26.** The DCS patch reworked TARPS: a
*significantly* reduced performance cost, pilot-operable recording (`hold Store
Release`, plus a Jester submenu) so it is a single-seat sortie, the KA-99 panoramic
camera, and an "intel analysis department" that circles and describes units in the
developed photos. The imagery itself is **not script-reachable** — it lives in
`F14-Avionics.dll` and renders to a cockpit indicator — which is precisely why C is
the right shape: we cannot consume DCS's product, but we can hand the same pilot our
own card for the same pass. Full reading in
[414th-dcs-update-2026-08-26-notes.md](414th-dcs-update-2026-08-26-notes.md) §6.3.

### C.2 — WITHDRAWN as written; the fog gate is what it actually was

**C.2 was wrong, and it was written here on 2026-08-26 by the same session that
built C.1.** It said the card should become recon's *output* — that flying a pass
earns the detailed card for a later strike. That is scout-to-reveal in a kneeboard
costume, and **the constraint section at the top of this very note forbids it**:
recon "cannot reveal an un-engaged site's composition — that is 'hidden until
scouted', the rule the rework removed". Under §3 there is no room for recon to grant
composition, so there was never a legal version of C.2 to build. Do not re-propose it.

**What was really there was a fog leak, and it is now fixed.** The recon pages read
enemy state through no gate at all — `grep` found zero references to `known_for`,
`hidden_from` or `visibility_for` across all 17 modules:

| Site | Handed over ungated |
|---|---|
| `DetailReconPage._build_aimpoints` | exact unit positions, type descriptions, footprints, alive/dead state |
| `OverviewReconPage._nearby_threats` | `max_threat_range()`, `max_detection_range()` and true position for every enemy TGO in the corridor |

The canonical contract is `game/server/tgos/models.py` `TgoJs.for_tgo`, which
withholds exactly those fields for an un-engaged site **and jitters the position**.
So a strike fragged at a site nobody had touched printed its composition and accurate
rings, while the map beside it showed a jittered circle and nothing else.

Both now gate on `_known_to_blue` (a thin wrapper over `known_for(Player.BLUE)`,
tolerant of non-fogged targets like a ControlPoint or FrontLine). Two tests pin it and
were checked to **fail without the gate**, which is the only reason to trust them —
every pre-existing test used `MagicMock` targets that read as "known" and passed
unchanged either way.

**One deliberate asymmetry, recorded so it is not read as an oversight.** An
un-engaged site is dropped from the overview entirely rather than drawn ring-less.
The map can show a bare contact because it jitters the position; this page has no
jitter, so a ring-less marker at the true coordinate would still leak a location the
map conceals. The cost is that an unknown threat is absent rather than shown as an
unranged contact — under-showing is the safe direction for a fog fix.

Not a nerf, either: nothing was taken from a player who was entitled to it. The
un-engaged card is now sparse **because the fog says so**, which is the same reason
the map is.

`generate_target_recon_kneeboard` stays **default off**: the tile-alignment fix of
2026-07-18 is still unflown (checklist **H15**/**H16**). Those rows gate the whole of
C — and this leak is why the setting could not have come on before now regardless.

## Recommendation

**A first, on its own** — done. It was small, it fixed a live hole rather than inventing a
mechanic, and it gives recon a job that is impossible to confuse with scout-to-reveal: it only
reaches sites that are not on the map at all.

**C.1 followed, 2026-08-26** — same character: a live hole, not a new mechanic. The
2026-08-26 TARPS rework is what made it worth doing.

**C.2 is withdrawn** — it was never legal under §3, and the fog gate is what it was
actually pointing at. B remains open, and is the largest and the one most likely to
feel like a lag to a player even though it technically is not.

**Recon's job is therefore settled at A + C.1**: it finds what is hidden outright
(command posts), and its own pilot carries the target card. Anything more requires
changing §3 itself, which is a DM decision and not a recon decision.

## See also

- [414th-features.md §3](../414th-features.md) — the reveal rule this has to live under
- [414th-features.md §12](../414th-features.md) — the recon engine, removed 2026-08-20
- `414th-tars-recon-notes.md` — deleted 2026-08-20, recoverable from git before
  `5db34150f`. Do not author against
