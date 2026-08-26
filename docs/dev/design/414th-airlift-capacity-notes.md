# Airlift capacity: lift slots

**Built 2026-08-26.** Replaces one constant with two graded tables.
Code: `game/data/airliftcapacity.py`, wired into
`AirliftPlanner.create_airlift_flight` (`game/transfers.py`).

## What was there

```python
capacity_each = 1 if squadron.aircraft.dcs_unit_type.helicopter else 2
required = math.ceil(self.transfer.size / capacity_each)
```

One number for every aircraft in the game, multiplied by a raw count of
vehicles. It said a Gazelle and a C-17 differ by one unit, and that a main
battle tank is the same cargo as an infantry squad. `transfer.size` is
`sum(self.units.values())` — a headcount with no notion of what is in it.

## Why not `cabin_size`

This was the obvious fix and it is wrong. `AircraftType.cabin_size` is a CTLD
infantry-seat count:

- **Clamped for gameplay, not measured.** `CH-47D.yaml`: *"24 # It should have 33
  but we do not want so much for CTLD to be possible."* The Mi-26 (real 60+) and
  CH-53E (real 37) carry the same comment.
- **Flat across lift classes.** `C-17A`, `Il-76MD`, `C-130J-30` and `An-26B` are
  all 24. One of those carries an Abrams; one carries light freight.
- **Zero by default for fixed-wing**, and authored on only 39 airframes — so
  reading it as capacity would silently remove the airlift leg from every
  unauthored transport.

There is also no denominator. `GroundUnitType` carries no mass, size or
transportability field at all: only `class`, `price`, `spawn_weight`, `mobile`.

## The model

One unit, the **lift slot**, anchored at roughly **seven tonnes** — one army
truck. Both tables derive from that anchor, which is what makes them
re-derivable rather than taste:

- **Cargo cost** = the class's representative vehicle's combat weight ÷ 7.
  Infantry 1, APC 2, IFV 3, artillery 4, TELAR 5, **tank 8**. Keyed on the
  existing `class:` field, populated on 606 of 622 ground units; the 16 without
  one fall to `DEFAULT_LIFT_COST` (3).
- **Aircraft capacity** = published maximum payload ÷ 7, floored at 1, in the
  optional aircraft-data field `airlift_capacity`. C-5 17, C-17 11, Il-76 7,
  A400M 5, C-130J-30 3, Mi-26 3, Chinook 2, **An-26 1**.

Neither table is measured inside DCS. It is a proportionality model, and the
shared anchor is what keeps the two halves proportional to each other.

## Backwards compatibility

`airlift_capacity` is unauthored on all but 16 airframes, and the fallback is the
**old constant read as slots** — 1 helo, 2 fixed-wing. So an airframe nobody
authored moves exactly what it moved before for cargo of the default cost, and
less only for cargo heavier than that. Nothing in a save changes; the field is
data, not state.

The 16 authored are the transports where the real figure differs from the
fallback. Every other transport-capable airframe (23 of the 31 that declare the
Transport task) is unchanged on purpose.

## The two traps

1. **The count must agree with the split.** `PendingTransfers.split_transfer`
   consumes `transfer.units` greedily in the dict's own iteration order, so
   `units_fitting_in` counts in that same order. A count derived any other way
   would not describe the units the split actually hands to the flight.
   Checked over 20,000 randomised transfers: the count always matches what the
   split hands over, and the resulting load never exceeds the flight's slots.
2. **Zero must break the loop.** `create_package_for_airlift` loops
   `while … self.transfer.transport is None`, and an aircraft too small for the
   next vehicle assigns no transport and consumes no aircraft — it would spin
   forever. `create_airlift_flight` returns 0 in that case and the caller breaks.
   The same guard covers `flight_size < 1`, which was already reachable through
   `max_fulfillable_aircraft` and would have built an empty flight.

## Consequences, stated plainly

- **A helicopter can no longer airlift armour.** A tank costs 8 slots and the
  biggest helo in the game is 3. This is the intended result.
- **A transfer led by tanks cannot be part-lifted by a small helo**, even when
  lighter cargo sits behind them in the order. `units_fitting_in` returns 0, the
  planner tries a squadron with a bigger aircraft, and if none exists the
  transfer waits for a road or a ship (`TransferOrder.description` already reads
  "No transports available"). Reordering somebody's transfer to suit the
  available airframe is the alternative, and it is worse.
- **Heavy transfers between disconnected bases may now simply not move by air.**
  Airlift is the fallback when there is no road or shipping link, so a
  tank-heavy transfer to an island base can stall where it used to fly. Nobody
  has played a campaign against this yet — it is the thing to watch.

## Not done

- **No per-unit tonnage.** The cost is per *class*, so every tank costs the same
  whether it is a T-55 or an M1A2. Per-unit weight would be a data-authoring
  project across 622 files; the class tier is the cheap 80%.
- **Convoys and cargo ships are untouched.** They carry the cargo itself and have
  no capacity model at all. See
  [414th-het-convoy-notes.md](414th-het-convoy-notes.md) for the road half.
- **No setting.** The model is always on. If it turns out to strand transfers in
  real play, the knob to add is a floor on capacity, not a master switch.
