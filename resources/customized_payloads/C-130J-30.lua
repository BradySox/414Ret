local unitPayloads = {
	["name"] = "C-130J-30",
	["payloads"] = {
		[1] = {
			-- 414th Combat SAR "King": the C-130J-30 flies the on-scene-command
			-- overhead orbit (TACAN beacon + LARS), it does not fight. Its wing
			-- tanks are a removable module pylon, not model-default, so a King with
			-- no payload spawns clean. This payload mounts the two external wing
			-- tanks so the King looks (and ranges) right. See checklist G13.
			["name"] = "Retribution Combat SAR",
			["pylons"] = {
				[1] = {
					["CLSID"] = "{C130J_Ext_Tank_L}",
					["num"] = 1,
				},
				[2] = {
					["CLSID"] = "{C130J_Ext_Tank_R}",
					["num"] = 2,
				},
			},
			["tasks"] = {
				[1] = 35,
			},
		},
	},
	["tasks"] = {
	},
	["unitType"] = "C-130J-30",
}
return unitPayloads
