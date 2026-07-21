# Developer's Guide

> **Adopted standard (2026-07-20).** This page is the upstream
> [Developer's Guide](https://github.com/dcs-retribution/dcs-retribution/wiki/Developer's-Guide),
> adopted as the 414th's own development standard — we do things upstream's way.
> Fork-specific differences are called out in **414th:** notes. When upstream revises
> their page, refresh this one and re-check the notes.

Welcome to the dev guide!

## Technical sum up

DCS Retribution is coded in Python, with Qt6 as the UI framework.
It uses [pydcs](https://github.com/pydcs/dcs) to generate DCS World missions.

Before contributing to DCS Retribution, you should also maybe consider contributing to
pydcs — this is a great way to contribute indirectly to the project.

**414th:** pydcs changes go to the upstream project's own fork,
[dcs-retribution/pydcs](https://github.com/dcs-retribution/pydcs) — that is where this
project's pydcs pin points and where our pydcs PRs are sent. Runtime mission behavior
additionally lives in **Lua 5.1 plugins** under `resources/plugins/` (MOOSE is the
in-mission framework; MIST is retired in favor of a compatibility shim) — see
[Lua Plugins](Lua-Plugins) and the Lua notes under
[Type checkers, linters, and tests](#type-checkers-linters-and-tests) below.

## Project history

DCS Liberation was a project started in 2018 by shdwp; the original repo is still
available here: https://github.com/shdwp/dcs_liberation

The original UI was different, and the mission generation process was different as well
from version 2.0+.

DCS Retribution is a 2022 fork of DCS Liberation and is the actively-maintained project
this guide covers. **414Ret** is the 414th Joint Fighter Group's fork of DCS Retribution,
carrying the squadron's features on top of upstream `dev` — see
[What's Different in the 414th Fork](414th-Fork-Overview).

## Required tools

* [Python](https://www.python.org/downloads/) — upstream asks for 3.10+; **414th:** use
  **Python 3.11**, which is what CI pins and what the shipped build runs.
* A code editor for Python.
  [PyCharm Community Edition](https://www.jetbrains.com/pycharm/download/) is
  recommended; you can add a plugin for Lua.
* [Node.js + npm](https://nodejs.org/en/download/) to build the map front-end the first
  time you run from sources (see [Running from sources](#running-from-sources)).

When you install Python, make sure to install pip for dependency management. This should
come preinstalled.

## Checkout the repository code with git

**Branches**

* Upstream **`dev`**: the upstream integration branch — the branch all *upstream* pull
  requests target.
* **414th:** this fork's default and integration branch is **`main`**. Branch from
  `main` and PR back to `main`; never develop directly on `main`. Work destined for
  upstream is carved separately against `dcs-retribution/dev` (see
  [Pull requests](#pull-requests)).

Squadron members with repository access clone the fork directly:

```
git clone https://github.com/bradyccox/414Ret.git
```

Outside contributors: fork the repository through the GitHub UI first (the upstream
flow), then clone your fork the same way.

## Creating a Python virtual environment

A Python virtual environment (virtualenv) is a local copy of the Python distribution for
a specific project. This allows you to install the project dependencies local to the
environment rather than globally on your system, which makes it easier to reset your
environment if something goes wrong.

To create and use a virtualenv, run:

```
cd 414Ret
python -m venv ./venv
```

Then activate it. The command depends on your shell:

* **Windows, git-bash**: `source venv/Scripts/activate`
* **Windows, PowerShell**: `.\venv\Scripts\Activate.ps1`
* **Windows, cmd.exe**: `.\venv\Scripts\activate.bat`
* **macOS / Linux**: `source venv/bin/activate`

Once the virtualenv is **activated**, install the dependencies and the pre-commit hooks:

```
python -m pip install -r requirements.txt
pre-commit install
```

The first command creates the virtualenv in the directory `venv` (this matches the
directory name the CI pipeline uses). Activating it replaces the `python` and `pip` for
the current shell with the ones in the virtualenv — do this **before** installing,
otherwise the dependencies land in your system Python. The last command installs the
pre-commit hooks that run the auto-formatter on commit.

Whenever you open a new terminal, you'll need to re-run the activate command for your
platform.

**414th:** the DM's dev checkout names the environment `.venv` rather than `venv` (the
validation commands in
[`docs/dev/CLAUDE-ci.md`](https://github.com/bradyccox/414Ret/blob/main/docs/dev/CLAUDE-ci.md)
are written against `.venv`). Either name works — adjust paths to whichever your checkout
uses.

If you're using PyCharm, you can configure the project to use your virtualenv in the
project settings:
![virtualenv project settings](https://user-images.githubusercontent.com/315852/117738890-e6890800-b1b1-11eb-9eec-1796af594e79.png)

## Running from sources

### Windows terminal (using git-bash)

If you run from sources for the first time, you need to build the frontend, otherwise you
won't be able to see the map. For the frontend to build, you need npm installed, which
you can get on the [Node.js webpage](https://nodejs.org/en/download/). After installing
node.js and npm, do the following for the first build:

```
cd client
npm install
npm run build
```

Every time you update the repo you should rebuild the front-end:

```
cd client
npm run build
```

If you're not developing the front-end (or the API boundary) that's enough. Otherwise,
see `client/README.md`.

**414th:** the React/Leaflet client is **not** type-checked in CI, and many fork features
carry a "needs the CI client rebuild" note — the release workflows always build the
client fresh, so a stale local build only affects your own map view. Rebuild after every
pull that touches `client/`.

Set up your virtual env (described above), activate your env, then:

```
PYTHONPATH=. python ./qt_ui/main.py
```

### OS X terminal

Set up your virtual env (described above), activate your env, then:

```
PYTHONPATH=. LOCALAPPDATA=. python ./qt_ui/main.py
```

The `LOCALAPPDATA=.` environment variable will result in settings files being put in a
sub folder in your local dev directory.

### Running from PyCharm

You can run DCS Retribution from source with this configuration (adapt it to your env):

![PyCharm run configuration](https://user-images.githubusercontent.com/89945461/132121682-0c48c318-dd70-4d82-a506-fd62be241403.png)

### Command-line options

`qt_ui/main.py` accepts a few options beyond a plain launch:

* `--dev` — enable development mode (used with the front-end dev server above).
* `--show-sim-speed-controls` / `--no-show-sim-speed-controls` — show or hide the
  sim-speed controls in the top panel.

It also has subcommands for headless / tooling tasks:

* `new-game` — generate a game without the UI. Flags include `--blue`, `--red`,
  `--supercarrier`, `--auto-procurement`, `--use-new-squadron-rules`, `--inverted`,
  `--date`, `--restrict-weapons-by-date`, `--cheats`, and `--advanced-iads`.
* `lint-weapons <aircraft>` — check the weapon data for an aircraft variant.
* `dump-task-priorities` — dump the AI task-priority tables.

## Type checkers, linters, and tests

We use [black](https://github.com/psf/black) for auto-formatting. The pre-commit hook
will automatically run the formatter when you make a commit. See their docs for
instructions on configuring black to run in your editor.

We use [mypy](https://mypy.readthedocs.io/en/stable/) for type checking. Python has
built-in support for type annotations but does not perform any checking; that work is
delegated to tools like mypy. **All new code should include type annotations**, and it's
generally a good idea to add type annotations to any function you touch.

To check for type errors, run both of these — CI runs each as a required gate:

```
mypy game
mypy tests
```

`qt_ui` is not type-checked because PySide6 (the Python Qt API) contains many patterns
that do not play well with the type checker, but it's good to add the annotations anyway
as they help the reader.

The type checker is **not** run as part of pre-commit, since that makes it harder to
create WIP commits, but it is run as part of the PR and build checks, so it's best to run
before uploading a PR.

**414th: the full CI gate.** Every push to `main` runs (always-current list in
[`docs/dev/CLAUDE-ci.md`](https://github.com/bradyccox/414Ret/blob/main/docs/dev/CLAUDE-ci.md)):

1. **Black over the whole tree** (`black --check .`) — a formatting miss anywhere fails
   CI, including `qt_ui` and `tests`; mypy stays scoped to `game` + `tests` as upstream
   describes.
2. **pytest** over `tests` **plus** the three out-of-tree test dirs under `game/`
   (`game/missiongenerator/tests`, `game/missiongenerator/kneeboard_recon/tests`,
   `game/plugins/tests`).
3. **Lua syntax gate** (blocking): `luac5.1 -p` over every `resources/plugins/**/*.lua`,
   plus an advisory luacheck pass.
4. The rolling-release build (see [Release process](Release-process)).

The local pre-push trio (PowerShell, against a `.venv` checkout):

```powershell
.venv\Scripts\python.exe -m black --check .
.venv\Scripts\python.exe -m mypy game tests
.venv\Scripts\python.exe -m pytest tests game/missiongenerator/tests game/missiongenerator/kneeboard_recon/tests game/plugins/tests -q
```

**414th: Lua.** Plugins are Lua 5.1 sandbox scripts (no `os`/`io`, no `goto`, define
functions before first use, vanilla DCS units only). Beyond the syntax gate, the headless
harness in `tests/lua/` runs the real plugin scripts on Lua 5.1 (via `lupa`) against a
faked DCS sandbox inside the normal pytest run — run and extend it when you touch a
covered plugin. It models no DCS AI or physics, so real behavior still needs an in-game
pass (tracked in `docs/dev/414th-ingame-pass-checklist.md`). When merging upstream Lua,
grep it for `mist.` — MIST is retired here, and a symbol the compatibility shim lacks
dies at runtime, not in CI.

## Making a release

[Release process](Release-process)

## Pull requests

Please make a new branch and make your pull requests to the integration branch —
**414th:** branch from `main`, PR to `bradyccox/414Ret` `main`. (Upstream: branch from
`dev`, PR to `dcs-retribution/dev`.)

We can only merge/revert whole PRs, which means you should try and keep the size of each
individual PR as small as possible. Ideally, **one PR for one feature/bugfix/change**.
Also, review latency doesn't scale linearly with review time, and review time doesn't
scale linearly with PR complexity. **Smaller PRs will likely get reviewed sooner and
faster.** In addition, it's not possible for the testers to isolate bugs on a sub-build
level.

New features and bug fixes in pull requests are usually worth mentioning in the
changelog. Exceptions are fixes for bugs that never shipped (were only present in a
canary build), and changes with no intended user-observable behavior, such as a refactor.
If you're comfortable writing the note yourself, add it to `changelog.md` in the root of
the project in the section for the upcoming release.

**414th:** three fork-side additions to the upstream PR standard:

* **Docs move with the code.** Update the doc faces in the order `CLAUDE.md` prescribes
  (design note → `docs/dev/414th-features.md` → `README.md` if player-visible →
  `CLAUDE.md`/`AGENTS.md` → the in-game-pass checklist). A push that moves code past its
  docs is a broken push.
* **Commit messages are release notes.** The rolling `latest` release generates its
  changelog from commit history — write messages the squadron can read. Keep
  `changelog.md` current as well when a change is destined for upstream.
* **Everything is upstreamable** (2026-07-19 policy): "clean and correct" is the bar —
  there is no permanent fork-only category. Generic fixes get carved into focused PRs
  against `dcs-retribution/dev` via the `bradyccox/dcs-retribution` PR fork. Check the
  upstream-PR ledger in `CLAUDE.md` and
  [`docs/dev/414th-upstreaming-inventory.md`](https://github.com/bradyccox/414Ret/blob/main/docs/dev/414th-upstreaming-inventory.md)
  first — including the "crowded zones" list of upstream areas with active third-party
  PRs that we do not carve into without coordinating.

If you're new to GitHub, https://guides.github.com/introduction/flow/ and the other
tutorials on that site may be helpful.
