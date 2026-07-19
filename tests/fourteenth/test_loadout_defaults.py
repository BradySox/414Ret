"""Tests for the §73 per-(airframe, task) default loadout override.

The point of the feature is that a payload saved under the name a task *resolves* to
overrides Retribution's shipped fit for every future flight, so these drive the real
name resolution and the real payload files against real pydcs airframes, with the
scratch directory registered as pydcs's *preferred* payload dir and the repo's
``customized_payloads`` behind it -- the production arrangement from ``qt_ui.main``.
Asserting against a hardcoded ``"Retribution CAS"`` would pass while the feature
silently missed the slot the planner actually reads.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator, Type

import pytest
from dcs.payloads import PayloadDirectories
from dcs.planes import FA_18C_hornet, F_4E_45MC
from dcs.unittype import FlyingType

from game.ato.flighttype import FlightType
from game.ato.loadouts import Loadout
from game.fourteenth import loadout_defaults

PAYLOADS_DIR = Path(__file__).parent.parent.parent / "resources" / "customized_payloads"


@pytest.fixture(autouse=True)
def user_payloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point both the writers and pydcs at a scratch user payload directory.

    Registering it as the *preferred* directory (repo presets behind it) is what
    makes these tests meaningful: overriding is entirely a question of which
    directory supplies a given payload name first.
    """
    payloads = tmp_path / "UnitPayloads"
    backups = payloads / "_retribution_backups"
    payloads.mkdir(parents=True)
    backups.mkdir()

    def fake_payloads_dir(backup: bool = False) -> Path:
        return backups if backup else payloads

    monkeypatch.setattr(loadout_defaults, "payloads_dir", fake_payloads_dir)
    PayloadDirectories.set_fallback(PAYLOADS_DIR)
    PayloadDirectories.set_preferred(payloads)
    # Class-level pydcs state: force a rescan rather than inherit whatever an
    # earlier test (or the developer's real Saved Games) left cached.
    FlyingType._payload_cache = None  # type: ignore[assignment]
    yield payloads
    FlyingType._payload_cache = None  # type: ignore[assignment]


@pytest.fixture
def hornet() -> Iterator[Type[FlyingType]]:
    """The Hornet, with its parsed payloads reset before and restored after.

    ``FlyingType.payloads`` is process-global class state that the writers mutate on
    purpose, so it has to be put back or later tests inherit the scratch entries.
    """
    original = FA_18C_hornet.payloads
    FA_18C_hornet.payloads = None
    yield FA_18C_hornet
    FA_18C_hornet.payloads = original


def a_payload(name: str, clsid: str = "{FPU-8A}") -> dict[str, Any]:
    return {
        "displayName": name,
        "name": name,
        "pylons": {1: {"CLSID": clsid, "num": 1}},
        "tasks": {1: 31},
    }


def test_override_name_is_the_name_the_task_actually_resolves_to(
    hornet: Type[FlyingType],
) -> None:
    # Not merely "Retribution CAS": the override only bites if it lands in the slot
    # Loadout.default_for reads, so the two must agree by construction.
    for task in (FlightType.CAS, FlightType.STRIKE, FlightType.BARCAP):
        name = loadout_defaults.override_name_for(task, hornet)
        assert name == Loadout.default_for_task_and_aircraft(task, hornet).name


def test_override_name_never_claims_an_expanded_weapons_slot_by_default() -> None:
    # The F-4E is the airframe that ships (XW) fits (§71), for SEAD only. CAS has
    # none, so its override must land on the plain name rather than inventing one.
    name = loadout_defaults.override_name_for(FlightType.CAS, F_4E_45MC)
    assert not Loadout.is_expanded_weapons_name(name)


def test_the_override_becomes_what_the_task_resolves_and_clearing_hands_it_back(
    hornet: Type[FlyingType],
) -> None:
    """The end-to-end claim: save it, and every future flight of the task gets it."""
    task = FlightType.CAS
    name = loadout_defaults.override_name_for(task, hornet)
    stock = Loadout.default_for_task_and_aircraft(task, hornet)
    assert stock.pylons, "this test needs a real shipped preset to override"

    # The shipped fit minus its lowest station: distinguishable from the original,
    # while every CLSID stays real so the payload still validates.
    dropped = min(stock.pylons)
    payload = {
        "displayName": name,
        "name": name,
        "pylons": {
            key: {"CLSID": weapon.clsid, "num": number}
            for key, (number, weapon) in enumerate(sorted(stock.pylons.items()), 1)
            if number != dropped and weapon is not None
        },
        "tasks": {1: 31},
    }

    assert loadout_defaults.write_payload_entry(hornet, name, payload)
    loadout_defaults._reload_payloads(hornet)

    overridden = Loadout.default_for_task_and_aircraft(task, hornet)
    assert overridden.name == name
    assert set(overridden.pylons) == set(stock.pylons) - {dropped}

    assert loadout_defaults.remove_payload_entry(hornet, name)

    restored = Loadout.default_for_task_and_aircraft(task, hornet)
    assert set(restored.pylons) == set(stock.pylons)


