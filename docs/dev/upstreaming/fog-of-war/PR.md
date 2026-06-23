# Upstream PR kit — Recon fog-of-war

> ## ✅ Status: fully carved & verified (2026-06-23)
> The carve is **done** — not just a manifest. `fog-of-war-complete.patch` is a
> single-commit, `git am`-ready patch built against and verified on a clean
> upstream `dev` (`a31357b`):
> - `git apply --check` clean on a pristine `dev` checkout
> - `black --check game qt_ui tests` clean
> - `mypy game tests` clean (439 files)
> - `pytest` green: 9 fog tests (intel-fog gate/setting/migration, reveal-on-engage,
>   `/fog-of-war/reveal` route)
>
> **To land it from your PC** (where you have push creds):
> ```
> cd ..\retribution-pr            # a clean dcs-retribution/dev checkout
> git checkout -b feature/recon-fog-of-war
> git am path\to\fog-of-war-complete.patch
> cd client && npm install && npm test    # client wasn't runnable in the carve env
> # push to bradyccox/dcs-retribution and open the PR against dcs-retribution/dev
> ```
> The other files here are the working notes: `CARVE-MANIFEST.md` (the generic-vs-SCAR
> -vs-PR#2 reasoning) and `0001-fog-of-war-new-files.patch` (just the new files —
> superseded by the complete patch). Use the title/body below for the PR.

Target: `dcs-retribution/dcs-retribution` `dev`. Carve from the 414th fork
(`bradyccox/414Ret`). This is **PR #1 of a 2-PR stack**:

- **PR #1 (this kit): recon intel-fog + overview reveal toggle.** Self-contained,
  aircraft-agnostic, no fork features required. Hides enemy *site composition +
  threat/detection rings* until a site is engaged, with a runtime "reveal" switch.
- **PR #2 (stacked, separate kit): TARPS recon platform + BDA damage-lag.** Adds the
  player recon flight that *confirms* kills, plus the `alive_for` /
  `alive_at_last_recon` damage-lag layer it drives. Deferred because TARPS is a large,
  F-14-flavored feature in its own right and the damage-lag half is only meaningful
  once a recon platform exists to do the confirming. See
  [`CARVE-MANIFEST.md`](CARVE-MANIFEST.md) §"Deferred to PR #2".

> Why split here: the **intel-fog** half (hide composition until attacked/scouted)
> works with a generic reveal-on-attack trigger and needs nothing fork-specific. The
> **damage-lag** half (struck enemy units keep showing alive until recon confirms the
> kill) only does something if a recon sortie confirms — in the fork that's TARPS/TARS.
> Strip those and `sync_confirmed_status` only ever fires for friendly TGOs, so enemy
> kills would never confirm. That half belongs with the recon platform that activates it.

---

## PR #1 — title

> Recon fog-of-war: hide enemy site composition until scouted, with an overview toggle

## PR #1 — body

### What

Adds an opt-in **recon intel-fog** to the human player's map. With it on (campaign
setting, default can be your call — the fork ships it ON for new campaigns), a newly
seen enemy ground site appears as a **targetable marker** (position, category,
allegiance) but its **actual composition and threat/detection rings stay hidden**
until the site is **attacked, scouted, or has a unit destroyed**. Once discovered, it
stays discovered (sticky, per-site, enemy-only).

A companion **"Reveal fog of war" overview toggle** — a transient, never-persisted
runtime switch — forces every player-facing fog accessor back to ground truth, so a
host can flip the whole map to the real picture for briefing/debrief without altering
any saved state.

The **AI planner and threat math are never fogged**: they pass `viewer=None`
(omniscient) everywhere, so auto-planning, threat zones used for routing, and
opponent reasoning all use full truth. The fog is purely a human-UI presentation
layer.

### Why

Today the player sees every enemy site's exact composition and SAM rings the instant
the campaign generates them, which removes any reason to scout and makes recon
flights pointless. This gates that knowledge behind contact, so the map reflects what
you've actually found.

### How (design)

- One **viewer-aware leaf** — `TheaterGroundObject.known_for(viewer)` — is the single
  source of truth for "does this viewer know what's actually here". `viewer=None`
  (AI/planner/threat) and friendly viewers always return `True`; an enemy viewer
  returns the sticky `discovered_by_player` flag, gated by the `recon_intel_fog`
  setting.
- Consumers **gate at the edge**: the map's TGO payload, IADS connections, and the
  enemy threat-zone builder all call `known_for(BLUE)` and emit a fogged
  (empty-rings, hidden-units) result when it is false; the Qt ground-object/building
  dialogs show "Not yet scouted — composition unknown".
- **Discovery** is flipped in the mission-results processor: any enemy site that was
  struck (a unit destroyed) or overflown by a surviving offensive sortie this turn is
  marked `discovered_by_player = True`.
- The **overview toggle** is a process-global `bool` in a new dependency-free
  `game/theater/fogofwar.py` (`fog_revealed()` / `set_fog_revealed()`), flipped via a
  new `PUT /fog-of-war/reveal` endpoint. `known_for` short-circuits to `True` when it
  is set, so the entire fogged render path un-fogs at once with no model changes. It
  is **never pickled** — a save can't carry a god-view.
- **Save migration**: a campaign saved before this feature has every site already on
  the map, so `TheaterGroundObject.__setstate__` defaults missing
  `discovered_by_player` to `True` (in-progress campaigns stay fully revealed; the fog
  is felt on new campaigns).

### Files

New:
- `game/theater/fogofwar.py` — the transient overview flag.
- `game/server/fogofwar/{__init__,routes}.py` — the `/fog-of-war/reveal` endpoint.

Changed:
- `game/theater/theatergroundobject.py` — `known_for`, `discovered_by_player`,
  `__setstate__` migration.
- `game/settings/settings.py` — the `recon_intel_fog` campaign setting.
- `game/threatzones.py` — `for_faction` filters air defenses by `known_for(viewer)`.
- `game/server/tgos/models.py` — `TgoJs.for_tgo` fogs composition/rings when unknown.
- `game/server/iadsnetwork/models.py` — hide IADS connections to/from unknown sites.
- `game/server/app.py` — register the router.
- `game/sim/missionresultsprocessor.py` — `reveal_discovered_sites` +
  `attacked_tgos_this_turn` (reveal-on-engage).
- `qt_ui/windows/groundobject/{QGroundObjectMenu,QBuildingInfo}.py` — viewer-aware
  dialogs.
- Client: a "Reveal fog of war" checkbox that `PUT`s the endpoint and re-pulls
  `/game`. (Wire into whatever layer control upstream uses; the fork's custom panel
  is not part of this PR — see manifest.)

### Tests

- `tests/test_recon_intel_fog.py` — discovery gate, setting off, default-on,
  save migration.
- `tests/server/test_fogofwar_route.py` — the reveal endpoint flips the shared flag.

### Notes for the maintainer

- **Setting default**: the fork defaults `recon_intel_fog` ON for new campaigns. Pick
  whatever default you prefer; behavior with it OFF is identical to today.
- **Reveal trigger is deliberately generic** (struck or overflown by a surviving
  STRIKE/DEAD/SEAD/anti-ship flight). Confirm those `FlightType` member names against
  current upstream before merging.
- **The damage-lag half is intentionally not here.** Without it, the fog reveals
  composition on contact but does not lag *kills*; that's the clean separable line and
  the rest follows in PR #2 with the recon platform.
- **Client integration is the one non-portable bit** — the checkbox + `useEffect` is
  tiny, but it has to land in upstream's actual map-layer control, not the fork's
  custom panel. The Python endpoint is fully self-contained and tested.
