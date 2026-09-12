# Skynet is the IADS engine again — the MANTIS detour, closed

**Date:** 2026-09-12 (DM call)
**Replaces:** `414th-mantis-iads-HANDOFF.md`, `414th-mantis-migration-notes.md`,
`414th-mantis-vs-skynet-iads-parity.md`, `414th-mist-moose-shim-notes.md` — all four deleted
in the same change. `git show <this commit>^:docs/dev/design/<name>` recovers them.
**In-game pass:** checklist row G42.

## 1. The decision

The fork runs upstream's Skynet-IADS again, on upstream's MIST. The MOOSE MANTIS bridge
(`mantisiads`, 2026-06-24 to 2026-09-12) and the MIST-to-MOOSE shim (`mist_moose_shim.lua`,
2026-07-10 to 2026-09-12) are removed. Every other MOOSE plugin stays: upstream bundles
`Moose.lua` itself, and QRA, TIC, CSAR, Vietnam Ops, cruise missiles, ATIS and BigEye run on it.

Scope was put to the DM as a choice and the answer was "Skynet + MIST only".

## 2. Why — the evidence

- **Skynet was never shown broken.** The parity note that made the 2026-06 decision recorded
  zero Skynet defects. Its reasons were a squadron member's opinion, "dormant" maintenance
  (last release 2023-12-29) and the MIST retirement. Its own verdict said "Skynet is actively
  broken right now is NOT established."