def test_write_then_read_back_reports_an_override(
    hornet: Type[FlyingType], user_payloads: Path
) -> None:
    name = loadout_defaults.override_name_for(FlightType.CAS, hornet)
    assert not loadout_defaults.has_override_for(hornet, name)

    assert loadout_defaults.write_payload_entry(hornet, name, a_payload(name))

    assert (user_payloads / f"{hornet.id}.lua").exists()
    assert loadout_defaults.has_override_for(hornet, name)


def test_saving_twice_replaces_the_entry_instead_of_duplicating_it(
    hornet: Type[FlyingType], user_payloads: Path
) -> None:
    name = loadout_defaults.override_name_for(FlightType.CAS, hornet)
    loadout_defaults.write_payload_entry(hornet, name, a_payload(name, "{FIRST}"))
    loadout_defaults.write_payload_entry(hornet, name, a_payload(name, "{SECOND}"))

    payloads = loadout_defaults._load_unit_payloads(user_payloads / f"{hornet.id}.lua")
    assert payloads is not None
    entries = [e for e in payloads["payloads"].values() if e["name"] == name]
    assert len(entries) == 1
    assert entries[0]["pylons"][1]["CLSID"] == "{SECOND}"


def test_clearing_removes_only_the_named_entry(
    hornet: Type[FlyingType], user_payloads: Path
) -> None:
    name = loadout_defaults.override_name_for(FlightType.CAS, hornet)
    loadout_defaults.write_payload_entry(hornet, name, a_payload(name))
    # A payload the user made by hand in the Mission Editor, in the same file.
    loadout_defaults.write_payload_entry(
        hornet, "My Ferry Fit", a_payload("My Ferry Fit")
    )

    assert loadout_defaults.remove_payload_entry(hornet, name)

    assert not loadout_defaults.has_override_for(hornet, name)
    assert loadout_defaults.has_override_for(hornet, "My Ferry Fit")


def test_clearing_an_absent_override_reports_that_it_did_nothing(
    hornet: Type[FlyingType],
) -> None:
    assert not loadout_defaults.remove_payload_entry(hornet, "Never Saved")


def test_a_new_entry_never_lands_on_a_key_already_in_use(
    hornet: Type[FlyingType], user_payloads: Path
) -> None:
    # Keys that do not start at 1 are what a hand-edited or previously-pruned file
    # looks like. Sizing the new key off len() would collide and silently eat one.
    path = user_payloads / f"{hornet.id}.lua"
    loadout_defaults._write_unit_payloads(
        path,
        {
            "name": hornet.id,
            "payloads": {2: a_payload("Second"), 3: a_payload("Third")},
            "unitType": hornet.id,
        },
    )

    loadout_defaults.write_payload_entry(hornet, "Fourth", a_payload("Fourth"))

    payloads = loadout_defaults._load_unit_payloads(path)
    assert payloads is not None
    names = sorted(e["name"] for e in payloads["payloads"].values())
    assert names == ["Fourth", "Second", "Third"]


def test_an_unparseable_file_is_left_alone_rather_than_rewritten(
    hornet: Type[FlyingType], user_payloads: Path
) -> None:
    # Overwriting it would destroy every other payload saved for the airframe. One
    # refused save is much cheaper than that.
    path = user_payloads / f"{hornet.id}.lua"
    corrupt = "local unitPayloads = { this is not lua"
    path.write_text(corrupt, encoding="utf-8")

    assert not loadout_defaults.write_payload_entry(hornet, "Nope", a_payload("Nope"))
    assert path.read_text(encoding="utf-8") == corrupt


def test_the_first_write_backs_the_existing_file_up(
    hornet: Type[FlyingType], user_payloads: Path
) -> None:
    loadout_defaults.write_payload_entry(hornet, "First", a_payload("First"))
    backup = user_payloads / "_retribution_backups" / f"{hornet.id}.lua"
    assert not backup.exists(), "nothing to back up when we created the file"

    loadout_defaults.write_payload_entry(hornet, "Second", a_payload("Second"))
    assert backup.exists()
    assert "First" in backup.read_text(encoding="utf-8")
    assert "Second" not in backup.read_text(encoding="utf-8")


def test_state_checks_degrade_to_no_override_without_a_saved_games_tree(
    hornet: Type[FlyingType], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Read on every payload-tab build, including headless runs where persistency was
    # never set up. It must answer, not raise.
    def explode(backup: bool = False) -> Path:
        raise RuntimeError("no Saved Games")

    monkeypatch.setattr(loadout_defaults, "payloads_dir", explode)
    assert not loadout_defaults.has_override_for(hornet, "Retribution CAS")
