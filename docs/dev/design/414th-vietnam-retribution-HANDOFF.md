# 414th — "Vietnam Retribution" mode — HANDOFF (start here)

**Status:** design landed, **no implementation yet**.
**Read first:** [`414th-vietnam-retribution-notes.md`](414th-vietnam-retribution-notes.md) — the
full design (architecture, tasking map, save-compat, phased plan, integration-point index).
This file is just the next-agent pickup.

---

## What's decided (don't relitigate)

- **Taskings:** doctrine-gated + rename. **One `FlightType` enum.** Renames are a
  display-override layer — **never edit the persisted enum values.**
- **Entry point:** a dedicated "Vietnam" card on the New Game screen that pre-seeds a profile
  + filters the pickers, reusing the existing metadata-driven wizard. **Not** a parallel wizard.
- **Fork identity** (like the Iran pack / Red Tide). **Do not** carve any of this upstream.

## What exists already (verified 2026-06-28)

- Factions, **3** campaigns (`1968_Yankee_Station`, `khe_sanh_niagara`,
  `operation_velvet_thunder`), and ~18 era mod packs in `pydcs_extensions/`. See the design
  note §2 for the exact list.
- `Doctrine` (`game/data/doctrine.py`) already carries `cas/cap/sead/strike/antiship` flags +
  planning geometry, with `MODERN/COLDWAR/WWII` instances. Vietnam factions declare
  `"doctrine": "coldwar"` today.

## First moves (phased — each is independently shippable + CI-gated)

- **P0 — content tags.** Tag the 3 Vietnam campaigns + Vietnam factions (e.g. `era: vietnam`);
  confirm the existing `tests/` Vietnam content gate still passes.
- **P1 — doctrine profile (the cheap 70%).**
  1. Add `VIETNAM_DOCTRINE` in `game/data/doctrine.py`; register in `ALL_DOCTRINES`.
     `Doctrine` is `@dataclass(frozen=True)` → **new fields need defaults** (tasking whitelist,
     display-name override map) so MODERN/COLDWAR/WWII stay valid.
  2. Add a `"vietnam"` case in `game/factions/faction.py` (~line 358 load, ~431 serialize);
     repoint the Vietnam factions from `"coldwar"` to `"vietnam"`.
  3. Wire the display-override read path in UI + kneeboard (fall back to `FlightType.value`).
  4. Gate the planner at the task edge in `game/commander/tasks/` (same place
     `Doctrine.sead`/`.antiship` are already consulted) — disallowed tasks just never get
     proposed. Drop `DEAD`/`ANTISHIP` from the Vietnam whitelist.
- **P2 — era preset + shell.** Mirror `game/settings/difficultypreset.py` for a Vietnam era
  bundle; add the New Game "Vietnam" card + list filtering (`qt_ui/windows/newgame/`).
- **P3 — behavior taskings.** Alpha Strike sizing; Iron Hand = Shrike-vs-live-emitter.
- **P4 (optional flavor).** FAC(A), Arc Light, branding.

## Gotchas

- **`FlightType` values are persisted in the ATO** — renames are display-only; a true retire
  goes through `_LEGACY_FLIGHT_TYPE_VALUES` (`game/ato/flighttype.py`).
- **`Doctrine` is frozen** — additive fields only, with defaults.
- **Any new game-level mode/era flag** needs a `__setstate__` default so old saves load.
- **Adding a tasking-behavior change (P3+)** → add a row to
  `docs/dev/414th-ingame-pass-checklist.md` (CI can't exercise runtime AI behavior).
- Reuse the existing `coldwarassets` mod-on plumbing (`faction.py` ~line 730) for the preset.

## Open decision (note §8, not blocking P0/P1)

Under Vietnam doctrine, should the manual "create flight" task list in the UI also be filtered
to the era whitelist, or stay full (planner-gated only)? **Lean: filter it with a "show all"
escape hatch.** Confirm with the maintainer at P2.

## Docs to update when implementation lands

Per CLAUDE.md docs-hygiene: design note → `docs/dev/414th-features.md` (new §) → `README.md`
(player-facing) → register in `game/fourteenth/features.py` → checklist row → CLAUDE.md feature
list → sync `AGENTS.md`.
