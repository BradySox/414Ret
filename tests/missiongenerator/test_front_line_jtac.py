"""The front-line JTAC is the ONLY JTAC model, gated on nothing but `has_jtac`.

Background (2026-08-05). The fork briefly ran two mutually-exclusive JTAC models:
upstream's invisible/immortal FAC orbiting the FLOT, and a 414th packaged drone
that rode air-to-ground packages and lased from there
(`AircraftGenerator._maybe_configure_jtac`, gated by `coin_packaged_jtac_drone`).
The drone model was stripped on a DM call, leaving the front-line FAC as the only
model -- and the strip deleted the only tests that touched this code path, which
had covered the *drone* side and the exclusion between them.

That left the build's sole JTAC model with zero coverage, so these replace it. The
full generator body cannot be exercised here (it builds a real pydcs flight group,
resolves a livery, and needs theater geometry for `frontline_position`), but the
part the strip actually CHANGED is the gate, and that is exactly what is worth
pinning: a future change must not reintroduce a second suppression condition in
front of the FAC.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from game.missiongenerator import flotgenerator
from game.missiongenerator.flotgenerator import FlotGenerator


class _ReachedTheBody(Exception):
    """Raised from the first call past the gate, so we can detect the gate opening."""


def _generator(*, has_jtac: bool) -> FlotGenerator:
    gen = FlotGenerator.__new__(FlotGenerator)
    gen.game = SimpleNamespace(  # type: ignore[assignment]
        blue=SimpleNamespace(faction=SimpleNamespace(has_jtac=has_jtac)),
        theater=SimpleNamespace(),
        settings=SimpleNamespace(plugins={}),
    )
    gen.conflict = SimpleNamespace(front_line=SimpleNamespace())  # type: ignore[assignment]
    gen.radio_registry = SimpleNamespace(  # type: ignore[assignment]
        alloc_uhf=lambda: pytest.fail("allocated a radio past a closed gate")
    )
    gen.mission_data = SimpleNamespace(jtacs=[])  # type: ignore[assignment]
    return gen


def test_a_faction_without_a_jtac_generates_none(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        flotgenerator.FrontLineConflictDescription,
        "frontline_position",
        staticmethod(lambda *a, **k: (_ for _ in ()).throw(_ReachedTheBody())),
    )
    gen = _generator(has_jtac=False)

    gen._generate_front_line_jtac()

    assert gen.mission_data.jtacs == []


def test_has_jtac_is_the_only_gate(monkeypatch: Any) -> None:
    """A faction that fields a JTAC reaches the body -- nothing else suppresses it.

    This is the regression guard for the strip: the drone model used to short-circuit
    this method via a setting BEFORE the `has_jtac` check. If anything ever returns
    early again for a JTAC-fielding faction, the sentinel is never raised and this
    fails.
    """
    monkeypatch.setattr(
        flotgenerator.FrontLineConflictDescription,
        "frontline_position",
        staticmethod(lambda *a, **k: (_ for _ in ()).throw(_ReachedTheBody())),
    )
    gen = _generator(has_jtac=True)

    with pytest.raises(_ReachedTheBody):
        gen._generate_front_line_jtac()


def test_the_stripped_drone_setting_is_gone() -> None:
    """The rip must not leave a dead gate behind for someone to re-wire."""
    from game.settings import Settings

    settings = Settings()
    assert not hasattr(settings, "coin_packaged_jtac_drone")
    assert not hasattr(settings, "auto_jtac_drone")
