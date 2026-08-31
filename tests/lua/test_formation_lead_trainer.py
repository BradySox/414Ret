"""Runtime tests for the Formation Lead Trainer's followability model.

Flies synthetic lead profiles through the real plugin code on Lua 5.1 and asserts
the model grades them the way formation doctrine does. The physics is the feature
here, so these pin the model itself, not just that the script loads.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import lupa.lua51
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "resources/plugins/formationlead/formation_lead_trainer.lua"

# Minimal vanilla-DCS sandbox. The trainer touches nothing else -- it is read-only
# telemetry plus text output, which is why this fake can be this small.
STUBS = """
_T = 0
timer = { getTime = function() return _T end, scheduleFunction = function() end }
_msgs = {}
trigger = { action = { outTextForGroup = function(_, t) _msgs[#_msgs+1] = t end } }
missionCommands = {
    addSubMenuForGroup = function() end,
    addCommandForGroup = function() end,
}
coalition = { side = { BLUE = 2, RED = 1 }, getGroups = function() return {} end }
Group = { Category = { AIRPLANE = 0, HELICOPTER = 1 } }
land = { getHeight = function() return 0 end }
env = { info = function() end, error = function() end }
"""

# Builds a DCS orientation matrix and flies a coordinated turn under a bank schedule,
# so the test exercises rollOf/headingOf and the wingman model together.
RIG = """
local G = 9.80665
local function orient(h, phi)
    local fwd = { x = math.cos(h), y = 0, z = math.sin(h) }
    local rl  = { x = -math.sin(h), y = 0, z = math.cos(h) }
    local up  = { x = rl.y*fwd.z - rl.z*fwd.y,
                  y = rl.z*fwd.x - rl.x*fwd.z,
                  z = rl.x*fwd.y - rl.y*fwd.x }
    local right = { x = rl.x*math.cos(phi) - up.x*math.sin(phi),
                    y = rl.y*math.cos(phi) - up.y*math.sin(phi),
                    z = rl.z*math.cos(phi) - up.z*math.sin(phi) }
    local up2 = { x = up.x*math.cos(phi) + rl.x*math.sin(phi),
                  y = up.y*math.cos(phi) + rl.y*math.sin(phi),
                  z = up.z*math.cos(phi) + rl.z*math.sin(phi) }
    return fwd, up2, right
end

-- bankDeg/rollRate describe the roll-in; dur seconds at 10 Hz, 300 kt TAS.
function FLY(formationKey, bankDeg, rollRate, dur)
    local FLT = FormationLeadTrainer
    local f
    for _, ff in ipairs(FLT.FORMATIONS) do
        if ff.key == formationKey then f = ff end
    end
    local s = FLT.Session.new("TEST", 1)
    s.formation = f
    local V, dt = 154.0, 1.0 / FLT.cfg.sample_hz
    local h, p = 0, { x = 0, y = 3000, z = 0 }
    local fwd, up, right
    local unit = {}
    function unit.getPosition() return { p = p, x = fwd, y = up, z = right } end
    function unit.getVelocity() return { x = fwd.x*V, y = fwd.y*V, z = fwd.z*V } end
    _T = 0
    local peak = 0
    for _ = 0, math.floor(dur / dt) do
        local phi = 0
        if _T >= 1 then
            phi = math.min(math.rad(bankDeg), math.rad(rollRate) * (_T - 1))
        end
        fwd, up, right = orient(h, phi)
        s:step(unit, dt)
        if s.lastErr and s.lastErr.total > peak then peak = s.lastErr.total end
        h = h + (G * math.tan(phi) / V) * dt
        p = { x = p.x + fwd.x*V*dt, y = p.y, z = p.z + fwd.z*V*dt }
        _T = _T + dt
    end
    local faults = {}
    for k, v in pairs(s.events) do faults[k] = v end
    return {
        score = 100.0 * s.goodTime / math.max(s.gradedTime, 0.001),
        peak = peak,
        faults = faults,
        debrief = s:debrief(),
    }
end
"""


@pytest.fixture
def lua() -> Any:
    rt = lupa.lua51.LuaRuntime(unpack_returned_tuples=False)
    rt.execute(STUBS)
    rt.execute(SCRIPT.read_text(encoding="utf-8"))
    rt.execute(RIG)
    return rt


def fly(
    lua: Any, formation: str, bank: float, roll_rate: float, dur: float = 40.0
) -> Any:
    return lua.globals().FLY(formation, bank, roll_rate, dur)


def test_script_loads_and_registers_formations(lua: Any) -> None:
    flt = lua.globals().FormationLeadTrainer
    assert flt is not None
    assert len(flt.FORMATIONS) == 4


def test_straight_and_level_holds_the_slot(lua: Any) -> None:
    """The v*dt regression: measuring after integrating put a constant 15 m at
    300 kt into every sample, gain-independent, reading as a permanent acute error."""
    for key in ("fingertip", "route", "cruise", "spread"):
        result = fly(lua, key, 0.0, 0.0, dur=30.0)
        assert result.peak < 1.0, f"{key} drifted {result.peak:.2f} m wings-level"
        assert result.score == pytest.approx(100.0, abs=0.01)


@pytest.mark.parametrize(
    "formation,bank,roll_rate",
    [
        ("fingertip", 30.0, 8.0),
        ("route", 25.0, 6.0),
        ("cruise", 8.0, 1.5),
        ("spread", 6.0, 0.8),
    ],
)
def test_correct_technique_is_clean(
    lua: Any, formation: str, bank: float, roll_rate: float
) -> None:
    """A turn flown inside the spacing's limits must raise no fault at all."""
    result = fly(lua, formation, bank, roll_rate)
    assert dict(result.faults) == {}
    assert result.score == pytest.approx(100.0, abs=0.01)


def test_snap_roll_in_is_caught(lua: Any) -> None:
    result = fly(lua, "route", 60.0, 75.0)
    faults = dict(result.faults)
    assert "roll" in faults, "a 75 deg/s roll-in must fault the roll-rate limit"
    assert "accel" in faults, "a snap roll-in must fault the outside man's acceleration"
    assert result.score < 95.0


def test_wide_formation_cannot_be_turned_by_banking(lua: Any) -> None:
    """The doctrine the tool exists to teach: at 1.5 nm the outside man needs speed
    that does not exist, so the answer is a tac turn, not a gentler bank."""
    result = fly(lua, "spread", 15.0, 5.0)
    faults = dict(result.faults)
    assert "turn" in faults
    assert result.score < 25.0


def test_same_turn_is_survivable_close_and_not_wide(lua: Any) -> None:
    """The whole model in one assertion: demand scales linearly with spacing."""
    close = fly(lua, "fingertip", 30.0, 8.0)
    wide = fly(lua, "cruise", 30.0, 8.0)
    assert dict(close.faults) == {}
    assert "turn" in dict(wide.faults)
    assert close.score > wide.score + 50.0


def test_faults_are_counted_as_episodes_not_samples(lua: Any) -> None:
    """One botched turn is one fault. Counting samples reported 177 for a single
    roll-in and made the debrief unreadable."""
    result = fly(lua, "route", 60.0, 75.0)
    for key, count in dict(result.faults).items():
        assert count <= 3, f"{key} counted {count} times for one roll-in"


def test_limits_scale_linearly_with_spacing(lua: Any) -> None:
    flt = lua.globals().FormationLeadTrainer
    cfg = flt.cfg
    route = flt.turnRateLimit(cfg, 150.0)
    cruise = flt.turnRateLimit(cfg, 900.0)
    # dv = omega * d, so six times the spacing is a sixth of the turn rate.
    assert route / cruise == pytest.approx(6.0, rel=1e-6)


def test_debrief_renders(lua: Any) -> None:
    text = fly(lua, "route", 60.0, 75.0).debrief
    assert "FORMATION LEAD DEBRIEF" in text
    assert "FOLLOWABLE:" in text
