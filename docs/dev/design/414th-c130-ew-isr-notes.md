# 414th C-130J EW/ISR Notes

## Source of truth

The 414th's scripted electronic-warfare gameplay is the C-130J-30 JAMMING
flight type backed by `resources/plugins/c130j/c130j_mission_systems.lua`.
That plugin turns the player-flown C-130J into an EC-130H/RC-130H-style
platform with area, directional, and spot jamming, missile spoofing, ISR/ELINT
tracking, F10 marks, and handoff briefs.

## Retired generic EW plugin

The old generic `ewrj` / "EW Jammer Script 2.1" plugin is intentionally
retired. Do not re-add it to `resources/plugins/plugins.json`, do not restore
the Python hooks that call `EWJamming`, `startEWjamm`, or `startIAdefjamming`,
and do not use F-16/A-10 jammer pods as a reason to bring it back.

Why it was removed:

- It duplicated the newer C-130J EW role but applied to generic aircraft based
  on ECM pod metadata.
- It created confusing F10 "Jammer menu" entries on aircraft such as F-16s
  carrying ALQ-184 pods.
- It added AI SEAD/DEAD waypoint script hooks and package threat-reaction
  changes that were separate from the 414th C-130J EW/ISR design.
- Its plugin options could still appear in the plugin config menu even though
  the plugin was hidden and default-off, making it look supported.

The retirement migration removes saved `ewrj` and `ewrj.*` settings on load.
The legacy YAML fields `has_built_in_ecm` and `has_built_in_jamming` are kept
only for third-party aircraft-data compatibility; they no longer drive 414th EW
mission scripting.

## Expected behavior

- A C-130J-30 planned as `FlightType.JAMMING` gets the C-130J Mission Systems
  menu and runtime behavior.
- Fighter/attack aircraft ECM pods still exist as loadout equipment and DCS
  native ECM settings, but they do not create a scripted 414th F10 jammer menu.
- AI SEAD/DEAD flights no longer receive generic `ewrj` Lua start/stop jamming
  waypoint actions.

## If more EW is needed later

Extend the C-130J Mission Systems model or design a new explicitly scoped
platform/flight type. Do not resurrect `ewrj` as a generic pod-based fighter
jammer.
