# Neutral-Faction Border Defense — Design Note

**Status: BUILT 2026-08-24 (§96).** Scope locked in a DM Q&A session the same day; every
decision below is a DM call from that session. Read this before editing or re-litigating
any of it. Features doc §96 carries the file list; in-game passes B110/B111 owed.

## What it is now

This note is chronological below this point; the 2026-08-24 sections describe the shape
the feature was first built in, not the shape it is in. Read this section for what is
true, then the dated sections for why.

- **Every nation on the map is drawn with its real border**, the map's own nation
  included. Alignment is derived from who holds the airfields inside it, counted per
  country: both sides holding it is contested grey and claimed by neither, a country
  already in the war is outline-only, and red-aligned airspace joins §1's QRA accept
  zones. Overflight consent comes from the same airbases -- you may cross what you fly
  from, and what both sides fly from.
- **A country not in the war flies a standing patrol inside its own border**, spawned
  in the air at mission generation, orbiting for the whole mission. It is on the neutrals
  coalition, so it cannot shoot and nothing shoots it. **The scramble is gone** -- three
  flown attempts to launch one on demand failed the same way each time (see *The standing
  patrol*, 2026-08-29).
- **Crossing gets you hailed on the radio immediately, then warned again at dwell.**
  Neither call launches anything -- the patrol is already up.
- **Pressing turns the patrol hostile in place**: `GROUP:Respawn(template, true)` with the
  intruder's opposing `CountryID`/`CoalitionID`, which copies live position, altitude and
  heading. It then engages with §61's raw `AttackGroup` task, re-set only when the target
  id changes. **Players only** -- an AI intruder is shadowed, never engaged.
- **Both sides violating one country gets a second flight**, not a re-swap: the first
  patrol keeps its coalition and a `NEUTRAL AF2 <country>` clone comes up on the other.
  Two intruders on one side gets nearest-target retasking on a 20 s loop.
- **The SAM belt is an escalation-time clone, not standing units.** A cold late-activation
  SA-6 template (1S91 + 2x2P25) sits at the field and is SPAWN-cloned under the opposing
  coalition only when a player escalates. No standing red units at a neutral field -- which
  also avoids DCS auto-capturing the airbase at mission start. Composition is fixed v1;
  the yaml carries `sam: true` by default.
- **Borders ship with the terrain**, built by `tools/build_terrain_borders.py` from
  public-domain GeoJSON into `resources/borders/*.yaml` -- 8 terrains, 8,244 vertices at a
  384-vertex / 500 km2 budget. A campaign authors none of this.
- **Reference campaign: Into the Hornet's Nest + Lebanon** (DM call). Rayak field, MiG-29A
  (the type Russia offered Lebanon in 2008), 10,000 ft floor, SA-6 on. Desert Storm + Iran
  was investigated and rejected on the evidence: the DS corridor is H-3 to Baghdad (west)
  and the map's only Iranian field is Kharg, far south -- the border would never trip.
- **Nothing here is verified in DCS.** The Lua harness cannot exercise DCS AI; B110/B111
  carry the flown verdicts, and both are `PARTIAL` against the standing-patrol redesign.

## Engine verdict (investigated 2026-08-24 — do not re-investigate)

- **A true-neutral unit cannot be made to fire.** Weapons release is gated on coalition
  hostility, not tasking. `AttackUnit` / weapons-free on a `coalition.side.NEUTRAL` unit
  does nothing, a neutral SAM never engages, and the scripting engine has no API to move a
  country between coalitions at runtime.
- **The loophole is spawn-time coalition choice.** `SPAWN:InitCountry` / `InitCoalition`
  override the template's country before `coalition.addGroup`
  (`resources/plugins/base/Moose.lua:20316`); the fork already uses this live
  (`airboss.lua`). The violator's coalition is known at trip time, so alert units spawn
  under the coalition that opposes the intruder.
- **Respawn-in-place under a new coalition exists** as a fallback mechanism:
  `coalition.addGroup` with an existing group name silently swaps the units, firing only
  S_EVENT_BIRTH (`land_relocate.lua` documents it; `mist.dynAdd` implements it). Flown
  only for ships at mission start — an airborne swap is unproven. **Not used in v1** (see
  the accepted risk), but recorded here so the fallback never needs re-research.
- **Generated missions already carry a neutrals coalition with countries**
  (`missiongenerator.py:226`) and neutral-coalition spawns are proven (civilian traffic).
- **Structural template: §61 redscramble** (`redscramble-config.lua`) — late-activation
  templates, `SPAWN:NewWithAlias`, air-spawn overhead the field, forced vectoring onto a
  target group. The engage half of this feature is that plugin's proven mechanism.

## Decisions (DM calls, 2026-08-24)

| Question | Call |
|---|---|
| Combat shape | **Single-flight escalation ladder.** One alert flight spawns red-flagged (visible as red) at the neutral field, shadows the intruder without firing, and on escalation the *same* flight is tasked to engage the group it is shadowing. No two-flight handoff, no coalition swap. |
| Shadow-phase ROE | **Return-fire**, not weapons-hold — a shadower that is shot at defends itself but never initiates. (Refinement inside the "spawn red, do not attack before escalation" call.) |
| Border trigger | **Authored border polygon + altitude floor.** Inside the polygon below the floor for N seconds trips it. A high transit over neutral territory is legal. |
| Who trips it | **Everyone.** Players get the full ladder. **AI intruders are shadowed only — never escalated on.** The planner stays blind (no navmesh hazard; do not reopen the §6 revert). |
| Consequences | **In-mission only for v1.** Nothing persists past the debrief. Escalating posture / joining the war are explicitly future work. |
| Unit tracking | Spawned alert units are **free, untracked event content** — the §61 precedent, called out explicitly against the no-phantom-units constraint. Valid while v1 is in-mission-only. |
| Ground layer | **SAM belt at the neutral field**, red-flagged, ROE weapons-hold, flipped weapons-free by the plugin on player escalation only. ROE-only suppression/release — the §51/§63/§77 mechanism. Never `enableEmission` (hard constraint). |

## Accepted risk (DM call, reaffirmed after the caveat was raised)

