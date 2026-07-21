# Contributing to DCS Retribution

> **Adopted standard (2026-07-20).** This page is the upstream
> [Contributing to DCS Retribution](https://github.com/dcs-retribution/dcs-retribution/wiki/Contributing-to-DCS-Retribution)
> page, adopted as the 414th's own contribution standard, with **414th:** notes on where
> fork contributions go. When upstream revises their page, refresh this one.

Hello, and thanks for your interest in contributing to DCS Retribution — directly, or
through the 414th's fork.

There are multiple simple ways to contribute to the project indirectly.

* Open an issue on the GitHub repo when you find one. Before opening a bug, please search
  existing issues first (you may need to clear the default "open" filter to find
  already-closed or resolved reports). **414th:** fork problems go to the
  [414Ret issue tracker](https://github.com/bradyccox/414Ret/issues); if the bug
  reproduces on stock Retribution, report it
  [upstream](https://github.com/dcs-retribution/dcs-retribution/issues) as well.
* You can also report bugs on the DCS Retribution Discord server (on the #bugs channel).
* Help new users on Discord.
* Answer questions on the "help wanted" channel on Discord.
* Raise awareness about the project, by making a video and/or a tutorial.

## Contributing campaigns

You don't need to be a programmer to contribute content. You can create new campaigns
(see the [Custom Campaigns](Custom-Campaigns) guide) or improve existing ones, then
submit them — upstream on the "campaigns" channel on Discord or as a Pull Request;
**414th:** as a PR to the fork, or file the
[Campaign Update issue template](https://github.com/bradyccox/414Ret/issues/new?template=campaign_update.md)
with the updated files attached. Volunteering to maintain an existing campaign is also
very welcome — see [Campaign maintenance](Campaign-maintenance).

You can join the upstream Discord here:
[![Discord](https://img.shields.io/discord/595702951800995872?label=Discord&logo=discord)](https://discord.gg/b4x34Bg4We)

And last but not least, you could also help develop new features. For this, refer to the
[Developer's Guide](Developers-Guide), which covers setting up a development environment
(Python virtual environment, dependencies), running the type checker, and the Pull
Request workflow.

## 414th: where a contribution goes

The fork runs a two-repo flow:

1. **Fork work** lands as a PR to
   [`bradyccox/414Ret`](https://github.com/bradyccox/414Ret) `main` — squadron features,
   campaign work, fixes. Every merge to `main` ships automatically as the rolling
   `latest` build (see [Release process](Release-process)).
2. **Upstream carves**: everything is upstreamable ("clean and correct" is the bar —
   there is no permanent fork-only category). Generic fixes and features get carved into
   focused PRs against `dcs-retribution/dev` via the `bradyccox/dcs-retribution` PR
   fork. The queue and readiness marks live in
   [`docs/dev/414th-upstreaming-inventory.md`](https://github.com/bradyccox/414Ret/blob/main/docs/dev/414th-upstreaming-inventory.md),
   and the live upstream-PR ledger in `CLAUDE.md`.

Contributing upstream first and letting the fork pull the change back on the next sync is
equally welcome — that is the healthiest direction of all.

Please also note that upstream has a
[Code of Conduct](https://github.com/dcs-retribution/dcs-retribution/wiki/Code-of-Conduct);
the 414th adopts it — please follow it in all your interactions with the project, here
and upstream.
