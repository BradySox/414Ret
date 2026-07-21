"""Headless runtime check for the air-droppable minefields plugin (minefields-config.lua).

Pins the same-turn mining path: a blue drop of the dispenser (CBU-99) lays a proximity
minefield at the weapon's ground impact, and an enemy (RED) ground unit crossing it trips a
mine (a real trigger.action.explosion). One-trip-per-unit + charge depletion bound the field;
a non-dispenser drop or a red drop lays nothing; the startup grace holds detonation; a
persisted (seeded) field re-arms; and a mission with nothing dropped is a clean no-op.

The explosion is the observable -- the harness models no DCS AI/physics/weapon flight, so the
actual convoy kill (and that DCS reports the death for native loss accounting) is confirmed by
the in-game pass. Detonation is made deterministic here with tripChancePct=100.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/minefields/minefields-config.lua"


def _shooter(name: str = "Striker") -> dict[str, Any]:
    return {
        "name": name,
        "side": 2,  # BLUE
        "category": 0,  # AIRPLANE
        "units": [
            {
                "name": name + "-1",
                "type": "A-7E",
                "x": 0.0,
                "z": 0.0,
                "alt": 3000,
                "airborne": True,
            }
        ],
    }


def _red_shooter(name: str = "RedStriker") -> dict[str, Any]:
    spec = _shooter(name)
    spec["side"] = 1  # RED
    spec["units"][0]["type"] = "Su-25"
    return spec


def _red_ground(name: str, x: float, z: float, count: int = 1) -> dict[str, Any]:
    return {
        "name": name,
        "side": 1,  # RED
        "category": 2,  # GROUND
        "units": [
            {"name": f"{name}-{i}", "type": "Ural-375", "x": x, "z": z}
            for i in range(1, count + 1)
        ],
    }


def _load(
    h: DcsPluginHarness, *, fields: list[dict[str, Any]] | None = None, **opts: Any
) -> None:
    base: dict[str, Any] = {
        "tripChancePct": 100,  # deterministic: every crossing vehicle trips
        "startGraceS": 10,
        "scanIntervalS": 5,
        "detonationCooldownS": 0,
        "fieldRadiusFt": 656,  # ~200 m
        "chargesPerField": 6,
    }
    base.update(opts)
    cfg: dict[str, Any] = {"plugins": {"minefields": base}}
    if fields is not None:
        cfg["minefields"] = {"fields": fields}
    h.lua.globals().dcsRetribution = h.to_lua(cfg)
    h.load_plugin_script(PLUGIN)


def _drop(
    h: DcsPluginHarness,
    x: float,
    z: float,
    *,
    wtype: str = "CBU_99",
    shooter: str = "Striker",
) -> None:
    # The dispenser sits at (x, z) and vanishes at t+1 -> the tracker resolves that impact point.
    h.fire_shot(
        {
            "weapon": {
                "typeName": wtype,
                "x": x,
                "z": z,
                "alt": 0,
                "vanishAt": h.harness.now + 1,
            },
            "initiator": shooter,
        }
    )


def test_drop_lays_a_field_that_detonates_on_a_crossing_convoy() -> None:
    h = DcsPluginHarness()
    h.add_group(_shooter())
    h.add_group(_red_ground("Convoy-1", 1000.0, 0.0))  # sits on the drop point
    _load(h)
    _drop(h, 1000.0, 0.0)

    # The weapon tracks + the field is laid (~t=1), but the grace holds detonation.
    h.advance_to(3)
    assert h.records("explosions") == []
    assert any("laid" in t["text"].lower() for t in h.records("texts"))

    # Past the grace: the convoy sitting in the field trips a mine.
    h.advance_to(30)
    booms = h.records("explosions")
    assert booms, "a convoy inside a laid field must trip a mine"
    assert booms[0]["power"] == 100
    assert booms[0]["x"] == 1000.0 and booms[0]["z"] == 0.0
    h.assert_no_lua_errors()


def test_one_trip_per_unit_and_charges_deplete() -> None:
    h = DcsPluginHarness()
    h.add_group(_shooter())
    # Three vehicles parked in the field, but only two charges.
    h.add_group(_red_ground("Convoy-1", 1000.0, 0.0, count=3))
    _load(h, chargesPerField=2)
    _drop(h, 1000.0, 0.0)

    h.advance_to(120)
    booms = h.records("explosions")
    # Two charges -> exactly two detonations (one per vehicle), then the field clears; the
    # third vehicle drives on. No vehicle trips twice.
    assert len(booms) == 2
    assert (
        len(h.records("removedMarks")) == 1
    )  # the exhausted field's F10 mark is cleared
    h.assert_no_lua_errors()


def test_non_dispenser_drop_lays_nothing() -> None:
    h = DcsPluginHarness()
    h.add_group(_shooter())
    h.add_group(_red_ground("Convoy-1", 1000.0, 0.0))
    _load(h)
    _drop(h, 1000.0, 0.0, wtype="MK_82")  # an ordinary bomb, not the dispenser

    h.advance_to(60)
    assert h.records("explosions") == []
    h.assert_no_lua_errors()


def test_red_drop_lays_nothing() -> None:
    h = DcsPluginHarness()
    h.add_group(_red_shooter())
    h.add_group(_red_ground("Convoy-1", 1000.0, 0.0))
    _load(h)
    _drop(
        h, 1000.0, 0.0, shooter="RedStriker"
    )  # blue-only v1: a red drop lays no mines

    h.advance_to(60)
    assert h.records("explosions") == []
    h.assert_no_lua_errors()


def test_grace_holds_detonation() -> None:
    h = DcsPluginHarness()
    h.add_group(_red_ground("Convoy-1", 1000.0, 0.0))
    # A persisted (seeded) field, exercising the prior-turn re-arm path the emitter fills later.
    _load(
        h,
        startGraceS=300,
        fields=[{"id": 7, "x": 1000.0, "z": 0.0, "radius": 200, "charges": 4}],
    )

    h.advance_to(250)  # inside the 300 s grace
    assert h.records("explosions") == []

    h.advance_to(400)  # past the grace -> the seeded field is live
    assert h.records(
        "explosions"
    ), "a seeded field must detonate once the grace expires"
    h.assert_no_lua_errors()


def test_no_drop_is_a_clean_noop() -> None:
    h = DcsPluginHarness()
    h.add_group(_red_ground("Convoy-1", 1000.0, 0.0))
    _load(h)  # armed, but nothing is ever dropped
    h.advance_to(600)
    assert h.records("explosions") == []
    h.assert_no_lua_errors()


# -- Phase 2: the minefields_state write-back channel (Python reconciles this at debrief) -----


def _state(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return h.to_python(h.lua.globals().minefields_state) or []


def test_writes_state_for_a_laid_field() -> None:
    h = DcsPluginHarness()
    h.add_group(_shooter())
    _load(h)
    _drop(h, 1000.0, 0.0)
    h.advance_to(3)  # the weapon tracks + the field is laid (~t=1)
    state = _state(h)
    assert len(state) == 1
    assert state[0]["id"] == 0  # newly laid -> Python assigns the id
    assert state[0]["x"] == 1000.0 and state[0]["z"] == 0.0 and state[0]["charges"] == 6
    h.assert_no_lua_errors()


def test_state_charges_deplete_on_detonation() -> None:
    h = DcsPluginHarness()
    h.add_group(_shooter())
    h.add_group(_red_ground("Convoy-1", 1000.0, 0.0, count=2))
    _load(h, chargesPerField=3)
    _drop(h, 1000.0, 0.0)
    h.advance_to(120)
    state = _state(h)
    assert len(state) == 1
    # 3 charges, 2 vehicles cross -> 2 detonations -> 1 charge reported remaining.
    assert state[0]["charges"] == 1
    h.assert_no_lua_errors()


def test_seeded_field_reports_its_persisted_id() -> None:
    h = DcsPluginHarness()
    h.add_group(_red_ground("Convoy-1", 1000.0, 0.0))
    _load(
        h,
        startGraceS=300,
        fields=[{"id": 7, "x": 1000.0, "z": 0.0, "radius": 200, "charges": 4}],
    )
    h.advance_to(10)  # inside the grace -> undisturbed
    state = _state(h)
    assert len(state) == 1
    assert state[0]["id"] == 7 and state[0]["charges"] == 4
    h.assert_no_lua_errors()
