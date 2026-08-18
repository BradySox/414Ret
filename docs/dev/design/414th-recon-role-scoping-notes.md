# 414th — what recon does now (scoping, not built)

Status: **scoping only.** Nothing here is implemented. Written 2026-08-18, immediately after
the §3 recon rework (see [414th-features.md §3](../414th-features.md)) left `FlightType.TARPS`
and the `recon` plugin mechanically inert.

## The constraint any new job must satisfy

Engaging a site reveals it **completely and permanently**. So recon cannot:

- reveal an un-engaged site's composition — that is "hidden until scouted", the rule the
  rework removed;
- confirm anything about an engaged site — that is the BDA damage lag, also removed.

Whatever recon does, it has to answer a question that engaging the site does not already
answer, about something engagement cannot settle.

## Candidate A — recon finds what is hidden outright

**This closes a hole the rework opened, and is the strongest candidate.**

Enemy **command posts** are hidden from the player's map entirely — no marker, not
right-clickable, not plannable (`hidden_on_player_map`, gated `scar_command_post_intel`,
default ON). They are revealed by `_command_post_revealed()`, which is
`captured_commander or discovered_by_player`.

Both keys are now dead ends for a player who plans by hand:

- `captured_commander` is **never set True anywhere in the tree** — the commander-capture
  mechanic was removed 2026-07-01 and only the flag survives.
- `discovered_by_player` is now set only by engagement, and you cannot frag a package at a
  target that is not on your map.

The one remaining path is the **auto-planner**, which enumerates strike targets on ground
truth (`ObjectiveFinder.strike_targets`, `viewer=None`) and will happily frag a package at a
command post the player cannot see. Once that package flies, `attacked_tgos_this_turn`
reveals the site. So the feature is reachable *only* by delegating planning — a hand-planner
can never map the command network.

Before the rework, recon was the intended path; the wiki said so in as many words.

**Shape:** a recon sortie whose route passes within some radius of a hidden command post
reveals it (marker + exact coordinates), and nothing else. Ordinary sites are unaffected
because they are already on the map. §50 ambush teams stay excluded — their whole point is
that the first sign of them is the in-mission TROOPS IN CONTACT call.

**Size:** small. The reveal path (`discovered_by_player = True`) already exists; this is a
geometric proximity check in `missionresultsprocessor` plus a gate so it only applies to
`hidden_on_player_map` sites.

## Candidate B — recon tracks what moves

Fleet control points genuinely relocate between turns: `ControlPoint.process_turn` sets
`self.position = self.target_position` and shifts every linked
`GenericCarrierGroundObject` by the same delta (`controlpoint.py:1174`). An enemy carrier
group you found last turn is somewhere else this turn, and nothing tells you where.

**Shape:** an enemy naval group's *position* on the player map is its last observed position,
not its live one, and a recon pass re-fixes it. Composition stays fully known (it was engaged)
— only the fix goes stale. This does not reintroduce a lag, because the thing going stale is
a coordinate that actually changed, not a fact about damage.

**Size:** medium. Needs a per-TGO "last observed position" field, a save migration, and the
map/DTC/kneeboard consumers pointed at it.

**⚠️ The mobile-missile version of this does NOT work today.** §49 relocation is
**in-mission Lua only** (`resources/plugins/mobilemissiles/mobilemissiles-config.lua`, fed by
`game/missiongenerator/mobilemissileluadata.py`). There is no Python-side position writeback,
so a launcher's campaign coordinate never moves — which is what the Marianas note already
recorded ("once photographed the coordinate stays good"). Extending B to §49 means building
the writeback first. Do not propose "recon re-fixes a scooted SCUD" without that.

## Candidate C — recon produces an intel product, not campaign state

Recon stops touching the fog entirely and instead produces something you read: a per-target
imagery card on the kneeboard — individual unit positions inside the site, revetment layout,
an aimpoint list, approach notes. You always know *what* is at an engaged site; recon tells
you *how to hit it*.

**Shape:** the recon kneeboard machinery already exists (`game/missiongenerator/kneeboard_recon/`)
and ships default-off pending an in-game pass on the tile alignment fix. This would give it a
reason to be on.

**Size:** medium, and it is the only candidate that is purely additive — it can never
conflict with the reveal rule because it never writes campaign state.

## Recommendation

**A first, on its own.** It is small, it fixes a live hole rather than inventing a mechanic,
and it gives recon a job that is impossible to confuse with scout-to-reveal: it only reaches
sites that are not on the map at all.

B and C are both defensible follow-ons. C composes with A cleanly; B is the largest and the
one most likely to feel like a lag to a player even though it technically is not.

## See also

- [414th-features.md §3](../414th-features.md) — the reveal rule this has to live under
- [414th-features.md §12](../414th-features.md) — the recon engine, currently inert
- [414th-tars-recon-notes.md](414th-tars-recon-notes.md) — historical, do not author against
