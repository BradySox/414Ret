# Motorpools

> **Adopted standard (2026-07-20).** This page is the upstream
> [Motorpools](https://github.com/dcs-retribution/dcs-retribution/wiki/Motorpools) page,
> adopted as the 414th's own standard for authoring motorpools. The fork runs this
> feature as adopted from upstream (PR #859 plus follow-up fixes), so the behavior below
> is identical here; fork specifics are in the **414th** section at the bottom. When
> upstream revises their page, refresh this one.

A **motorpool** is a strikeable vehicle park that renders a control point's
not-yet-deployed reserve armor. It lets players strike an enemy's armor reserves by
bombing the depot instead of only meeting them at the front line.

Motorpools are opt-in. A control point renders one only if the campaign authors it. With
none authored, nothing changes.

## Authoring a motorpool

Place a **Garage A** fortification static (`Fortification.Garage_A`) in the campaign
`.miz`, on the side (`Combined Joint Task Forces Blue` or `Combined Joint Task Forces
Red`) that should own it. The **Garage A** should be located **outside the control
point's 3,000 m capture radius.** See [Capture zone](#capture-zone) below.

* Retribution assigns the static to the **nearest control point** at load and stores it
  as a preset location.
* At new-game generation each authored location becomes a motorpool objective, gated on
  the **Spawn strikeable motorpool reserves** setting (on by default).
* Each motorpool gets a codename like any other theater ground objective.
* The static's heading sets the orientation of the parked-vehicle grid and the depot
  building.

## Physical layout

Leave clear space around the Garage A, especially along the local +x/+y and −x/−y
diagonals (≈50 m+ each way), so parked vehicles and the depot don't collide with each
other or neighboring spawns; and keep the whole thing outside the 3,000 m capture
radius.

<img width="1019" height="1510" alt="motorpool" src="https://github.com/user-attachments/assets/0fc09d74-1590-4b54-877c-fec677149909" />

### Origin and orientation

* The Garage A static's position in the campaign `.miz` is the motorpool's origin
  (`tgo.position`). The static's heading sets the orientation. At heading 0 the grid is
  world-axis-aligned; at any other heading the entire layout is rotated clockwise about
  the origin to follow the garage facing.

### Parked-vehicle grid

From `motorpoolpopulator.py`:

* Spacing: 12 m between vehicles (`_SPACING_M = 12.0`), same in both axes.
* Width: 5 columns (`_COLUMNS = 5`) — fixed, regardless of vehicle count.
* Filled row-by-row: slot `index` → column = `index % 5`, row = `index // 5`, with
  `dx = col×12`, `dy = row×12` (both positive). Slot 0 sits exactly on the origin.
* So the grid grows in local +x / +y from the Garage A. Columns sit at 0, 12, 24, 36,
  48 m.

### Where the depot building goes

From `motorpoolgenerator._spawn_depot`:

* The Garage A depot is placed at 50 m in the local −x/−y corner
  (`_DEPOT_OFFSET_M = 50.0`) — diagonally opposite the +x/+y vehicle grid — then rotated
  by the garage heading.
* 50 m is deliberately just past the grid's max reach (48 m), so the depot never
  overlaps a parked vehicle at any heading. It's inert scenery (bombing it does nothing)
  and respawns every mission even at zero reserve.

### Overall footprint

The full site spans from the depot corner (−50 m, −50 m local) to the far corner of the
vehicle grid (+48 m, +48 m at max) — roughly a ~100 m × 100 m box at the maximum cap,
rotated to the garage heading. At the default cap it's about 100 m on the depot-to-grid
diagonal but the vehicle part is only ~48 × 12 m. The layout is recomputed every mission
and is ephemeral. If the TGO is performance-culled (`generate()` returns early), nothing
renders — not even the depot.

## How a motorpool behaves

A motorpool generates no income and does not replace factories or ammunition depots. It
only projects reserve armor that already exists at the control point. The motorpool is a
live, per-turn view of the control point's reserve armor. It is not a separate
stockpile.

* **Reserve projection.** It shows only the armor that is *not* deployed to the front
  that turn. If the control point has no connected enemy (nothing reaches the front),
  all of its armor is reserve.
* **1:1 grind.** Each motorpool vehicle destroyed decrements the control point's armor
  by one. The owner must repurchase it next turn.
* **No economy.** Motorpools produce no money.
* **No front-line shift.** Motorpool losses are tracked in their own loss category and
  never count toward the front-line battle result.
* **Passive units.** Parked vehicles hold fire (weapon-hold ROE), have no waypoints, and
  cannot be driven. They do not move or return fire, but they still register kills.
* **Spawn cap.** At most **10** vehicles render per control point per turn by default
  (setting: *Maximum motorpool vehicles per turn*, range 0 to 25). The cap is shared
  across every motorpool on that control point.
* **Shared pool.** If a control point has more than one motorpool, they all draw from
  the same reserve pool and split it round-robin.

### Capture zone

A control point cannot be taken by ground assault while live motorpool units sit inside
its capture radius. If an authored motorpool falls inside the 3,000 m radius, the UI
warns at new-game generation and again when the save is loaded. Keep Garage A statics
clear of the capture radius.

## How flights interact

* **Strikeable.** Players can plan strike and BAI packages against a motorpool exactly
  like other theater objectives.
* **Auto-targeted.** The AI commander plans strike and BAI packages (with escorts)
  against enemy motorpools that hold reserve armor. Targets are considered only when
  motorpools are enabled, the spawn cap is above zero, and the owning control point
  actually has reserves.
* **Depot building is inert.** Bombing the Garage A building itself does nothing. It
  respawns every mission, produces no debrief loss, and never touches armor. Only the
  parked vehicles matter. The map always shows the depot as present, never "destroyed".
* **Debrief.** Motorpool kills appear in the post-mission debrief as a "Motorpool units
  lost" row, with per-type detail lines.
* **Map symbol.** A maintenance-facility installation symbol, distinct from armor
  groups.

## Settings

| Setting | Default | Effect |
|---|---|---|
| Spawn strikeable motorpool reserves | On | Render reserve armor as strikeable motorpools where the campaign authored them. |
| Maximum motorpool vehicles per turn | 10 (0 to 25) | Caps rendered reserve vehicles per control point per turn. |

## Limitations

* **Authored only.** A control point with no Garage A location renders no motorpool.
* **One reserve vehicle pool per control point.** Multiple motorpools on a control point
  share a single reserve pool.
* Upstream also notes Pretense mode is unsupported — moot in this fork, which does not
  ship Pretense at all.

## 414th

* **Reference implementation: Red Tide.** The campaign authors a Garage A near
  **Haina**, the forward Soviet base at the Fulda Gap — "bomb the motor pool before its
  armor reaches the front." Its parked rows fill as red procures armor (the reserve is
  the purchase stock, so it starts empty at turn 0). Every other campaign is inert until
  it places a `Garage_A`.
* **Recon fog.** The motorpool category is never concealed — the depot always draws an
  exact map marker, even with concealed enemy forces on.
* **The AI pressure is phase-aware.** The commander's motorpool-attack task rides the
  fork's campaign-phase and enemy-posture emphasis, so expect depot strikes to
  ebb and flow with the arc rather than fire every turn.
* **Authoring checklist.** When adding one to a fork campaign, follow
  [Campaign maintenance](Campaign-maintenance): note it in the campaign's design note,
  cover the Garage A binding in the campaign's CI lock, and remember a NEW game is
  required to materialise it.
