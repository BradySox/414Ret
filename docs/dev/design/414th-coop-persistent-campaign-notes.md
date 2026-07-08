# Co-op persistent campaign — the squadron layer

**Status: SCOPED 2026-07-08, not yet built** (design of record). Grounded against the real
MP / persistence / web stack. **v1 scope = Phase A (pilot identity) + Phase B (frag board),
advisory, LAN/local** — decided calls below. Phases C–E are documented as deferred.

Decided calls (session 2026-07-08):

- **[DECIDED] v1 = A + B only** — pilot identity + a persistent frag board. The remote shared
  dashboard (C) is a separate, later hardening effort; it is **not** in v1.
- **[DECIDED] Advisory slot binding** — the frag board expresses *intent* ("Maverick flies
  Uzi 1-1"); DCS still owns who actually occupies a `Skill.Client` seat. Retribution does not
  (cannot) enforce it. No in-mission Lua slot-check.
- **[DECIDED] LAN/local for now** — no work to expose the server beyond `::1`; no new auth or
  network-security surface in v1.

---

## The reframe (what the grounding found)

**Co-op *flying* already works.** Retribution already generates correct co-op missions:
`AircraftGenerator.use_client` (`game/missiongenerator/aircraft/aircraftgenerator.py`) emits
`Skill.Client` MP slots whenever there is >1 human slot across the ATO (auto-degrading to a
single `Skill.Player` for solo), and `Flight.client_count` threads player-awareness through the
whole generator. The **documented dedicated-server workflow** (`docs/wiki/Dedicated-Server-Guide.md`)
already closes the loop: one host runs Retribution, generates the `.miz`, the squadron flies it
on a DCS dedicated server, the server's single `state.json` comes back to the host, the host
clicks "Accept results," and `Game.pass_turn()` autosaves.

So the gap is **not** multiplayer — it is the **squadron layer** on top of the working loop:

1. **No human owns a pilot.** `Pilot.player` (`game/squadrons/pilot.py`) is an anonymous
   boolean — "this seat is human-flyable," not "this is *Maverick's* seat." DCS lets any
   connected human take any Client slot.
2. **No pre-session frag board.** Who flies what is the host ad-hoc-toggling player slots in
   the Qt UI each turn, and the toggles don't persist.
3. **No shared visibility.** The React client is a prebuilt bundle in the host's
   `QWebEngineView` bound to loopback; the squadron can't see the campaign except over the
   host's shoulder. (This is Phase C — deferred.)
4. **No "my pilot" continuity** — record / callsign / POW status don't follow a person across
   sessions. (This is Phase E — deferred, and where co-op meets pilot careers, a separate
   thread.)

## The fence — what the fork CANNOT do (out of scope by nature)

DCS owns the netcode. Retribution **cannot** run the MP session, **cannot** bind a specific
human to a specific cockpit slot at runtime (DCS lets anyone take any `Skill.Client` seat), and
does not touch **SRS voice**. "My slot is reserved for me" is therefore honor-system /
DCS-slot-block-mod territory — **advisory in Retribution**, per the decided call. This is the
central design tension and it is inherent, not a v1 shortcut.

## What exists to build on (the real seams)

- **`Pilot`** (`game/squadrons/pilot.py`) — a pickled dataclass (`name`, `player: bool`,
  `status: PilotStatus` = Active/OnLeave/Dead/POW, `record`), surviving turns inside
  `Squadron` (`game/squadrons/squadron.py`). `Pilot`/`Squadron` already use `__setstate__`
  migration, so new persisted fields load on old saves with a default. **The one persistent
  per-human anchor.**
- **The `qra_player_manned` precedent** — `Squadron.qra_player_manned` /
  `qra_player_ai_wingman` (`game/squadrons/squadron.py`, `__setstate__`-defaulted; design note
  `414th-qra-player-manning-notes.md`) is exactly the shape v1 extends: persist a per-squadron
  human-manning intent and auto-frag real client flights from it.
- **The roster → slot chain** — `Pilot.player` → `FlightMember.is_player`
  (`game/ato/flightmember.py`) → `FlightGroupConfigurator.set_skill()`
  (`game/missiongenerator/aircraft/flightgroupconfigurator.py`) → `set_client()`/`set_player()`.
  The **only** place a persistent pilot's humanness becomes a controllable DCS unit — the
  identity→miz translation point.
- **Callsigns are per-`Flight` and ephemeral** — `Flight` is the `CallsignContainer`; flights
  are rebuilt every planning turn, so a stable callsign must be sourced off the persistent
  `Pilot`/`Squadron`. The fork's role-callsign layer (`game/ato/flight.py` `role_callsign` /
  `_ROLE_CALLSIGN_BY_TYPE`) is the existing callsign-preference hook to extend.
- **Qt roster editing** — `qt_ui/models.py` `SquadronModel.toggle_ai_state()` (flips
  `pilot.player`), `qt_ui/windows/SquadronDialog.py`, and the per-flight
  `qt_ui/windows/mission/flight/settings/QFlightSlotEditor.py` (`PilotControls` / `PilotSelector`).

## Phase A — Pilot identity

Give a roster slot a *person*, not just a humanness flag.

- **Model:** add to `Pilot` (all `__setstate__`-defaulted so old saves load):
  - `human_id: Optional[str]` — the squadron's handle for the real person (e.g. a callsign or
    Discord name). `Pilot.player` stays "is a human seat"; `human_id` says *which* human.
  - `preferred_callsign: Optional[str]` — the flight callsign this human likes to fly under.
