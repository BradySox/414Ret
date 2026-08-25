# Upstream #896 — replacement PR body

Paste-ready description for [dcs-retribution#896](https://github.com/dcs-retribution/dcs-retribution/pull/896).
The published body still describes the code that was deleted on 2026-07-31, so a reviewer
opening the PR today reads an advertisement for the exact thing Druss99 requested changes over.

Updating an existing PR is allowed under the freeze, so this is not freeze-held. Only the
description changes; no commit is needed.

## Why it needs replacing

Verified against PR head `554c0a3` (2026-08-22, `Merge branch 'dev' into squadron-country-surfacing`),
fetched from `refs/pull/896/head`.

| Published body claims | Head actually does |
|---|---|
| §2 "The list is trimmed to the airframe's operators (`game/dcs/operatorcountries.py`)" plus the four-step curated → pydcs-roster → sibling → full chain | `game/dcs/operatorcountries.py` does not exist. `SquadronCountrySelector` builds from `country_dict.values()` and its docstring says "the full DCS country list" |
| §1 "Unknown country names log and degrade to the unpinned behavior (never abort New Game)" | `resolve_config_country` raises `ValueError`; `test_resolve_config_country` asserts `pytest.raises(ValueError)` |
| Not included: "the operator-list resolution by `tests/dcs/test_operator_countries.py` (6)" | That file does not exist |
| Not included: `test_squadron_country_pin.py` (9 tests) | 12 tests |
| Validation: "453 passed / 2 skipped on dev @ `3760cf2a`" | Opening-day number from 2026-07-20; head has merged dev through 2026-08-22 |
| "Draft until we've flown the fork's in-app pass" | The fork's I6 pass flew 2026-07-20 |

## Fork/carve convergence, checked 2026-08-25

The country half of the feature is the same code on both sides. Fork `main` and PR head carry an
identical `resolve_config_country` and an identical selector docstring, and both pin suites hold 12
tests. Fork-only, correctly: `tests/test_airwing_country_selector.py` (5 offscreen-Qt tests), the
campaign `country:` pins, and the QRA/CSAR couplings in `defaultsquadronassigner.py`. The carve keeps
its pin tests at `tests/campaignloader/test_squadron_country_pin.py`; the fork keeps them flat at
`tests/test_squadron_country_pin.py`.

Branch `claude/pr-896-review-8kg5xf` no longer exists on the fork remote — that work is on `main`.

## Before pasting

Run upstream's gates on the PR branch and fill the Validation line with the real numbers. Do not
carry a count forward from this file; a stale count is what this refresh exists to fix.

---

```markdown
## What

Answers the Discord discussion about #854/#627: how do you choose a squadron's nation? The country
lives only in preset yamls, so an airframe-name squadron config under a CJTF faction picks its preset
by `random.choice` across every nation's presets — a USAF-named F-16 squadron can roll an Israeli
preset and fly the campaign with the wrong DCS voice and pilot names. The only fix today is
hand-authoring a preset yaml.

This PR surfaces the nation in both authoring layers.

1. **Campaign yaml `country:`** — a squadron config can pin its nation (`country: USA`). The pick then
   accepts only same-nation presets, falls through to the squadron-def generator when no same-nation
   preset exists, and `override_squadron_defaults` stamps the pinned country either way: a preset
   squadron for that nation if one exists, otherwise a generated squadron set to that country. An
   unknown `country:` name raises, so New Game aborts and names the bad value instead of silently
   flying under the wrong nation. Configs without the field are byte-identical to today.
2. **Air Wing Configuration dialog "Country:" selector** — under Livery. Opens on the squadron's
   current nation and writes `squadron.country` live, following the livery-selector pattern. The list
   is the full DCS country list, plus the squadron's current country when pydcs does not list it (a
   mod nation). Pilot names follow automatically: the wizard shows the dialog before
   `populate_for_turn_0` recruits the roster, and `Squadron.faker` (#854) reads the country live, so a
   mid-campaign change affects newly recruited pilots.
3. **Preset dropdowns show each preset's nation** (`VF-103 (Sluggers) [USA]`). Under a CJTF the
   presets span many countries and the country decides the comms voice.
4. **Save Config / Load Config round-trips the country** — `_build_air_wing` exports `country:`, so
   reloading an air wing no longer rerolls each squadron's nation. This records a `country:` for every
   squadron in the saved config.

**Bugfix in passing:** after "Replace with preset" the livery selector kept writing to the discarded
squadron object — `bind_data` re-bound the combo but never re-pointed `livery_selector.squadron`.
`bind_data` now re-points it. The country selector's `set_squadron` avoids the same trap.

## Changed on review

- **Operator-country trim removed** (Druss99, 31 Jul — "a massive burden when adding a new aircraft
  module"). `game/dcs/operatorcountries.py`, the curated operator tables and the operator-derived CJTF
  default are gone. An unpinned squadron under a CJTF keeps the picked def's own country: stock
  behavior, untouched by this PR.
- **Selector lists every DCS country again**, with no operator filtering.
- **An unknown `country:` raises** instead of degrading silently.

What is left is the yaml pin, the dialog selector, the preset-nation labels and the Save/Load
round-trip. No default behavior changes.

## Not included

- No shipped campaign uses `country:` yet. Behavior changes only when an author pins a nation or a
  player uses the selector.
- No Qt test — there is no `qt_ui` test precedent upstream. The pick and override semantics are
  covered by `tests/campaignloader/test_squadron_country_pin.py` (12 tests). Our fork additionally
  carries an offscreen-Qt selector test.

## Validation

- `black --check .`, `mypy game tests` and `pytest tests` on the branch. <!-- fill in the run's counts -->

---
_Generated by [Claude Code](https://claude.ai/code)_
```
