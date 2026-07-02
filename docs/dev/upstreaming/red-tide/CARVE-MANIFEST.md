# Red Tide — upstream publication carve

Publishes **Germany - Red Tide** (the 414th's *Red Storm Rising* 1988 NATO-counteroffensive
campaign on the GermanyCW map) as a public Retribution campaign, via
`bradyccox/dcs-retribution` → `dcs-retribution/dcs-retribution` (`dev`).

**Everything upstream needs is in `payload/`** — copy it over a checkout of the PR fork,
validate (step 3), open the PR with `PR.md` as the body. The payload is **generated** by
`build_payload.py` (run from anywhere; paths are repo-relative) — edit the builder and re-run
rather than hand-editing payload files.

## What the payload contains

| File | What / why |
|---|---|
| `resources/campaigns/red_tide.yaml` | The campaign. Differences from the fork's copy: **(1)** the fork-only YAML `supply_routes:`/`shipping_lanes:` blocks are removed (upstream reads routes from miz groups — see the miz row); **(2)** the four 414th-identity squadron names are swapped for squadron defs that already exist upstream (`414th Voodoo Squadron`→`23rd FS`, `414th JFG Hornets`→`VMFA-251`, `414th Tactical Fighter Squadron`→`336th Fighter Squadron`, `414th Aviation Detachment`→`HMLA-269 (UH-1H)`), and the one description line naming the 414th is neutralized; **(3)** `aircraft_type: C-130J-30` (a fork/mod consolidation) → vanilla `C-130`; **(4)** `recommended_enemy_faction: Russia 1980` → `Russia 1988` (below). |
| `resources/campaigns/red_tide.miz` | The fork miz **plus the 12 land supply routes baked back as blue M-113 front-line path groups and the Baltic shipping lane as a blue HandyWind group** — upstream's native route mechanism (the fork had migrated these to YAML). Pure text surgery on the mission Lua: group/unit ids allocated past the existing max, brace balance asserted, `warehouses`/`options`/`theatre` byte-identical to the fork's shipped miz. The miz is marker-only vanilla units (Skynet-compatible statics for `advanced_iads` included). |
| `resources/factions/russia_1988.json` | **New faction**: upstream `russia_1980` verbatim + the stock `SA-11` and `SA-10/S-300PS` preset groups (in service 1980/1982 — era-honest for the campaign's 1988 date). Gives the campaign its premised deep LORAD belt without touching a stock faction, and fills the russia_1980→russia_1990 gap generally. |
| `resources/factions/blufor_late_coldwar.json` | Upstream copy + **one added line**: `KC-135 Stratotanker MPRS` in `tankers` (the campaign frags a drogue tanker for its F-14B/F/A-18C/A-6E). Diff against current dev before committing — if upstream has since added MPRS, drop this file. |
| `resources/squadrons/**` (44 files) | The fork-only squadron defs the campaign references — all real, historically-named units (USAF/USN/USMC/GAF squadrons; Soviet regiments). The `mission_types:` key in some defs is a fork extension upstream ignores (its loader reads only known keys). Defs whose names already resolve upstream (`GAF JG 74`, `185th GvIAP Fighter Regiment`, `VA-34 Blue Blasters`-style variants, the four swap targets) are **not** duplicated. |

## What was deliberately left fork-side

- The 414th identity (squadron names, the description credit) — replaced as above; the fork
  keeps its own branded copy unchanged.
- The fork's YAML supply-route mechanism, MANTIS, and every other 414th engine feature — the
  payload targets stock upstream `dev` and depends on none of them.
- The Red Tide wiki briefing pack (fork docs).

## Validation status

- Built and asserted against **upstream dev @ `dce851ea`** (this fork's base, via git): both
  factions exist there with the names used; every red squadron aircraft type is already in
  `russia_1980`; every blue type is in `blufor_late_coldwar` (after the MPRS line); the four
  swap-target squadron defs exist with the exact names referenced; the payload yaml parses;
  the payload miz is brace-balanced with all 12 routes + 1 lane present and warehouses
  untouched.
- **NOT yet validated against *current* upstream dev** — this sandbox can only see the fork.
  Before opening the PR (on the Windows box):

## Steps to open the PR

1. `git -C <dcs-retribution PR fork> fetch upstream && git checkout -b red-tide upstream/dev`
2. Copy `payload/*` over the checkout (`cp -r payload/resources <checkout>/`).
3. Validate against current dev:
   - `python -m pytest tests -q` (upstream suite),
   - a headless campaign load / New Game generation of Red Tide (the fork's usual
     upstream-validation harness), checking: both factions resolve, all squadrons fill
     (no "silently dropped squadron" log lines), the front forms Fulda↔Haina, the
     Kastrup→Peenemünde shipping lane appears, Skynet builds the per-base C2 cells.
   - Re-diff `blufor_late_coldwar.json`/`russia_1980`-derived content against current dev
     (upstream may have moved since `dce851ea`); reconcile rather than clobber.
4. Commit (suggested: `campaign(germany): add Germany - Red Tide -- a Red Storm Rising 1988
   NATO counteroffensive`), push, open the PR against `dcs-retribution/dcs-retribution`
   `dev` with `PR.md` as the body.
5. Coordinate zones: none of the crowded upstream areas (planning/QRA/frontline/SEAD/
   kneeboard/ATC) are touched — this is pure content (campaign + factions + squadron defs).

## Gotchas recorded during the carve

- Upstream's loader **silently drops** a squadron whose `aircraft:` preset name doesn't
  resolve — that's why every referenced def must exist (the fork hit this with
  `0038 43d Strategic Wing 0038`). The validation step's log check is the guard.
- `squadron_start_full:` in the campaign `settings:` block appears to be a dead key in both
  trees (settings are applied via a blind dict update; nothing reads that name). Kept for
  consistency with upstream's own campaigns that carry it — do not rely on it.
- Factories quirk does not apply here (no factory markers were added); the miz's objective
  markers are unchanged from the fork build documented in
  `docs/dev/design/414th-red-tide-campaign-notes.md`.
