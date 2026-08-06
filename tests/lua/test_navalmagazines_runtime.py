"""Headless runtime check for the naval-magazines plugin (navalmagazines-config.lua).

Pins the "script errors and the feature silently never starts" invariant plus the
§81 safety contract: releases are spread across the window rather than landing
together (the §49 lesson), a real anti-ship shot decrements the emitted magazine
and mirrors into ``naval_magazines_state`` for the turn-boundary debit, a spent
group is dropped back to ReturnFire (winchester, never weapons-hold), a group
that starts dry is never released, land-attack weapons are ignored so §63's
magazine is never double-charged, and a mission with no navalMagazines node is a
clean no-op.

Release-on-attack (the 2026-08-05 flown finding — a DCS group on ReturnFire
mounts no missile defense at all): the first ENEMY weapon aimed at (SHOT target)
or landing on (HIT) a managed group frees it to weapons-free immediately — held
or winchester — a friendly shot never does, and an attacked winchester group
keeps defending (its overshoot stays counted).
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/navalmagazines/navalmagazines-config.lua"

ROE_ID = 0
ROE_WEAPON_FREE = 0
ROE_RETURN_FIRE = 3


def _ship_group(
    name: str, side: int, *, x: float = 0.0, z: float = 0.0
) -> dict[str, Any]:
    return {
        "name": name,
        "side": side,
        "category": 3,  # SHIP
        "units": [
            {"name": name + "-1", "type": "USS_Arleigh_Burke_IIa", "x": x, "z": z}
        ],
    }


def _config(
    magazines: list[dict[str, Any]],
    *,
    stagger: bool = True,
    metered: bool = True,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "plugins": {"navalmagazines": options or {}},
        "navalMagazines": {
            # Values arrive as strings from the emitter; the plugin coerces.
            "stagger": "true" if stagger else "false",
            "metered": "true" if metered else "false",
            "magazines": magazines,
        },
    }


def _load(h: DcsPluginHarness, config: dict[str, Any]) -> None:
    h.lua.globals().dcsRetribution = h.to_lua(config)
    h.load_plugin_script(PLUGIN)


def _roe(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return [r for r in h.records("options") if r.get("option") == ROE_ID]


def _state(h: DcsPluginHarness) -> list[dict[str, Any]]:
    return h.to_python(h.lua.globals().naval_magazines_state) or []


def test_releases_are_spread_across_the_window_not_stacked() -> None:
    h = DcsPluginHarness()
    names = ["0001 | A", "0002 | B", "0003 | C"]
    for name in names:
        h.add_group(_ship_group(name, int(h.side.BLUE)))
    _load(
        h,
        _config(
            [{"group": n, "coalition": "blue", "remaining": "8"} for n in names],
            options={"releaseMinS": 100, "releaseMaxS": 400},
        ),
    )
    h.advance_to(500)
    h.assert_no_lua_errors()

    released = [r for r in _roe(h) if r["value"] == ROE_WEAPON_FREE]
    assert {r["group"] for r in released} == set(names)
    times = sorted(r["t"] for r in released)
    # Evenly spread over [100, 400] for three groups.
    assert times == [100, 250, 400]


def test_nothing_is_released_before_the_window_opens() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("0001 | A", int(h.side.BLUE)))
    _load(
        h,
        _config(
            [{"group": "0001 | A", "coalition": "blue", "remaining": "8"}],
            options={"releaseMinS": 300, "releaseMaxS": 300},
        ),
    )
    h.advance_to(299)
    assert _roe(h) == []
    h.advance_to(301)
    assert [r["value"] for r in _roe(h)] == [ROE_WEAPON_FREE]
    h.assert_no_lua_errors()


def test_a_dry_group_is_never_released() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("0001 | Spent", int(h.side.BLUE)))
    _load(
        h,
        _config(
            [{"group": "0001 | Spent", "coalition": "blue", "remaining": "0"}],
            options={"releaseMinS": 100, "releaseMaxS": 100},
        ),
    )
    h.advance_to(300)
    h.assert_no_lua_errors()
    assert [r for r in _roe(h) if r["value"] == ROE_WEAPON_FREE] == []


def test_a_dry_group_is_pulled_to_return_fire_when_the_stagger_is_off() -> None:
    """Without the stagger the generator left every ship weapons-free, so a group
    that starts the mission spent must be pulled back at load."""
    h = DcsPluginHarness()
    h.add_group(_ship_group("0001 | Spent", int(h.side.BLUE)))
    h.add_group(_ship_group("0002 | Loaded", int(h.side.BLUE)))
    _load(
        h,
        _config(
            [
                {"group": "0001 | Spent", "coalition": "blue", "remaining": "0"},
                {"group": "0002 | Loaded", "coalition": "blue", "remaining": "4"},
            ],
            stagger=False,
        ),
    )
    h.assert_no_lua_errors()
    held = [r for r in _roe(h) if r["value"] == ROE_RETURN_FIRE]
    assert [r["group"] for r in held] == ["0001 | Spent"]


def test_an_antiship_shot_decrements_and_mirrors_into_the_state() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("0001 | Burke", int(h.side.BLUE)))
    _load(
        h,
        _config(
            [{"group": "0001 | Burke", "coalition": "blue", "remaining": "3"}],
            stagger=False,
        ),
    )
    for _ in range(2):
        h.fire_shot(
            {"initiator": "0001 | Burke", "weapon": {"typeName": "AGM_84D_Harpoon"}}
        )
    h.assert_no_lua_errors()
    assert _state(h) == [{"group": "0001 | Burke", "fired": 2}]
    assert h.lua.globals().dirty_state is True
    # Still has one left, so it has NOT been dropped to return fire.
    assert [r for r in _roe(h) if r["value"] == ROE_RETURN_FIRE] == []


def test_the_last_shot_takes_the_group_winchester_to_return_fire() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("0001 | Burke", int(h.side.BLUE)))
    _load(
        h,
        _config(
            [{"group": "0001 | Burke", "coalition": "blue", "remaining": "1"}],
            stagger=False,
        ),
    )
    h.fire_shot({"initiator": "0001 | Burke", "weapon": {"typeName": "RGM_84F"}})
    h.assert_no_lua_errors()
    held = [r for r in _roe(h) if r["value"] == ROE_RETURN_FIRE]
    assert [r["group"] for r in held] == ["0001 | Burke"]
    assert _state(h) == [{"group": "0001 | Burke", "fired": 1}]
    # Winchester is announced to the owning coalition.
    assert any("WINCHESTER" in str(t.get("text", "")) for t in h.records("texts"))


def test_a_land_attack_shot_is_never_charged_to_the_antiship_magazine() -> None:
    """§63's cruise missiles must not spend §81's stock, and vice versa."""
    h = DcsPluginHarness()
    h.add_group(_ship_group("0001 | Burke", int(h.side.BLUE)))
    _load(
        h,
        _config(
            [{"group": "0001 | Burke", "coalition": "blue", "remaining": "2"}],
            stagger=False,
        ),
    )
    for weapon in ("BGM_109B", "weapons.missiles.BGM_109B", "3M14"):
        h.fire_shot({"initiator": "0001 | Burke", "weapon": {"typeName": weapon}})
    h.assert_no_lua_errors()
    assert _state(h) == []
    assert _roe(h) == []


def test_a_shot_from_an_untracked_group_is_ignored() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("0001 | Burke", int(h.side.BLUE)))
    h.add_group(_ship_group("0009 | Stranger", int(h.side.RED)))
    _load(
        h,
        _config(
            [{"group": "0001 | Burke", "coalition": "blue", "remaining": "2"}],
            stagger=False,
        ),
    )
    h.fire_shot({"initiator": "0009 | Stranger", "weapon": {"typeName": "YJ-83"}})
    h.assert_no_lua_errors()
    assert _state(h) == []


def test_metering_off_leaves_shots_uncounted() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("0001 | Burke", int(h.side.BLUE)))
    _load(
        h,
        _config(
            [{"group": "0001 | Burke", "coalition": "blue", "remaining": "2"}],
            metered=False,
            options={"releaseMinS": 100, "releaseMaxS": 100},
        ),
    )
    h.advance_to(200)
    h.fire_shot({"initiator": "0001 | Burke", "weapon": {"typeName": "YJ-83"}})
    h.assert_no_lua_errors()
    assert _state(h) == []
    # The stagger still runs, and with metering off a dry emit cannot hold it.
    assert [r["value"] for r in _roe(h)] == [ROE_WEAPON_FREE]


def test_an_enemy_shot_at_a_held_group_releases_it_immediately() -> None:
    """The hold decides who STARTS the war, never who may defend — a targeted
    group goes weapons-free at the shot, and its scheduled release is a no-op."""
    h = DcsPluginHarness()
    h.add_group(_ship_group("0001 | Held", int(h.side.BLUE)))
    h.add_group(_ship_group("0099 | Raider", int(h.side.RED)))
    _load(
        h,
        _config(
            [{"group": "0001 | Held", "coalition": "blue", "remaining": "8"}],
            options={"releaseMinS": 300, "releaseMaxS": 300},
        ),
    )
    h.advance_to(50)
    h.fire_shot(
        {
            "initiator": "0099 | Raider",
            "weapon": {"typeName": "AGM_84D_Harpoon"},
            "target": "0001 | Held",
        }
    )
    freed = [r for r in _roe(h) if r["value"] == ROE_WEAPON_FREE]
    assert [(r["group"], r["t"]) for r in freed] == [("0001 | Held", 50)]
    # The scheduled stagger release later must not double-fire.
    h.advance_to(400)
    h.assert_no_lua_errors()
    freed = [r for r in _roe(h) if r["value"] == ROE_WEAPON_FREE]
    assert len(freed) == 1


def test_an_attack_frees_the_escort_screen_but_not_the_next_task_force() -> None:
    """The flown geometry: a screen rides 1.91 km off its flagship and the next
    task force was 59 km away. Attacking the flagship must free the escorts —
    they carry the area-defence SAMs — and nobody else."""
    h = DcsPluginHarness()
    h.add_group(_ship_group("0057 | LHA", int(h.side.BLUE), x=0, z=0))
    h.add_group(_ship_group("0058 | Escort", int(h.side.BLUE), x=1910, z=0))
    h.add_group(_ship_group("0051 | Far Group", int(h.side.BLUE), x=59_020, z=0))
    h.add_group(_ship_group("0099 | Raider", int(h.side.RED), x=200_000, z=0))
    _load(
        h,
        _config(
            [
                {"group": "0057 | LHA", "coalition": "blue", "remaining": "8"},
                {"group": "0058 | Escort", "coalition": "blue", "remaining": "8"},
                {"group": "0051 | Far Group", "coalition": "blue", "remaining": "8"},
            ],
            options={"releaseMinS": 3000, "releaseMaxS": 3000},
        ),
    )
    h.advance_to(100)
    h.fire_shot(
        {
            "initiator": "0099 | Raider",
            "weapon": {"typeName": "AGM_84D_Harpoon"},
            "target": "0057 | LHA",
        }
    )
    h.assert_no_lua_errors()
    freed = {r["group"] for r in _roe(h) if r["value"] == ROE_WEAPON_FREE}
    assert freed == {"0057 | LHA", "0058 | Escort"}


def test_the_formation_release_is_one_hop_never_a_cascade() -> None:
    """A neighbour freed by the formation rule does not free ITS neighbours, so
    an attack cannot ripple across the whole fleet."""
    h = DcsPluginHarness()
    h.add_group(_ship_group("A | Hit", int(h.side.BLUE), x=0, z=0))
    h.add_group(_ship_group("B | Near", int(h.side.BLUE), x=10_000, z=0))
    h.add_group(_ship_group("C | Beyond", int(h.side.BLUE), x=20_000, z=0))
    h.add_group(_ship_group("R | Raider", int(h.side.RED), x=200_000, z=0))
    _load(
        h,
        _config(
            [
                {"group": "A | Hit", "coalition": "blue", "remaining": "8"},
                {"group": "B | Near", "coalition": "blue", "remaining": "8"},
                {"group": "C | Beyond", "coalition": "blue", "remaining": "8"},
            ],
            options={"releaseMinS": 3000, "releaseMaxS": 3000},
        ),
    )
    # C is 20 km from A (outside the 15 km radius) but only 10 km from B.
    h.fire_shot(
        {
            "initiator": "R | Raider",
            "weapon": {"typeName": "YJ-83"},
            "target": "A | Hit",
        }
    )
    h.assert_no_lua_errors()
    freed = {r["group"] for r in _roe(h) if r["value"] == ROE_WEAPON_FREE}
    assert freed == {"A | Hit", "B | Near"}


def test_an_enemy_formation_is_never_freed_by_our_own_attack() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("0057 | LHA", int(h.side.BLUE), x=0, z=0))
    h.add_group(_ship_group("0090 | Shadow", int(h.side.RED), x=2_000, z=0))
    h.add_group(_ship_group("0099 | Raider", int(h.side.RED), x=200_000, z=0))
    _load(
        h,
        _config(
            [
                {"group": "0057 | LHA", "coalition": "blue", "remaining": "8"},
                {"group": "0090 | Shadow", "coalition": "red", "remaining": "8"},
            ],
            options={"releaseMinS": 3000, "releaseMaxS": 3000},
        ),
    )
    h.fire_shot(
        {
            "initiator": "0099 | Raider",
            "weapon": {"typeName": "YJ-83"},
            "target": "0057 | LHA",
        }
    )
    h.assert_no_lua_errors()
    freed = {r["group"] for r in _roe(h) if r["value"] == ROE_WEAPON_FREE}
    assert freed == {"0057 | LHA"}


def test_formation_release_can_be_switched_off() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("0057 | LHA", int(h.side.BLUE), x=0, z=0))
    h.add_group(_ship_group("0058 | Escort", int(h.side.BLUE), x=1910, z=0))
    h.add_group(_ship_group("0099 | Raider", int(h.side.RED), x=200_000, z=0))
    _load(
        h,
        _config(
            [
                {"group": "0057 | LHA", "coalition": "blue", "remaining": "8"},
                {"group": "0058 | Escort", "coalition": "blue", "remaining": "8"},
            ],
            options={"releaseMinS": 3000, "releaseMaxS": 3000, "formationReleaseKm": 0},
        ),
    )
    h.fire_shot(
        {
            "initiator": "0099 | Raider",
            "weapon": {"typeName": "YJ-83"},
            "target": "0057 | LHA",
        }
    )
    h.assert_no_lua_errors()
    freed = {r["group"] for r in _roe(h) if r["value"] == ROE_WEAPON_FREE}
    assert freed == {"0057 | LHA"}


def test_a_friendly_shot_never_releases_a_held_group() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("0001 | Held", int(h.side.BLUE)))
    h.add_group(_ship_group("0002 | Clumsy", int(h.side.BLUE)))
    _load(
        h,
        _config(
            [{"group": "0001 | Held", "coalition": "blue", "remaining": "8"}],
            options={"releaseMinS": 300, "releaseMaxS": 300},
        ),
    )
    h.advance_to(50)
    h.fire_shot(
        {
            "initiator": "0002 | Clumsy",
            "weapon": {"typeName": "AGM_84D_Harpoon"},
            "target": "0001 | Held",
        }
    )
    h.assert_no_lua_errors()
    assert [r for r in _roe(h) if r["value"] == ROE_WEAPON_FREE] == []


def test_a_hit_releases_a_held_group() -> None:
    """The HIT backstop: dumb ordnance carries no SHOT target, but a shell
    landing on the group is reason enough to defend."""
    h = DcsPluginHarness()
    h.add_group(_ship_group("0001 | Held", int(h.side.BLUE)))
    _load(
        h,
        _config(
            [{"group": "0001 | Held", "coalition": "blue", "remaining": "8"}],
            options={"releaseMinS": 300, "releaseMaxS": 300},
        ),
    )
    h.advance_to(60)
    h.fire_hit("0001 | Held")
    h.assert_no_lua_errors()
    freed = [r for r in _roe(h) if r["value"] == ROE_WEAPON_FREE]
    assert [(r["group"], r["t"]) for r in freed] == [("0001 | Held", 60)]


def test_an_attacked_dry_group_is_released_anyway() -> None:
    """A spent group is passive until attacked — then it defends itself, even
    though the ordinary release path refuses a dry magazine."""
    h = DcsPluginHarness()
    h.add_group(_ship_group("0001 | Spent", int(h.side.BLUE)))
    h.add_group(_ship_group("0099 | Raider", int(h.side.RED)))
    _load(
        h,
        _config(
            [{"group": "0001 | Spent", "coalition": "blue", "remaining": "0"}],
            stagger=False,
        ),
    )
    # Pulled to ReturnFire at load (dry, stagger off)...
    assert [r["value"] for r in _roe(h)] == [ROE_RETURN_FIRE]
    h.fire_shot(
        {
            "initiator": "0099 | Raider",
            "weapon": {"typeName": "YJ-83"},
            "target": "0001 | Spent",
        }
    )
    h.assert_no_lua_errors()
    # ...and released the moment the enemy fires at it.
    assert [r["value"] for r in _roe(h)] == [ROE_RETURN_FIRE, ROE_WEAPON_FREE]


def test_an_attacked_winchester_group_keeps_defending_and_counts_overshoot() -> None:
    """Running dry while under attack must NOT re-defang the ship — no ReturnFire
    drop — and anything it fires past its stock is still counted for the debit."""
    h = DcsPluginHarness()
    h.add_group(_ship_group("0001 | Burke", int(h.side.BLUE)))
    h.add_group(_ship_group("0099 | Raider", int(h.side.RED)))
    _load(
        h,
        _config(
            [{"group": "0001 | Burke", "coalition": "blue", "remaining": "1"}],
            stagger=False,
        ),
    )
    h.fire_shot(
        {
            "initiator": "0099 | Raider",
            "weapon": {"typeName": "YJ-83"},
            "target": "0001 | Burke",
        }
    )
    for _ in range(2):
        h.fire_shot({"initiator": "0001 | Burke", "weapon": {"typeName": "RGM_84F"}})
    h.assert_no_lua_errors()
    # Winchester announced, but never dropped back to ReturnFire while under attack.
    assert any("WINCHESTER" in str(t.get("text", "")) for t in h.records("texts"))
    assert [r for r in _roe(h) if r["value"] == ROE_RETURN_FIRE] == []
    # The overshoot past the 1-round stock is still recorded for the turn debit.
    assert _state(h) == [{"group": "0001 | Burke", "fired": 2}]


def test_no_node_is_a_clean_no_op() -> None:
    h = DcsPluginHarness()
    h.lua.globals().dcsRetribution = h.to_lua({"plugins": {}})
    h.load_plugin_script(PLUGIN)
    h.advance_to(1000)
    h.assert_no_lua_errors()
    assert _roe(h) == []


def test_custom_weapon_patterns_are_honored() -> None:
    h = DcsPluginHarness()
    h.add_group(_ship_group("0001 | Burke", int(h.side.BLUE)))
    _load(
        h,
        _config(
            [{"group": "0001 | Burke", "coalition": "blue", "remaining": "2"}],
            stagger=False,
            options={"ashmWeaponPatterns": "SOME_MOD_ASHM"},
        ),
    )
    h.fire_shot({"initiator": "0001 | Burke", "weapon": {"typeName": "HARPOON"}})
    assert _state(h) == []
    h.fire_shot(
        {"initiator": "0001 | Burke", "weapon": {"typeName": "some_mod_ashm_1"}}
    )
    h.assert_no_lua_errors()
    assert _state(h) == [{"group": "0001 | Burke", "fired": 1}]
