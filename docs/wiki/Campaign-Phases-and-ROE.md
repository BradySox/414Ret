# Campaign Phases and Rules of Engagement

Every 414Ret campaign knows what **phase of the air war it is in**, shows it to you, and leans
the auto-planner's offensive tasking to match. On top of the phase machinery ride two optional
layers a campaign can author: a **Rules-of-Engagement layer** (no-strike zones, locked target
classes, or — inverted — free-fire kill boxes) and a **political-will economy** that can end the
war at the negotiating table. This page is the generic machinery; the two shipped flavours are
the **[Vietnam campaign layer](Vietnam-Campaign-Layer)** (Rolling Thunder → Linebacker II) and
the **[COIN campaign](Enduring-Resolve-Campaign-Briefing)** (kill boxes over the Helmand).

*Toggle: **Campaign phases** (Campaign Management page) — default **ON** for every campaign.
It is the kill switch for everything on this page except the will economy, which has its own
toggle.*

---

## The inferred phase arc (every campaign, zero authoring)

A turn-by-turn classifier reads the live campaign — how much of the enemy's long/medium-range
SAM network is still standing, the enemy air threat, whether the front is moving, last turn's
captures — and picks the phase:

**Air Superiority → SEAD / Rollback → Interdiction → Offensive**

- A theater that opens with a real SAM belt starts in **Rollback** (peel the IADS); a genuinely
  belt-less theater skips straight past it.
- A live peer air force holds the campaign in **Air Superiority** until it stops being one.
- Phases advance with hysteresis (no flip-flopping on a noisy turn) and default
  monotonic-forward — the war progresses unless a campaign *authors* regression.
- The active phase **reorders only the opportunistic offensive middle** of the planner's
  priorities — which objectives get first claim on offensive jets. Reactive defense (BARCAP,
  QRA, escort sizing, threat response) is never touched.

**The phase always explains itself.** The status ribbon and kneeboard don't just name the phase
— they show the reasoning ("Interdiction — enemy IADS 22% · air threat low · front static") and,
in the arc expander, the live values of whatever condition would advance it.

## Where you see it

- **The campaign-status ribbon** over the map: campaign name, turn, date, and the current phase
  chip. On a will-economy campaign the two will meters ride here too. Click the chip to expand
  the **whole arc**: every phase, what each locked and released, the **objectives checklist**
  with live ✓/○ ticks, and exactly what advances the current phase (authored conditions with
  live values, or the classifier thresholds on an inferred arc).
- **The kneeboard cover page** carries a campaign-phase band with the same explanation — and
  **spells the ROE out**: OFF LIMITS zones, LOCKED target classes, CLEARED classes (or the
  WEAPONS FREE kill-box list on an inverted-ROE campaign). You can brief the month's rules from
  the cockpit.
- **The turn SITREP** notes phase transitions and the will movers (below).

## Authored arcs

A campaign can replace the inferred arc with an **authored** one — named phases on a turn
schedule, accelerated by live conditions:

- **`min_turn`** pins the earliest turn a phase can open; **`advance_when`** conditions
  (political will below a threshold, enemy resolve below a threshold, a named base captured…)
  can bring it forward.
- **Objectives** — each phase can carry a checklist of objectives with live done-conditions,
  ticked in the arc expander as you complete them.