- **Every IADS bug since June was MANTIS or our bridge.** The prefix bug that left MANTIS
  controlling 0 SAMs for weeks (06-26); the SA-10 typed as a 6 km POINT site (06-27); the
  ground-start AWACS dropped from the net (06-27); the blind-network problem; the C2 layer dying
  after one mission (08-19, Python-side, found by juanjux #97 against Skynet).
- **The EWR corrections were forced by MANTIS's model, not by Skynet.** A Skynet SAM with no
  EWR coverage defaults to autonomous DCS AI and still fights (`AUTONOMOUS_STATE_DCS_AI` is the
  SAM-site default). A MANTIS SAM never self-detects, so the same laydown produced a blind net.
  Every EWR fix (the blind-network warning 06-27, the P-14/1L13 sites 07-04, the
  `fallback_classes` restore 07-27, the backstop removal 08-06) landed after the switch.
- **The diff-from-upstream argument was measured.** Against upstream's tip the fork's diff is
  334k lines. Skynet, MIST, the shim and the MANTIS bridge together are 16k of it (5 %).
  Restoring them is real and cheap; the fork's diff is the planner, the features, the tests and
  the campaigns.
- **HDSUC ships no Skynet profiles.** The installed mod folder has none. The S-400 / S-300V4 /
  SAMP/T / Pantsir-SM profiles are ours, from #851, carried in juanjux's open upstream #956.

## 3. What was restored, and from where

| File | Source | Delta from upstream |
|---|---|---|
| `resources/plugins/base/mist_4_5_126.lua` | upstream `dev` | byte-identical (same blob as the copy deleted 2026-07-10) |
| `resources/plugins/base/plugin.json` | upstream `dev` | plus the fork's `sortie_recorder.lua` work order |
| `resources/plugins/skynetiads/plugin.json`, `LICENSE.md` | upstream `dev` | byte-identical |
| `resources/plugins/skynetiads/skynet-iads-compiled.lua` | upstream #956 head (`juanjux/hds_2_1_0_and_ultimate`) | see §4 |
| `resources/plugins/skynetiads/skynetiads-config.lua` | upstream `dev` | see §5 |

Upstream's compiled Skynet has not changed since our removal (last real edit 2025-01, #443).

## 4. The compiled build — three layers

1. **Upstream's vendored Skynet** (baron-branch, build 2023-05-16), with Retribution's own
   hand-added units (P-37 in the S-200 profile, the HDS SA-10B block). Adding `samTypesDB`
   entries here is the accepted pattern.
2. **The HDSUC profiles from #956**: S-400, S-300V4, SAMP/T, Pantsir-SM, and the renamed
   SA-10B radars. This is our #851 work as upstream will ship it, so the fork converges on
   upstream's file when #956 merges. **Drift-watch #956.**
3. **CurrentHill SAM profiles from `HFXLegion/Skynet-IADS`** (Apache-2.0, the same licence
   as Skynet): the Russia, US, UK, Germany and China packs — Buk-M3, S-350, Pantsir-S1/S2,
   Tor-M2, Patriot (CH), NASAMS 3, THAAD, HQ-22, Sky Sabre and the rest. That fork is walder's
   Skynet plus these data files and nothing else (2 commits ahead, 0 behind, 2025-07). Its
   `sampack_s300` file is **not** taken: it overlaps the #956 profiles and would override the
   SA-10 block. 14 of its 64 unit ids name units no fork faction fields (the Germany pack and
   newer US-pack Patriots); an unmatched profile is inert.

Plus one fork line: `P14_SR` in the S-200 search-radar block, because the two SA-5 Legacy
Site layouts pair the S-200 with a Tall King. Coverage audit 2026-09-12: of the 151 unit ids
the anti-air layouts and preset groups field, every radar id is in the database.

## 5. The config bridge — upstream's plus two additions

Upstream's `skynetiads-config.lua` is kept whole. Two blocks are added, both harness-tested
in `tests/lua/test_skynet_bridge.py`:

- **DeadC2.** The campaign emits, per coalition, the C2 nodes it already knows are destroyed
  (`IadsNetwork.dead_c2_names`, kept from the 08-19 fix). Skynet reads a SAM with no comms or
  power object as fully connected (`genericCheckOneObjectIsAlive` returns true on an empty
  list), and a node killed on an earlier turn may have no DCS object left (destructible scenery
  never has one). The bridge registers each named node as a stand-in that answers
  `isExist() == false`; a command centre stand-in also answers its coalition and type. Skynet
  asks nothing else of a node object. Without this, the SAMs behind a bombed power station come
  back fully operational on the next turn, and losing every command centre hands the coalition
  perfect command (`isCommandCenterUsable` is true on an empty list).
- **AWACS fold.** A ground-starting AWACS is not a spawned group when the bridge runs, and
  upstream's bridge skips it for the whole mission. Ours keeps looking every 60 s for 90 min,
  reading the coalition from the campaign's `AWACs` entry (emitted by `luagenerator`), and
  adds the aircraft once it exists. Skynet accepts a new EWR after activation.

## 6. Constraints carried over from the MANTIS period

These cost missions to learn and still hold, or hold in a changed form:

- **`enableEmission` is what Skynet uses to go live and dark** (three calls in the compiled
  file). The hard constraint that `enableEmission(false)` crashed DCS came from the C-130 line,
  where the script toggled it on player-driven events; upstream has flown Skynet on it for years
  and this fork did until June without a recorded crash. Row G42 watches for it. The C-130,
  growler and cruise-missile plugins still never touch emissions; they hold sites with ROE
  `WEAPON_HOLD`, and Skynet re-asserts ROE itself, so those writes are self-healing under it.
- **A campaign still needs early warning.** Under Skynet an uncovered SAM fights autonomously
  rather than staying blind, so the failure is softer, but a network with no EWR and no AWACS is
  a set of isolated sites, not an IADS. The `fallback_classes` on the EWR layout stays
  load-bearing.
- **The dead-C2 graph fix is Python-side and stays.** `iads_nodes` keeps dead C2 nodes and
  edges; `DeadC2` names them. This is the juanjux #97 hole, which was live against Skynet too.
- **Skynet has no name-prefix matching**, so the `escape_prefix` lesson does not apply to it.
  It still applies to every MOOSE `SET_*` filter the fork uses (intercept, cruise missiles).
- **Never spawn a backstop EWR** (§1) and **never double-count radars** (§60 vs regiments)
  are engine-independent and unchanged.
- **Point defence** is explicit under Skynet (`addPointDefence`, from the emitted `PD`
  arrays), so the SEAD-triggered SHORAD link that the MANTIS bridge built has a native
  equivalent. Row G30 is re-pointed at it.

## 7. What was removed with the bridge

- The MANTIS plugin options: emissions control, the SEAD scoot radius (B81), the MEZ band
  override, the per-band active-SAM caps, the SHORAD link timings, the C2 poll. Skynet's own
  options (`actMobile*`, `adjustGoLiveRange*`, the radio menu) are back in their place.
- The generation-time blind-network warning in `luagenerator`. Under Skynet an uncovered site
  goes autonomous, so the warning's premise ("its SAMs will never engage") is false.
- `MANTIS_MANAGED_ROLES` in the AI-sleep emitter is `IADS_MANAGED_ROLES`: the same three roles,
  because Skynet drives the same groups.
- The `engine` marker in the emitted IADS table. Nothing reads it.
- The Lua harness tests for the bridge and the shim.

## 8. Not done, and why

- **No engine selector.** Upstream has none; the `IadsEngine` enum stub stays only so
  2026-06 to 2026-09 saves unpickle, and `_migrate_legacy_settings` drops the value.
- **The HDS fallback_classes / faction EWR content** is untouched. It was right for MANTIS and
  is still right.
- **The MOOSE plugins are untouched.** Rolling back MOOSE was put to the DM and declined; it is
  not a diff reducer.
