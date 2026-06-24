-- F-14B Tomcat loadouts for 414th Retribution
-- Preset set matches resources/units/aircraft/F-14B.yaml tasks:
--   BARCAP TARCAP Escort "Fighter sweep" DEAD CAS BAI Strike OCA/Aircraft
--   OCA/Runway TARPS
--   (NO SEAD / Anti-ship: the DCS F-14B has no HARM and no anti-ship missile;
--    Retribution does not task it for those roles. DEAD is done with GBU-24 LGB
--    against known SAM sites. The F-14 carries no GPS/JDAM weapons.)
-- Pylon layout (num): 1/10 wingtips (AIM-9), 2/9 shoulders (AIM-7/AIM-54/LANTIRN),
--   3/8 glove tanks, 4-7 belly (AIM-54 or bombs).
-- All CLSIDs verified against pydcs F_14B pylon tables.
local unitPayloads = {
	["name"] = "F-14B",
	["payloads"] = {
		[1] = {
			["displayName"] = "Retribution BARCAP",
			["name"] = "Retribution BARCAP",
			-- 4x AIM-54C + 2x AIM-7MH + 2x AIM-9M + 2 tanks
			["pylons"] = {
				[1]  = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 10 },
				[2]  = { ["CLSID"] = "{SHOULDER AIM-7MH}", ["num"] = 9 },
				[3]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 7 },
				[5]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 6 },
				[6]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 5 },
				[7]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 4 },
				[8]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 3 },
				[9]  = { ["CLSID"] = "{SHOULDER AIM-7MH}", ["num"] = 2 },
				[10] = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 11, [2] = 10 },
		},
		[2] = {
			["displayName"] = "Retribution TARCAP",
			["name"] = "Retribution TARCAP",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 10 },
				[2]  = { ["CLSID"] = "{SHOULDER AIM-7MH}", ["num"] = 9 },
				[3]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 7 },
				[5]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 6 },
				[6]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 5 },
				[7]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 4 },
				[8]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 3 },
				[9]  = { ["CLSID"] = "{SHOULDER AIM-7MH}", ["num"] = 2 },
				[10] = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 11, [2] = 10 },
		},
		[3] = {
			["displayName"] = "Retribution Escort",
			["name"] = "Retribution Escort",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 10 },
				[2]  = { ["CLSID"] = "{SHOULDER AIM-7MH}", ["num"] = 9 },
				[3]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 7 },
				[5]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 6 },
				[6]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 5 },
				[7]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 4 },
				[8]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 3 },
				[9]  = { ["CLSID"] = "{SHOULDER AIM-7MH}", ["num"] = 2 },
				[10] = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 18 },
		},
		[4] = {
			["displayName"] = "Retribution Fighter Sweep",
			["name"] = "Retribution Fighter Sweep",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 10 },
				[2]  = { ["CLSID"] = "{SHOULDER AIM-7MH}", ["num"] = 9 },
				[3]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 7 },
				[5]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 6 },
				[6]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 5 },
				[7]  = { ["CLSID"] = "{AIM_54C_Mk60}", ["num"] = 4 },
				[8]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 3 },
				[9]  = { ["CLSID"] = "{SHOULDER AIM-7MH}", ["num"] = 2 },
				[10] = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 19 },
		},
		[5] = {
			["displayName"] = "Retribution DEAD",
			["name"] = "Retribution DEAD",
			-- 2x GBU-24 Paveway III against hardened/known SAM sites + LANTIRN
			["pylons"] = {
				[1]  = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 10 },
				[2]  = { ["CLSID"] = "{SHOULDER AIM_54C_Mk60 L}", ["num"] = 2 },
				[3]  = { ["CLSID"] = "{F14-LANTIRN-TP}", ["num"] = 9 },
				[4]  = { ["CLSID"] = "{BRU-32 GBU-24}", ["num"] = 4 },
				[5]  = { ["CLSID"] = "{BRU-32 GBU-24}", ["num"] = 6 },
				[6]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 8 },
				[8]  = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 32 },
		},
		[6] = {
			["displayName"] = "Retribution CAS",
			["name"] = "Retribution CAS",
			-- 4x GBU-12 Paveway II 500lb + LANTIRN
			["pylons"] = {
				[1]  = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 10 },
				[2]  = { ["CLSID"] = "{F14-LANTIRN-TP}", ["num"] = 9 },
				[3]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{BRU-32 GBU-12}", ["num"] = 7 },
				[5]  = { ["CLSID"] = "{BRU-32 GBU-12}", ["num"] = 6 },
				[6]  = { ["CLSID"] = "{BRU-32 GBU-12}", ["num"] = 5 },
				[7]  = { ["CLSID"] = "{BRU-32 GBU-12}", ["num"] = 4 },
				[8]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 3 },
				[9]  = { ["CLSID"] = "{SHOULDER AIM-7MH}", ["num"] = 2 },
				[10] = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 31 },
		},
		[7] = {
			["displayName"] = "Retribution BAI",
			["name"] = "Retribution BAI",
			-- 4x GBU-16 Paveway II 1000lb for battlefield interdiction + LANTIRN
			["pylons"] = {
				[1]  = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 10 },
				[2]  = { ["CLSID"] = "{F14-LANTIRN-TP}", ["num"] = 9 },
				[3]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{BRU-32 GBU-16}", ["num"] = 7 },
				[5]  = { ["CLSID"] = "{BRU-32 GBU-16}", ["num"] = 6 },
				[6]  = { ["CLSID"] = "{BRU-32 GBU-16}", ["num"] = 5 },
				[7]  = { ["CLSID"] = "{BRU-32 GBU-16}", ["num"] = 4 },
				[8]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 3 },
				[9]  = { ["CLSID"] = "{SHOULDER AIM-7MH}", ["num"] = 2 },
				[10] = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 32 },
		},
		[8] = {
			["displayName"] = "Retribution Strike",
			["name"] = "Retribution Strike",
			-- 4x GBU-16 Paveway II 1000lb for precision strike + LANTIRN
			["pylons"] = {
				[1]  = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 10 },
				[2]  = { ["CLSID"] = "{F14-LANTIRN-TP}", ["num"] = 9 },
				[3]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{BRU-32 GBU-16}", ["num"] = 7 },
				[5]  = { ["CLSID"] = "{BRU-32 GBU-16}", ["num"] = 6 },
				[6]  = { ["CLSID"] = "{BRU-32 GBU-16}", ["num"] = 5 },
				[7]  = { ["CLSID"] = "{BRU-32 GBU-16}", ["num"] = 4 },
				[8]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 3 },
				[9]  = { ["CLSID"] = "{SHOULDER AIM_54C_Mk60 L}", ["num"] = 2 },
				[10] = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 33 },
		},
		[9] = {
			["displayName"] = "Retribution OCA/Aircraft",
			["name"] = "Retribution OCA/Aircraft",
			-- 4x GBU-16 against parked aircraft + LANTIRN
			["pylons"] = {
				[1]  = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 10 },
				[2]  = { ["CLSID"] = "{F14-LANTIRN-TP}", ["num"] = 9 },
				[3]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{BRU-32 GBU-16}", ["num"] = 7 },
				[5]  = { ["CLSID"] = "{BRU-32 GBU-16}", ["num"] = 6 },
				[6]  = { ["CLSID"] = "{BRU-32 GBU-16}", ["num"] = 5 },
				[7]  = { ["CLSID"] = "{BRU-32 GBU-16}", ["num"] = 4 },
				[8]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 3 },
				[9]  = { ["CLSID"] = "{SHOULDER AIM-7MH}", ["num"] = 2 },
				[10] = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 32 },
		},
		[10] = {
			["displayName"] = "Retribution OCA/Runway",
			["name"] = "Retribution OCA/Runway",
			-- Mk-82 (MAK79 racks) for runway cratering
			["pylons"] = {
				[1]  = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 10 },
				[2]  = { ["CLSID"] = "{SHOULDER AIM-7MH}", ["num"] = 9 },
				[3]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{MAK79_MK82 4}", ["num"] = 7 },
				[5]  = { ["CLSID"] = "{MAK79_MK82 3R}", ["num"] = 6 },
				[6]  = { ["CLSID"] = "{MAK79_MK82 3L}", ["num"] = 5 },
				[7]  = { ["CLSID"] = "{MAK79_MK82 4}", ["num"] = 4 },
				[8]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 3 },
				[9]  = { ["CLSID"] = "{SHOULDER AIM-7MH}", ["num"] = 2 },
				[10] = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 34 },
		},
		[11] = {
			-- TARPS recon profile: KS-87D camera pod on the belly recon station plus a
			-- light self-defense fit (2x AIM-9L, 2x AIM-54A, drop tanks) for the photo run.
			-- Editor-verified (F-14B "Aerial-1" in Tues test 1.miz): "{F14-TARPS}" on
			-- station 6, station 5 left clean.
			["displayName"] = "Retribution TARPS",
			["name"] = "Retribution TARPS",
			["pylons"] = {
				[1] = { ["CLSID"] = "{LAU-138 wtip - AIM-9L}", ["num"] = 10 },
				[2] = { ["CLSID"] = "{SHOULDER AIM_54A_Mk47 R}", ["num"] = 9 },
				[3] = { ["CLSID"] = "{F14-300gal}", ["num"] = 8 },
				[4] = { ["CLSID"] = "{F14-TARPS}", ["num"] = 6 },
				[5] = { ["CLSID"] = "{F14-300gal}", ["num"] = 3 },
				[6] = { ["CLSID"] = "{SHOULDER AIM_54A_Mk60 L}", ["num"] = 2 },
				[7] = { ["CLSID"] = "{LAU-138 wtip - AIM-9L}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 10 },
		},
	},
	["unitType"] = "F-14B",
}
return unitPayloads
