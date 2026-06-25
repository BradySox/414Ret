-- FA-18C Hornet loadouts for 414th Retribution
-- Preset set matches resources/units/aircraft/FA-18C_hornet.yaml tasks:
--   BARCAP TARCAP Escort "Fighter sweep" SEAD "SEAD Escort" DEAD CAS BAI Strike
--   OCA/Aircraft OCA/Runway Anti-ship
-- CLSID reference:
--   AIM-9X:          {5CE2FF2A-645A-4197-B48D-8720AC69394F}  (wingtips 1,9)
--   AIM-120C:        {40EF17B7-F508-45de-8566-6FFECC0C1AB8}  (cheek pylon 6)
--   2xAIM-120C rack: LAU-115_2*LAU-127_AIM-120C              (outer pylons 2,8)
--   ATFLIR TGP:      {AN_ASQ_228}                             (pylon 4)
--   330gal tank:     {FPU_8A_FUEL_TANK}
--   AGM-88C HARM:    {B06DD79A-F21E-4EB9-BD9D-AB3844618C93}
--   AGM-65F Mav:     LAU_117_AGM_65F
--   GBU-38 JDAM:     {GBU-38}
--   GBU-31V2B JDAM:  {GBU_31_V_2B}
--   GBU-31V4B pen:   {GBU_31_V_4B}
--   AGM-84D Harpoon: {AGM_84D}
--   2xAGM-154C rack: {BRU55_2*AGM-154C}
-- All CLSIDs verified against pydcs FA_18C_hornet pylon tables.
local unitPayloads = {
	["name"] = "FA-18C_hornet",
	["payloads"] = {
		[1] = {
			["displayName"] = "Retribution BARCAP",
			["name"] = "Retribution BARCAP",
			["pylons"] = {
				[1] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 3 },
				[4] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 7 },
				[5] = { ["CLSID"] = "LAU-115_2*LAU-127_AIM-120C", ["num"] = 8 },
				[6] = { ["CLSID"] = "LAU-115_2*LAU-127_AIM-120C", ["num"] = 2 },
				[7] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[8] = { ["CLSID"] = "{AN_ASQ_228}", ["num"] = 4 },
				[9] = { ["CLSID"] = "<CLEAN>", ["num"] = 5 },
			},
			["tasks"] = { [1] = 11, [2] = 10 },
		},
		[2] = {
			["displayName"] = "Retribution TARCAP",
			["name"] = "Retribution TARCAP",
			["pylons"] = {
				[1] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 3 },
				[4] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 7 },
				[5] = { ["CLSID"] = "LAU-115_2*LAU-127_AIM-120C", ["num"] = 8 },
				[6] = { ["CLSID"] = "LAU-115_2*LAU-127_AIM-120C", ["num"] = 2 },
				[7] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[8] = { ["CLSID"] = "{AN_ASQ_228}", ["num"] = 4 },
				[9] = { ["CLSID"] = "<CLEAN>", ["num"] = 5 },
			},
			["tasks"] = { [1] = 11, [2] = 10 },
		},
		[3] = {
			["displayName"] = "Retribution Escort",
			["name"] = "Retribution Escort",
			["pylons"] = {
				[1] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 3 },
				[4] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 7 },
				[5] = { ["CLSID"] = "LAU-115_2*LAU-127_AIM-120C", ["num"] = 8 },
				[6] = { ["CLSID"] = "LAU-115_2*LAU-127_AIM-120C", ["num"] = 2 },
				[7] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[8] = { ["CLSID"] = "{AN_ASQ_228}", ["num"] = 4 },
				[9] = { ["CLSID"] = "<CLEAN>", ["num"] = 5 },
			},
			["tasks"] = { [1] = 18 },
		},
		[4] = {
			["displayName"] = "Retribution Fighter sweep",
			["name"] = "Retribution Fighter sweep",
			["pylons"] = {
				[1] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 3 },
				[4] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 7 },
				[5] = { ["CLSID"] = "LAU-115_2*LAU-127_AIM-120C", ["num"] = 8 },
				[6] = { ["CLSID"] = "LAU-115_2*LAU-127_AIM-120C", ["num"] = 2 },
				[7] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[8] = { ["CLSID"] = "{AN_ASQ_228}", ["num"] = 4 },
				[9] = { ["CLSID"] = "<CLEAN>", ["num"] = 5 },
			},
			["tasks"] = { [1] = 19 },
		},
		[5] = {
			["displayName"] = "Retribution SEAD",
			["name"] = "Retribution SEAD",
			-- 4x AGM-88C HARM + AIM-120C + 2x AIM-9X + ATFLIR + centerline tank
			["pylons"] = {
				[1] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[4] = { ["CLSID"] = "{AN_ASQ_228}", ["num"] = 4 },
				[5] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 3 },
				[6] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 7 },
				[7] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 2 },
				[8] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 8 },
				[9] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 5 },
			},
			["tasks"] = { [1] = 29 },
		},
		[6] = {
			["displayName"] = "Retribution SEAD Escort",
			["name"] = "Retribution SEAD Escort",
			["pylons"] = {
				[1] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[4] = { ["CLSID"] = "{AN_ASQ_228}", ["num"] = 4 },
				[5] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 3 },
				[6] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 7 },
				[7] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 2 },
				[8] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 8 },
				[9] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 5 },
			},
			["tasks"] = { [1] = 29 },
		},
		[7] = {
			["displayName"] = "Retribution DEAD",
			["name"] = "Retribution DEAD",
			-- 4x AGM-154C JSOW (BRU-55 racks) standoff + AIM-120C + 2x AIM-9X + 2 tanks
			["pylons"] = {
				[1] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[4] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 7 },
				[5] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 3 },
				[6] = { ["CLSID"] = "{BRU55_2*AGM-154C}", ["num"] = 8 },
				[7] = { ["CLSID"] = "{BRU55_2*AGM-154C}", ["num"] = 2 },
				[8] = { ["CLSID"] = "{AN_ASQ_228}", ["num"] = 4 },
				[9] = { ["CLSID"] = "<CLEAN>", ["num"] = 5 },
			},
			["tasks"] = { [1] = 32 },
		},
		[8] = {
			["displayName"] = "Retribution CAS",
			["name"] = "Retribution CAS",
			-- 4x AGM-65F Maverick + AIM-120C + 2x AIM-9X + ATFLIR + centerline tank
			["pylons"] = {
				[1] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3] = { ["CLSID"] = "LAU_117_AGM_65F", ["num"] = 2 },
				[4] = { ["CLSID"] = "LAU_117_AGM_65F", ["num"] = 8 },
				[5] = { ["CLSID"] = "LAU_117_AGM_65F", ["num"] = 7 },
				[6] = { ["CLSID"] = "LAU_117_AGM_65F", ["num"] = 3 },
				[7] = { ["CLSID"] = "{AN_ASQ_228}", ["num"] = 4 },
				[8] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[9] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 5 },
			},
			["tasks"] = { [1] = 31 },
		},
		[9] = {
			["displayName"] = "Retribution BAI",
			["name"] = "Retribution BAI",
			-- 4x GBU-38 JDAM + AIM-120C + 2x AIM-9X + ATFLIR + centerline tank
			["pylons"] = {
				[1] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3] = { ["CLSID"] = "{GBU-38}", ["num"] = 2 },
				[4] = { ["CLSID"] = "{GBU-38}", ["num"] = 8 },
				[5] = { ["CLSID"] = "{GBU-38}", ["num"] = 7 },
				[6] = { ["CLSID"] = "{GBU-38}", ["num"] = 3 },
				[7] = { ["CLSID"] = "{AN_ASQ_228}", ["num"] = 4 },
				[8] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[9] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 5 },
			},
			["tasks"] = { [1] = 32 },
		},
		[10] = {
			["displayName"] = "Retribution Strike",
			["name"] = "Retribution Strike",
			-- Uniform 4x GBU-31V2B 2000lb JDAM (degrades to 4x Mk-84) + AIM-120C
			-- + 2x AIM-9X + ATFLIR + centerline tank. No mixed bomb sizes.
			["pylons"] = {
				[1] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3] = { ["CLSID"] = "{GBU_31_V_2B}", ["num"] = 2 },
				[4] = { ["CLSID"] = "{GBU_31_V_2B}", ["num"] = 8 },
				[5] = { ["CLSID"] = "{GBU_31_V_2B}", ["num"] = 7 },
				[6] = { ["CLSID"] = "{GBU_31_V_2B}", ["num"] = 3 },
				[7] = { ["CLSID"] = "{AN_ASQ_228}", ["num"] = 4 },
				[8] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[9] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 5 },
			},
			["tasks"] = { [1] = 33 },
		},
		[11] = {
			["displayName"] = "Retribution OCA/Aircraft",
			["name"] = "Retribution OCA/Aircraft",
			-- 4x AGM-154C JSOW (BRU-55 racks) cluster vs parked aircraft + AIM-120C + AIM-9X
			["pylons"] = {
				[1] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 3 },
				[4] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 7 },
				[5] = { ["CLSID"] = "{BRU55_2*AGM-154C}", ["num"] = 8 },
				[6] = { ["CLSID"] = "{BRU55_2*AGM-154C}", ["num"] = 2 },
				[7] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[8] = { ["CLSID"] = "{AN_ASQ_228}", ["num"] = 4 },
				[9] = { ["CLSID"] = "<CLEAN>", ["num"] = 5 },
			},
			["tasks"] = { [1] = 32 },
		},
		[12] = {
			["displayName"] = "Retribution OCA/Runway",
			["name"] = "Retribution OCA/Runway",
			-- 4x GBU-31V4B 2000lb penetrators + AIM-120C + 2x AIM-9X + ATFLIR
			["pylons"] = {
				[1] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 5 },
				[4] = { ["CLSID"] = "{GBU_31_V_4B}", ["num"] = 7 },
				[5] = { ["CLSID"] = "{GBU_31_V_4B}", ["num"] = 3 },
				[6] = { ["CLSID"] = "{GBU_31_V_4B}", ["num"] = 2 },
				[7] = { ["CLSID"] = "{GBU_31_V_4B}", ["num"] = 8 },
				[8] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[9] = { ["CLSID"] = "{AN_ASQ_228}", ["num"] = 4 },
			},
			["tasks"] = { [1] = 34 },
		},
		[13] = {
			["displayName"] = "Retribution Anti-ship",
			["name"] = "Retribution Anti-ship",
			-- 4x AGM-84D Harpoon + 2x AIM-9X + AIM-120C + ATFLIR + centerline tank
			["pylons"] = {
				[1] = { ["CLSID"] = "{AGM_84D}", ["num"] = 8 },
				[2] = { ["CLSID"] = "{AGM_84D}", ["num"] = 7 },
				[3] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[4] = { ["CLSID"] = "{AN_ASQ_228}", ["num"] = 4 },
				[5] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[6] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[7] = { ["CLSID"] = "{AGM_84D}", ["num"] = 3 },
				[8] = { ["CLSID"] = "{AGM_84D}", ["num"] = 2 },
				[9] = { ["CLSID"] = "{FPU_8A_FUEL_TANK}", ["num"] = 5 },
			},
			["tasks"] = { [1] = 30 },
		},
	},
	["unitType"] = "FA-18C_hornet",
}
return unitPayloads
