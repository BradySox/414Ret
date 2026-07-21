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

**https://github.com/bradyccox/414Ret/releases/tag/latest**

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
   [Releases](https://github.com/bradyccox/414Ret/releases).
7. Announce the release. (**414th:** the squadron's channels; upstream announces in
   their Discord #releases.)
