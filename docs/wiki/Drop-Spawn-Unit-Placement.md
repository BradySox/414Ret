# Drop-Spawn Unit Placement

Drop-spawn is a sandbox tool that lets you **right-click blank map space to place a unit
group** — armor, a SAM site, an EWR, a ship, or a coastal/missile site — anywhere on the map,
attached to the nearest friendly command post. It is gated behind cheat settings and is
intended for sandboxing, testing laydowns, and shaping a campaign by hand rather than for
normal play.

## Enabling it

Two cheat settings control drop-spawn:

| Setting | Effect | Default |
|---|---|---|
| `enable_unit_placement` | Unlocks the feature — right-clicking blank map space opens the placement dialog | OFF |
| `enable_free_unit_placement` | Free placement: skips the budget cost and bypasses the range limit | OFF |

With `enable_unit_placement` **off**, a right-click on blank map space behaves normally — for
example, right-clicking a target marker to plan a package — and never pops the placement
dialog. The unlock has to be on for the dialog to appear.

## Placing a unit group

1. Turn on `enable_unit_placement` (and optionally `enable_free_unit_placement`).
2. **Right-click blank map space.** The placement dialog opens, anchored on the spot you
   clicked.
3. Choose from the dialog:
   - **Coalition** — Blue by default; Red is locked behind the enemy buy/sell cheat.
   - **Category** — Air Defense SAM/AAA, EWR, Coastal/Missile, Ground Force, or Navy.
   - **Unit type** — drawn from the full set of named layouts the campaign engine knows
     (S-300, SA-2, Patriot, NASAMS, Early-Warning Radar, ship classes, and so on), filtered
     down to what the selected faction can actually field. If a category shows "(no
     compatible units for this faction)", that faction has no units matching that layout type.
   - **Unit rows** — pick the unit type and count for each group in the layout.
   - **Deploy timing** — **Spawn Now** or **Deploy Next Turn**.
   - **Respawn** — auto-revive the group on destruction each turn.
4. The dialog shows the **cost against your budget**; the Place button is disabled if you're
   over budget (unless free placement is on).
5. On confirm, placement **validates terrain and range** — the spot must be land-appropriate
   for the unit and within **200 km of the nearest friendly command post** (the range check is
   bypassed by free placement). The new group is attached to that command post and appears on
   the map immediately.

### Deploy timing and respawn

- **Spawn Now** creates the group right away.
- **Deploy Next Turn** queues the placement and materializes it at the start of the next turn;
  the budget is deducted when you queue it.
- **Respawn** revives a destroyed user-placed group at the start of each turn.

## Removing a placed unit

**Right-click a unit you placed** and choose **Remove**. The group is deleted and the marker
disappears from the map immediately. (Note: there is currently no budget refund on removal.)

## See also

- [The-Retribution-UI](The-Retribution-UI)
