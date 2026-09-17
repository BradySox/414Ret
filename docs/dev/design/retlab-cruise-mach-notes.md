# Per-airframe cruise mach, and the package pacing that needs it

**Status:** BUILT 2026-09-01. **One airframe is authored: the F/A-18C at M0.78.** Every
other airframe is unauthored and therefore unchanged. The measurement pass for the rest is
owed, and so is a clean-Hornet reading (see the caveat below).

## The measured defect

Syria, Operation Syrian Shield turn 2. One package, F10 map ground speed read off both
units after the join, before the ingress:

| Flight | Altitude | Commanded | Measured | Actual mach |
|---|---|---|---|---|
| PUFFERFISH SEAD Escort, F-16CM | 22,000 ft | 517.1 kt | 542 kt | M0.89 |
| PUFFERFISH Strike, F/A-18C | 21,000 ft | 519.2 kt | 478 kt | M0.78 |

The escort ran ahead of the striker it was escorting. Reported as role-shaped, not
airframe-shaped: the escort family does it, whatever airframe flies it.

## What was ruled out, with the evidence

Do not re-investigate these without new evidence.

- **The planner.** The two flights are coordinated to 2 knots and 2 seconds. The escort
  passes the Hornet's ingress point at t=2311; the Hornet is there at t=2313.
- **The airframe, as a code path.** `GroundSpeed.for_flight` returned `mach(0.85, alt)`
  for every supersonic jet. `CRUISE_ALTITUDE_BAND_KFT = (20, 20)` for every airframe. The
  22,000/21,000 split is the ±2,000 ft `plane_altitude_offset` scatter roll, worth 8 kt
  across its whole range.
- **Wind.** 23 kt maximum aloft in that mission, and both flights fly track 052° 1,000 ft
  apart.
- **Terrain following.** Every waypoint on both routes is `BARO`. No AGL legs.
- **Store weight. This is the one that matters, and it is counter-intuitive.** Resolved
  against pydcs `weapon_ids`:

  | | External stores | Internal fuel | Fraction |
  |---|---|---|---|
  | F-16 SEAD Escort | 4,400.8 kg (2× 370 gal tanks at 1,338 kg each, AGM-88C, AGM-65G, ALQ-184, HTS, ATFLIR, 4 AAM) | 3,249 kg | 1.36 |
  | F/A-18C Strike | 4,693.4 kg (2× GBU-31, 2× FPU-8A, ATFLIR, 4 AAM) | 4,900 kg | 0.96 |

  **The faster jet carries the larger store fraction.** Absolute weights are within 6%.
  Any drag model keyed on store mass predicts the wrong sign. A first attempt at one was
  abandoned mid-build for exactly this reason.

What is left is airframe transonic drag, for which this tree has no data at all — pydcs
exposes `max_speed` and nothing else. So the number is **authored from measurement, never
derived**. Same standing as `startup_minutes:`, and the same failure mode: an unsourced
value is worse than no value.

## What was built

1. **`cruise_mach:`** — optional per-airframe yaml key on the same footing as
   `cruise_altitude:` / `combat_altitude:` (`AircraftType.cruise_mach`). An authored value
   wins outright in `GroundSpeed.for_flight`, for any airframe including helicopters.
   Unauthored is unchanged: supersonic jets get `DEFAULT_CRUISE_MACH = 0.85`, subsonic
   aircraft `max_speed.mach() × 0.85`, helos `× 0.7`.
2. **`ingress` added to `FormationAttackFlightPlan.package_speed_waypoints`.** It was the
   one transit leg with no package harmonisation, which is exactly the leg the divergence
   was measured on. The package minimum (`Package.formation_speed`) now binds there.
3. **`combat_speed_waypoints` pinned to the old set** (join, split, targets). It defaults
   to `package_speed_waypoints` on `FormationFlightPlan` and drives fuel burn, so without
   the override every strike package would silently start charging combat consumption from
   the join.

Point 2 does nothing on its own — with every jet at M0.85 the package minimum comes out
517.1 kt against the current 517.1/519.2, a 2 kt change. It only bites once airframes
differ, which is what point 1 is for.

## The F/A-18C at M0.78, and its known caveat

Authored on the DM's call, from the reading above. Verified end to end: with the value in
place, `GroundSpeed.for_flight` returns **476.4 kt at FL210** against the measured 478, and
the F-16C is untouched at 517.1. It applies to all three yaml variants (CF-188, EF-18A+,
F/A-18C Lot 20), which inherit the top-level key.

**The caveat, recorded because it is real and was raised before authoring.** The same
file's hand-flown `fuel:` block is measured at cruise `# 0.85 mach for 100NM`, so a Hornet
demonstrably holds M0.85 in *some* configuration. The 478 kt reading is a Hornet carrying
two 2,000 lb JDAMs and two tanks. `cruise_mach:` is airframe-wide and cannot tell those two
apart, so **every** Hornet now cruises at the loaded-strike figure — BARCAP and TARCAP
included, roughly 5% slower in transit than before.

The knob has **no per-loadout axis and must not grow one** until store weight is shown to
predict something, which the table above says it does not. If a clean-Hornet F10 reading
comes back near M0.85, the honest response is to reconsider the airframe-wide value, not to
add a loadout term.

## Measurement procedure

Read **F10 map ground speed and altitude together**, on a level cruise leg between the
join and the ingress, for both an escort-configured and a strike-configured example of the
airframe. Convert with the ladder below and record the loadout alongside the number.

mach 0.85 by altitude, for reading a GS back into a mach:

| ft | kt | ft | kt |
|---|---|---|---|
| 10,000 | 541.6 | 21,000 | 519.2 |
| 15,000 | 531.5 | 22,000 | 517.1 |
| 18,000 | 525.4 | 25,000 | 510.8 |
| 20,000 | 521.3 | 30,000 | 500.1 |

The model floors temperature at −70 °F above 36,152 ft, so mach 0.85 bottoms out at
**486.5 kt**. A planned speed below that is impossible and means something other than
`GroundSpeed.for_flight` produced it.

## Traps

- **`best_flight_formation_speed` is a `cached_property` on the flight plan.** A loadout
  change does not invalidate it. That is fine while `cruise_mach` is per airframe; it
  becomes a live problem the moment anything makes the speed depend on stores.
- **Escort routes have no ingress on the AI route.** `escort.py` sets
  `ingress.only_for_player = True` and `target.only_for_player = True`, so an AI escort
  flies `HOLD → JOIN → ESCORT HOLD → SPLIT` — one straight leg to a point ~18 nm beyond
  the strike's ingress. The waypoint still exists in the layout and is still priced, which
  is why adding it to `package_speed_waypoints` reaches escorts at all.
- **Do not read a package's speed off `speed_locked` waypoints.** Join/ingress carry
  `speed_locked = False` with `ETA_locked = True`, so DCS flies the ETA solution, not the
  commanded number. Split is `speed_locked = True`.
