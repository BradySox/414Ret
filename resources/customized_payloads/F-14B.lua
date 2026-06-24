-- F-14B Tomcat loadouts for 414th Retribution
-- Pylon layout:
--   1        = left wingtip    (AIM-9)
--   2        = left shoulder   (AIM-7 or AIM-54)
--   3        = left glove tank
--   4,5,6,7  = belly stations  (bombs or AIM-54)
--   8        = right glove tank
--   9        = right shoulder  (AIM-7, AIM-54, or LANTIRN)
--   10       = right wingtip   (AIM-9)
-- CLSID reference:
--   AIM-9M wingtip:     {LAU-138 wtip - AIM-9M}
--   AIM-9L wingtip:     {LAU-138 wtip - AIM-9L}
--   AIM-7MH shoulder:   {SHOULDER AIM-7MH}
--   AIM-54C Mk60 L:     {SHOULDER AIM_54C_Mk60 L}
--   AIM-54C Mk60 R:     {SHOULDER AIM_54C_Mk60 R}
--   AIM-54C Mk47 belly: {AIM_54C_Mk47}
--   AIM-54C Mk60 belly: {AIM_54C_Mk60}
--   AIM-54A Mk47 R:     {SHOULDER AIM_54A_Mk47 R}
--   AIM-54A Mk60 L:     {SHOULDER AIM_54A_Mk60 L}
--   ADM-141 TALD:       {BRU3242_ADM141}
--   GBU-12 LGB:         {BRU-32 GBU-12}
--   GBU-16 LGB:         {BRU-32 GBU-16}
--   GBU-24 Pave III:    {BRU-32 GBU-24}
--   GBU-38 JDAM:        {GBU-38}
--   MAK79 4x Mk-82:     {MAK79_MK82 4}
--   MAK79 3x Mk-82 L:   {MAK79_MK82 3L}
--   MAK79 3x Mk-82 R:   {MAK79_MK82 3R}
--   LANTIRN TGP:        {F14-LANTIRN-TP}
--   300-gal tank:       {F14-300gal}
--   TARPS pod:          {F14-TARPS}
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
			-- F-14 SEAD role: ADM-141 TALD decoys to spoof SAM engagement radars
			["displayName"] = "Retribution SEAD",
			["name"] = "Retribution SEAD",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 10 },
				[2]  = { ["CLSID"] = "{SHOULDER AIM_54C_Mk60 R}", ["num"] = 9 },
				[3]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{BRU3242_ADM141}", ["num"] = 7 },
				[5]  = { ["CLSID"] = "{BRU3242_ADM141}", ["num"] = 6 },
				[6]  = { ["CLSID"] = "{BRU3242_ADM141}", ["num"] = 5 },
				[7]  = { ["CLSID"] = "{BRU3242_ADM141}", ["num"] = 4 },
				[8]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 3 },
				[9]  = { ["CLSID"] = "{SHOULDER AIM_54C_Mk60 L}", ["num"] = 2 },
				[10] = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 29 },
		},
		[6] = {
			["displayName"] = "Retribution DEAD",
			["name"] = "Retribution DEAD",
			-- 2x GBU-24 Paveway III for hardkill against hardened SAM sites
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
		[7] = {
			["displayName"] = "Retribution CAS",
			["name"] = "Retribution CAS",
			-- 4x GBU-12 Paveway II + LANTIRN
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
		[8] = {
			["displayName"] = "Retribution BAI",
			["name"] = "Retribution BAI",
			-- 4x GBU-38 JDAM for all-weather BAI
			["pylons"] = {
				[1]  = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 10 },
				[2]  = { ["CLSID"] = "{F14-LANTIRN-TP}", ["num"] = 9 },
				[3]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{GBU-38}", ["num"] = 7 },
				[5]  = { ["CLSID"] = "{GBU-38}", ["num"] = 6 },
				[6]  = { ["CLSID"] = "{GBU-38}", ["num"] = 5 },
				[7]  = { ["CLSID"] = "{GBU-38}", ["num"] = 4 },
				[8]  = { ["CLSID"] = "{F14-300gal}", ["num"] = 3 },
				[9]  = { ["CLSID"] = "{SHOULDER AIM-7MH}", ["num"] = 2 },
				[10] = { ["CLSID"] = "{LAU-138 wtip - AIM-9M}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 32 },
		},
		[9] = {
			["displayName"] = "Retribution Strike",
			["name"] = "Retribution Strike",
			-- 4x GBU-16 Paveway II 1000lb for precision strike
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
			["tasks"] = { [1] = 32, [2] = 33 },
		},
		[10] = {
			["displayName"] = "Retribution OCA/Aircraft",
			["name"] = "Retribution OCA/Aircraft",
			-- Same as Strike: GBU-16 against parked aircraft + fuel + support
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
			["tasks"] = { [1] = 32 },
		},
		[11] = {
			["displayName"] = "Retribution OCA/Runway",
			["name"] = "Retribution OCA/Runway",
			-- Mk-82 unguided cluster for runway cratering (pre-LANTIRN era accuracy)
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
		[12] = {
			-- F-14 anti-ship: GBU-16 LGB guided by LANTIRN against surface targets
			["displayName"] = "Retribution Anti-ship",
			["name"] = "Retribution Anti-ship",
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
			["tasks"] = { [1] = 30 },
		},
		[13] = {
			-- TARPS recon profile: KS-87D camera pod on the belly recon station plus a
			-- light self-defense fit (2x AIM-9L, 2x AIM-54A, drop tanks) for the photo run.
			-- Editor-verified (F-14B "Aerial-1" in Tues test 1.miz): "{F14-TARPS}" on
			-- station 6, station 5 left clean. The earlier "{SHOULDER AIM-7MH}" /
			-- "{LAU-138 wtip - AIM-9M}" CLSIDs were stale and made DCS drop the whole
			-- loadout (pod included) on load; these CLSIDs validate and keep the pod.
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
