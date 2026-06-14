-- Civilian background air traffic injected by the 414Ret civilian_traffic plugin.
-- Do not edit in the Mission Editor. Edit the plugin source in 414Ret instead.
--
-- _CIVILIAN_TRAFFIC_EXCL is a Lua array of DCS airbase names baked in by the
-- Python preamble before this file loads. It contains every airbase Retribution
-- has assigned to combat operations this turn. The script enumerates all remaining
-- airbases on the map at runtime so it works on any terrain without modification.
--
-- Traffic flies ONLY between NEUTRAL-coalition airdromes that Retribution is not
-- using this turn. Heliports and FARPs are excluded (fixed-wing transports can't
-- taxi there). RED/BLUE airbases are military and never used. Distance does not
-- matter -- any neutral field can fly to any other. Density scales with the number
-- of available neutral airfields so the map feels alive without a fixed count.

local _excl = {}
for _, b in ipairs(_CIVILIAN_TRAFFIC_EXCL) do
    _excl[b] = true
end

-- Build the civilian pool: every NEUTRAL airdrome NOT used by Retribution for
-- combat ops this turn. Category check drops heliports/FARPs.
local _neutral_pool = {}
for _, ab in pairs(world.getAirbases()) do
    local name = ab:getName()
    local desc = ab:getDesc()
    if not _excl[name]
        and ab:getCoalition() == coalition.side.NEUTRAL
        and desc and desc.category == Airbase.Category.AIRDROME
    then
        _neutral_pool[#_neutral_pool + 1] = name
    end
end

-- Need at least two airdromes to fly between. With fewer, MOOSE RAT silently
-- falls back to spawning at ALL map airbases (including FARPs), so bail instead.
if #_neutral_pool < 2 then
    return
end

-- Density scales with the map: roughly 1.5 civilian flights per available
-- neutral airfield, split across the template aircraft types. Clamped so small
-- maps still feel alive and huge maps don't tank performance.
local _per = math.ceil(#_neutral_pool / 2)
if _per < 3 then _per = 3 end
if _per > 12 then _per = 12 end

-- One RAT object per template aircraft so the traffic is a mix of C-130s and
-- Antonov transports. Each template group (RAT_CIV_*) is placed late-activated
-- by the Python mission generator; pcall guards against a template that could
-- not be parked (e.g. no airfield with parking for that type).
local _templates = { "RAT_CIV_C130", "RAT_CIV_AN26", "RAT_CIV_AN30" }
local _spawned = 0

for _, tmpl in ipairs(_templates) do
    local ok, r = pcall(function() return RAT:New(tmpl) end)
    if ok and r then
        r:SetDeparture(_neutral_pool)
        r:SetDestination(_neutral_pool)
        r:SetMinDistance(5)   -- distance is irrelevant; just avoid same-field hops
        r:SetTakeoff("hot")
        r:SetROE("hold")
        r:SetROT("evade")
        r:Invisible()
        r:RespawnAfterLanding(90)
        r:Spawn(_per)
        _spawned = _spawned + 1
    end
end

env.info(string.format(
    "414Ret civilian_traffic: %d neutral airdromes, %d template type(s) active, %d flights each",
    #_neutral_pool, _spawned, _per))
