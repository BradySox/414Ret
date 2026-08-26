# Neutral-Faction Border Defense — Design Note

**Status: BUILT 2026-08-24 (§96).** Scope locked in a DM Q&A session the same day; every
decision below is a DM call from that session. Read this before editing or re-litigating
any of it. Features doc §96 carries the file list; in-game passes B100/B101 owed.

## Build outcome (what changed between the sketch and the code)

- **The SAM belt is an escalation-time clone, not standing units.** A cold late-activation
  SA-6 template (1S91 + 2×2P25) sits at the field and is SPAWN-cloned under the opposing
  coalition only when a player escalates. No standing red units at a neutral field — which
  also avoids DCS auto-capturing the airbase at mission start. Composition is fixed v1;
  the yaml carries only `sam: true`.
- **The engage task is §61's exact shape**: raw `getController():setTask({id="AttackGroup",
  params={groupId=...}})`, re-set only when the target id changes — not the MOOSE task
  builder. The vector loop uses MOOSE `RouteToVec3` for the benign shadow phase.
- **One fighter template per zone, cloned to either side** via `SPAWN:InitCountry` +
  `InitCoalition` at trip time (template itself lives under the neutral country in the
  neutrals coalition, so it collides with nobody's campaign forces).
- **Reference campaign locked: Into the Hornet's Nest + Lebanon** (DM call). Rayak field,
  MiG-29A (the type Russia offered Lebanon in 2008), 10,000 ft floor, SA-6 on. Desert
  Storm + Iran was investigated and rejected on the evidence: the DS corridor is
  H-3→Baghdad (west) and the map's only Iranian field is Kharg, far south — the border
  would never trip.
- **Border source**: `tools/neutral_border_geo.py` (GeoJSON → shapely simplify →
  `Point.from_latlng` → yaml). The Lebanon trace used the public-domain
  `georgique/world-geojson` country file, 44 vertices. The harness cannot exercise DCS
  behavior — B100/B101 carry the flown verdicts.

## The feature

On a map where most nations are bystanders, a neutral country keeps an alert force at an
airfield near its border. If red or blue violate that border, the neutral scrambles:
shadow first, shoot only if the intruder presses. A third party defending itself — as
theatre, and as a real hazard to a player who cuts the corner.

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
is verified in DCS yet** (B100/B101 still owed).

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
  needed, not default-on. Flipping the default is its own call after B100/B101 fly.

## Deferred (not built, not promised)

- Cross-mission consequences: escalating posture, airspace closure, the neutral joining
  the war. All were explicitly scoped out of v1 by DM call.
- Per-zone SAM composition in the yaml (fixed SA-6 today).
- Naval or ground border crossings — the watch is airborne groups only.

## In-game passes owed

**B100** (the player ladder end to end) and **B101** (AI shadowed only, plus the
accepted-risk watch: how often the intruder's own side kills the shadower before
escalation). Full setup, pass criteria and fail signatures are on those checklist rows.