A red-flagged shadower is a legal target for every blue AI in sensor range from the moment
it spawns — the intruder's wingmen or a nearby CAP may engage it during the shadow phase,
uninvited. The DM accepted this in exchange for the simpler single-flight build ("it's
fine if they spawn red and show up as red, as long as they do not attack and shadow before
escalation"). Return-fire ROE means the shadower fights back rather than dying passively.
If flown tests show shadowers routinely dying before escalation, the recorded fallback is
the respawn-in-place coalition swap above — do not re-derive it.

Mirror case: a *red* intruder gets a blue-flagged shadower, symmetric behavior.

## Escalation triggers (player intruders only)

1. Dwell — remaining inside the polygon below the floor past a second, longer timer.
2. Weapon release inside the polygon (S_EVENT_SHOT by the intruder group).
3. Firing on the shadower or any unit of the neutral country (also covered by return-fire).

On escalation: shadower goes weapons-free + `TaskAttackGroup` on the shadowed group, and
the field's SAM belt flips weapons-free against that coalition.

## Architecture as built

Planner/Lua split as usual — Python sets up, Lua executes:

- **Python** (mission generation, not campaign state): a `neutralborder` plugin +
  generator that, for each participating neutral CP, spawns the SAM belt and
  late-activation fighter templates as **miz-only units bound to no campaign TGO** (the
  civiliantraffic pattern — regenerated every mission, never in campaign state, so the
  planner and fog never see them). Emits config: border polygon, altitude floor, timers,
  template names, field name, per-side template coalitions.
- **Border authoring (DECIDED 2026-08-24): real border data, converted once by a tool.
  Real-world-georeferenced maps only — fictional-overlay campaigns are out of scope for
  this feature (DM call).** Pipeline: Natural Earth admin-0 boundaries (public domain,
  1:50m GeoJSON) → shapely simplify to a ~48–64 vertex budget → `Point.from_latlng` →
  terrain XY (the calibrated `tools/supply_route_geo.py` machinery) → emitted as a plain
  vertex list in the campaign yaml. New sibling tool `tools/neutral_border_geo.py`; the
  GeoJSON is a dev-time input the tool reads, never vendored, never touched at runtime.
  The author may clip to the war-facing slice of the border (tool flag). Not ME drawings
  (the loader does not read them); not quad trigger zones (4 vertices is not a border).
- **The border is drawn, not invisible** (the §86 lesson): the plugin renders the
  simplified polyline as F10 markup, default on, plus one kneeboard line naming the
  neutral country and the altitude floor. On maps whose baked F10 art draws real national
  borders, the real-data polygon aligns with lines the player already sees.
- **The neutral field needs no control point**: the alert flight air-spawns overhead a map
  airbase found by name (`AIRBASE:FindByName`), so the campaign yaml names any airfield on
  the map — including fields outside the campaign's CP set.
- **Lua** (`resources/plugins/neutralborder/`): timer scan of red+blue airborne units
  against the polygon + floor (point-in-polygon; `bigeye_ewr.lua` has prior art), dwell
  bookkeeping per group, spawn via `SPAWN:NewWithAlias` on the intruder-opposing template,
  follow/shadow tasking, escalation state machine, SAM ROE flip, radio warnings to the
  intruder. pcall-guarded throughout; definition order per Lua 5.1.
- **Two gates as always**: settings toggle + plugin toggle; campaigns must preseed both
  (§36 lesson).

## Settled during the build

- **Shadow spawn is air-start overhead the field** (§61/QRA default). A ground spawn can
  stall or fail on a congested ramp, and a ~0 kt air clone spawns stalled — hence
  `InitSpeedKnots(300)` at field elevation + 760 m.
- **One template set per zone**, cloned per incident with `InitCountry`/`InitCoalition` —
  not two authored sets.
- **Warnings are `outTextForGroup` to the intruder**, not a broadcast sound file. Only
  players see them (an AI stray is shadowed silently).
- **Liveries are left to the template's country default.** A per-campaign livery pin is
  possible later; nothing about the mechanism depends on it.

## The point-spawn extension (2026-08-24, same session)

**Found while scoping Afghanistan: the DCS Afghanistan map's 26 airfields are all
inside Afghanistan** — checked every one against the real country outline, 26 in, 0
out. Pakistan, Iran, Turkmenistan, Uzbekistan and Tajikistan have nothing to scramble
from, so the airfield-only v1 could not do the map the feature most wants.

A zone now declares **either** `airfield:` **or** `spawn: [x, y]` + `spawn_alt_ft:`
(exactly one; both or neither skips the zone). A point zone air-spawns a standing CAP
over its own territory via MOOSE `SpawnFromVec3`, which is what a nervous neighbour
actually keeps up anyway. Stand-down routes back to the station instead of a field.

**The corridor.** `tools/neutral_border_geo.py --corridor-lon MIN MAX` subtracts a
north-south lane before simplifying, so one country emits as the two walls of a flight
corridor. Afghanistan uses it for the OEF boulevard (see features doc §96). `--clip` is
effectively mandatory — Iran's real outline runs to the Persian Gulf and would spend
the whole vertex budget on coastline off the map.

**DCS has no Turkmenistan, Uzbekistan or Tajikistan.** Not pydcs countries; 92 exist
and those three are not among them. The northern border is undefended rather than
flown under a substitute flag. Do not "fix" this with Kazakhstan or Russia — it would
put a wrong nation's markings and tooltip over real territory.

## The alignment rework (2026-08-25, DM calls)

The feature's model grew from one axis to two, in the same session that added the
planning-map layer:

- **Every bordering nation is drawn**, not only the dangerous ones (DM call). A map
  that shows only the keep-outs reads as "the rest is unmodelled".
- **Alignment is derived, never authored**: a nation hosting a RED or BLUE airfield
  is aligned with that team; one hosting neither is the neutral (DM rule, verbatim).
  Computed by point-in-polygon over the control points inside each border
  (`NeutralBorderZone.posture_in`); off-map spawns excluded; contested resolves to
  the larger holder. `posture:` in the yaml overrides. **This caught our own defect
  the day it landed**: the Hornet's Nest preseed had shipped Lebanon as the neutral
  while Beirut hosts four red squadrons — under the rule it derives red-aligned with
  no hand-edit, and flips if Beirut ever falls.
- **Overflight is a separate authored fact from alignment** (DM call: "Neutral with
  overflight and Neutral without overflight"). Turkmenistan permitted coalition
  transit in 2006 and Iran did not; both were neutral. Only a neutral that refuses
  transit is enforced by §96. A permitting neutral spawns nothing — which is what
  finally let Turkmenistan/Uzbekistan/Tajikistan be drawn (no pydcs country needed).
- **A red-aligned nation is defended by the QRA it already has**: its polygon joins
  §1's accept zones (`aligned_defense_polygons` → `ZONE_POLYGON` → `SetBorderZone`),
  never a second §96 flight over the same ground (DM call: "tied in with the
  existing interceptor work").
- **Three colour families** (DM call): red for red-aligned, blue for blue-aligned,
  APP-6 green for the neutral; shading carries enforcement. Open airspace is drawn
  with a real (6%) fill after the bare outline proved invisible over satellite
  imagery — the §40 layer's own recorded lesson, relearned.

## Cross-map validation of the derivation (2026-08-25)

Run against two campaigns the rule had never seen, with **zero authoring** — the
derivation was fed each campaign's real base ownership and asked what it produced.

**Caucasus / Iron Gate (2018) — clean pass.** Georgia → blue (4 blue fields),
Russia → red (4 red fields), Turkey / Armenia / Azerbaijan → neutral (0,0). Exactly
right, nothing stated.

**Syria / Hornet's Nest — clean pass.** Lebanon → red (Beirut), Israel → blue
(Ramat David + Haifa), Turkey / Cyprus / Jordan / Iraq → neutral.

**Germany CW / Red Tide (1988) — the rule cannot work here, and it is a DATA gap,
not a logic one.** Modern Germany is one polygon; in 1988 it was two states, and
**6 of Red Tide's 12 bases sit in what was the GDR**. Fed modern borders the zone
derives `red` off a 5-blue/6-red split — a meaningless coin-toss. Denmark derives
blue correctly (1 blue field).

The fix is historical boundaries, not a code change: **a Cold-War Germany campaign
needs a 1949–1990 inner-German border** (and period Czechoslovakia, which also no
longer exists — its modern GeoJSON 404s under that name). Until that data exists,
**do not author §96 zones on `GermanyCW`**; the derivation will silently pick a
side. Recorded for the postures research, which faces the same problem for every
pre-1991 era: the USSR, Yugoslavia, Czechoslovakia and the two Germanys all need
period geometry, and the posture table's dated ranges are worthless without it.

### The `features[0]` defect (found and fixed the same day)

`tools/neutral_border_geo.py` read `data["features"][0]["geometry"]` — but these
GeoJSON files split a country into **one feature per landmass**: Denmark is 64
features, Russia 320, Germany 39. Denmark's first feature does not contain
Copenhagen, so its "border" was **0.8 % of the country**. Fixed by merging every
feature (`country_polygon` → `unary_union`).

**All eleven already-shipped borders were re-measured against the fix and are
unaffected** (<0.5 % delta inside each map's clip) — the mainland happened to be
`features[0]` every time. The bug was latent, never live. It is recorded because
the next country added could easily have been the one that broke, and a fragment
border is close to invisible on a map you have not seen drawn correctly.

## The postures table, wired (2026-08-25)

`overflight` is no longer a campaign's to state. `game/theater/nationalpostures.py`
reads the 47-country dated table against the campaign's date and each side's bloc;
the yaml key survives as an override. Three rules live in that module, none of them
in the data:

- **Which bloc a coalition is.** From its faction's own country in the table — the
  bloc it is most favourably disposed toward. USA resolves us-led, Russia ru-led; a
  faction whose country the table does not know (CJTF, Insurgents, "Bluefor Modern")
  falls back to blue=us-led / red=ru-led, which is every campaign we ship.
- **An uncovered date is `closed`.** The safe default for a border is that it
  defends.
- **`allied`/`permissive` permit transit; `contested`/`closed`/`hostile` do not.**
  Five buckets are kept in the data because the split will matter later; overflight
  is binary today.

**Consent is per side.** A country may wave one bloc through and intercept the
other, so the zone carries two flags and the Lua checks each intruder against its
own. This is not a corner case: in 2022 Turkey, Jordan and Iraq all permit US
transit and refuse Russian, so on Hornet's Nest they intercept red only.

### What wiring it immediately corrected

The table disagreed with the postures hand-authored the day before, and was right
twice:

- **Uzbekistan** — hand-authored permissive; the table reads `contested` from the
  Nov-2005 K2 expulsion. It should refuse and cannot, because DCS models no
  Uzbekistan to fly an interceptor. Kept permissive by an override that says so.
- **Turkey / Jordan / Iraq** on Hornet's Nest — hand-authored as permitting
  everyone. They are closed toward the Russian bloc, so they now intercept red.
  Given real defenders (Incirlik, King Hussein, H3).
- **Pakistan** on Enduring Resolve — the table reads `permissive` toward the US in
  2006 and that is correct history: the corridors were the consent. But the
  corridor is the lane the polygon leaves out, so the campaign overrides to refuse.
  **This is the case the override exists for** — geometry expressing a
  consent-with-conditions the country-level table cannot.

### A zone that cannot defend is drawn, never dropped

If a zone should enforce but the campaign gives it no aircraft or origin, the
generator emits it as drawn-only with an `info` line, rather than skipping it.
Every bordering nation is meant to appear (DM call), and the countries that cannot
field an interceptor — the ones DCS does not model — are exactly the case that rule
exists for. Dropping them would have silently deleted Turkmenistan's border the
moment the table said it refuses Russian transit.

## Automagic, built (2026-08-25)

**Found by a save, not by a test.** The DM turned both gates on, loaded
`test.retribution`, and saw nothing. The campaign was *Clash of the Titans*, and
the diagnosis was one number: **52 of the 54 campaigns on real-world maps author
no `neutral_border_defense:` block at all.** Only Enduring Resolve and Hornet's
Nest had borders, because those are the two this session hand-authored. The
feature worked and reached almost nobody.

Borders are a property of the **terrain**, not of a campaign — identical for
every campaign on the same map — so they are now shipped per terrain in
`resources/borders/<terrain>.yaml`, generated by `tools/build_terrain_borders.py`.
Eight terrains ship today: Afghanistan, Syria, Caucasus, Iraq, Kola, Persian Gulf,
Sinai and the Falklands. The rest are done or blocked, not pending: **Nevada and
both Marianas are all-US** and have no foreign border to draw (an absent file is
the correct answer, not a gap), Normandy and The Channel are WWII maps whose eras
predate the posture table's 1955 start, and **Germany Cold War stays blocked** on
the pre-1991 inner-German border.

- **Geometry and an origin only.** Posture *and airframe* resolve from the dated
  table at generation time (the table's `aircraft` column covers 39 countries),
  so one border file is correct in 1975 and 2025. A test pins that no terrain
  file may name an airframe or a posture.
- **Origin picks itself**: a real map airfield inside the polygon where one
  exists — the one furthest from the frontier, so nothing launches from a strip
  metres inside its own border — otherwise an air-spawn station at the polygon's
  representative point. **The origin names the flight; it does not have to be
  where the flight comes up** — see the stand-off below.
- **Every country on the map is drawn, the map's own included** (2026-08-26).
  The host was excluded until then, on the theory that a border round the
  battlefield is noise. Measured, that theory deleted **Russia from Kola, Iran
  from the Persian Gulf, Georgia from the Caucasus, Egypt from Sinai, Iraq from
  Iraq and Syria from Syria** — the most relevant border on each of those maps —
  and left the war itself as the one region on the map with no line on it. On
  Inherent Resolve the result was that Iran, not in the war, was the single
  largest shaded region while Iraq, the entire war, was blank. The treatment a
  country gets is decided at run time from who holds the control points inside
  it, so the geometry has no business leaving one out.
  - **Syria was also missing from the Iraq map** — never excluded, just never
    named in the tool's `--countries` list, which is how a border is lost
    silently. Iraq's own absence hid it: the country next to the hole is hard to
    notice when the hole is not there either.
- **Precedence is total, never merged.** A campaign that declares its own block
  owns its borders completely and the terrain file is not consulted. Merging
  would make it impossible to say where a zone came from — and Enduring Resolve
  depends on this, because its corridor-cut Pakistan must beat the terrain file's
  whole-country one.
- **Existing saves pick them up, and keep picking them up.**
  `ConflictTheater.__setstate__` fills empty border zones from the terrain file,
  so a campaign already in progress gets borders without a re-roll. Verified
  against the DM's own save: 0 zones before, 7 after, no campaign edit.
  A terrain list is also **refreshed** on load rather than frozen — it is a cache
  of a shipped file, and the 2026-08-26 host-nation fix is exactly why: a save
  that froze its list would never see Iraq or Syria. `from_terrain` on the zone
  is what makes that safe; a campaign's own zones are campaign state and are
  never touched.
  - **A save older than the flag is left alone**, because it cannot say where
    its zones came from and the two campaigns that author their own are the two
    most often under test. Refreshing them blind would hand Enduring Resolve the
    whole-country Pakistan its carrier corridor exists to avoid. Roll a new
    campaign to get the current set.

Country lists come from the **measured** per-terrain table in
`414th-national-postures-notes.md`, not from the eyeball — that table is why
India is on the Afghanistan map (1.03 % of its land, 12× China's footprint) and
why Saudi Arabia is on the Syria map (7.15 %, more than Israel, Lebanon and
Cyprus combined).

### Two terrains that needed a rule of their own

- **Sinai** shows the era-resolution better than any map, because its five
  campaigns span 1973–2025 off one border file: Operation Gazelle draws Israeli
  F-4Es and Syrian MiG-21s, the 2025 exercises F-16C Block 50s and MiG-29As, and
  1973 Lebanon correctly gets no airframe at all and is drawn toothless.
- **The Falklands needed an area floor.** Every surviving landmass becomes a zone
  with its own alert flight, and Tierra del Fuego is an archipelago: unfiltered,
  Chile came out as **five** zones, one of them the 1,439 km² Cape Horn group.
  Real territory, uncontested airspace. `--min-area-km2 5000` leaves six zones
  across both countries. **Argentina has no airframe in the posture table** and
  DCS ships no Argentine fighter, so an Argentine zone can only ever be drawn —
  the same honest dead end as Turkmenistan, on the one map where Argentina is
  the point.

### Two tool defects this shook out

- **Invalid published rings.** Saudi Arabia self-intersects on the Kuwaiti
  border and `unary_union` raises a `TopologyException` outright. `buffer(0)`
  repair, which leaves a valid ring untouched. Four terrain files failed to
  generate before this.
- The `features[0]` fragment bug is recorded above; it was found the same way.

## What the first flown test found (2026-08-25, Inherent Resolve, Iraq map)

The first mission with §96 live produced one clean pass and three defects, two of
them measured off the Tacview rather than reported. **All three are fixed; none
is verified in DCS yet** (B110/B111 still owed).

**It worked at all.** `6 border zone(s) drawn, 6 defended`, and against a blue
F-15E BAI package Iran launched a shadow on the opposing coalition and stood it
down when the package left. The clone mechanism, the scan, the dwell timers and
the stand-down all did what they were built to do.

### The alert flight could not reach the intruder — the one that mattered

The Tacview says the pair came up **224 NM behind** the F-15Es, closed to
**127 NM** over twelve minutes, then diverged. A MiG-29A has roughly 80 kt on a
cruising Strike Eagle; a stern chase from that range never converges.

The cause is the origin. Iran's is the **representative point of its clipped
polygon** — the geometric middle of the country — and the shadow spawned there.
That is fine for Kuwait and hopeless for Iran, Russia or Saudi Arabia, so *every*
launch on a large country was that launch. Nothing in the harness could catch it:
its fixture is a 20 km square, where the middle is always in reach.

The fix is a **stand-off**: within 25 NM of the intruder the origin is used as it
stands (a small country still scrambles off its own runway), and beyond that the
flight comes up 25 NM from the intruder on the line toward the origin, which is
inside the border for any intruder that is. 25 NM is ~3 minutes at the shadow's
speed, which is the engage dwell — so the shadow is present when the timer it
exists to enforce expires. The origin keeps its name in the radio call and the
log either way. A concave border can put that line briefly outside the country;
that case falls back to the origin, because launching a *national* alert flight
over the neighbour is worse than a slow response.

### DCS will not fill a concave freeform

Reported from the F10 map: the borders drew as bare lines with no shading, on a
map where the planner shades them. `trigger.action.markupToAll` with shape 7 took
the fill colour and ignored it.

**MOOSE had already hit this and worked around it**, which is the corroboration
that made it a five-minute diagnosis instead of a flight: `ZONE_POLYGON_BASE:ReFill`
triangulates the ring and fills triangle by triangle, and the single-freeform path
right below it is dead-coded behind `if false then`. A national border is about as
concave as a shape gets. The plugin now hands the ring to MOOSE for the fill and
keeps its own one-freeform outline on top, which DCS does honour and which carries
the dash pattern the triangles cannot. The outline also stopped repeating vertex
one — DCS closes a freeform itself, and the duplicate was a zero-length edge.

`markupToAll` and a `ZONE_POLYGON` facade are now stubbed in the Lua harness. They
were not before, which is why `drawBorders: false` in every fixture had hidden the
whole draw path from the one test suite that could have exercised it.

### A GeoJSON feature that is not land

Adding Russia to Kola surfaced it: `russia.json` carries a feature spanning
**359.8° of longitude in a 0.87° latitude band**. Merged in, it became a 75,554 km²
Russian claim across northern Norway — on a map where Norway is a real zone of its
own. Russia's *real* mainland feature spans the globe too (Chukotka crosses the
antimeridian) but is 36.6° tall, so the guard is on the **aspect ratio**, not the
width. Only Russia carries one; every other country file scanned clean.

This is the same class as the `features[0]` defect above, and the same lesson: the
source data is not a country, it is a pile of features, and some of them are not
land.

## What Kola found (2026-08-26, Able Archer 83)

Drawing the host nation put the derivation on a map where the war is fought
*inside* the drawn countries, and it broke in two ways at once. Both are fixed;
neither is verified in DCS.

### Alignment was derived per polygon piece, not per country

Russia is two zones on Kola — Karelia and the Pechenga strip — because the clip
splits it. The only Russian control point (Koshka Yavr) is in Pechenga, so
Karelia counted zero and read `neutral`. **The Soviet Union's own territory,
116,420 km² and the largest zone on the map, drew as an uninvolved third party
that would intercept you, in an Able Archer campaign.** Its neighbour piece drew
enemy-red. Counting is now over every zone of the same country name.

### A country both sides hold is contested, not the majority holder's

| Country | Holds | Was | Now |
|---|---|---|---|
| Norway | Bodo (blue), Banak + Kirkenes (red) | **red** | contested |
| Finland | Rovaniemi (blue), 3 red | **red** | contested |
| Sweden | 3 blue | blue | blue |
| Russia | 1 red | neutral + red | red |

Norway is the NATO host. Drawing it in enemy red because the Soviets hold two of
its three fields reports the **front line** as though it were **allegiance**.

`contested` (DM call) is a fourth alignment: neutral grey outline over the same
faint belligerent wash, never enforcing, and claimed by **neither** side's QRA
accept zones — handing a contested country's sky to whoever holds one more
airfield would scramble a QRA over ground its enemy also holds.

**The postures table does not solve this** and was checked before the call: on
1983-11-09 it reads Norway `allied`, Finland `closed`, Sweden `closed`, Russia
`closed` — historically right, but it would draw Sweden and Finland as enforcing
neutrals while both sides fly combat sorties from their runways. The two signals
answer different questions: the table says *whose side a country is on*, the
control points say *whose ground it is now*. §96 needs the second, and
`contested` is what the second says when both answers are true.

### The vertex budget was too low for a real coastline

Measured by symmetric difference against the true clipped country:

| Country | 24 vertices | 64 |
|---|---|---|
| **Norway** | **30.2 %** | 14.7 % |
| Sweden | 9.7 % | 1.3 % |
| Finland | 7.0 % | 2.7 % |
| Pakistan | 6.3 % | 2.6 % |

Norway is the worst case Douglas-Peucker meets here — a thin fjord coast
wrapping around Sweden — and at 24 nearly a third of it was wrong. The budget is
**64**; 96 buys another point or two for double the cost. Fjords are not fully
resolvable at any sane budget, so Norway stays the outlier.

**The cost is F10 markup count.** The fill is drawn triangle by triangle, so a
64-vertex ring is 62 shapes: **446 on Afghanistan**, the busiest map, against
~176 before. They are static and drawn once, with no per-frame work, but this is
the number to watch if the F10 map feels heavy — `drawBorders` turns the whole
draw off without touching the interception.

## Consent moved to the airbases (2026-08-26, DM call)

> "Keep the research, drop what we did with it. Overflight should be derived by
> airbases in the borders."

The dated posture table answered *may this side transit* from the day it was
wired. It no longer does. Consent is now derived from the same fact as
alignment — the airbases inside the border:

| Inside the border | Blue may cross | Red may cross | Defends |
|---|---|---|---|
| Blue's bases only | yes | no | no — blue's QRA covers it |
| Red's bases only | no | yes | no — red's QRA covers it |
| Both sides' bases | yes | yes | no — it plainly already let them both in |
| Neither | no | no | **yes** |

A campaign's `overflight:` still wins outright, which is what keeps Enduring
Resolve's corridor-cut Pakistan correct.

### Why the table lost the job

It made consent a fact about the **calendar** rather than about the campaign in
front of you.

- It reads Sweden and Finland `closed` in 1983 — historically right — while on
  Kola both sides fly combat sorties off their runways.
- It cannot see a base change hands. Take an airfield and the country's posture
  toward you does not move; the airbase rule flips it that turn.
- Turkey was the case that surfaced it: in the Aleppo Insurgency campaign it
  holds Gaziantep, Hatay and **Incirlik** for blue. Table and airbases happened
  to agree there, which is exactly why it was worth checking what happens when
  they do not.

### What was kept, and what was deleted

**Kept:** `resources/borders/national_postures.yaml` — all 47 countries and 244
ranges, untouched — plus `load_postures` and `posture_for` that read it, and
`aircraft_for`, which is the one answer nothing else can give: a country holding
no control points has no faction to borrow a jet from, so without it a border
cannot scramble anything.

**Deleted:** `permits_overflight`, `bloc_for_country`, `bloc_for_faction`. All
three existed only to answer consent, and the fork does not keep code for a
question nothing asks.

### Two consequences to know

**Altitude floors are gone.** They were derived from the table's `contested`
bucket, so a floor is authored-only now and a defending country defends at any
height. `DEFAULT_CONTESTED_FLOOR_FT` is deleted.

**More countries defend.** Measured on the Aleppo Insurgency save: Turkey reads
friendly (blue's three bases) and Syria contested, but **Lebanon, Israel, Jordan,
Iraq, Cyprus and Saudi Arabia all defend**, where the table had Israel, Jordan
and Saudi Arabia as `allied` transit corridors. That is the rule working as
stated — nobody is based in them, so nobody has been invited — and it is a large
change to how much of a map is closed. The rule a pilot can hold is one
sentence: *if we do not fly from it, do not fly over it.*

**Consent no longer depends on the date at all.** The same map on the same turn
reads identically in 1975 and 2025. Era-correctness was the research's selling
point and is now unused by this feature, deliberately.

## Shared frontiers: one line, not two (2026-08-26)

Each country was clipped and simplified **on its own**, so every frontier two
countries share came out as two independently-simplified traces of the same
border, weaving across each other with slivers between them. Measured: the two
lines coincided **35-65 %** of the time, and Russia/Norway on Kola at **7 %**,
with overlaps up to 12.8 % of the smaller country.

The whole map is now simplified as **one polygon coverage**:

1. `set_precision` snaps every clipped outline to a 100 m grid. Two source files
   trace the same frontier a few metres apart, and noding that raw leaves a
   chain of hairline slivers — each becoming its own face, and
   `coverage_simplify` floors every face at a triangle. Armenia came out of the
   Caucasus build as ~32 faces with a 97-vertex floor it could never get under.
2. The boundaries are unioned (which nodes them) and `polygonize`d into faces
   that tile the arrangement exactly. Each face goes to the **first** country
   that contains it, so an overlap is awarded once instead of twice.
3. `shapely.coverage_simplify` (2.1+) simplifies that coverage — shared edges
   once, handed to both sides identically.

### Result

| | Before | After |
|---|---|---|
| Overlap between neighbours | up to 12.8 % | **0 on every map** |
| Shared frontier | two traces | **one line** — 7 of 8 maps are a valid coverage |
| Norway's shape error (Kola) | 14.7 % | **7 %** |
| Vertices, Afghanistan | 454 | **255** |
| F10 markup shapes, Afghanistan | 446 | **247** |

Better on every axis at once, because Visvalingam on a coverage spends vertices
where the shape needs them instead of giving every country the same budget.

**Falklands is the one map that is not exactly valid**, and the test asserts it
as a known exception: Argentina and Chile interlock across Tierra del Fuego, and
writing the rings as whole metres leaves a **12.5 m²** degenerate touch. Twelve
square metres is far below anything drawable.

### Three things that bit, worth not repeating

- **Never truncate a MultiPolygon to its largest part.** Dropping a component
  leaves the neighbour that shared its edge matched against nothing — that alone
  made Falklands invalid, and it silently deletes islands.
- **The vertex budget is a target, not a guarantee.** A landlocked country whose
  every edge is shared has a floor: Armenia settles at ~98 however hard it is
  pushed. The search stops at the plateau rather than refusing to build a map.
- **A small country legitimately becomes a quad.** Bahrain is 571 km², and
  coverage simplification reduces a small polygon to a triangle in the limit, so
  the clip-artifact test can no longer read "few vertices" as "fake shape".

## Into the Hornet's Nest stopped authoring its own borders (2026-08-26)

It preseeded one zone, Lebanon. **Precedence is total, so authoring one zone
costs a campaign the other seven** — it was getting Lebanon alone where the Syria
terrain file gives Syria, Turkey, Lebanon, Israel, Jordan, Iraq, Cyprus and Saudi
Arabia. Lebanon derives red-aligned there anyway (Beirut's four red squadrons),
so the block enforced nothing and was purely a subtraction.

The block is deleted; both gates stay preseeded. **Enduring Resolve keeps
its own**, because its corridor-cut Pakistan is the thing total precedence exists
to protect.

The lesson generalises: **now that borders ship per terrain, a campaign should
author a block only when it needs geometry the terrain file cannot give.** For
anything else, authoring is a way to opt out of seven countries by accident.

## The F10 map names each border (2026-08-26)

A drawn polygon with nothing written on it is a shape the pilot has to guess at.
Each zone now carries a two-line label, in the same hue as its own border:

```
IRAN
CLOSED - alert from Bandar Abbas
```

Captions are `friendly` / `enemy-held` / `contested` / `transit permitted` /
`CLOSED - alert from <field>`. A spawn-point zone's origin is
"<country> border CAP", and the country's name is already the line above, so the
prefix is stripped — otherwise Saudi Arabia read "SAUDI ARABIA / alert from
Saudi Arabia border CAP".

**Drawn in the border's own colour, deliberately.** §45's support orbits own the
cyan; matching each label to its border makes the label and the line read as one
object and keeps the two systems apart.

**Placed at the polygon's representative point**, not its centroid — a country
is usually concave (Norway spectacularly), and a centroid lands in the sea or in
the neighbour. Computed Python-side with shapely, which guarantees it is inside,
and shipped as `labelX`/`labelZ`; verified on all 8 zones of a Syria campaign.

`drawBorders` still switches the whole draw off, labels included.

**Not verified in DCS**: whether `trigger.action.textToAll` renders the `\n` as
two lines. If it does not, the label will read as one run-on line — cosmetic,
and on the B110 fail-signature list.

## A faint line is not a quiet line (2026-08-26)

Reported: "friendly still showing red", on a Syria map where a blue-aligned
country appeared to carry its enforcing neighbour's crimson border.

**Not reproduced from the save**, and the colour chain is not capable of it: a
`blue` posture takes `airspaceBlue` before `enforced` is ever consulted, and the
shipped bundle compiles to exactly that. What the layer *was* doing is drawing a
belligerent as an **uncased 2 px line** — the only family on the map without the
dark halo `CasedShapes` exists to provide. Over satellite imagery, on a map
already full of `#0084ff` flight paths, a thin blue border is not a subtle line;
it is an absent one, and the eye takes the nearest thing that IS legible, which
is the neighbour's crimson dash.

Two things make that easy to fall into:

- The overdraw is real but small: at a shared frontier both countries draw the
  same line and the later one wins. **Measured on Israel: 97 km of its 876 km
  border (11 %) is painted over by Jordan**, drawn after it. Enough to mislead
  at a glance, not enough to recolour a country.
- The 6 % belligerent wash was chosen to stop half the Syria map reading pink.
  It does that, and it also removed the last thing making the border findable.

All three airspace strokes are cased now (7 / 6 / 5 px) and the layer draws
through `CasedPolygon` like the rest of the family. The belligerent weight goes
2 → 2.5.

**If a friendly country still reads crimson after this, it is a real defect and
the save is needed in the state it shows it** — the one on disk has Israel as a
genuine enforcing neutral with no bases inside it, which is a different campaign
state from the screenshot.

## The remaining automagic gap (DECIDED, NOT BUILT)

**"I do not wish this to be specified in any existing campaign, I want this to
automagically work with existing campaigns, but if we or Starfire wish to establish
it via the yaml we can."**

Target architecture, to be built after the national-postures research lands:

- **Borders become terrain data, not campaign data**: shipped per-terrain border
  files (generated once by `tools/neutral_border_geo.py` for every real-world map),
  so a campaign needs no `border:` vertices at all.
- **Overflight becomes date-resolved**: `resources/borders/national_postures.yaml`
  (five buckets, both blocs, dated ranges — see
  `414th-national-postures-notes.md`)
  is read against the campaign's start date and each side's bloc; `allied`/
  `permissive` collapse to overflight-allowed, `contested`/`closed`/`hostile` to
  refused. **The data landed 2026-08-25** — 48 countries, 246 ranges, unwired;
  the four gaps between it and this feature are listed in that note. The data supports per-side asymmetry (a nation open to blue and closed
  to red), which the Lua does not model yet — the zone gains per-side overflight
  when this is built.
- **Alert origin and aircraft become automatic** for a defending neutral: an
  airfield inside the polygon if the terrain has one, else the representative-point
  spawn; the airframe from the postures table's optional `aircraft` column, else a
  documented fallback.
- **The campaign yaml survives as pure override** — same schema, highest
  precedence. The derived airfield-alignment rule is untouched by all of this and
  always wins over the table.
- Gate unchanged (`neutral_border_defense` + plugin): "automagic" means no yaml
  needed, not default-on. Flipping the default is its own call after B110/B111 fly.

## Audit, 2026-08-27 — two defects the gates could not see

A full pass over the PR against `upstream/dev`. The mechanics were clean (black,
mypy, 4450 tests, and the 11 upstream-owned files touched additively, nothing
deleted). Both findings were behavioural, and neither is the kind CI catches.

### The planning map promised an interception the mission could not deliver

`NeutralBorderGenerator` degrades a neutral that cannot field an interceptor to
**drawn and toothless** — no airframe for the era, or no airfield/spawn. The web
map computed `enforced` from posture and consent alone and never asked that
question, so the two disagreed on **14 zones across 6 of the 8 shipped terrains**:

| Terrain | Drawn closed, actually toothless |
|---|---|
| Afghanistan | Afghanistan, Turkmenistan, Uzbekistan, Tajikistan ×2 |
| Caucasus | Armenia, Azerbaijan ×2 |
| Syria | Iraq, Cyprus |
| Iraq | Iraq |
| Kola | Sweden |
| Falklands | Argentina ×2 |

Cyprus was drawn "Closed to you at any altitude" over a mission that let you fly
straight through it. **The whole feature is a planning decision** — go around, or
go through — so a map that overstates the threat is worse than one that draws no
line: the player routes around nothing, and learns to distrust the layer.

Fixed by asking it once: `NeutralBorderZone.can_field_an_interceptor(day)`, used
by the generator and by `NeutralBorderJs.all_in_game`. Same shape as
`visibility_for` — one question, one place.

### A per-side floor read the other side's number

`neutralborder-config.lua` resolved the altitude floor with the Lua ternary
idiom, at two sites:

```lua
local floor = is_blue and zone.floor_blue_m or zone.floor_red_m
```

`cond and a or b` is not a ternary when `a` can be falsy, and **`nil` is the
normal case here** — no floor means no sanctuary. With blue's floor unset and
red's authored, blue was judged against *red's* number: a blue player crossed a
closed border above red's floor and was never warned, never shadowed, never
engaged. The `warn` site had it too, so the radio call would have offered blue a
safe altitude taken from red's — under a comment saying it must not.

**Masked, not live**: `floor_for` currently ignores `is_blue` and returns the
authored value, so both sides read the same number today. But the field is
per-side end to end (`floorBlueFt`/`floorRedFt` emitted and parsed separately)
and `floor_for` takes `is_blue`, so the first per-side floor would have shipped
a silent hole in the enforcement path.

Both sites are long-hand `if` now. Two harness tests pin it, and **both were
confirmed to fail against the old idiom** — every pre-existing floor test set
the two sides to the same value, which is exactly why it survived review.

### The alert flight was based on a helipad

Reported from the map 2026-08-27: Lebanon's card read **"alert from HL07"**.
`airfield_in` picked the airport furthest inside the polygon, and pydcs's
`airport_list()` includes helipads, so a helipad that happened to sit deepest
won. Four Syria-map zones were on one:

| Country | Was | Now |
|---|---|---|
| Lebanon | HL07 | **Rayak** |
| Syria | HS03 | **Palmyra** |
| Jordan | HMed22 | **Marka** |
| Iraq | HS26 | **H3 Northwest** |

The flight air-spawns overhead its origin, so it flew regardless — this was a
card that read as a bug rather than a broken intercept. `airfield_in` now skips
anything with no runway. Regenerating Syria changed **exactly those four lines**;
the geometry is byte-identical, which is the check worth repeating after any
tool change. The other seven terrain files are unchanged and were not
regenerated: the rule only excludes helipads, and a sweep confirmed these four
were the only helipad origins on any shipped map.

`test_no_zone_launches_its_alert_flight_from_a_helipad` pins it across all eight
terrains, and was confirmed to fail against the old file.

### Air-spawn stations were standing off the map

A clip box is bigger than the terrain it clips, so a country that only catches
the map's edge gets a polygon whose *middle* is off the map. The station was
`representative_point()` of that polygon, with no check that the map models
anything there. Measured against each terrain's landmap:

| Terrain | Country | Was, from modelled land | Airframe |
|---|---|---|---|
| Afghanistan | India | 272 km | Su-30 |
| Caucasus | Turkey | 171 km | F-16C / F-4E |
| Iraq | Jordan | 37 km | F-16A MLU |
| Iraq | Turkey | 26 km | F-16C |

All four scramble something, so all four would have tried to launch from there.
`spawn_station` now intersects the border with the landmap's inclusion zones and
takes the representative point of the largest piece; every station that can
field an interceptor is on modelled land.

**Calibrate before calling a point off-map.** The landmap's coastline is
approximate: Novorossiysk and Anapa are real Caucasus airfields and read 0.2 km
and 1.1 km *outside* the inclusion zones. A first pass flagged Falklands/Chile
at 1.3 km as off-map; it was a coastal artifact, not a defect. Distance to the
nearest land polygon is the discriminator, and the off-map signature is
"in neither inclusion nor sea zones, and tens of km from land" -- the same
reading a point in the Caspian gives.

Caucasus/Azerbaijan's Nakhchivan piece stays off-map and is **correct as it
stands**: the map models no land inside it to move to, and Azerbaijan has no
airframe in any era, so it never launches. The tool says so on stderr rather
than silently leaving a bad station.

**Regeneration gotcha:** zone order follows the `--countries` order, so passing
a different order rewrites the whole file for no semantic change. Take the order
from the existing file's own zones, then the diff is the `spawn:` lines alone --
which is also the check that the geometry did not move.

### The posture was derived twice per zone on every map poll

Not a defect, but measured and worth taking: `permits()` called `posture_in()`
internally, and both natural callers ask for the posture and the consent
together. So `/game` derived it twice per zone and the mission generator three
times (blue and red consent), and deriving it is not cheap -- it walks every
zone on the map to find same-country pieces, then builds a shapely polygon and
tests every control point against it.

`permits()` now takes an optional precomputed `posture`. Measured on the
payload build, before → after:

| Terrain | Before | After |
|---|---|---|
| Falklands | 86.6 ms | 42.9 ms |
| Afghanistan | 43.8 ms | 21.4 ms |
| Persian Gulf | 39.1 ms | 13.9 ms |
| Iraq | 34.0 ms | 20.2 ms |
| Kola | 31.0 ms | 15.9 ms |
| Sinai | 25.5 ms | 12.8 ms |
| Syria | 24.5 ms | 17.5 ms |
| Caucasus | 23.9 ms | 12.1 ms |

**A parameter, deliberately not a cached field.** The whole value of deriving
posture is that a country flips the turn its airfield changes hands; a stored
one would go stale exactly then, which is the bug the derivation exists to
avoid. Two tests pin that passing the posture gives the same answer as deriving
it, across all four postures and both sides.

### The checklist rows collided with main's -- three times

This PR added its in-game rows as **B100/B101**, and `main` already owned both
(the DCS parking rework, and the F-4E Shrike row). Renumbering to **B106/B107**
collided again -- main had meanwhile taken B106 for the CSAR King row. The third
merge, on 2026-08-29, brought main's log-noise work, which had taken **B107,
B108 and B109**. The §96 rows are **B110/B111** now.

Three collisions on one branch is the pattern, not bad luck: a long-lived branch
allocates from the highest id it can see, and main keeps allocating from the same
end while the branch is open. There is no reservation mechanism, so the only
defence is re-checking on every merge.

The consequence is worse than an ambiguous label. `_row_statuses()` in
`tests/test_flycard_board.py` keys by row id, so a duplicate silently overwrites
its twin and the board **under-reports outstanding work**: the first collision
hid the §96 rows (78 stated, 80 real), and the second hid main's own CSAR row
(80 stated, 81 real). The count test is what catches it, and only when run from
the worktree -- `CHECKLIST` is a CWD-relative path, so running pytest from the
main checkout silently validates the wrong tree.

**Re-check the highest id in use after every merge from main**, not just when the
row is first written:

```
grep -oP "^### [A-Z]+[0-9]+(?= )" docs/dev/414th-ingame-pass-checklist.md | sort | uniq -d
```

Renumber your own rows, never main's. The renumber reaches five places, and
`resources/whatsnew.yaml` is the one that gets forgotten -- 16 entries carried
`row: B107` on the third pass. Also: the checklist's glance table and detail
sections, the features doc, this note, and the Lua runtime test's docstring.

### Also corrected

The late direction changes — terrain-shipped borders, and consent derived from
airfields — reached the code and the design notes but not the inline docs. Nine
places still said the feature needs a campaign to author zones (including the
Settings description and the plugin-options text the host reads), the module
docstring still said "three postures" and described overflight as authored, and
`IntotheHornetsNest.yaml` pointed at a block deleted earlier in the branch. This
is the failure mode CLAUDE.md's step 7 exists for: the feature's own faces were
updated, the notes that merely mention it were not.

## Flown 2026-08-28 (Syria, Lebanon) — the first real pass

Session `New test/19`. The ladder itself worked exactly as specified. Three
defects and one measurement came out of it.

**Timeline from `dcs.log`**, mission start 22:08:31:

| Time | Event |
|---|---|
| 22:08:31 | 8 borders drawn, 5 defended; warn 30 s, engage 180 s |
| 22:14:25 | shadow R3#001 up from Rayak vs the player's flight |
| 22:16:56 | ESCALATED — 180 s after entry, to the second |
| 22:24:10 | shadow R3#002 up vs the other BARCAP element |

### The SAM could not have fired on any campaign

`sam` was an **authored-only** field defaulting False, and the terrain files —
which became the only source of borders once the campaign block was deleted —
never set it. So `NeutralBorderGenerator` built no template, `wake_sam` found
none and **returned silently**, and the escalation looked identical to a ladder
that had not run. Confirmed in the log: five fighter templates registered
(`NeutralBorder|Lebanon|MiG-29A` and four more), **zero SAM templates**.

Meanwhile the setting text and the plugin description both promised "the field's
SAM battery wakes". The feature advertised something unreachable.

`sam` defaults **on** now, in the dataclass and in `from_yaml` — both, because
`from_yaml` passed its own `False` default and silently beat the field. An
authored `sam: false` still wins. `wake_sam` says why it did nothing.

### The alert flight cold-started on the ramp

Measured from the sortie tracks: both pairs sat at **908 m — Rayak's own field
elevation — for 270 s** before climbing. The Lua asked MOOSE for
`SPAWN.Takeoff.Air` at field elevation + 760 m, but `SpawnAtAirbase` **keeps the
template's own start type**, and the template was built `StartType.Cold`. The
air spawn was silently ignored and the jets did engine start, taxi and takeoff
while the intruder left.

Both sides say **runway** now (DM call: "lets set them to runway spawn"), which
is what a QRA scramble is anyway. The point-spawn path was never affected — it
builds an in-flight template.

### The hail arrived 30 s after the crossing

The radio call and the shadow launch were the same event, gated on
`warnDwellS`. DM: *"good text, pop it immediately on entry to airspace"*. Split:
`hail` fires on the first scan that finds you inside (so within
`scanIntervalS`), `warn` still launches the flight at the dwell. Being told is
instant; being intercepted is not.

### Measured: the shadow does not survive the intruder's escort

**All four alert aircraft were killed, and the un-escalated pair never fired.**

| Flight | Shots | Alive | Escalated? |
|---|---|---|---|
| R3#001 (2 ×  MiG-29A) | 1 | 360 s | yes |
| R3#002 (2 ×  MiG-29A) | **0** | 270 s | no |

Blue's BARCAP took them all: four pilots, 7 shots, 5 hits. R3#001 had escalated
and was fighting, which is legitimate. **R3#002 was still a shadow at
return-fire ROE and was shot down without firing** — it cannot shoot first by
design, so an escorted intruder kills it for free.

**Fixed by standing it off** (DM call, 2026-08-28), which is the second of the
two levers — the first, arming the shadow, would break "defends, never
initiates" and stays shut.

The cause was in the vector loop, not the spawn: an un-escalated shadow was
routed to the intruder's own position **+1200 m**, i.e. it closed to a merge and
sat there. Measured against the harness, that put it **0.9 NM** off an escorted
flight it is forbidden to shoot at first. It now shepherds from
`shadowHoldNm`, a plugin option defaulting to **20 NM**; escalation still closes,
because an engaged flight is no longer shadowing.

**This buys time, not safety, and the note should not be read as closing the
risk.** The shadow spawns on the intruder's *opposing* coalition, so it is a
hostile contact to that side and a CAP tasked over the area will hunt it at any
range — 20 NM delays that, it does not prevent it. The re-fly is what says
whether the loss rate actually moved; 20 NM is a starting point, not a measured
optimum, which is why it is an option rather than a constant.

## Full-detail borders, 2026-08-28 — detail is free on the line, not in the wash

The vertex budget was 96 and it was **binding on six of the 52 zones** — Syria
96, Azerbaijan 109, Armenia 99, Norway 93, UAE 93, Egypt 91, Iraq 91. Those are
exactly the ones losing shape. Measured against the true clipped country:

| Budget | Norway error | Kola verts | Syria verts |
|---|---|---|---|
| 96 | **7.31 %** | 228 | 377 |
| 192 | 5.52 % | 306 | 516 |
| **384** | **1.28 %** | 780 | 1210 |
| 800 | 0.17 % | 1611 | 2625 |

192 buys almost nothing; 384 is where the curve turns. Shipped at **384**:
2,240 → 8,244 vertices, 3.7×, with every map keeping the same zones and the
same countries.

**The cost is not symmetric, and that is what makes this affordable.** The web
map draws any number of points for free. In DCS the *outline* is a single
freeform however many points it carries — but the *fill* cannot be, because DCS
will not fill a concave shape, so it goes through MOOSE's triangulation and
comes back as roughly one markup per vertex.

So the rings ship at full resolution and **only the fill is thinned**, to
`FILL_MAX_VERTS = 96` per zone on an even stride. Result per map:

| | Outline markups | Fill vertices |
|---|---|---|
| Before | 5–8 | 222–377 |
| Full detail, unthinned | 5–8 | 715–1264 |
| **Shipped (thinned fill)** | **5–8** | **340–516** |

DCS pays about 1.4×, still below the 446 shapes Afghanistan shipped with before
the coverage work; the planning map gets the whole 3.7×. At 5 % alpha under a
precise outline the thinned wash is not visible.

**A higher budget needs an area floor.** Finer geometry stops absorbing slivers:
at 384 with no floor, Kola gained a 340 km²/6-vertex Russian fragment and a
0 km²/**3-vertex** Norwegian one, each of which becomes a zone with its own
alert flight, and the 3-vertex one trips `test_no_zone_is_a_clip_artifact`. The
floor is **500 km²**, which cuts between those and the smallest genuine
territories — Bahrain 598 km², Oman's Musandam 1,799, Iran's coastal piece
1,973, all with 32+ vertices. Falklands keeps its own 2,000 km² archipelago
floor. **Regenerating without `--min-area-km2` reintroduces the slivers.**

## Flown 2026-08-28 (Afghanistan) — the alert flight launched 271 NM away

Session `New test/20`, reported as a regression from the vertex-budget change.
**It is not one.** The fallback fires identically at 96 and at 384 vertices,
measured against the player's own recorded track — this map is simply the first
to expose a rule that never survived a long country.

Two things from the same log confirm the previous pass's fixes work in game:
`SAM battery awake at Pakistan border CAP`, and the escalation on the player's
flight.

### What happened

`launch_point` computed a point 25 NM from the intruder on the bearing toward
the origin, and if that point fell outside the border it **gave up and launched
from the origin** — a rule written so a national alert flight never transits the
neighbour. Pakistan on the Afghanistan map is a band roughly 700 km long and
90 km deep, and its station is the polygon's representative point, which sits at
the far end from wherever you cross. So the straight line always left the band
early, the rule always fired, and the flight always spawned at the far end:

| Crossing (mission time) | Station distance | Old rule | Fixed |
|---|---|---|---|
| t=330 | 271 NM | falls back **271 NM** | 25.0 NM, inside |
| t=390 | 271 NM | falls back **271 NM** | 25.0 NM, inside |
| t=540 | 276 NM | falls back **276 NM** | 25.0 NM, inside |

### The fix

The intruder is inside the polygon by definition, so a point near it is too —
there was never a need to give up and go home. `launch_point` now sweeps
bearings outward from the homeward one (0, ±30°, ±60° …) at the standoff radius,
then at half and a quarter of it, and takes the first point that lies inside the
border. The origin is the last resort only, for a country thinner than a quarter
of the standoff, where it is close by anyway.

The bearing order matters: the first hit is the closest bearing to home that is
actually in the country, so the flight still reads as coming from its own
territory rather than materialising abeam.

**The lesson is about the shape of the country, not the shape of the code.**
Lebanon hid this: it is small enough that the fallback landed at Rayak, inside
the action. Every rule here needs testing against a long thin country as well as
a compact one, which is what `THIN_BAND` in the harness now does.

## The standing patrol (DM call, 2026-08-29) — the scramble is gone

**A neutral country now flies a real air patrol over its own border from mission
start.** It orbits as a true neutral, is visible before you cross, warns you by
radio on entry, and — only if you press — its coalition is swapped in place so it
can attack. No scramble, no chase, no standoff.

### Why the scramble had to go

Three flown passes, three failures, all of the same kind:

| Flown | Failure |
|---|---|
| 08-28 (Syria) | cold on the ramp: **270 s** to get airborne |
| 08-28 (Afghanistan) | launch point fell back to the station: **271 NM** behind |
| 08-29 (Afghanistan) | airborne, but closed **22.8 → 6.5 NM** while still shadowing |

The last one is the one that settles it. The standoff cannot be held, because
**the closing geometry belongs to the intruder**: the vector loop re-asserts the
hold every 45 s and the measured closure was 488 m/s — 11.8 NM per tick. Tuning
the cadence does not fix it; a fighter told to keep its distance from someone
flying at it either runs away, which is not shadowing, or merges.

A patrol already on station never plays that game. It also fixes the thing none
of the scramble versions could: **you can see it before you cross.** A border you
only discover after violating it is a trap, not a deterrent.

### How a neutral ends up able to shoot

The engine verdict stands — a neutral cannot fire. The patrol is generated as a
live in-flight group under a **neutral** country with an `OrbitAction` racetrack,
and on escalation the plugin swaps its coalition:

```lua
local tpl = grp:GetTemplate()
tpl.CountryID  = <country opposing the intruder>
tpl.CoalitionID = <coalition opposing the intruder>
grp:Respawn(tpl, true)
```

`GROUP:Respawn(template, true)` copies every live unit's x/y/**alt**/heading into
the template, and `DATABASE:Spawn` reads `CountryID`/`CoalitionID` off it and
hands them to `coalition.addGroup` (`Moose.lua:11648`). This is the fallback the
2026-08-24 engine research recorded and did not use; it is used now.

**The one thing that cannot be proven outside DCS.** `Respawn` is a
`Destroy(false)` plus a re-add 0.1 s later. Position, altitude and heading
survive; **velocity does not** — the group takes its speed from the route's first
waypoint. If a swapped flight ever drops out of the sky, that is why. There is
also a 0.1 s blink if you happen to be looking at it. **DM call: if the swap
misbehaves, stop and report rather than picking a fallback.**

### What went with it

`spawn_shadow`, `launch_point`, `spawner_for`, `shadow_for`, `stand_down`,
`destroy_shadow_later`, the vector loop, and the `SHADOW_*` constants. The
`vectorIntervalS`, `maxShadows` and `shadowHoldNm` plugin options are deleted —
they tuned a mechanism that no longer exists. `warnDwellS` now gates a second
radio call ("our patrol has been advised") rather than a launch.

Kept unchanged: the border scan, the immediate hail, the escalation triggers
(dwell, weapon release, fire on the patrol), the SAM wake, AI-never-engaged, and
the F10 drawing.

### The tests

Eleven scramble-only tests were deleted rather than adapted — they pinned launch
distance, hold distance, takeoff type and stand-down, none of which exist. The
harness gains a `coalitionSwaps` recorder, and the fixture now puts a live
neutral patrol in the air so the swap has something to act on.

One test had to change shape rather than assertion:
`test_a_side_that_is_permitted_transit_is_never_challenged` used to watch a
refused AI get shadowed. With a standing patrol **and** AI-never-engaged, a
refused AI produces no observable at all, so consent is now tested from both
sides of the same border against the player.

## Flown 2026-08-29 (test 22) — the patrols fell out of the sky

**Every patrol crashed within a minute of mission start** — Pakistan's F-16A,
Iran's MiG-29A, India's Su-30. One bug, and it produced both symptoms the DM
reported (the crash, and "flying at stall speed").

`OrbitAction`'s speed argument is **km/h**, like every pydcs speed argument, and
pydcs divides by 3.6 on write. The generator converted `CAP_SPEED_KPH` to m/s
first, so the division happened twice. Read out of the generated `.miz`, the
route carried:

```
208.33 m/s   <- waypoint speed, correct (750 km/h)
 57.78 m/s   <- the ORBIT task: 112 kt
208.33 m/s
```

A fighter commanded to hold 112 kt departs. Pakistan's track shows 8,125 m to
2,196 m in one 30-second sample.

**This is the trap the `pydcs-speed-args-are-kph` memory exists for, and it was
walked into anyway** — the value looks plausible in every file it passes
through, and no gate can tell 57.8 from 208.3. `test_the_orbit_speed_is_written_in_km_h_not_m_s`
now asserts the task lands between 250 and 700 kt.

## Two incursions into one country (DM calls, 2026-08-29)

The standing patrol raised two questions the scramble never had to answer,
because it spawned per-intruder.

**Both sides violate the same country.** Once the patrol has swapped it belongs
to one coalition, which makes it an *ally* of the other side: it cannot fire on
them, and an `AttackGroup` task on an ally is silently dropped. **The country
puts a second flight up** (`NEUTRAL AF2 <country>`), cloned from the standing
patrol's own template onto the coalition opposing the new violator. Flipping the
first patrol's allegiance instead was rejected — it costs a second
destroy-and-re-add mid-fight and a country visibly changing sides while shooting.

This is the one place a spawn survives the standing-patrol redesign, and it is
deliberate: a country fighting two enemies at once genuinely needs two flights.

**Two intruders on the same side.** The patrol re-targets the **nearest**, on a
20-second loop, rather than whoever escalated last — committing to the newest
abandoned an engagement already in progress. The §61 rule still applies: the
task is only re-set when the target id actually changes, because a repeated
identical `setTask` restarts the attack run.

## Flown 2026-08-29 (test 23) — a racetrack with one waypoint is not a racetrack

The 112 kt fix held: the orbit task carried 208.33 m/s and the patrols were up
and orbiting. Everything from crossing to the SAM firing then ran end to end for
the first time. What still failed was the route itself.

### Every leader flew into the ground; every wingman lived

| Aircraft | Died at | Wingman |
|---|---|---|
| India Su-30 #1 | 43.3 s | #2 flew the full 649 s |
| Iran MiG-29A #1 | 42.2 s | #2 flew the full 649 s |
| Pakistan F-16A #1 | 34.6 s | #2 flew to the swap at 440 s |

Three for three, and the split is exact: **#1 dies, #2 lives**. The wingmen were
not spared — they followed the leaders down to 1,035 / 1,035 / 3,791 m and
pulled out once the lead was gone.

**A DCS Race-Track orbit flies between its waypoint and the next one.** The
patrol was built by `flight_group_inflight`, which makes a one-waypoint route,
and the orbit task was attached to it. There was no second point, so there was
no leg. The descent starts at the first sample and never levels: 6,093 m to
1,866 m in 34 s at ~210 m/s — a dive under power, not a stall.

The control is in the same `.miz`: every working Race-Track in it (the blue
BARCAP, both tankers, the AWACS, the CSAR orbit) has **13–15 route points**. The
three neutral patrols had **one**. The tree's only single-waypoint orbit —
`holdpoint.py` — uses `Circle`, which is the pattern that needs no second point.

**The first fix** was `patrol_leg_end`: a 25 NM leg on the first of twelve
bearings whose whole length stayed inside the border polygon. That got the
patrols flying and was not enough — see *The orbit had to clear the frontier*
below. `test_the_generated_patrol_has_a_second_waypoint` builds the real group
through the real generator and asserts two points, because the leg maths
passing in isolation is not what shipped broken.

### What did work, and is now proven in DCS

- **The airborne coalition swap.** Pakistan's pair came back as `Coalition=Allies,
  Country=xr` at the same altitude (6,093.4 m) and was doing **211 m/s within
  5 s**. The recorded risk was that `Respawn` is a destroy-and-re-add that does
  not carry velocity; measured, it does not matter. **That risk is closed.**
- **The SAM fired.** Two `SA3M9M` launches at 517 s and 528 s. The escalation
  clone works end to end, which no earlier test reached.
- **The ladder.** `ESCALATED on Kandahar BARCAP|...` logged in both sessions.

### The patrol never fired back, and that is the loadout

`load_task_default_loadout(CAP)` gave the F-16A **4× AIM-9M, 2× 370 gal, ALQ-131**
— a pure WVR fit. The player's Block 50 killed both from AMRAAM range, so the
patrol died without a shot. This is not a defect; it is what a Sidewinder-armed
jet does against AMRAAMs. Whether a neutral's deterrent should carry a BVR
weapon is a **DM call and has not been made** — do not change the loadout
silently.

### Test 24 confirmed the diagnosis on a second terrain, before the fix shipped

Test 24 (Caucasus, Turkey, F-16C bl.50) was **generated at 16:22, before the
racetrack fix landed at 16:47** — its `.miz` carries one route point and two
pilots, so it is provably the test-23 build. It was flown for the Iron Gate
turn-1 questions, not for §96 -- the same session is the evidence on checklist
row B99 -- so what it gives §96 is an unplanned replication, and it replicates
exactly:

| | Leader | Wingman |
|---|---|---|
| Test 23, Afghanistan, Pakistan F-16A | ground at **34.6 s** | recovered, flew to the swap |
| Test 24, Caucasus, Turkey F-16C | ground at **34.3 s** | ground at **65.3 s** |

Four airframes across two terrains, and the leader dies at the same 34 seconds.
Both aircraft hit terrain — last samples at **13 m and 4 m AGL** — and the
wingman's last attitude is **−66.9° pitch at 71.9° bank**, a near-vertical
spiral, not a stall mush. That rules out the 112 kt reading a second time: the
orbit task in this `.miz` carries 208.33 m/s.

**Neither Afghanistan wingman was saved by anything the patrol did** — they had
ground to recover into. Turkey's spawn sits over ~2,000 m of rock and neither
aircraft got out. On this map the whole patrol was gone in 65 s, which is why
the session logs no escalation at all: there was nothing left to escalate with.

The fix was checked against this exact zone: Turkey's spawn `(-426756, 661245)`
yields a **25.0 NM leg**, and the patrol is now four aircraft.

### The orbit had to clear the frontier, not just start inside it (2026-08-30)

Flown with the 25 NM leg: **the patrols overflew the neighbouring country**,
by the DM's read *under 10 NM past each end of the orbit*. A DCS racetrack
overshoots before it turns back, so a leg that merely sits inside the polygon
flies out of it. Requiring the *line* to be contained was the wrong test.

**And the stations themselves were the bigger half.** Measured across the 52
shipped zones, the distance from each station to its own border:

| Zone | Station was | Its zone could hold |
|---|---|---|
| Afghanistan / India | **0.6 NM** | 75.4 NM |
| Afghanistan / Iran | 2.6 NM | 82.9 NM |
| Syria / Israel | 4.0 NM | 14.7 NM |
| Iraq / Jordan | 4.9 NM | 26.0 NM |
| Caucasus / Azerbaijan | 8.6 NM | 52.2 NM |

Seven stations sat closer to the frontier than any orbit could clear, in
countries with room to spare. No leg length fixes that.

**`patrol_orbit` replaces `patrol_leg_end`** and does both jobs. It pulls the
polygon in by a clearance — 12 NM first, then 8, 5, 3 — and fits the leg inside
*that*. A station already that deep is left exactly where the campaign put it; a
station that is not is moved to the **nearest** point that is, which is the
smallest correction that works rather than a jump to the country's deep
interior. The leg itself is **12 NM**, down from 25.

Measured over the shipped geometry afterwards:

- **All 52 zones still get a racetrack.** Nothing fell back to `Circle`.
- **46 of 52 clear their border by 12 NM or more**; the leg is the full 12 NM
  in 49 of them.
- **Only 8 stations moved at all**, and six of those by under 6 NM. The largest
  are Syria/Israel 22.8 NM, Afghanistan/India 17.3 and Iraq/Jordan 14.8 — the
  ones that were on the line.

**Three zones cannot be fixed by geometry, so they fly nothing (DM call).**
Bahrain (largest inscribed circle **5.0 NM**), Persian Gulf Oman (6.1) and
Persian Gulf Iran (7.1) are smaller than the overshoot. A patrol that
permanently trespasses on its neighbours is worse theatre than no patrol, so
**the last clearance is a floor, not a fallback**: a country that cannot clear
8 NM puts nothing up. It keeps its border, its radio calls and **its SAM**,
which becomes its whole air defence.

That needed three changes beyond the generator, because a patrol had been
assumed everywhere:

- the emitter's `assert zone.fighter_template is not None` is now a conditional;
- the plugin read `cap_group = tostring(raw.fighterTemplate)`, which turns a
  missing template into the group name `"nil"`;
- and the plugin's `usable` rule **dropped an enforcing zone outright** unless
  it carried a fighter template, so the SAM-only zone never loaded at all. An
  enforcing zone now needs a fighter template *or* a SAM.
  `test_a_country_with_no_patrol_still_wakes_its_sam` pins that, and it failed
  on the first run for exactly this reason.

Final measurement over the shipped geometry: **49 patrols and 3 SAM-only
zones**, the leg at the full 12 NM in 48 of the 49, and the tightest clearances
**8.1 and 8.2 NM — both Azerbaijan zones on the Caucasus**. Those two sit at
the floor, so they are the ones to look at if a patrol still clips a frontier.

### Flown 2026-09-01 (test 25, Syria) — the ladder ran end to end

Five four-ship patrols — Lebanon, Iraq, Jordan, Saudi Arabia, Turkey — airborne
from `t=0.1` and holding **6,074–6,095 m** for the whole mission. **Sixteen of
the twenty were never removed at all**, against every leader dying at 34 s two
tests earlier.

**The border containment is measured, not eyeballed.** Every sample of every
patrol track, tested against its own polygon:

| Country | Samples | Outside | Closest approach |
|---|---|---|---|
| Turkey | 3,017 × 4 | **0** | 24.5 NM |
| Iraq | 3,017 × 4 | **0** | 19.1 NM |
| Jordan | 3,017 × 4 | **0** | 8.7 NM |
| Saudi Arabia | 3,017 × 4 | **0** | 7.1 NM |
| Lebanon (pre-swap) | 1,415 × 4 | **0** | 3.9 NM |

23 of 24 aircraft never left. The one exception is Lebanon's #4 **after it
turned hostile** — 400 samples up to 7.2 NM out, which is a fighter chasing the
intruder under `AttackGroup`, not a patrol on its orbit. That is the intended
behaviour and is not a containment failure.

**The overshoot, now a number: up to 8.1 NM.** Fitted leg clearance minus the
closest approach actually flown — Lebanon 12.0 → 3.9 (**8.1**), Jordan 15.2 →
8.7 (6.5), Iraq 25.3 → 19.1 (6.2), Saudi 13.2 → 7.1 (6.1), Turkey 27.4 → 24.5
(2.9). The DM's "under 10 NM" eyeball was good, and 12 NM is the right first
clearance: it leaves Lebanon, the tightest zone flown, 3.9 NM of margin.

**Consequence for the 8 NM floor.** A zone fitted at exactly 8 would fly at
roughly zero clearance. Only the **two Caucasus Azerbaijan zones** are near it
(8.1 and 8.2), so at worst they graze their own frontier — nothing like the
10 NM that started this. Not changed; recorded so the number exists if it ever
matters. Everything else is fitted at 10 or more.

**Orbit footprint:** a 12 NM leg flies a **~22.6 NM** diagonal box.

**The rest of the ladder, all first-time evidence in one session:**

- **The swap took all four together.** Removed `t=330.04`, re-added `t=330.1`
  as `Coalition=Allies`, then fought for 80–150 s before being shot down.
- **The SA-6 fired** — two `SA3M9M` at `t=381.7` and `386.9`.
- **The patrol fired back** — two `P_73` and one `P_27P`. The WVR fit is doing
  what the numbers call was meant to buy, against four AIM-120C-armed Vipers.

Not evidenced here: an AI intruder (B111), and the radio calls, which are not
logged — the DM confirmed those in test 19.

### Numbers, not better missiles (DM call, 2026-08-29)

The patrol takes `load_task_default_loadout(CAP)`, which on the F-16A is
**4x AIM-9M, 2x 370 gal, ALQ-131** — a pure WVR fit. In test 23 the player's
Block 50 killed both jets from AMRAAM range and the patrol never fired.

Three options were put up: leave it, give it the era's best A2A fit, or keep the
fit and put up more aircraft. **The call was more aircraft** — `PATROL_SIZE = 4`.
The deterrent stays the warning and the SAM; what changes is that killing the
whole flight and carrying on is no longer one BVR pass. **Do not "fix" this by
upgrading the loadout** — the WVR fit is the decision, not an oversight.

**This surfaced a live bug in the second flight.** `second_patrol` called
`SPAWN:InitLimit(2, 0)`, and MOOSE refuses the whole spawn when
`AliveUnits + #template.units > SpawnMaxUnitsAlive` (`Moose.lua:21358`) — so the
moment the template grew to 4 the second flight would have silently never
appeared. It is `InitLimit(0, 0)` now; one flight per zone is guaranteed by the
`zone.second_group` latch, which is where that guarantee always belonged.

**The cost, measured.** Test 23's Afghanistan turn drew 8 borders and defended
3, so this is **12 orbiting AI fighters instead of 6**. The upper bound across
the shipped terrains is every zone that can field an interceptor: Iraq 2020 is
8 of 8, so 32. That bound needs a campaign where no coalition holds a field in
any bordering country, which is not a campaign anyone has authored — but if a
turn ever feels heavy with this on, this is the first number to check.

### One log line, guarded

`OptionROEWeaponFree` ran on MOOSE's pre-`Respawn` GROUP and logged a `GetVec3`
error, once per escalation. The call now asks DCS whether the group exists first.

### The self-scan guard missed the patrol after the rename

`scan_group` skips a country's own aircraft by name, and the list was written
for the scramble: `NEUTRAL AF` and `NEUTRAL SAM`. The standing patrol is
`NeutralBorder|<country>|<type>`, so from the moment it swaps — which puts it on
a coalition — it was scanned as an intruder inside its own border. **Nothing
player-facing came of it**: hail, warn, escalation and the SAM wake are all
gated on `is_player`, and the patrol is never a player. The guard now lists the
patrol's real prefix as well.

**No test.** With every rung `is_player`-gated the guard has no observable
effect from the harness, and `intruders` is a file-local. A test here would
have to fake the patrol into a player group to see anything, which asserts a
situation that cannot occur. The guard is defensive: it costs a string compare
and it closes the trap for whoever later relaxes one of those gates.

## Deferred (not built, not promised)

- Cross-mission consequences: escalating posture, airspace closure, the neutral joining
  the war. All were explicitly scoped out of v1 by DM call.
- Per-zone SAM composition in the yaml (fixed SA-6 today).
- Naval or ground border crossings — the watch is airborne groups only.

## In-game passes owed

**B110** (the player ladder end to end) and **B111** (AI shadowed only, plus the
accepted-risk watch: how often the intruder's own side kills the shadower before
escalation). Full setup, pass criteria and fail signatures are on those checklist rows.
