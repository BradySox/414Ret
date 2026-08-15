-- Living battlespace voice net (§89 P4): transmit the generator's scheduled
-- ATO radio calls from their real flights on the AWACS frequency.
-- Design + schedule contract: docs/dev/design/414th-living-battlespace-notes.md
-- and game/missiongenerator/battlespacenetluadata.py (the emitter).
-- Constraints a reader could undo by accident:
--   * A call is keyed ONLY from a live unit's position -- a dead or despawned
--     transmitter is silence, never a fallback point (the net tells the truth).
--   * Audio only. No kills, no tasking, no gameplay-model change here.
--   * Clips are one-shot (loop=false); nothing needs stopRadioTransmission.

local cfg = dcsRetribution
    and dcsRetribution.plugins
    and dcsRetribution.plugins.battlespacenet
if not cfg then
    return
end

local net = dcsRetribution and dcsRetribution.battlespaceNet
if not net or type(net.calls) ~= "table" or #net.calls == 0 then
    env.info("BSNET|: no calls emitted; plugin idle")
    return
end

local POWER_W = tonumber(cfg.powerW) or 100
local SHOW_SUBTITLES = (tonumber(cfg.showSubtitles) or 0) ~= 0

local function speak(call, index)
    local group = Group.getByName(tostring(call.group or ""))
    if not group or not group:isExist() then
        env.info("BSNET|: " .. tostring(call.group) .. " off net (gone); call skipped")
        return
    end
    local unit = group:getUnit(1)
    if not unit or not unit:isExist() then
        env.info("BSNET|: " .. tostring(call.group) .. " off net (no unit); call skipped")
        return
    end
    local p = unit:getPoint()
    local ok = pcall(
        trigger.action.radioTransmission,
        tostring(call.file),
        { x = p.x, y = p.y, z = p.z },
        0, -- AM: the AWACS strike net
        false, -- one-shot clip; ends on its own
        call.hz,
        POWER_W,
        "bsnet-" .. index
    )
    if ok and SHOW_SUBTITLES and call.text and call.text ~= "" then
        pcall(trigger.action.outTextForCoalition, coalition.side.BLUE, tostring(call.text), 8)
    end
end

local armed = 0
for index, rec in ipairs(net.calls) do
    local t = tonumber(rec.t) or 0
    local mhz = tonumber(rec.mhz) or 0
    if t > 0 and mhz > 0 and rec.file and rec.file ~= "" and rec.group then
        rec.hz = mhz * 1000000
        timer.scheduleFunction(function()
            local okCall, err = pcall(speak, rec, index)
            if not okCall then
                env.error("BSNET|: call error: " .. tostring(err))
            end
            return nil
        end, {}, timer.getTime() + math.max(5, t))
        armed = armed + 1
    end
end

env.info(string.format("BSNET|: armed %d scheduled calls", armed))
