-- F-16C Block 50 loadouts for 414th Retribution
-- Preset set matches the airframe's tasks in resources/units/aircraft/F-16C_50.yaml:
--   BARCAP TARCAP Escort "Fighter sweep" SEAD "SEAD Escort" DEAD CAS BAI
--   Strike OCA/Aircraft OCA/Runway   (NO Anti-ship: the DCS F-16C has no Harpoon)
-- Pylon layout (num):
--   1,9   = wingtips    (AIM-9 only)
--   2,8   = outer wing  (AIM-120/AIM-9)
--   3,7   = mid wing     -- versatile: AMRAAM, Maverick, HARM, JDAM, JSOW, LGB
--   4,6   = inner wing   -- bomb/tank station: LGB, cluster, GP, HARM, fuel tank
--                           (NOT AMRAAM, NOT Maverick, NOT JDAM)
--   5     = centerline  (ALQ-184 ECM)
--   10    = HTS-R pod station (SEAD only)
--   11    = Sniper XR TGP station
-- All CLSIDs verified against pydcs F_16C_50 pylon tables.
local unitPayloads = {
	["name"] = "F-16C_50",
	["payloads"] = {
		[1] = {
			["displayName"] = "Retribution BARCAP",
			["name"] = "Retribution BARCAP",
			-- 4x AIM-120C (2/8/3/7) + 2x AIM-9X tips + 2x 370gal wing tanks + ECM
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 7 },
				[4]  = { ["CLSID"] = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}", ["num"] = 6 },
				[5]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[6]  = { ["CLSID"] = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}", ["num"] = 4 },
				[7]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 3 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[9]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 11, [2] = 10 },
		},
		[2] = {
			["displayName"] = "Retribution TARCAP",
			["name"] = "Retribution TARCAP",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 7 },
				[4]  = { ["CLSID"] = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}", ["num"] = 6 },
				[5]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[6]  = { ["CLSID"] = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}", ["num"] = 4 },
				[7]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 3 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[9]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 11, [2] = 10 },
		},
		[3] = {
			["displayName"] = "Retribution Escort",
			["name"] = "Retribution Escort",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 7 },
				[4]  = { ["CLSID"] = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}", ["num"] = 6 },
				[5]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[6]  = { ["CLSID"] = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}", ["num"] = 4 },
				[7]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 3 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[9]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 18 },
		},
		[4] = {
			["displayName"] = "Retribution Fighter Sweep",
			["name"] = "Retribution Fighter Sweep",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 7 },
				[4]  = { ["CLSID"] = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}", ["num"] = 6 },
				[5]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[6]  = { ["CLSID"] = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}", ["num"] = 4 },
				[7]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 3 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[9]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 19 },
		},
		[5] = {
			["displayName"] = "Retribution SEAD",
			["name"] = "Retribution SEAD",
			-- 4x AGM-88C HARM (3/7 mid + 4/6 inner) + 2x AIM-120C + AIM-9X tips + HTS + ECM
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[3]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 7 },
				[4]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 6 },
				[5]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[6]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 4 },
				[7]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 3 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[9]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[10] = { ["CLSID"] = "{AN_ASQ_213}", ["num"] = 10 },
			},
			["tasks"] = { [1] = 29 },
		},
		[6] = {
			["displayName"] = "Retribution SEAD Escort",
			["name"] = "Retribution SEAD Escort",
			-- 2x HARM (3/7) + fuel inner + AMRAAM/AIM-9X self-escort + HTS + ECM
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[3]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 7 },
				[4]  = { ["CLSID"] = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}", ["num"] = 6 },
				[5]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[6]  = { ["CLSID"] = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}", ["num"] = 4 },
				[7]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 3 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[9]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[10] = { ["CLSID"] = "{AN_ASQ_213}", ["num"] = 10 },
			},
			["tasks"] = { [1] = 29 },
		},
		[7] = {
			["displayName"] = "Retribution DEAD",
			["name"] = "Retribution DEAD",
			-- 4x AGM-154A JSOW standoff (BRU-57 on 3/7) + fuel inner + AMRAAM/AIM-9X + Sniper
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[3]  = { ["CLSID"] = "{BRU57_2*AGM-154A}", ["num"] = 7 },
				[4]  = { ["CLSID"] = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}", ["num"] = 6 },
				[5]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[6]  = { ["CLSID"] = "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}", ["num"] = 4 },
				[7]  = { ["CLSID"] = "{BRU57_2*AGM-154A}", ["num"] = 3 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[9]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 32 },
		},
		[8] = {
			["displayName"] = "Retribution CAS",
			["name"] = "Retribution CAS",
			-- 2x AGM-65D triple-rack (3/7) + 2x GBU-12 LGB inner + AMRAAM/AIM-9X + Sniper
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[3]  = { ["CLSID"] = "{DAC53A2F-79CA-42FF-A77A-F5649B601308}", ["num"] = 7 },
				[4]  = { ["CLSID"] = "{DB769D48-67D7-42ED-A2BE-108D566C8B1E}", ["num"] = 6 },
				[5]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[6]  = { ["CLSID"] = "{DB769D48-67D7-42ED-A2BE-108D566C8B1E}", ["num"] = 4 },
				[7]  = { ["CLSID"] = "{DAC53A2F-79CA-42FF-A77A-F5649B601308}", ["num"] = 3 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[9]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 31 },
		},
		[9] = {
			["displayName"] = "Retribution BAI",
			["name"] = "Retribution BAI",
			-- 2x GBU-38 JDAM (3/7) + 2x CBU-97 SFW inner + AMRAAM/AIM-9X + Sniper
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[3]  = { ["CLSID"] = "{GBU-38}", ["num"] = 7 },
				[4]  = { ["CLSID"] = "{5335D97A-35A5-4643-9D9B-026C75961E52}", ["num"] = 6 },
				[5]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[6]  = { ["CLSID"] = "{5335D97A-35A5-4643-9D9B-026C75961E52}", ["num"] = 4 },
				[7]  = { ["CLSID"] = "{GBU-38}", ["num"] = 3 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[9]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 32 },
		},
		[10] = {
			["displayName"] = "Retribution Strike",
			["name"] = "Retribution Strike",
			-- 2x GBU-31 2000lb JDAM (3/7) + 2x GBU-12 LGB inner + AMRAAM/AIM-9X + Sniper
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[3]  = { ["CLSID"] = "{GBU-31}", ["num"] = 7 },
				[4]  = { ["CLSID"] = "{DB769D48-67D7-42ED-A2BE-108D566C8B1E}", ["num"] = 6 },
				[5]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[6]  = { ["CLSID"] = "{DB769D48-67D7-42ED-A2BE-108D566C8B1E}", ["num"] = 4 },
				[7]  = { ["CLSID"] = "{GBU-31}", ["num"] = 3 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[9]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 33 },
		},
		[11] = {
			["displayName"] = "Retribution OCA/Aircraft",
			["name"] = "Retribution OCA/Aircraft",
			-- 2x GBU-38 JDAM (3/7) + 2x CBU-97 cluster vs parked aircraft + AMRAAM/AIM-9X
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[3]  = { ["CLSID"] = "{GBU-38}", ["num"] = 7 },
				[4]  = { ["CLSID"] = "{5335D97A-35A5-4643-9D9B-026C75961E52}", ["num"] = 6 },
				[5]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[6]  = { ["CLSID"] = "{5335D97A-35A5-4643-9D9B-026C75961E52}", ["num"] = 4 },
				[7]  = { ["CLSID"] = "{GBU-38}", ["num"] = 3 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[9]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 32 },
		},
		[12] = {
			["displayName"] = "Retribution OCA/Runway",
			["name"] = "Retribution OCA/Runway",
			-- 2x GBU-31(V)3 penetrator (3/7) + 2x GBU-24 Paveway III inner + AMRAAM/AIM-9X
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[3]  = { ["CLSID"] = "{GBU-31V3B}", ["num"] = 7 },
				[4]  = { ["CLSID"] = "{34759BBC-AF1E-4AEE-A581-498FF7A6EBCE}", ["num"] = 6 },
				[5]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[6]  = { ["CLSID"] = "{34759BBC-AF1E-4AEE-A581-498FF7A6EBCE}", ["num"] = 4 },
				[7]  = { ["CLSID"] = "{GBU-31V3B}", ["num"] = 3 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[9]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 34 },
		},
	},
	["unitType"] = "F-16C_50",
}
return unitPayloads
