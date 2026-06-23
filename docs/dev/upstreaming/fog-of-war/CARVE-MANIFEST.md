# Fog-of-war carve manifest (PR #1: recon intel-fog + overview toggle)

Exact per-file changes to reproduce **PR #1** on a clean
`dcs-retribution/dcs-retribution` `dev` checkout (the fork's working clone lives at
`..\retribution-pr`). The fork's `main` already contains all of this *plus* the
SCAR/TARPS glue; this manifest is the subset that is generic, with the fork-only bits
called out so they are left behind.

**This repo has no upstream baseline commit**, so the new files ship as an apply-able
patch (`0001-fog-of-war-new-files.patch`) and the *edits* to existing files are listed
below as copy-paste hunks (apply by hand / search-and-insert, then run upstream's
Black + mypy + pytest). Line numbers are from this fork @ `claude/fog-of-war-pr-97adar`
and will differ upstream — match on the surrounding code, not the numbers.

Legend: ✅ = include in PR #1 · ⛔ = fork-only, leave out · ⏭ = belongs to PR #2.

---

## A. New files (in `0001-fog-of-war-new-files.patch`)

`git apply 0001-fog-of-war-new-files.patch` from the upstream repo root adds:

- ✅ `game/theater/fogofwar.py` — the transient `fog_revealed()` / `set_fog_revealed()`
  flag. Dependency-free on purpose (no import cycle from the theater layer).
- ✅ `game/server/fogofwar/__init__.py` + `routes.py` — `GET`/`PUT /fog-of-war/reveal`.
- ✅ `tests/server/test_fogofwar_route.py` — endpoint flips the shared flag.
- ✅ `tests/test_recon_intel_fog.py` — `known_for` gate, setting-off, default-on,
  save migration. (Self-contained; uses only `SamGroundObject` + a fake settings
  namespace.)

> `tests/test_bda_tarps_reveal.py` and `tests/test_recon_intel_api_fog.py` are **not**
> in the patch — they exercise the damage-lag (`alive_for`, PR #2) and the SCAR
> `hidden_on_player_map` gate (⛔) respectively.

---

## B. Edits to existing files

### B1. `game/theater/theatergroundobject.py` ✅ (with one ⛔ removal)

Add the import near the other `game.theater` imports:

```python
from game.theater.fogofwar import fog_revealed
```

Add the field at the end of `__init__` (after `self.hide_on_mfd = hide_on_mfd`):

```python
        # Recon intel-fog: has the human (BLUE) player discovered what is actually
        # at this site? New enemy sites start unknown (composition + threat rings
        # hidden) until attacked, scouted, or destroyed. Friendly/neutral sites and
        # omniscient (viewer=None) callers are handled by known_for(), so this flag
        # only matters for enemy sites from the player's perspective.
        self.discovered_by_player = False
```

In `__setstate__`, add the migration default (keep the existing `_threat_poly` reset):

```python
        # Save compatibility: a campaign saved before recon intel-fog has every
        # site already on the player's map, so treat it as fully discovered rather
        # than suddenly blanking an in-progress campaign.
        if "discovered_by_player" not in state:
            state["discovered_by_player"] = True
```

Add `known_for` — **the SCAR command-post branch is dropped** for the upstream
version (that gate + `_command_post_revealed()` + `hidden_on_player_map()` are ⛔
fork-only, see §C):

```python
    def known_for(self, viewer: Optional[Player] = None) -> bool:
        """Whether the viewer knows what is actually at this site.

        ``viewer=None`` (omniscient — AI, planner, threat math) and friendly
        viewers always know. An enemy viewer only knows once the site has been
        discovered (attacked / scouted / destroyed). The whole feature can be
        switched off via the ``recon_intel_fog`` campaign setting, and the
        ``fog_revealed()`` overview forces full knowledge for any viewer.
        """
        if viewer is None or fog_revealed() or self.is_friendly(viewer):
            return True
        settings = self.control_point.coalition.game.settings
        if not settings.recon_intel_fog:
            return True
        return self.discovered_by_player
```

> ⏭ PR #2 also adds `is_dead(viewer)`, `dead_units(viewer)`,
> `alive_unit_count(viewer)`, `max_threat_range(viewer)`,
> `max_detection_range(viewer)`, `sidc_status_for(viewer)`, `sidc_for(viewer)`,
> `sync_confirmed_status()` here. For PR #1 these keep their existing (no-viewer /
> truth) signatures; the consumers below call the truth form for *known* sites.

