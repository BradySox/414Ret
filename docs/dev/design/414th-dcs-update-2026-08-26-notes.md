# DCS update 2026-08-26 — what it does to the fork

Triage of the 2026-08-26 DCS patch against this tree. Written from the published
patch notes plus a read of our own files; **nothing here has been verified against
an updated install**, because the update is not installed on the machine this was
written on.

The single blocking fact: `requirements.txt:37` pins
`BradySox/pydcs@f84e7d2cb967bd5eebdf9180c1f7b0d5e994d8bd`, cut for DCS
2.9.28.26283. Every new unit, trailer, loadout and AI skill level in this patch is
unreachable until that pin moves.

---

## 1. Do the export first

Nothing below can be settled without it.

1. Run the wiki's `pydcs_export.lua` process on the updated install. The runbook and
   the heavy-mod gotchas are in `tools/verify_mod_export.py`'s docstring; the
   nil-guarded copy is at `C:\Users\brady\dcs-export\pydcs_export.lua`.
2. Diff the export against `pydcs_extensions/` and `resources/units/ground_units/`.
3. Run `pytest tests/test_layout_unit_types.py`. That test exists because of the
   2026-08-08 LvS-103 breakage, and item 2.1 below is the same failure class.

## 2. Three silent-breakage candidates

### 2.1 "BMP-3 IFV (replaces the old model)"

Listed under the Current Hill Assets Pack, which ED now ships in
`CoreMods/tech/Currenthill Assets Pack` under `CHAP_*` ids.

We field the vanilla `BMP-3` id in `resources/units/ground_units/BMP-3.yaml`, and
`resources/plugins/tic/TIC_v1.1.lua:146` keys `["IFV BMP-3"]` by name.

If "replaces" means a new id rather than a new 3D model on the old id, layouts
naming `BMP-3` resolve to `None`, `GroupLayoutMapping.from_dict` drops them without
an error, and the affected sites raise `LayoutException` at generation. That is
exactly what cost Sweden 2020 its only long-range SAM in August.

**Check:** does `BMP-3` still appear in the export, and is there a new `CHAP_BMP3`?
**Catcher:** `tests/test_layout_unit_types.py`.

### 2.2 AGM-45B clsid collision (§71)

`pydcs_extensions/f4e_expanded_weapons/f4e_expanded_weapons.py:9` injects:

```python
AGM_45B_Shrike_ARM__LAU_34_ = {
    "clsid": "{LAU_34_AGM_45B}",
    "weight": 224,
    "settings": Weapons.AGM_45A_Shrike_ARM["settings"],
}
```

This patch adds "AGM-45B loadouts for LAU-34 rail" to core weapons and "AGM-45B
(Shrike B)" to the F-4E. If either ships `{LAU_34_AGM_45B}`, our copy collides.

