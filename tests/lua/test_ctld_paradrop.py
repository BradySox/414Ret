"""Headless runtime check for the CTLD paradrop layer (ctld-config.lua).

Pins the fixed-wing paratrooper wiring the in-game pass cannot cheaply cover:
the config parses the Logistics paradrop flag and target zones without error;
an airborne fixed-wing "Unload / Extract Troops" jumps the stick (cargo cleared
immediately, the troop group ground-spawns at the velocity-projected drop point
after a real descent delay) while grounded unloads and every helicopter path
fall through to stock CTLD; the player jump ceiling refuses a too-high drop;
the AI release loop drops one stick per sortie when a transport crosses its own
air-assault target zone and never touches players or helos; and the preload
retry finds a late-activated transport instead of silently leaving it empty.

CTLD itself is stubbed to a minimal core (the real CTLD.lua needs the full
mist/MOOSE world); what runs for real here is the ctld-config.lua layer under
test, exactly as the mission would load it.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

CONFIG = "resources/plugins/ctld/ctld-config.lua"

# Constants mirrored from ctld-config.lua's paradrop block.
SINK_MPS = 6.5
MAX_DESCENT_S = 90
EXIT_THROW_S = 2
AI_RANGE_M = 1200
AI_POLL_S = 5

_CTLD_STUB = """
-- Minimal mist + trigger.misc the config layer expects from the full sandbox.
mist = {
    vec = {
        mag = function(v)
            return math.sqrt((v.x or 0) ^ 2 + (v.y or 0) ^ 2 + (v.z or 0) ^ 2)
        end,
    },
    utils = {
        round = function(n)
            return math.floor(n + 0.5)
        end,
    },
}

local zones = {}
trigger.misc = trigger.misc or {}
trigger.misc.getZone = function(name)
    return zones[name]
end
function AddTestZone(name, x, z, radius)
    zones[name] = { point = { x = x, y = 0, z = z }, radius = radius }
end

-- Minimal CTLD core: just the surface ctld-config.lua touches. The config's
-- own additions (paradrop functions, overrides) attach to this table.
ctld = {
    loadableGroups = {},
    inTransitTroops = {},
    droppedTroopsRED = {},
    droppedTroopsBLUE = {},
    jtacGeneratedLaserCodes = { 1688, 1687, 1686 },
    _spawns = {},
    _messages = {},
    _stockUnloadCalls = {},
    _preloads = {},
    _jtacStarts = {},
}

function ctld.getTransportUnit(name)
    if name == nil then
        return nil
    end
    for _, g in pairs(DcsHarness.groupsByName) do
        for _, u in ipairs(g.units or {}) do
            if u:getName() == name and u:isExist() and u:getLife() > 0 then
                return u
            end
        end
    end
    return nil
end

function ctld.troopsOnboard(unit, troops)
    local onboard = ctld.inTransitTroops[unit:getName()]
    if onboard == nil then
        return false
    end
    if troops then
        return onboard.troops ~= nil and onboard.troops.units ~= nil
            and #onboard.troops.units > 0
    end
    return onboard.vehicles ~= nil and onboard.vehicles.units ~= nil
        and #onboard.vehicles.units > 0
end

function ctld.heightDiff(unit)
    return unit:getPoint().y
end

function ctld.adaptWeightToCargo(name) end

function ctld.getPlayerNameOrType(unit)
    if unit:getPlayerName() == nil then
        return unit:getTypeName()
    end
    return unit:getPlayerName()
end

function ctld.displayMessageToGroup(unit, text, duration)
    table.insert(ctld._messages, { unit = unit:getName(), text = text })
end

function ctld.spawnDroppedGroup(point, details, spawnBehind)
    local name = details.groupName or "Dropped Troops #1"
    table.insert(ctld._spawns, {
        x = point.x,
        z = point.z,
        name = name,
        count = #details.units,
        t = timer.getTime(),
    })
    return {
        getName = function()
            return name
        end,
    }
end

function ctld.JTACStart(groupName, code)
    table.insert(ctld._jtacStarts, { group = groupName, code = code })
end

function ctld.processCallback(args) end

function ctld.unloadExtractTroops(args)
    table.insert(ctld._stockUnloadCalls, args[1])
end

function ctld.preLoadTransport(name, amount, troops)
    table.insert(ctld._preloads, { unit = name, amount = tonumber(amount) })
    LoadTestTroops(name, tonumber(amount) or 0)
end

