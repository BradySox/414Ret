# Campaign maintenance

> **Adopted standard (2026-07-20).** This page is the upstream
> [Campaign maintenance](https://github.com/dcs-retribution/dcs-retribution/wiki/Campaign-maintenance)
> page, adopted as the 414th's own campaign-maintenance standard, with the fork's
> campaign-authoring rules appended. When upstream revises their page, refresh this one.

## Campaigns

### Supported campaigns

These campaigns have owners who are willing to keep them up to date for each release of
Retribution. They might still be (frequently) incompatible on a preview/`main` build, but
they should be fixed before a pinned release.

Upstream's shipped campaigns live in
[dcs-retribution/resources/campaigns/](https://github.com/dcs-retribution/dcs-retribution/tree/dev/resources/campaigns);
the fork's in
[`resources/campaigns/`](https://github.com/bradyccox/414Ret/tree/main/resources/campaigns).

**414th:** every campaign the fork *authored* (Red Tide, Enduring Resolve, Inherent
Resolve, 1968 Yankee Station, Velvet Thunder, Red Flag 81-2, the Tanker War, Desert
Storm, …) is squadron-owned by definition: each has a design note under
`docs/dev/design/` and a CI lock under `tests/` that fails when its laydown drifts.
Campaigns inherited from upstream follow the upstream rule below.

### Unsupported campaigns

Every other campaign has no owner. **When they break they will be removed from
Retribution.** If you don't want to see those campaigns disappear, you can volunteer to
maintain them.

## Becoming a campaign maintainer

Upstream's process: if there is a campaign with no owner that you want to volunteer to
own, join their Discord and say so in the #campaign-maintenance channel (you don't need
approval, they just want to know), then edit the wiki page to add the campaign to the
Supported Campaigns section. If there's an _owned_ campaign that you just wish was more
frequently updated, reach out to the owner in that channel — they may want to keep their
role, but they might also be glad to hand off the burden.

**414th:** tell the DM which campaign you're taking. Ownership means flying it, keeping
its design note honest, and fixing it when a fork feature or an upstream sync breaks it.

To send campaign updates, send a Pull Request. If you don't know how to do so but want to
learn, the
[GitHub docs](https://docs.github.com/en/desktop/contributing-and-collaborating-using-github-desktop/working-with-your-remote-repository-on-github-or-github-enterprise/creating-an-issue-or-pull-request)
can help. If you don't know how to use GitHub and _don't_ want to learn, that's okay too
— file the
[Campaign Update template](https://github.com/bradyccox/414Ret/issues/new?template=campaign_update.md)
with the updated files attached. It won't be handled as quickly as a PR, but it will be
handled.

We don't recommend anyone take on more than one or two campaigns, perhaps more if they're
small. Spreading yourself too thin means you have less time to focus on each campaign,
and we'd rather have a few great campaigns than many that merely work.

## 414th campaign standards

The fork holds campaign work to a few standards beyond upstream's. All of these are
binding; the details, rationale, and reference implementations live in `CLAUDE.md` and
the per-campaign design notes.

* **Supply lines follow the driveable corridor.** Authored `supply_routes:` waypoints
  trace the corridor you would actually *drive* between two points — the road, the river
  valley, the pass — never a straight line across a ridge. On real-world-coordinate maps,
  generate the intermediate waypoints from the real road network's lat/lon with
  `tools/supply_route_geo.py`.
* **SAM belts by system class.** Legacy/mobile systems (SA-2/3/6, Hawk, generic launcher
  sites) place as single sites — their layouts already carry two guidance radars.
  Strategic belts (S-300/S-400, Patriot, the long-range systems) prefer the
  regiment-by-authoring pattern: several single-radar fire units plus a shared EWR,
  netted by MANTIS. Never stack both redundancy models on the same system.
* **Know the miz's source of truth.** A *generated* campaign miz
  (`tools/build_*_miz.py`) is edited in the generator and re-run — never hand-edit the
  output. A *decorate-a-base* campaign (hand-positioned in the Mission Editor) is the
  opposite: edit the committed `.miz`, never regenerate it. Each campaign's design note
  states which pattern it uses.
* **CI-lock the laydown.** A shipped campaign gets a test that loads it headlessly and
  asserts the laydown (control-point count, key sites, supply routes, setting preseeds)
  so a later edit can't silently drop content.
* **Say when a NEW game is required.** Most laydown, faction, and preseed changes only
  take effect on a fresh campaign — record that in the change description and the design
  note.

## Resources

* [Custom Campaigns](Custom-Campaigns) — how to author and structure a campaign,
  including the campaign YAML format
* [`resources/campaigns/`](https://github.com/bradyccox/414Ret/tree/main/resources/campaigns)
  — the shipped campaign files you'll be editing
* [Issue tracker](https://github.com/bradyccox/414Ret/issues) — report or track campaign
  breakage
* [`game/version.py`](https://github.com/bradyccox/414Ret/blob/main/game/version.py) —
  the `CAMPAIGN_FORMAT_VERSION` constant; check this when a campaign needs migrating to a
  newer save/campaign format
