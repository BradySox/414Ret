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
  [414Ret issue tracker](https://github.com/BradySox/414Ret/issues); if the bug
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
[Campaign Update issue template](https://github.com/BradySox/414Ret/issues/new?template=campaign_update.md)
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
   [`BradySox/414Ret`](https://github.com/BradySox/414Ret) `main` — squadron features,
   campaign work, fixes. Every merge to `main` ships automatically as the rolling
   `latest` build (see [Contributing to DCS Retribution](Contributing-to-DCS-Retribution)).
2. **Upstream carves**: everything is upstreamable ("clean and correct" is the bar —
   there is no permanent fork-only category). Generic fixes and features get carved into
   focused PRs against `dcs-retribution/dev` via the `BradySox/dcs-retribution` PR
   fork. The queue and readiness marks live in
   [`docs/dev/414th-upstreaming-inventory.md`](https://github.com/BradySox/414Ret/blob/main/docs/dev/414th-upstreaming-inventory.md),
   and the live upstream-PR ledger in `CLAUDE.md`.

Contributing upstream first and letting the fork pull the change back on the next sync is
equally welcome — that is the healthiest direction of all.

Please also note that upstream has a
[Code of Conduct](https://github.com/dcs-retribution/dcs-retribution/wiki/Code-of-Conduct);
the 414th adopts it — please follow it in all your interactions with the project, here
and upstream.

---

# Release process
> **Adopted standard (2026-07-20).** The pinned-release steps below are the upstream
> [Release process](https://github.com/dcs-retribution/dcs-retribution/wiki/Release-process),
> adopted as the 414th's own process for pinned builds. The fork's *primary* release
> channel — the rolling `latest` build — is described first, because it is fully
> automatic and has hard rules attached. When upstream revises their page, refresh this
> one.

## The rolling `latest` build (the squadron's primary channel)

Every push to `main` runs `414th-latest.yml`: lint and tests gate the build, PyInstaller
packages the app on Windows, and the workflow **upserts a rolling pre-release tagged
`latest`**. The permanent download URL the squadron bookmarks:

**https://github.com/BradySox/414Ret/releases/tag/latest**

There is nothing to do to "make" this release — merging to `main` is the release. Rules
(pinned in `CLAUDE.md`):

* The `latest` tag is **owned by the workflow**. Never delete it and never push it
  manually — breaking it breaks the squadron's bookmarked URL.
* Never run `git push --tags`: your local clone carries the `latest` tag, and pushing it
  by hand clobbers the rolling release. Push specific tags only (see below).
* Do **not** modify `414th-latest.yml` without understanding the impact. Test in a
  branch and verify the `latest` release after merging.
* Release notes are generated from recent commit history — write commit messages the
  squadron can read.

## Pinned releases (the upstream process, adopted)

The `release.yml` workflow (inherited from upstream) builds and publishes a versioned
release from **any pushed tag**. Fork tag convention:
**`v$MAJOR.$MINOR.$PATCH-414th`** (e.g. `v1.6.2-414th` — the existing pinned builds),
marking which upstream version line the build is based on; upstream itself tags plain
`$MAJOR.$MINOR.$PATCH` (e.g. `1.6.0`).

To release a pinned version of the fork, follow upstream's steps:

1. Make sure the version number and changelog are up to date in the release branch. If
   the changelog needs to be updated, fix it in the integration branch first
   (**414th:** `main`; upstream: `dev`) and cherry-pick the updates to the release
   branch so they stay in sync. (**414th:** we usually tag `main` directly rather than
   keeping a separate release branch — in that case this step is just "make sure `main`
   is green and the docs/changelog are current.")
2. Announce a preview build before creating the release, with a link to the GitHub
   Action build for the specific branch, and wait some time. This allows you to get some
   feedback on the build. (**414th:** the rolling `latest` build *is* the standing
   preview — announce the candidate build to the squadron and let it get flown.)
3. When everything is ready for release, tag the corresponding branch. **Do not create a
   release by hand.** A release will be created and published automatically by the
   GitHub action from the tag. For example:
   `git tag v1.6.3-414th && git push origin v1.6.3-414th` — push the specific tag rather
   than `--tags`, which would push every local tag (**414th:** including your local
   `latest`, which must never be pushed manually).
4. Smoke test the tagged build.
5. Update the bug templates in `.github` to allow reporting bugs against the new
   release. Old versions should be removed.
6. Verify the release. The GitHub action publishes the release automatically (non-draft)
   as soon as the tag is pushed, with the description pre-filled from the changelog —
   there is no manual "promote to release" step. Just confirm it appears correctly in
   [Releases](https://github.com/BradySox/414Ret/releases).
7. Announce the release. (**414th:** the squadron's channels; upstream announces in
   their Discord #releases.)
