# Custom Factions

A faction is the roster a side draws from — its aircraft, ground units, air defenses,
ships, support assets, and the doctrine and liveries that go with them. This page covers
the faction file format, how to add units, how date gating works, and the fork's
`[CH] Iran 2020` faction backed by the CurrentHill Iran assets pack.

## Where faction files live

Factions are JSON files in `resources/factions/` (you can also place overrides in your
DCS Saved Games directory). The name string inside the file is what the new-game wizard
and a campaign's `recommended_*_faction` fields reference, so it must match exactly.

## File format

A faction is a JSON object. The core fields:

| Field | Meaning |
|---|---|
| `country` | A valid DCS country name. Determines mission generation and which liveries are available. |
| `name` | Display name shown in Retribution (e.g. `[CH] Iran 2020`). |
| `authors`, `description` | Credit and a short HTML blurb. |
| `locales` | Pilot-name generation locale(s), e.g. `["fa_IR"]`. |
| `doctrine` | `modern`, `coldwar`, or `ww2` — affects flight-planning parameters. |

Units are grouped into category lists:

| List | Holds |
|---|---|
| `aircrafts` | Combat aircraft roster (each entry is a unit-type name). |
| `awacs`, `tankers` | Support aircraft. |
| `frontline_units`, `artillery_units`, `infantry_units` | Ground combat forces. |
| `air_defense_units` (and SAM preset groups) | SAMs, AAA, EWR. |
| `naval_units` | Ships and carriers. |
| `logistics_units` | Supply and transport vehicles. |

Optional extras include JTAC settings (`has_jtac` / `jtac_unit`), carrier name lists,
building-set selection, and per-aircraft livery assignments. A livery only renders if it
is available to the faction's `country`.

Every field has a default, so a minimal faction file is short — but a faction needs a
spread of unit categories for the auto-purchaser to plan sensibly. The shipped faction
files in `resources/factions/` are the best worked examples.

## Adding units and aircraft

Add the unit-type name string to the matching category list. The name must be a unit type
Retribution knows about — a vanilla DCS unit, or a mod unit registered through
`pydcs_extensions/` (see the Iran pack below). Complex air-defense formations are pulled
from named **preset groups** rather than listed unit-by-unit; reference the preset name in
the faction.

To make a unit fly with a specific squadron name and livery, define a predefined squadron
under `resources/squadrons/<type>/<unit>.yaml` and reference it by name from the campaign
(see [Custom Campaigns](Custom-Campaigns)) — the faction supplies the airframe, the
squadron def supplies the identity. A squadron def only loads if the faction is
`any_country` (like `Combined Joint Task Forces Blue`) or the def's `country` matches the
faction's `country`.

## Date gating

Retribution knows each unit and weapon's introduction year. A campaign's
`recommended_start_date` (and the wizard's date picker) filters out anything not yet in
service: a 1988 campaign won't auto-purchase or spawn a unit introduced in 2015. So you
can list modern variants in a faction and rely on the campaign date to restrict what
actually appears. The fork extends this to weapon coverage — modern munitions are
date-gated the same way (see `docs/dev/design/414th-weapon-dates-proposal.md`) — and to
era-defining **payload-editor properties**: with `restrict_weapons_by_date` on, the **JHMCS**
helmet sight (fielded ~2003) is hidden from the dropdown and clamped to the baseline visor when
generating a pre-2003 mission. A faction can also nudge specific weapons with
`weapons_introduction_year_overrides` (e.g. the NVA's MiG-17 missiles pushed past the era so the
Fresco stays guns-only).

## The `[CH] Iran 2020` faction and CurrentHill Iran pack

The fork adds a dedicated `[CH] Iran 2020` faction (`resources/factions/CH_iran_2020.json`,
country `Iran`, locale `fa_IR`) representing Iran in the 2020s. It pairs with the
**CurrentHill Iran assets pack**, which registers extra mod units:

- `CH_Shahed136` — Shahed-136 one-way attack drone
- `IranFAC_MG`, `IranFAC_MG_AShM` — IRGCN fast attack craft

These are defined in `pydcs_extensions/iranmilitaryassetspack/` and re-exported from
`pydcs_extensions/__init__.py`, with radar data in `game/data/radar_db.py`.

Because the pack is a mod, it is gated behind a **new-game mod toggle**
(`iranmilitaryassetspack`, in `game/theater/start_generator.py` and the new-game wizard
pages). When the toggle is off, the mod-only units are stripped from the faction by the
removal logic in `game/factions/faction.py`, so the faction still loads without the mod
installed. Enable the toggle in the new-game wizard when you want the Shahed/IRGCN content
in play.

## See also

- [Custom Campaigns](Custom-Campaigns) — where factions are assigned
- [Custom Loadouts](Custom-Loadouts) — default payloads for faction aircraft
- [Squadrons and Pilots](Squadrons-and-Pilots) — squadron defs, names, and liveries
- [Air Wing Configuration](Air-Wing-Configuration) — building a side's air wing