### B2. `game/theater/fogofwar.py` consumers in `theatergroup.py`

⏭ **Nothing in PR #1.** `TheaterUnit.alive_for` / `alive_at_last_recon` /
`sync_confirmed_status` and the `viewer` params on `threat_range` / `detection_range`
/ `alive_units` / `max_*_range` are the **damage-lag layer → PR #2**. PR #1's threat
ring hiding is done entirely by the `known_for` gate in the consumers (B4–B6): a known
site reports truthful rings, an unknown one reports none.

### B3. `game/settings/settings.py` ✅

Add the `recon_intel_fog` boolean option (Campaign Doctrine page, General section):

```python
    recon_intel_fog: bool = boolean_option(
        "Recon intel fog (hide enemy site composition until scouted)",
        page=CAMPAIGN_DOCTRINE_PAGE,
        section=GENERAL_SECTION,
        default=True,
        invert=False,
        detail=(
            "When enabled, enemy ground sites appear on the map as targets you can "
            "plan against, but what is actually there — unit types, counts, damage "
            "state, and threat/detection rings — stays hidden until the site is "
            "attacked, scouted by recon, or has a unit destroyed. The AI "
            "planner and threat math always use full truth, so auto-planning is "
            "unaffected. Existing campaigns keep everything revealed; the fog "
            "applies to new campaigns."
        ),
    )
```