`pydcs_extensions/weapon_injector.py` writes with a bare `setattr` and a bare
`weapon_ids[clsid] = value`. There is no collision check and no error. Injection
runs after import, so **our stale dict wins** — including the borrowed AGM-45A
settings, which the patch has now diverged from ("Forwarded all changes from
AGM-45A to AGM-45B", plus a reworked FM and a 3-degree autopilot deadzone).

**Check:** is `{LAU_34_AGM_45B}` in the fresh export?
**If yes:** delete the `WeaponsF4EExpanded` entry, keep the pylon wiring — the
pylons reference `Weapons.AGM_45B_Shrike_ARM__LAU_34_`, which resolves natively
once pydcs carries it.

`resources/weapons/standoff/AGM-45B.yaml` already lists that clsid, so the 1972
date gate holds either way.

### 2.3 F-4E SUU-23 migration

HB shipped "Migration for existing missions with old SUU-23 pods". Our pack wires
`Weapons.SUU_23` on pylons 3 and 11
(`f4e_expanded_weapons.py:256`, `:416`), and `resources/customized_payloads/F-4E.lua`
and `F-4E-45MC.lua` may name the old clsid directly.

A changed clsid means every F-4E fit carrying the gun pod falls through to a
fallback loadout. This is the F-14A-135-GR-Early failure mode (upstream #889): the
jet flies, it just does not carry what the file says.

**Check:** grep both payload Lua files for the SUU-23 clsid and compare against the
export.

## 3. AH-64D DTC — the largest new opportunity (§74)

DCS added a full Apache DTC. Its partitions map onto data §74 already computes:

| DCS partition | What we already build |
|---|---|
| WPTHZ 01-50, CTRLM 51-99, 10 Routes | `DtcOptions.route` — steerpoints + route sequence |
| TGT/THRT 01-50 | `DtcOptions.threat_rings` — recon-fogged SAM rings |
| 15 LINES, 12 AREAS, 8 PFZ / 8 NFZ | `DtcOptions.flot_and_zones` — the front line |
| RADIOS, 10 COM presets | `DtcOptions.comms` — the radio allocator's channels |
| 10 ADF presets | CSAR pins a 260 kHz survivor beacon (checklist G33) |

Also in the partition set and **not** currently computed anywhere: laser
settings/codes, ASE settings and chaff/flare programs, the RLWR threat table, PERF
data, and 10 MPS text messages.

`game/missiongenerator/dtc/` holds `viper.py`, `hornet.py` and `tomcat.py` behind a
shared `common.py` and one `generator.py`. An `apache.py` is a fourth sibling on a
settled pattern, and the module gained a DMS DTU sub-page plus TSD LINES/AREAS
pages to read the upload back — so the result is observable in the cockpit.

The Apache is an Iron Gate and COIN airframe, so it earns its place in those
campaigns rather than being a demo.

**Not scoped here.** Nobody has confirmed the cartridge's on-disk shape. §74's
existing three were reverse-engineered from a hand-built MP mission and are locked
against the ME's own DTC editor schemas in `tests/missiongenerator/test_dtc.py`;
the Apache needs the same treatment before a line of it is written.

## 4. Two smaller §74 items

- **F-16C gained COLR and MPD ROE partitions.** Not cosmetic: the patch says air
  track sovereignty (Friendly / Unknown / Suspect / Hostile) "now relies on DTC ROE
  tab settings", and that ROE factors apply to onboard FCR tracks and offboard
  datalink tracks alike. A Viper we generate without an ROE tab may declare tracks
  differently than it did yesterday. Read `game/missiongenerator/dtc/viper.py`
  against it.
- **"F-16 DTC Multiple in multiplayer loads only first DTC" is fixed.** The §74
  checklist row's open question is whether `AutoLoad` fires on the two §64 spawn
  paths (uncontrolled carrier client, late-activated delayed flight). This fix is
  adjacent to that and may close part of it for free. Do not mark the row on the
  strength of a patch note — fly it.
- **F/A-18C DTC HARM TOO default moved PRI → ALL.** `hornet.py` writes no HARM
  partition, so there is nothing to reconcile. Recorded so the next reader does not
  re-check it.

## 5. Behaviour shifts with no code owed

### 5.1 The airfield taxi and parking rework

ED rebuilt AI taxiway pathing to use aircraft dimensions, and states the change
alters parking placement and increases the number of slots for large aircraft.

Three of ours sit on that surface:

- `game/missiongenerator/aircraft/flightgroupspawner.py:277` and `:316` classify
  "large" as `dcs_unit_type.width > 40`, then fall back through
  `ground_spawns_large`. The threshold is ours; the slot supply underneath it is
  DCS's, and it just moved.
- **B96** (Iron Gate's fields fill without an aircraft losing its stand) is ◐
  PARTIAL and is a stand-count row.
- Iron Gate and Northern Russia both had every squadron's `size:` hand-fitted to
  its base's stand count within the last month. If slot counts changed, those
  numbers are stale in both directions — oversubscription starves the bottom of the
  list silently, and undersubscription just wastes ramp.

The hard constraint stands unchanged: **never restore the per-base backstop EWR**
(§1). It was removed because a ground unit sat on taxiways and broke AI taxi
routing, and the routing code is what just changed. A rework is not evidence the
constraint lapsed.

### 5.2 Legacy SAM belts got more dangerous at low level

- SA-2 (V755) and SA-3 (5V27) gained "the missing K-method of guidance (Half-lead,
  elevated by constant) **for low-level targets**".
- SA-8 (9M33 Osa) moved to a new CFD-derived FM with real motor data and CLOS
  guidance enabled.
- Patriot MIM-104 DLZ corrected against ballistic targets.

Nothing on our side changes — threat rings come from pydcs sensor data, and
guidance method is not in it. But low ingress against a legacy MERAD screen is the
Red Tide, Desert Storm and Vietnam profile, and it is now a different proposition.
Worth telling the squadron before they fly it, not after.

### 5.3 Red SEAD got worse

Kh-25MP had a guidance error added — the note says it plainly, "this missile was
too accurate" — plus a corrected loft shape and a 1 s control delay. Red Weasel
Fitters and Fencers will miss more.

Blue's AGM-45 was reworked from scratch: slightly worse ballistics, substantially
lower steering losses, a wider A/B split. Roughly a wash.

### 5.4 AI air combat

- Radar shots now fly an attack curve to the intercept point; IR shots fly a pure
  pursuit curve.
- The crank is restricted to head-on engagements inside ±60 degrees of the enemy
  axis; otherwise the fighter keeps closing.

§1's QRA reserve feeds the MOOSE `AI_A2A_DISPATCHER`, so red intercepts will play
differently. No change owed; expect different outcomes and do not read them as a
§1 regression.

### 5.5 The AI waypoint fix

"In some cases the AI group does not follow pre-planned waypoint altitude and
speed" is fixed. That is the engine half of what upstream #920 and #925 are about,
and of checklist rows **B79** (ground-level waypoints read the field's elevation)
and **B85** (a flight with an unreachable TOT flies instead of orbiting). Re-run
both after the update; the fix may move them without any work here.

### 5.6 F-16C jammer burnthrough ranges fixed

§77 escort jamming and §2's C-130J both model jamming script-side — spoof bubbles
and ROE weapons-hold pulses — so there is no collision with the engine's burnthrough
math. But **B31** and **B52** are both ◐ PARTIAL jamming rows, and what burnthrough
looks like from the cockpit has changed. Note it on the fly card rather than
re-verifying blind.

## 6. Smaller opportunities

### 6.1 Native trailers (§85)

ED added trailer ATZ-60 for the MAZ-7410, and trailers TZ-22 and **S-75** for the
KrAZ-258B1 and ZIL-131. The S-75 trailer is the SA-2 missile transporter.

§85 already dresses SAM batteries with refuellers and power in the faction's own
kit. A period-correct transloader for every SA-2 site we place is the obvious
extension.

**Gate before promising it:** the patch says "In ME, use the task to attach/detach a
trailer". That is a *task*, not a static or a separate unit. Confirm pydcs can
express it from the generator at all — if it cannot, this is a nice idea with no
route to the miz.

### 6.2 The "Cadet" AI skill

`game/settings/skilloption.py:21` hardcodes
`["Average", "Good", "High", "Excellent"]`. Adding "Cadet" is one line there once
pydcs exposes the enum value, plus a slot in `difficultypreset.py` (the Easy preset
currently uses `Average` for both `enemy_skill` and `enemy_vehicle_skill`).

Clean, self-contained, and an obvious upstream carve. **It answers no open upstream
issue**, so the freeze binds it — the 2026-08-20 issue-ledger exception does not
cover it, and the 2026-08-25 §69 precedent says put it to the DM as a call rather
than infer.

### 6.3 F-14 TARPS

The module reworked TARPS: photos are visible only after the flight ends, a KA-99
panoramic camera was added, and an "intel analysis department" auto-circles units
found in the imagery and writes descriptions.

The landing-gate matches §3's own shape — our recon cue is held until touchdown for
the same reason. That is a convergence, not a conflict.

**The seam worth a call:** DCS's own TARPS now delivers real identification
imagery, while §3's rule is that engaging a site is the only thing that reveals it
and recon reveals nothing except a hidden command post within 3 NM. We also just
rewrote every Threat Intel kneeboard row from "Fly TARPS to ID" to "Engage to ID".
A pilot who flies a TARPS pass will now get pictures with circles on them that the
campaign refuses to act on.

This is a design question, not a defect. Do not resolve it in code — §3's rework is
recent, deliberate, and cost eight doc files to land.

## 7. Nothing owed

Checked and clear, recorded so they are not re-checked:

- **Disembark-from-start crash fix** — we set it nowhere. The only tree hit is a
  comment in `resources/plugins/opscsar/OpsCSAR.lua:633`.
- **Removed CA missile player control** for Pantsir-S1, Tor M2 and Project 22160's
  Tor M2KM. We field `CHAP_PantsirS1`, `CHAP_TorM2` and `CHAP_Project22160`, but
  only Combined Arms is affected; the generator never gave a player those seats.
- **F-100D added to the Quick Action Generator** — unrelated to our `f100`
  extension.
- MB-339 AIM-9B, JF-17 airspace drawing, NS430 radio, the P-47D campaign, the new
  "Start Here" menu.

## 8. Rows to re-run after the update

Existing checklist rows this patch touches, none of them rewritten here:

| Row | Why this patch touches it |
|---|---|
| B79, B85 | The AI pre-planned waypoint altitude/speed fix (§5.5) |
| B96 | Stand counts after the parking rework (§5.1) |
| B17 | §64 carrier spawn policy — dynamic spawn parking/FARP improvements |
| B31, B52 | Jammer burnthrough changed in the cockpit (§5.6) |
| G19, G40 | TARPS behaviour and imagery changed under §3 (§6.3) |

New rows added by this triage: **B100**, **B101**, **B102** — see
[414th-ingame-pass-checklist.md](../414th-ingame-pass-checklist.md).
