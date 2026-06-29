# Custom Loadouts

By default, Retribution picks a stock weapon loadout for each flight based on its mission
type. You can override those defaults per aircraft so that, for example, every Strike F-16
spawns with your preferred bombs. This page explains the two ways to set custom loadouts
and the CLSID pitfall that silently breaks them.

![The Edit flight Payload tab: flight-member and same-loadout/same-livery toggles, the assigned TGP laser code with a preset-code selector, an internal-fuel slider, the named-loadout dropdown, and the per-pylon station list with a Save Payload / Create Backup row](https://raw.githubusercontent.com/bradyccox/414Ret/main/docs/wiki/img/edit-flight-payload.png)

*The flight payload editor. The named-loadout dropdown (here an `IRON` profile) is where a `Retribution <mission type>` loadout gets picked up; tick **Use custom loadout** to set pylons by hand. Laser code and internal fuel are set on the same tab.*

## Two ways to customize

### 1. Name a loadout in the Mission Editor (per-install)

The simplest path needs no code:

1. Open the DCS Mission Editor, place the aircraft, and build a loadout.
2. Name the loadout `Retribution <mission type>`, where the mission type matches what
   appears in Retribution's UI — for example `Retribution OCA/Aircraft`,
   `Retribution Strike`, or `Retribution TARPS`.
3. Save. Retribution looks up a loadout with that exact name when it generates a flight of
   that type.

If you don't define a loadout for a given mission type, Retribution falls back to the
included defaults — missing names are harmless, not errors. All stock DCS loadouts also
remain selectable in the flight-editing interface, so you can always change a payload by
hand.

### 2. Customized payload files (shipped with the fork)

The fork ships curated default payloads as Lua files under
`resources/customized_payloads/`, one per aircraft type (e.g. `F-14B.lua`, `F-16C_50.lua`).
Each file is a table of named profiles keyed by the same `Retribution <mission type>`
convention, with pylons listing weapons by **CLSID**:

```lua
{
  ["displayName"] = "Retribution Strike",
  ["name"]        = "Retribution Strike",
  ["pylons"]      = {
      [3] = { ["CLSID"] = "{GBU-12}", ["num"] = 3 },
      -- ...
  },
}
```

This is how the fork bakes in role-appropriate loadouts that ship with the build rather
than depending on each player's Mission Editor.

## The fork's TARPS payload (worked example)

The 414th treats TARPS as a real player task (see [Fog of War and
Reconnaissance](Fog-of-War-and-Reconnaissance)), so the F-14 payload files add a
`Retribution TARPS` recon profile alongside the usual BARCAP/TARCAP/Escort/Strike entries.
It mounts a reconnaissance camera pod on the Tomcat's belly recon station — for example, in
`F-14B.lua`:

```lua
["displayName"] = "Retribution TARPS",
["name"]        = "Retribution TARPS",
["pylons"]      = {
    [4] = { ["CLSID"] = "{F14-TARPS}", ["num"] = 6 },
    -- ...
},
```

The same `Retribution TARPS` profile is present across the F-14A/F-14B variant files so
the photo-recon task is available whichever Tomcat a squadron flies.

## CLSID currency — the gotcha that bites

A pylon's `CLSID` is the exact weapon identifier DCS uses internally. These strings change
when ED renames, splits, or removes a store across DCS updates. If **any** CLSID in a
named loadout is stale, **DCS rejects the entire loadout** — the aircraft spawns with the
fallback, not your payload, and there's no obvious error message.

So when you add or edit a loadout:

- Copy CLSIDs from a current DCS install or a freshly-saved Mission Editor loadout, not
  from memory or an old guide.
- After a DCS update, re-verify the payloads for any aircraft whose stores changed.
- If a custom loadout "isn't taking," suspect a stale CLSID before anything else — verify
  the offending profile in the Mission Editor for that aircraft.

Keeping CLSIDs current is the single most important discipline for custom loadouts.

## Date-gated stores and properties

With **Restrict weapons by campaign date** on (a difficulty setting — off by default, on for the
Veteran/Ace presets), the payload editor hides stores **and properties** that postdate the campaign:
modern munitions drop out of the lists, and era-defining options like the **JHMCS** helmet sight are
removed and clamped to the baseline visor for a pre-2003 mission. The generator is authoritative —
even a *defaulted* JHMCS is degraded at generation — so a period campaign stays period-correct
without hand-editing every loadout. See [Custom Factions](Custom-Factions) for the unit/weapon side
of date gating.

## See also

- [Custom Factions](Custom-Factions) — which aircraft a side can field
- [Custom Campaigns](Custom-Campaigns) — where mission types come from
- [Fog of War and Reconnaissance](Fog-of-War-and-Reconnaissance) — why TARPS matters
- [Mission planning](Mission-planning) — assigning flights and tasks