> ⛔ Do **not** carry `scar_command_post_intel` (the next field in the fork) — SCAR-only.
> Confirm `boolean_option`, `CAMPAIGN_DOCTRINE_PAGE`, `GENERAL_SECTION` exist upstream
> (they do on the fork's base) and that `Settings.__setstate__` already tolerates new
> defaulted fields (it does — bool fields default cleanly on old saves).

### B4. `game/threatzones.py` ✅

`for_faction` gains a `viewer` param and filters air defenses through `known_for`, so
an undiscovered enemy SAM projects no avoidance ring on the human map (AI still passes
`viewer=None`):

```python
    @classmethod
    def for_faction(
        cls, game: Game, player: Player, viewer: Player | None = None
    ) -> ThreatZones:
        ...
        for cp in game.theater.control_points_for(player):
            air_threats.append(cp)
            air_defenses.extend(
                go
                for go in cp.ground_objects
                if go.has_aa and (viewer is None or go.known_for(viewer))
            )
```

Callers that build the *human-facing* threat overlay pass `viewer=Player.BLUE`; every
AI/planner/navmesh caller keeps the default `viewer=None`. (Find the server/map
threat-zone construction site and thread `Player.BLUE`.)

> ⏭ The `viewer` argument forwarded into `for_threats` /
> `_construct_from_air_defenses_at_locations` / `radar_sam_rings` →
> `group.max_threat_range(viewer)` is part of the damage-lag plumbing (PR #2). For
> PR #1, `for_faction` only needs the `known_for` *filter* above; the ranges of the
> sites that pass the filter are computed at truth.

### B5. `game/server/tgos/models.py` ✅ (with one ⛔ removal)

`TgoJs.for_tgo` — fog composition + rings when the site is unknown to BLUE:

```python
    @staticmethod
    def for_tgo(tgo: TheaterGroundObject) -> TgoJs:
        blue = tgo.control_point.captured.is_blue
        threat_ranges: list[float]
        detection_ranges: list[float]
        units: list[str]
        if tgo.known_for(Player.BLUE):
            threat_ranges = [g.max_threat_range().meters for g in tgo.groups]
            detection_ranges = [g.max_detection_range().meters for g in tgo.groups]
            units = [unit.display_name for unit in tgo.units]
            dead = tgo.is_dead()
        else:
            # Recon intel-fog: the site stays on the map and remains targetable
            # (position, category, allegiance), but its actual composition and
            # threat/detection rings are hidden until discovered.
            threat_ranges = []
            detection_ranges = []
            units = []
            dead = False
        ...
        return TgoJs(..., sidc=str(tgo.sidc), ...)
```

> ⏭ In the fork these read `max_threat_range(Player.BLUE)`, `display_name_for(BLUE)`,
> `is_dead(BLUE)`, `sidc_for(BLUE)` — the viewer-aware (damage-lag) forms. For PR #1
> use the plain truth properties shown above (`max_threat_range()`, `display_name`,
> `is_dead()`, `sidc`); PR #2 swaps them to the `(BLUE)` forms when the lag layer lands.
>
> ⛔ `all_in_game` in the fork skips `tgo.hidden_on_player_map(Player.BLUE)` — drop that
> filter entirely; leave the loop as upstream has it.

### B6. `game/server/iadsnetwork/models.py` ✅ (with one ⛔ removal)

`connections_for_node` (and the `viewer` param on `connections_for_tgo` /
`from_network`) — hide a connection if either endpoint is unknown to the viewer:

```python
    @staticmethod
    def connections_for_node(
        network_node: IadsNetworkNode, viewer: Player = Player.BLUE
    ) -> list[IadsConnectionJs]:
        iads_connections: list[IadsConnectionJs] = []
        tgo = network_node.group.ground_object
        if not tgo.known_for(viewer):          # ⛔ drop the `hidden_on_player_map(viewer) or` prefix
            return iads_connections
        for id, connection in network_node.connections.items():
            connected_tgo = connection.ground_object
            if not connected_tgo.known_for(viewer):   # ⛔ same: no hidden_on_player_map
                continue
            ...
```

> ⏭ The fork's `active=(network_node.group.alive_units(viewer) > 0 and
> connection.alive_units(viewer) > 0)` uses the damage-lag `alive_units(viewer)`. For
> PR #1 keep upstream's existing truth `alive_units` call here; PR #2 threads `viewer`.

### B7. `game/server/app.py` ✅

```python
from game.server import ..., fogofwar
...
app.include_router(fogofwar.router)
```

### B8. `game/sim/missionresultsprocessor.py` ✅ (TARPS/TARS reveals stripped)

Add the **reveal-on-engage** logic and call it from `commit_ground_losses` (right
after the strike/scenery kills, where the fork calls `update_confirmed_bda`). For
PR #1, call `reveal_discovered_sites` directly (the `update_confirmed_bda` *sync* wrapper
is the damage-lag layer → PR #2):

```python
        # ... after the kill loops in commit_ground_losses:
        self.reveal_discovered_sites(struck_tgos, debriefing, events)

    def reveal_discovered_sites(
        self,
        struck_tgos: set[TheaterGroundObject],
        debriefing: Debriefing,
        events: GameUpdateEvents,
    ) -> None:
        """Recon intel-fog: flip enemy sites to "known" once the player has engaged
        them this turn (attacked with a kill, or overflown by a surviving offensive
        sortie). Permanent. Friendly/neutral and the omniscient planner are never
        fogged."""
        discovered: set[TheaterGroundObject] = set()
        discovered |= struck_tgos
        discovered |= self.attacked_tgos_this_turn(debriefing)
        for tgo in discovered:
            if tgo.is_friendly(Player.BLUE):
                continue
            if not tgo.discovered_by_player:
                tgo.discovered_by_player = True
                events.update_tgo(tgo)

    def attacked_tgos_this_turn(
        self, debriefing: Debriefing
    ) -> set[TheaterGroundObject]:
        # A surviving offensive sortie that reached its target reveals the site even
        # with no kills — the pilots saw what was there. Blue ATO only.
        attacked: set[TheaterGroundObject] = set()
        offensive = {
            FlightType.STRIKE,
            FlightType.DEAD,
            FlightType.SEAD,
            FlightType.ANTISHIP,   # confirm the upstream enum name
        }
        for package in self.game.blue.ato.packages:
            target = package.target
            if not isinstance(target, TheaterGroundObject):
                continue
            for flight in package.flights:
                if (
                    flight.flight_type in offensive
                    and debriefing.air_losses.surviving_flight_members(flight) > 0
                ):
                    attacked.add(target)
                    break
        return attacked
```

> ⏭ Leave out `update_confirmed_bda` (the `sync_confirmed_status` damage-lag wrapper),
> `reconned_tgos_this_turn` / `_reconned_tgos_from_ato` (TARPS), and
> `tars_reconned_tgos` (TARS plugin bridge) — all PR #2. They are *also* OR-ed into
> `discovered` in the fork; PR #1's `reveal_discovered_sites` drops those two `|=` lines.

### B9. `qt_ui/windows/groundobject/QGroundObjectMenu.py` ✅

- Set a viewer in `__init__`: `self.viewer = Player.BLUE if gm.is_ownfor else Player.RED`.
- In `doLayout`, gate the composition section on `self.ground_object.known_for(self.viewer)`
  and show a "Not yet scouted — composition unknown" placeholder when false.
- Pass `self.viewer` to the `QBuildingInfo(...)` construction and to the intel rows.

> ⏭ The fork also passes `self.viewer` to `display_name_for` / `max_threat_range` /
> `alive_unit_count` / `dead_units` (damage-lag, PR #2). For PR #1 the *known* branch
> can use the truth forms; the only PR #1-essential change is the `known_for` gate +
> the "not scouted" placeholder.

### B10. `qt_ui/windows/groundobject/QBuildingInfo.py` ⏭ (PR #2)

The fork's `QBuildingInfo` changes (`viewer` param, `alive_for(viewer)`,
`short_name_for(viewer)`) are all damage-lag. PR #1 does not need to touch this file —
buildings have no threat rings to fog and their composition is a single static. Defer
to PR #2.

### B11. Client — "Reveal fog of war" checkbox ✅ (adapt to upstream's layer control)

The fork wires it into its custom `MapLayersControl.tsx` (its own feature). For
upstream, add an equivalent checkbox to **whatever map-layer control upstream ships**.
The load-bearing part is this effect (transient — do not persist the value):

```tsx
// Fog-of-war overview: flip the server flag and re-pull /game so the map
// re-fogs/un-fogs. Driven by state (not layer add/remove) so unchecking reliably
// turns it back OFF. Skip the initial mount.
const fogReady = useRef(false);
useEffect(() => {
  if (!fogReady.current) {
    fogReady.current = true;
    return;
  }
  backend
    .put("/fog-of-war/reveal", null, { params: { revealed: revealFog } })
    .then(() => reloadGameState(dispatch, true))   // true = no recenter
    .catch((error) => console.log(`Error toggling fog of war: ${error}`));
}, [dispatch, revealFog]);
```

The PUT must be followed by a full `/game` re-pull so `tgos` / `iads_network` /
`threat_zones` are rebuilt through the (now short-circuiting) `known_for` path.

---

## C. ⛔ Explicitly excluded (fork-only — leave on `main`)

- `TheaterGroundObject._command_post_revealed()` and `hidden_on_player_map()` — SCAR
  commander-capture; not generic fog.
- The `category == "commandcenter" and settings.scar_command_post_intel` branch in
  `known_for`.
- `Settings.scar_command_post_intel`.
- The `hidden_on_player_map(Player.BLUE)` skip in `TgoJs.all_in_game` and the
  `hidden_on_player_map(viewer) or` prefixes in `IadsConnectionJs.connections_for_node`.
- All SCAR/TARPS/TARS call sites in `missionresultsprocessor.commit` (`commit_scar_results`, etc.).
- `game/missiongenerator/triggergenerator.py` — its mark-suppression gate is the
  *target-intel-precision* feature, **not** fog. Do not carry it here.

---

## D. ⏭ Deferred to PR #2 (TARPS recon platform + BDA damage-lag)

Stacked on PR #1. Carry together because the damage-lag layer is inert without a recon
platform to confirm kills:

- `game/theater/theatergroup.py`: `TheaterUnit.alive_at_last_recon`, `__setstate__`
  migration, `sync_confirmed_status()`, `alive_for(viewer)` (+ `or fog_revealed()`
  short-circuit), `display_name_for`/`short_name_for`/`detection_range`/`threat_range`
  viewer params; `TheaterGroup.alive_units`/`max_detection_range`/`max_threat_range`
  viewer params.
- `game/theater/theatergroundobject.py`: viewer params on `is_dead` / `dead_units` /
  `alive_unit_count` / `max_threat_range` / `max_detection_range` / `sidc_status_for` /
  `sidc_for`, and `sync_confirmed_status()`.
- `missionresultsprocessor.py`: `update_confirmed_bda` (sync), `reconned_tgos_this_turn`,
  `_reconned_tgos_from_ato`, `tars_reconned_tgos`; swap consumers (B5/B6/B9) to the
  `(viewer)` forms.
- `tests/test_bda_tarps_reveal.py`, `tests/test_recon_intel_api_fog.py`.
- The TARPS feature proper: `FlightType.TARPS`, `configure_tarps`,
  `game/ato/flightplans/{tarps,reconingress}.py`, `INGRESS_RECON` waypoint type,
  `packagefulfiller` auto-add, F-14 payloads/CLSIDs + YAML task priorities. (Much of
  the F-14 payload side is fork-flavored; carve the generic recon-flight scaffold and
  leave the squadron-specific payloads behind, or ship them as a separate aircraft PR.)

---

## E. Verify (in the upstream clone, not the fork)

```
git apply docs/.../0001-fog-of-war-new-files.patch   # from upstream root
# apply the B-section hunks by hand
black --check .
mypy game tests
pytest tests/test_recon_intel_fog.py tests/server/test_fogofwar_route.py -q
```