- The four Vietnam campaigns author the **Rolling Thunder → Bombing Halt → Linebacker →
  Linebacker II** arc; the COIN campaign authors **Disrupt → Clear and Hold → Break the
  Momentum**. Authoring is a YAML `phases:` block in the campaign file — see
  [Custom Campaigns](Custom-Campaigns#authoring-the-campaign-layer).

---

## The ROE layer

An authored phase can carry the era's political restrictions. Three instruments:

### Restricted zones (no-strike)

Sanctuaries the campaign forbids striking — Hanoi's ring, a border buffer, a population center.
Zones come in three shapes:

- **Circle** — a radius around a point or control point.
- **Box** — a rotatable rectangle (Route Packages, "the Box" at Red Flag).
- **Corridor** — a buffered lane along a path (an ingress corridor, the Laos trail).

A campaign author can also **draw the zone in the DCS Mission Editor** (a named circle or
free-form polygon in the campaign `.miz`) and reference it by name instead of typing
coordinates.

**Enforcement is asymmetric, on purpose:**

- The **AI planner is hard-gated** — it will never frag offensive missions into an active
  restricted zone.
- **You are never hard-blocked.** The era's pilots could always break the rules — but kills
  inside an active zone are **ROE violations** that drain your political will at the debrief.
- The **package dialog warns you before you commit**: fragging a restricted target shows an
  ROE warning line that prices the choice. It never stops you.

### Target release (locked classes)

Early phases can keep whole target *classes* locked — factories, power, oil, airfields. A locked
target doesn't vanish: it shows a **RESTRICTED — ROE badge** on its map tooltip, so you can see
the target you're not allowed to hit yet. When the arc advances, the class releases and the
planner pours onto it.

### Free-fire kill boxes (inverted ROE)

A phase can author **`free_fire_zones`** instead — and the polarity flips. The whole map goes
**weapons-hold for fixed strike targets except inside a cleared kill box**. This is the COIN
model: you are cleared into this month's named AOs and nowhere else.

- A restricted zone still carves a **no-strike hole inside a kill box** — a box over a
  stronghold clears the ground around a town but never the town core.
- **Troops in contact are always legal.** Front-line forces and moving convoys are never
  ROE-gated, in either polarity — the ground fight and the interdiction war don't wait on
  paperwork.
- Same asymmetry: the AI is hard-gated to the pockets; you are soft-gated by will.

### The zones are on every map

Active zones are drawn identically in **both cockpits**:

- **The web map** — a dashed layer in the map layers panel ("Enemy intel" group, default on):
  **red dashed** restricted zones (tooltip "RESTRICTED (ROE)"), **green dashed** free-fire
  boxes (tooltip "WEAPONS FREE (ROE)").
- **The DCS F10 map** — the same shapes are painted into the generated mission, red dashed and
  green dashed, named. What you briefed on the web map is what your wingman sees on his F10.

---

## The political-will economy

*Toggle: **Political will tracking** — default off; pre-seeded on by the campaigns that use it.*

Some wars aren't won on the map. With the will economy on, each side carries a meter — by
default **your Political Will** vs **the enemy's Regime Resolve** — fed every turn from the
debrief: weighted airframe losses, POWs held, ROE violations, bases lost, logistics attrition,
warship losses. Exhaust either meter and the war ends at the table, whatever the front line
says — with era-framed victory/defeat banners. Territory victory always still applies.

- **The meters are campaign-authorable.** The Washington/Hanoi framing and every feed weight
  are just the *defaults* of a **will profile** — a campaign can relabel the meters ("The
  Coalition's mandate" vs "the insurgency's momentum"), rewrite the exhaustion banners, and
  re-weight every feed. The COIN campaign inverts the Vietnam weights entirely: body count is
  worth almost nothing; ammo caches and strongholds are the currency.
- **The will ledger keeps it honest.** Every will movement is recorded with a label — hover the
  meter for the top movers, and the SITREP lists them ("Will movers: ammo caches ×3 destroyed,
  F-4E ×2 lost"). You always know *why* the meter moved, which is what lets you fly to it.
- The arc can couple to the meters: an `advance_when` on bleeding will is how a campaign votes
  restraint out as patience runs dry.

Full detail on the Vietnam implementation — POW drains, the B-52 multiplier, the negotiation
endings — on the **[Vietnam campaign layer](Vietnam-Campaign-Layer)** page.

---

## Status

The phase model, zone shapes/containment, drawing reader, and planner gate are CI-locked, and
the full Vietnam ROE arc has been verified across a live fast-forwarded campaign (turns
1 → 8 → 11 → 16, zero AI violations). Still on the in-game checklist: the box/corridor shapes
rendered on a real F10 map (M7), the flown player-violation will penalty, and will pacing over
a long human campaign (M1).

## See also

- **[Vietnam Campaign Layer](Vietnam-Campaign-Layer)** — the Rolling Thunder → Linebacker II
  flavour: political will, sanctuaries, ambush MiGs, red tempo.
- **[Operation Enduring Resolve (COIN)](Enduring-Resolve-Campaign-Briefing)** — the inverted
  flavour: kill boxes, population rings, the insurgency's momentum.
- **[Custom Campaigns](Custom-Campaigns)** — authoring `phases:`, `will:`, and the zone blocks.
- **[Map Layers and Interface](Map-Layers-and-Interface)** — the zone layer, the ribbon, and
  what the F10 map shows.
- **[Kneeboards](Kneeboards)** — the cover-page phase/ROE band.
