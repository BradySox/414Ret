"""MANTIS bridge: the SEAD-evasion scoot distance override.

When a HARM is inbound, MOOSE's ``SEAD:onafterManageEvasion`` puts the SAM
alarm-green and drives it with a call hardcoded as
``RelocateGroundRandomInRadius(20, 300, false, false, "Diamond", true)``. There is
no setter for that 300, so the bridge wraps the shared ``CONTROLLABLE`` method and
rewrites the radius for that one call.

The whole risk is blast radius: the same method is what MANTIS uses to relocate
its own HQ and EWRs, and MOOSE calls it from four places. These tests pin that
only the SEAD signature is rewritten, and that the wrapper is not installed at all
when the option is left at MOOSE's own value.

What this cannot model: whether a larger radius is a good idea in flight. The site
goes weapons-free when the suppression window ends whether or not the drive
finished -- see checklist B81.
"""

from __future__ import annotations

from typing import Any

from tests.lua.harness import DcsPluginHarness

PLUGIN = "resources/plugins/mantisiads/mantis-config.lua"

# Minimal fakes: MANTIS so the bridge can build, CONTROLLABLE so there is
# something to wrap, and a recorder for what the stock method finally receives.
MOOSE_FAKE = """
RelocTest = { calls = {} }

CONTROLLABLE = {}
function CONTROLLABLE:RelocateGroundRandomInRadius(speed, radius, onroad, shortcut, formation, onland)
    table.insert(RelocTest.calls, { speed = speed, radius = radius, formation = formation, onland = onland })
end

MANTIS = { SamType = { LONG = "LONG", MEDIUM = "MEDIUM", SHORT = "SHORT", POINT = "POINT" }, radiusscale = {} }
function MANTIS._GetSAMRange(self, grpname) return 0, 0, "POINT", 0 end
function MANTIS:New(name, samprefixes, ewrprefixes, hq, coa)
    local obj = { name = name, coalition = coa, autoshorad = true,
                  SAM_Group = { CountAlive = function() return 0 end },
                  EWR_Group = { CountAlive = function() return 0 end } }
    function obj:SetSAMRange(...) end
    function obj:SetDetectInterval(...) end
    function obj:SetEWRGrouping(...) end
    function obj:SetMaxActiveSAMs(...) end
    function obj:SetAutoRelocate(...) end
    function obj:Debug(...) end
    function obj:Start() end
    function obj:AddShorad(...) end
    return obj
end
SHORAD = {}
function SHORAD:New(...) return { name = "shorad" } end
"""

# The four call sites in Moose.lua, by their real arguments.
SEAD_EVASION = (20, 300, False, False, "Diamond", True)
MANTIS_HQ_EWR = (20, 500, True, True, None, True)
OTHER_DIAMOND = (7, 100, False, False, "Diamond", None)


def _load(harness: DcsPluginHarness, options: dict[str, Any] | None = None) -> None:
    harness.set_retribution_config(plugin_options={"mantisiads": options or {}})
    harness.lua.globals().dcsRetribution.IADS = harness.to_lua({"RED": {"Sam": []}})
    harness.lua.execute(MOOSE_FAKE)
    harness.load_plugin_script(PLUGIN)
    harness.assert_no_lua_errors()


def _call(harness: DcsPluginHarness, args: tuple[Any, ...]) -> None:
    fn = harness.lua.globals().CONTROLLABLE.RelocateGroundRandomInRadius
    fn(harness.lua.globals().CONTROLLABLE, *args)


def _radii(harness: DcsPluginHarness) -> list[Any]:
    calls = harness.to_python(harness.lua.globals().RelocTest.calls)
    if isinstance(calls, dict):
        calls = list(calls.values())
    return [c["radius"] for c in calls]


def test_the_sead_evasion_call_is_rewritten() -> None:
    harness = DcsPluginHarness()
    _load(harness, {"seadScootRadiusM": 800})
    _call(harness, SEAD_EVASION)
    assert _radii(harness) == [800]


def test_mantis_own_hq_and_ewr_relocation_is_untouched() -> None:
    # The failure that would matter: widening the SEAD scoot also flings every EWR
    # and the HQ across the map.
    harness = DcsPluginHarness()
    _load(harness, {"seadScootRadiusM": 800})
    _call(harness, MANTIS_HQ_EWR)
    assert _radii(harness) == [500]


def test_the_other_diamond_caller_is_untouched() -> None:
    # Moose.lua has a second Diamond-formation caller at radius 100; formation alone
    # is not a safe discriminator, which is why radius and onland are matched too.
    harness = DcsPluginHarness()
    _load(harness, {"seadScootRadiusM": 800})
    _call(harness, OTHER_DIAMOND)
    assert _radii(harness) == [100]


def test_the_wrapper_is_not_installed_at_the_moose_default() -> None:
    # Left at 300 the bridge must not touch a shared MOOSE method at all.
    harness = DcsPluginHarness()
    _load(harness, {"seadScootRadiusM": 300})
    _call(harness, SEAD_EVASION)
    assert _radii(harness) == [300]


def test_no_option_means_no_wrapper() -> None:
    harness = DcsPluginHarness()
    _load(harness, {})
    _call(harness, SEAD_EVASION)
    assert _radii(harness) == [300]
