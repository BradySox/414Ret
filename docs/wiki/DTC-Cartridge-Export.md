# DTC Cartridge Export

414Ret can write a **native DCS Data Transfer Cartridge (DTC)** into the generated mission so
F/A-18C players spawn with their situational-awareness picture pre-built. The cartridge tags
CAP and tanker racetracks for the Hornet's SA page. It is **disabled by default** because the
current DCS build still requires players to load the cartridge manually once per sortie.

## What gets exported

- **F/A-18C only.** The export targets the Hornet; other airframes are not written.
- The shipped payload is the **SA page picture**: player and AI **CAP racetracks** plus
  **tanker tracks**, drawn on the Hornet SA page from the campaign's planned orbits. Hidden
  mobile SAMs are excluded from the picture using the same hide-on-MFD filter the rest of the
  app uses, so they never generate rings.
- The cartridge is **terrain-tagged** with a neutral name (`Retribution <terrain> DTC_1`) so
  it does not collide with a player's personal cartridge library.

## How it ships in the mission

When the `generate_dtc` setting is enabled, the generator:

1. Builds the cartridge by overlaying the CAP and tanker tracks onto a captured Mission
   Editor template, so the cartridge stays structurally complete (COMM, ALR-67, and CMDS keep
   their template defaults).
2. **Embeds** the `.dtc` file into the generated `.miz`.
3. **Mirrors** the same file into your `Saved Games\DCS\DTC\` library, because DCS resolves
   named cartridges from there rather than from the mission file.
4. Binds every player Hornet to auto-load that cartridge by name.

## Enabling and using it

- The feature is gated by the **`generate_dtc` setting, default OFF**.
- **Known limitation (the reason it's off by default):** on the current DCS build, ED's
  mission-start *pre-load* does not actually fire even with a fully correct setup. You must
  open the DTC manager in the cockpit and **manually load** `Retribution <terrain> DTC_1`
  **once per sortie**, after which the CAP and tanker tracks populate correctly on the SA
  page. Re-test pre-load on future DCS builds before assuming the manual step is still needed.
- The mirrored library write is **per-machine**, so it does not distribute over multiplayer —
  each client would need its own copy.

## See also

- [Mission-planning](Mission-planning)