- **Edit:** a field in the Qt roster UI (`SquadronModel` + `SquadronDialog`) alongside the
  existing player toggle — set a pilot's handle + preferred callsign once; it persists.
- **Identity → miz (optional in A, natural in B):** when a human-owned pilot leads a flight,
  stamp their `preferred_callsign` onto the flight via the role-callsign layer /
  `CallsignContainer`, so the generated `.miz` shows *their* callsign. Advisory only.
- Self-contained: pure persisted data + one UI field. No generation behaviour change is
  *required* for A (it is the identity substrate); no security surface; no NEW game (migrated).

## Phase B — The frag board

A **persistent** manning plan so the host stops re-toggling player slots every turn, and
everyone knows their seat.

- **Model:** a per-squadron manning intent (the `qra_player_manned` shape generalized): a small
  persisted list of "manned this session" entries — `(human_id, preferred_callsign, role /
  `FlightType`, wingman-count)` — on `Squadron` (or aggregated on the coalition), `__setstate__`
  -defaulted.
- **Apply at planning:** when the coalition builds its ATO and populates `FlightRoster`s
  (`game/ato/flightroster.py` / `flightmembers.py`), honour the plan — assign each manned
  human's `Pilot` into a member of a flight matching their role with `player=True`, and set that
  flight's callsign to their `preferred_callsign`. This rides the existing roster→`set_skill`
  chain, so those slots generate as `Skill.Client` automatically. Degrades gracefully (no
  matching flight this turn → the human simply isn't slotted that turn; never blocks planning).
- **Advisory (decided):** the board is *intent*. The `.miz` labels Uzi 1-1 as a Client slot with
  Maverick's callsign; DCS still lets anyone take Uzi 1-1. Enforcement is out of scope.
- **Surface it:** print the manning to the briefing / kneeboard ("Manning: Uzi 1-1 Maverick ·
  Uzi 1-2 Goose · …") using the existing kneeboard machinery, so in-mission everyone sees their
  slot. This is the v1 stand-in for the (deferred) web dashboard.
- **Edit:** a frag-board panel in the Qt UI (host-side) to assign humans → squadrons/roles; the
  plan persists across turns (the core pain today is that it doesn't).
- **Gating:** likely a small `persistent_player_manning` setting (default OFF) so the auto-apply
  never surprises a solo player; the identity fields (A) need no toggle (inert until used).
  [Open — resolve at build time: toggle vs. inert-until-a-plan-exists.]

## Deferred (documented, not in v1)

- **C — Shared read-only dashboard (web).** Expose roster + ATO + SITREP + campaign status via a
  new `game/server/roster/` router; make it remotely reachable (bind beyond `::1` in
  `game/server/settings.py`, **wire the dormant `ApiKeyManager`** in `game/server/security.py`,
  client sends `X-API-Key`), **guard the `/qt/*` callback routes** (`game/server/qt/routes.py`)
  so a remote viewer can't drive the host's PyQt dialogs, and read a **between-session snapshot**
  from the pickle (the in-memory `GameContext` only lives while the host app runs). The WebSocket
  broadcast (`ConnectionManager`) is already N-client-shaped, and the roster is currently
  invisible to the client (grep `client/` for pilot/squadron = zero). **This is a genuine
  hardening project** — the upstream comment "no client/server workflow yet, security has not
  been a focus" is the warning. LAN/local (B's kneeboard manning) covers v1 without it.
- **D — Multi-source result reconciliation.** Merge N participants' `state.json`s into one
  `Debriefing` at the pre-commit seam, mirroring `Debriefing.merge_simulation_results`
  (`game/debriefing.py`). The dedicated server exports *one* `state.json`, so this is only for
  listen-server / non-dedicated setups — not needed for the standard workflow.
- **E — Pilot career continuity.** `human_id` makes record / callsign / **POW status** follow
  the person across sessions. This is where co-op converges with the **pilot-careers** thread
  (#2 in the untapped-potential survey) — scope it there.

## Boundaries / gotchas

- **Single-host, single-writer stays.** The `.retribution` save is one pickle written atomically
  by the one Qt host process (`game/persistency.py`); v1 does not change that. The host remains
  the sole owner of the campaign; A+B add persisted *data* and a Qt editing surface, nothing
  networked.
- **No NEW game required.** All new state is `__setstate__`-migrated onto `Pilot`/`Squadron`.
- **Advisory binding is the honest ceiling.** Document it plainly in the UI so users don't expect
  Retribution to lock slots — DCS doesn't expose that to us.
- **Thin game-design surface, organizational payoff.** A+B is mostly persisted data + a Qt panel
  + a kneeboard readout; the value is "the squadron inhabits one campaign over weeks," not a new
  mechanic.

## Tests

- `Pilot` identity fields persist through a pickle round-trip + `__setstate__` default on a
  pre-feature save.
- The manning plan persists across turns and auto-slots a manned human into a matching flight
  with `player=True` + the preferred callsign (against a small faked squadron/ATO), and no-ops
  cleanly when no matching flight exists.
- The manning readout renders on the kneeboard.
- Off/empty-plan → byte-identical to stock generation (no surprise player slots).

## Delivery

Two small PRs (A then B), each green through Black/mypy/pytest, plus the registry/doc surfaces
(a §N registration, features doc, README, checklist row) when B lands its runtime behaviour.
C/D/E are separate, later efforts — C especially is its own hardening project and should not be
bundled with A+B.
