-- F-14A-135-GR: photo-recon (TARPS) only.
-- The 414th flies the Tomcat purely as a TARPS reconnaissance platform; all
-- other premade fits were dropped. Any non-recon tasking falls back to the
-- pydcs default loadout. (Matches the F-14A, which is already TARPS-only.)
local unitPayloads = {
	["name"] = "F-14A",
	["payloads"] = {
		[1] = {
			["displayName"] = "Retribution TARPS",
			["name"] = "Retribution TARPS",
			["pylons"] = {
				[1] = { ["CLSID"] = "{LAU-138 wtip - AIM-9L}", ["num"] = 10 },
				[2] = { ["CLSID"] = "{SHOULDER AIM-7M}", ["num"] = 9 },
				[3] = { ["CLSID"] = "{F14-300gal}", ["num"] = 8 },
				[4] = { ["CLSID"] = "{F14-TARPS}", ["num"] = 6 },
				[5] = { ["CLSID"] = "{F14-300gal}", ["num"] = 3 },
				[6] = { ["CLSID"] = "{SHOULDER AIM-7M}", ["num"] = 2 },
				[7] = { ["CLSID"] = "{LAU-138 wtip - AIM-9L}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 10 },
		},
	},
	["unitType"] = "F-14A-135-GR",
}
return unitPayloads