function LoadTestTroops(unitName, count, jtac)
    local units = {}
    for i = 1, count do
        units[i] = {
            type = "Soldier M4",
            name = string.format("%s trooper %d", unitName, i),
        }
    end
    ctld.inTransitTroops[unitName] = {
        troops = {
            units = units,
            groupName = unitName .. " troops",
            side = 2,
            country = 2,
            jtac = jtac or nil,
        },
    }
end
"""

_PLUGIN_OPTIONS = {
    "ctld": {
        "debug": False,
        "slingload": False,
        "smoke": False,
        "tailorctld": True,
        "logisticunit": False,
        "autolase": False,
        "airliftcrates": False,
    }
}


def _transport(aircraft_type: str, cabin: int, paradrop: bool) -> dict[str, Any]:
    # The emitter serializes every value as a string; mirror that.
    return {
        "aircraft_type": aircraft_type,
        "cabin_size": str(cabin),
        "troops": "true" if cabin > 0 else "false",
        "crates": "false",
        "paradrop": "true" if paradrop else "false",
    }


def _flight(
    pilots: list[str],
    aircraft_type: str,
    target_zone: str | None = None,
    preload: bool = True,
) -> dict[str, Any]:
    flight: dict[str, Any] = {
        "pilot_names": pilots,
        "side": "2",
        "aircraft_type": aircraft_type,
        "preload": "true" if preload else "false",
    }
    if target_zone is not None:
        flight["target_zone"] = target_zone
    return flight


def _config(
    flights: list[dict[str, Any]], transports: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "plugins": _PLUGIN_OPTIONS,
        "Logistics": {
            "flights": flights,
            "transports": transports,
            "crates": [],
            "spawnable_crates": [],
        },
    }


def _load(
    h: DcsPluginHarness,
    flights: list[dict[str, Any]],
    transports: list[dict[str, Any]],
) -> None:
    h.lua.execute(_CTLD_STUB)
    h.lua.globals().dcsRetribution = h.to_lua(_config(flights, transports))
    h.load_plugin_script(CONFIG)


def _herc(
    h: DcsPluginHarness,
    name: str = "Herc 1-1",
    x: float = 50_000.0,
    z: float = 10_000.0,
    alt: float = 300.0,
    airborne: bool = True,
    player: str | None = None,
    velocity: dict[str, float] | None = None,
) -> None:
    h.add_group(
        {
            "name": name,
            "side": 2,
            "category": 0,
            "units": [
                {
                    "name": name,
                    "type": "C-130J-30",
                    "x": x,
                    "z": z,
                    "alt": alt,
                    "airborne": airborne,
                    "playerName": player,
                    "velocity": velocity or {"x": 100.0, "y": 0.0, "z": -50.0},
                }
            ],
        }
    )


def _spawns(h: DcsPluginHarness) -> list[dict[str, Any]]:
    spawns = h.to_python(h.lua.eval("ctld._spawns"))
    return spawns if isinstance(spawns, list) else []


def _texts(h: DcsPluginHarness) -> list[str]:
    return [t["text"] for t in h.records("texts")]


def test_config_arms_paradrop_only_for_flagged_fixed_wing() -> None:
    h = DcsPluginHarness()
    _load(
        h,
        flights=[
            _flight(["Herc 1-1"], "C-130J-30", target_zone="Herc 1 TARGET_ZONE"),
            _flight(["Dodge 1-1"], "UH-1H", target_zone="Dodge 1 TARGET_ZONE"),
        ],
        transports=[
            _transport("C-130J-30", 24, paradrop=True),
            _transport("UH-1H", 10, paradrop=False),
        ],
    )

    assert h.lua.eval('ctld.paradropUnitTypes["C-130J-30"] == true')
    assert h.lua.eval('ctld.paradropUnitTypes["UH-1H"] == nil')
    # The override wrapped the stock unload, and the AI release loop is armed.
    assert h.lua.eval("type(ctld.paradropTroops)") == "function"
    h.assert_no_lua_errors()


def test_preload_retries_until_a_late_activated_transport_spawns() -> None:
    h = DcsPluginHarness()
    _load(
        h,
        flights=[_flight(["Herc 1-1"], "C-130J-30", target_zone="Z1")],
        transports=[_transport("C-130J-30", 24, paradrop=True)],
    )

    # t+5: the TOT-delayed transport does not exist yet -- no load, retry armed.
    h.advance_to(20)
    assert h.to_python(h.lua.eval("ctld._preloads")) in (None, {}, [])

    # The flight late-activates; the retry finds and loads it exactly once.
    _herc(h, airborne=False)
    h.advance_to(120)
    preloads = h.to_python(h.lua.eval("ctld._preloads"))
    assert preloads == [{"unit": "Herc 1-1", "amount": 24}]
    h.assert_no_lua_errors()


def test_player_airborne_unload_paradrops_after_descent() -> None:
    h = DcsPluginHarness()
    _load(
        h,
        flights=[_flight(["Herc 1-1"], "C-130J-30", preload=False)],
        transports=[_transport("C-130J-30", 24, paradrop=True)],
    )
    _herc(h, alt=300.0, player="Brady", velocity={"x": 100.0, "y": 0.0, "z": -50.0})
    h.lua.execute('LoadTestTroops("Herc 1-1", 24)')

    h.advance_to(10)
    h.lua.execute('ctld.unloadExtractTroops({ "Herc 1-1" })')

    # The stick left the aircraft immediately -- cargo gone, coalition told --
    # but nobody is on the ground until the chutes get there.
    assert h.lua.eval('ctld.inTransitTroops["Herc 1-1"].troops == nil')
    assert any("paradropped troops" in t for t in _texts(h))
    assert _spawns(h) == []
    assert h.to_python(h.lua.eval("ctld._stockUnloadCalls")) in (None, {}, [])

    # Landing: 300 m AGL at 6.5 m/s ~= 46 s, at the velocity-projected point.
    h.advance_to(10 + 300 / SINK_MPS + 1)
    spawns = _spawns(h)
    assert len(spawns) == 1
    assert spawns[0]["x"] == 50_000 + 100 * EXIT_THROW_S
    assert spawns[0]["z"] == 10_000 - 50 * EXIT_THROW_S
    assert spawns[0]["count"] == 24
    assert h.lua.eval("#ctld.droppedTroopsBLUE") == 1
    assert any("on the ground" in t for t in _texts(h))
    h.assert_no_lua_errors()


def test_player_too_high_is_refused_and_keeps_the_troops() -> None:
    h = DcsPluginHarness()
    _load(
        h,
        flights=[_flight(["Herc 1-1"], "C-130J-30", preload=False)],
        transports=[_transport("C-130J-30", 24, paradrop=True)],
    )
    # 2,000 m AGL is above the 3,000 ft jump ceiling.
    _herc(h, alt=2_000.0, player="Brady")
    h.lua.execute('LoadTestTroops("Herc 1-1", 24)')

    h.lua.execute('ctld.unloadExtractTroops({ "Herc 1-1" })')

    messages = h.to_python(h.lua.eval("ctld._messages"))
    assert any("Too high to paradrop" in m["text"] for m in messages)
    assert h.lua.eval('ctld.inTransitTroops["Herc 1-1"].troops ~= nil')
    h.advance_to(200)
    assert _spawns(h) == []
    h.assert_no_lua_errors()


def test_grounded_unload_falls_through_to_stock_ctld() -> None:
    h = DcsPluginHarness()
    _load(
        h,
        flights=[_flight(["Herc 1-1"], "C-130J-30", preload=False)],
        transports=[_transport("C-130J-30", 24, paradrop=True)],
    )
    _herc(h, airborne=False, alt=0.0, velocity={"x": 0.0, "y": 0.0, "z": 0.0})
    h.lua.execute('LoadTestTroops("Herc 1-1", 24)')

    h.lua.execute('ctld.unloadExtractTroops({ "Herc 1-1" })')

    assert h.to_python(h.lua.eval("ctld._stockUnloadCalls")) == ["Herc 1-1"]
    assert _spawns(h) == []
    h.assert_no_lua_errors()


def test_airborne_helo_falls_through_to_stock_ctld() -> None:
    h = DcsPluginHarness()
    _load(
        h,
        flights=[_flight(["Dodge 1-1"], "UH-1H", preload=False)],
        transports=[_transport("UH-1H", 10, paradrop=False)],
    )
    h.add_group(
        {
            "name": "Dodge 1-1",
            "side": 2,
            "category": 1,
            "units": [
                {
                    "name": "Dodge 1-1",
                    "type": "UH-1H",
                    "x": 1_000.0,
                    "z": 2_000.0,
                    "alt": 30.0,
                    "airborne": True,
                    "playerName": "Brady",
                    "velocity": {"x": 20.0, "y": 0.0, "z": 0.0},
                }
            ],
        }
    )
    h.lua.execute('LoadTestTroops("Dodge 1-1", 10)')

    h.lua.execute('ctld.unloadExtractTroops({ "Dodge 1-1" })')

    # Not a paradrop airframe: the stock unload (land / fast-rope rules) runs.
    assert h.to_python(h.lua.eval("ctld._stockUnloadCalls")) == ["Dodge 1-1"]
    assert _spawns(h) == []
    h.assert_no_lua_errors()


def test_ai_drops_once_when_crossing_its_own_target_zone() -> None:
    h = DcsPluginHarness()
    _load(
        h,
        flights=[_flight(["Herc 1-1"], "C-130J-30", target_zone="Herc 1 TARGET_ZONE")],
        transports=[_transport("C-130J-30", 24, paradrop=True)],
    )
    h.lua.execute('AddTestZone("Herc 1 TARGET_ZONE", 100000, 20000, 2500)')
    # AI (no player name), still 10 km short of the zone centre. High AGL:
    # the jump ceiling is player-only, so the AI still delivers -- but the
    # descent is capped.
    _herc(h, x=90_000.0, z=20_000.0, alt=2_000.0)

    # Preload fires at t+5, the release loop polls but the zone is far.
    h.advance_to(30)
    assert _spawns(h) == []
    assert not any("paradropped troops" in t for t in _texts(h))

    # The run-in crosses the release range; the next poll drops the stick.
    h.update_unit("Herc 1-1", {"x": 99_500.0})
    h.advance_to(40)
    assert any("paradropped troops" in t for t in _texts(h))
    assert _spawns(h) == []
    assert h.lua.eval('ctld.inTransitTroops["Herc 1-1"].troops == nil')

    # 2,000 m AGL would be 300+ s of descent; the cap lands them at +90 s.
    drop_texts = [t for t in h.records("texts") if "paradropped troops" in t["text"]]
    drop_t = drop_texts[0]["t"]
    h.advance_to(drop_t + MAX_DESCENT_S + 1)
    assert len(_spawns(h)) == 1

    # One drop per sortie: even if the aircraft somehow reloads over the zone,
    # the release plan is spent.
    h.lua.execute('LoadTestTroops("Herc 1-1", 24)')
    h.advance_to(drop_t + MAX_DESCENT_S + 30)
    assert len(_spawns(h)) == 1
    h.assert_no_lua_errors()


def test_ai_helo_air_assault_is_never_paradropped() -> None:
    h = DcsPluginHarness()
    _load(
        h,
        flights=[_flight(["Dodge 1-1"], "UH-1H", target_zone="Dodge 1 TARGET_ZONE")],
        transports=[_transport("UH-1H", 10, paradrop=False)],
    )
    h.lua.execute('AddTestZone("Dodge 1 TARGET_ZONE", 100000, 20000, 2500)')
    h.add_group(
        {
            "name": "Dodge 1-1",
            "side": 2,
            "category": 1,
            "units": [
                {
                    "name": "Dodge 1-1",
                    "type": "UH-1H",
                    "x": 100_000.0,
                    "z": 20_000.0,
                    "alt": 30.0,
                    "airborne": True,
                    "velocity": {"x": 20.0, "y": 0.0, "z": 0.0},
                }
            ],
        }
    )

    # Right over its target zone with troops aboard: a helo lands and unloads
    # through stock CTLD (the AI dropoff-zone loop), never the paradrop path.
    h.advance_to(60)
    assert _spawns(h) == []
    assert not any("paradropped troops" in t for t in _texts(h))
    h.assert_no_lua_errors()


def test_jtac_stick_starts_lasing_on_landing() -> None:
    h = DcsPluginHarness()
    _load(
        h,
        flights=[_flight(["Herc 1-1"], "C-130J-30", preload=False)],
        transports=[_transport("C-130J-30", 24, paradrop=True)],
    )
    _herc(h, alt=300.0, player="Brady")
    h.lua.execute('LoadTestTroops("Herc 1-1", 24, true)')

    h.lua.execute('ctld.unloadExtractTroops({ "Herc 1-1" })')
    h.advance_to(300 / SINK_MPS + 1)

    jtacs = h.to_python(h.lua.eval("ctld._jtacStarts"))
    assert jtacs == [{"group": "Herc 1-1 troops", "code": 1688}]
    h.assert_no_lua_errors()
