# campaign(germany): Germany - Red Tide — a Red Storm Rising 1988 NATO counteroffensive

## What

A new bundled campaign for the Cold War Germany map, plus the small content set it needs:

- **`resources/campaigns/red_tide.yaml` + `red_tide.miz`** — *Germany - Red Tide*, 13 July
  1988: a Warsaw Pact invasion has **culminated** — Hamburg fallen, Copenhagen seized, the
  Soviet spearhead overextended and not yet dug in — and the player leads the NATO
  counteroffensive to take it all back. Inspired by Tom Clancy's *Red Storm Rising*.
  - **Asymmetric-by-design start:** red holds the north, centre, and east (including a
    captured Hamburg airhead and a Backfire base at Copenhagen/Kastrup); blue's Rhineland
    cluster (Ramstein/Spangdahlem/Hahn/Frankfurt + a forward Fulda FARP) is the springboard.
    Blue-offensive economy skew and two recommended planner settings
    (`ownfor_autoplanner_aggressiveness: 10`, `oca_target_autoplanner_min_aircraft_count: 40`)
    keep the AI cautious so the human's sorties carry the push.
  - **Full route network:** 12 land supply routes as M-113 front-line path groups (front
    forms on the Fulda↔Haina axis) and a Kastrup→Peenemünde **Baltic shipping lane**
    (HandyWind), all road/sea-realistic.
  - **`advanced_iads` ready:** red SAM bases carry co-located command/comms/power statics for
    Skynet's range mode.
  - Every squadron is a **named historical unit** (USAF/USN/USMC/GAF squadrons, Soviet
    regiments) with era-right airframes; the F-4E note in the description flags the Heatblur
    module tie-in.
- **`resources/factions/russia_1988.json`** (new) — `russia_1980` + the stock `SA-11` and
  `SA-10/S-300PS` presets (in service 1980/1982). Gives the campaign its premised deep SAM
  belt without altering a stock faction, and fills the 1980→1990 faction gap generally.
- **`resources/factions/blufor_late_coldwar.json`** — one added line: `KC-135 Stratotanker
  MPRS` (the campaign frags a drogue tanker for its Navy jets).
- **44 new squadron defs** — the historical units above that didn't exist yet (the campaign
  also reuses existing defs: `GAF JG 74`, `336th Fighter Squadron`, `23rd FS`, `VMFA-251`,
  `HMLA-269 (UH-1H)`, `185th GvIAP Fighter Regiment`, …).

## Why

A ready-to-fly, scenario-driven Cold War Germany campaign with a strong fictional premise and
a fully-authored order of battle. It has been the origin squadron's most-flown GermanyCW
scenario; this contributes it back as stock content.

## Testing

- Campaign loads and generates headless against dev: both factions resolve, all squadrons
  fill (no dropped-squadron log lines), the single front forms on the Fulda↔Haina axis, the
  Baltic shipping lane and red naval objectives appear, Skynet wires the per-base C2 cells.
- Content-only change: no engine code touched.

*(Authored by Starfire & the 414th JFG; carved from the 414th's Retribution fork.)*
