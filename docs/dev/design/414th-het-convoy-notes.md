# Heavy equipment transporters for ground transfers

**Scoping only. Nothing built.** Written 2026-08-26 after the DCS patch added the
SLT-50 tractor, SLT-50 trailer and HX81 tractor to the Current Hill assets pack.
The units are not reachable until the pydcs pin moves — see
[414th-dcs-update-2026-08-26-notes.md](414th-dcs-update-2026-08-26-notes.md) §1.

## The defect

A ground transfer between two bases spawns the cargo itself.

`ConvoyGenerator._create_mixed_unit_group` (`game/missiongenerator/convoygenerator.py:219`)
builds the convoy group straight out of the transfer's unit counts, and
`UnitMap.add_convoy_units` (`game/unitmap.py:175`) zips the spawned vehicles 1:1 with
`convoy.iter_units()`.

So moving ten T-90Ms from a rear base to the front drives ten T-90Ms down a road under
their own power, and killing one on the road kills exactly one tank in the transfer.

Two things are wrong with that:

- **Operationally.** Armour does not self-deploy between bases. Over any distance it
  rides a heavy equipment transporter, because tracks and powerpacks are the scarce
  thing. A road march of MBTs is what you do for the last few kilometres.
- **As a target.** Every vehicle on the road is worth the same, so an interdiction
  sortie against a convoy is arithmetic — kill N vehicles, remove N tanks. There is no
  shape to attack.

## The mechanism already exists

This is not a new model. §78 built it for sea transfers.

`ConvoyUnit` (`game/unitmap.py:50`) already carries a `shipment` field, documented in
place: *"This hull's share of the shipment (unit type -> count). A sea convoy of N ships
… losses are proportional. A single-hull convoy (feature off / a one-unit …)"*.

One spawned object standing for a manifest of cargo, with proportional losses, is
exactly what a transporter is. The road convoy needs the wheeled version of the thing
the sea convoy already has.

## What the patch adds

| Unit | Role |
|---|---|
| SLT-50 Tractor + SLT-50 Trailer | German heavy equipment transporter |
| HX81 Tractor | the newer German HET tractor |

**We have no tank transporter today.** The tree carries `M4_Tractor`,
`CH_HEMTT_M983` and the various trailer units, but nothing that carries an MBT. So this
genuinely needs the patch; it is not buildable ahead of the export.

## Shape

1. **Decide what rides.** Not everything needs a transporter — wheeled and light
   vehicles road-march fine. The `class:` field on each ground unit yaml is the obvious
   discriminator and is populated on 606 of 622 units (`Tank` 61, `IFV` 35, `APC` 19,
   `Artillery` 46, `Logistics` 60, …). A first cut: `Tank` and the heavier `Artillery`
   ride, everything else drives.
2. **Build the manifest.** Assign each riding unit to a transporter, N cargo per
   tractor, and record it in `ConvoyUnit.shipment` the way the sea convoy does.
3. **Spawn the mixed column.** Transporters carrying the heavy cargo, plus the
   self-driving remainder, in one group. `_create_mixed_unit_group` already builds mixed
   columns from a `dict[GroundUnitType, int]`, so the spawn side is mostly present.
4. **Map losses.** `MultiGroupTransport.kill_unit` (`game/transfers.py:417`) is keyed on
   `GroundUnitType`, and the sea path already resolves a hull's share, so this is
   re-using `shipment` rather than inventing an accounting path.

## Open questions

- **Does the trailer need the ME attach task?** The patch says trailers attach via a
  task in the mission editor. We already set DCS vehicle-group tasks from the generator
  (`tgogenerator.py:41` imports `EPLRS`; `:480` calls `enable_eplrs`), so the mechanism
  exists — but whether pydcs exposes a task class for the trailer attach is an export
  question, unanswered.
  If it does not, the fallback is to place tractor and trailer as separate units in the
  column, which loses the visual but keeps the model.
- **How many cargo per tractor?** One MBT per HET is the real answer. That makes a
  ten-tank transfer a ten-transporter column, which is a large road target. Whether
  that is good (legible, killable) or bad (a single sortie removes an entire armoured
  company) is a balance call, not a technical one.
- **Does this make interdiction too strong?** Right now killing a convoy vehicle costs
  the enemy one unit. Under a manifest it costs the whole load of whatever you hit. §35
  and §50 both get sharper, and nobody has measured whether that is proportionate.
- **Red only, or both sides?** The fork's convoys are symmetric today. A HET column is a
  better target for the player than for the AI, since the player picks targets better.

## Not in scope

- **Passengers.** The new troop carriers (M1296 IFV, ZA-SpN Titan MRAP, BMP-3 ERA,
  HX77 truck) do not belong here. Transfers move `GroundUnitType` counts; a vehicle
  moves *as* a unit and does not carry the transfer. Their place is §9 TIC's stance
  table and §90's front line. Adding a passenger concept to `transfers.py` would be a
  third cargo model on top of the two the tree already has.
- **The airlift leg.** Related, and was worse, but separate -- and now done.
  `AirliftPlanner` used to set `capacity_each = 1 if helicopter else 2` for every
  aircraft in the game. It is now graded in lift slots on both halves, cargo and
  aircraft. See
  [414th-airlift-capacity-notes.md](414th-airlift-capacity-notes.md). The road
  convoy is the half still outstanding, and it is the harder one, because a
  convoy is spawned cargo rather than an abstract capacity.
