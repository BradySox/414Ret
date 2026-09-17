# CH 1.5.0 / ED-CHAP wave — adoption backlog (2026-07-20)

The post-mod-update pydcs export (see `tools/verify_mod_export.py`) surfaced the
CH 1.5.0 pack wave + the ED-integrated vanilla **Currenthill Assets Pack**
(`CHAP_*` in `CoreMods`). Status after the migration commit: **418/418 registered
units verify against the live export**, and the adoption audit (registered → unit
yaml → faction/preset-group) shows the wave is ~98 % adopted already — the
extensions had been registered against newer pack versions all along, and every
new air-defense system (Patriot CH family, THAAD, NASAMS 3, IRIS-T SLM, RBS-70/98,
LvS-103 incl. HX-mobile) is fielded through an existing, factioned preset group.

**Genuinely open: two units** (was four — the two Project 22160 hulls closed
2026-08-23; see item 3). Fork-side work; the upstream PR freeze is irrelevant to it.

**Re-audited 2026-08-25** against the tree, since this file had not been touched
since it was written.

## Open items

1. **`CHAP_TigerUHT`** — Tiger UHT attack helicopter, vanilla (ED-integrated).
   pydcs pin ✔ · unit yaml ✖ · faction ✖. The single vanilla CHAP unit the
   21-yaml adoption missed. Ladder: authored `resources/units/helicopters` yaml
   (class/price/era/variants; the CHAP display-name style is
   `"<role> <name> [CH]"`) → add to the German-army-appropriate factions.
2. **`CH_B-21`** — B-21 Raider, CH USA 1.5.0. Registered ✔ · yaml ✔ ·
   faction ✖. Pure DM call: which (if any) faction gets a stealth bomber; task
   weights would make it a Strike/OCA platform. No technical work beyond the
   faction line.
3. ~~**`CHAP_Project22160`** / **`CHAP_Project22160_TorM2KM`** — Vasily Bykov
   patrol ships~~ — ✅ **CLOSED 2026-08-23** in `58c2f22c9` (#955, "Russia 2020 goes
   vanilla"). Both hulls are wired into the naval unit lists of `russia_2020.json`,
   `redfor_russia_2020.json`, `redfor_current.json` and `CH_russia_2020.json`.
   **The guidance still stands:** the Tor-M2KM hull is a §63-adjacent point-defense
   escort, NOT an LACM shooter — it takes no magazine entry.

## Adopted-and-verified inventory (receipts, no action)

- **CH USA 1.5.0**: AbramsX, M10 Booker, M1A2 SEPv3, M2A3, M551, the M270A1
  family (ATACMS/GLSDB/GMLRS), the M777 families (towed + MTVR), HEMTT/MTVR/L-ATV/
  M-ATV trucks, LAV-AD, Centurion C-RAM, Constellation frigate, the full US
  infantry set, Patriot/THAAD/NASAMS 3 (preset groups), and the LACM
  Burke IIA/III + Ticonderoga hulls (§63-live).
- **CH Sweden 1.5.0**: the renamed `CH_` roster incl. the LvS-103 HX-mobile
  variants (preset groups), Archer, Strv 103/2000, Grkpbv 90, the infantry set.
- **CH UK 1.5.0**: renamed `CH_Type45`/`CH_SkySabre` (+25→30 km retune);
  Scimitar/Scorpion superseded by vanilla `CHAP_FV107`/`CHAP_FV101`.
- **Vanilla CHAP (23 units)**: HIMARS ATACMS/GMLRS, TOS-1A, T-90M, T-64BV,
  T-84 Oplot-M, Iskander HE/CM, Pantsir-S1, Tor-M2, BMPT, Stryker CV, M1083,
  M-ATV, FV101/107, IRIS-T SLM (preset group) — all yamled + factioned except
  the four open items above.
- **CH Ukraine 2.0.0**: ids re-pointed (`CH_BTR-4`, `CH_MiG-29MU2`,
  `CH_Su-24MU`); the installed pack was double-nested in Saved Games and never
  loaded — fixed 2026-07-20; **export-verify its units on the next dump**.
