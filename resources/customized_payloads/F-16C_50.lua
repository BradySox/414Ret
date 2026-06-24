-- F-16C Block 50 loadouts for 414th Retribution
-- Pylon layout:
--   1,9   = wingtips    (AIM-9X)
--   2,8   = outer wing  (AIM-9X or AIM-120C)
--   3,7   = mid wing    (AIM-120C, bombs, HARMs)
--   4,6   = inner wing  (AIM-120C, bombs, HARMs)
--   5     = centerline  (ALQ-184 ECM or tank)
--   10    = HTS-R avionics station
--   11    = Sniper XR TGP cheek station
-- CLSID reference:
--   AIM-9X:          {5CE2FF2A-645A-4197-B48D-8720AC69394F}
--   AIM-120C:        {40EF17B7-F508-45de-8566-6FFECC0C1AB8}
--   AGM-88C HARM:    {B06DD79A-F21E-4EB9-BD9D-AB3844618C93}
--   AGM-65G Mav:     LAU_117_AGM_65G
--   3xAGM-65D rack:  {DAC53A2F-79CA-42FF-A77A-F5649B601308}
--   GBU-31V3B pen:   {GBU-31V3B}
--   GBU-38 JDAM:     {GBU-38}
--   2xCBU-105 rack:  {BRU57_2*CBU-105}
--   2xJSOW-A rack:   {BRU57_2*AGM-154A}
--   ALQ-184 ECM:     ALQ_184
--   Sniper XR TGP:   {AN_AAQ_33}
--   HTS-R pod:       {AN_ASQ_213}
local unitPayloads = {
	["name"] = "F-16C_50",
	["payloads"] = {
		[1] = {
			["displayName"] = "Retribution BARCAP",
			["name"] = "Retribution BARCAP",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 11, [2] = 10 },
		},
		[2] = {
			["displayName"] = "Retribution TARCAP",
			["name"] = "Retribution TARCAP",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 11, [2] = 10 },
		},
		[3] = {
			["displayName"] = "Retribution Escort",
			["name"] = "Retribution Escort",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 18 },
		},
		[4] = {
			["displayName"] = "Retribution Fighter Sweep",
			["name"] = "Retribution Fighter Sweep",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "<CLEAN>", ["num"] = 5 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 19 },
		},
		[5] = {
			["displayName"] = "Retribution SEAD",
			["name"] = "Retribution SEAD",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[5]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 6 },
				[8]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
				[11] = { ["CLSID"] = "{AN_ASQ_213}", ["num"] = 10 },
			},
			["tasks"] = { [1] = 29 },
		},
		[6] = {
			["displayName"] = "Retribution SEAD Sweep",
			["name"] = "Retribution SEAD Sweep",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[5]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 6 },
				[8]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
				[11] = { ["CLSID"] = "{AN_ASQ_213}", ["num"] = 10 },
			},
			["tasks"] = { [1] = 29 },
		},
		[7] = {
			["displayName"] = "Retribution SEAD Escort",
			["name"] = "Retribution SEAD Escort",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[5]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "LAU_117_AGM_65G", ["num"] = 6 },
				[8]  = { ["CLSID"] = "LAU_117_AGM_65G", ["num"] = 4 },
				[9]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
				[11] = { ["CLSID"] = "{AN_ASQ_213}", ["num"] = 10 },
			},
			["tasks"] = { [1] = 29 },
		},
		[8] = {
			["displayName"] = "Retribution DEAD",
			["name"] = "Retribution DEAD",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[5]  = { ["CLSID"] = "{BRU57_2*AGM-154A}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{BRU57_2*AGM-154A}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "{GBU-38}", ["num"] = 6 },
				[8]  = { ["CLSID"] = "{GBU-38}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
				[11] = { ["CLSID"] = "{AN_ASQ_213}", ["num"] = 10 },
			},
			["tasks"] = { [1] = 32 },
		},
		[9] = {
			["displayName"] = "Retribution CAS",
			["name"] = "Retribution CAS",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[5]  = { ["CLSID"] = "{DAC53A2F-79CA-42FF-A77A-F5649B601308}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{DAC53A2F-79CA-42FF-A77A-F5649B601308}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "{GBU-38}", ["num"] = 6 },
				[8]  = { ["CLSID"] = "{GBU-38}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
				[11] = { ["CLSID"] = "{AN_ASQ_213}", ["num"] = 10 },
			},
			["tasks"] = { [1] = 31 },
		},
		[10] = {
			["displayName"] = "Retribution BAI",
			["name"] = "Retribution BAI",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[5]  = { ["CLSID"] = "{BRU57_2*CBU-105}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{BRU57_2*CBU-105}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "{GBU-38}", ["num"] = 6 },
				[8]  = { ["CLSID"] = "{GBU-38}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
				[11] = { ["CLSID"] = "{AN_ASQ_213}", ["num"] = 10 },
			},
			["tasks"] = { [1] = 32 },
		},
		[11] = {
			["displayName"] = "Retribution Strike",
			["name"] = "Retribution Strike",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[5]  = { ["CLSID"] = "{GBU-31V3B}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{GBU-31V3B}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "{GBU-38}", ["num"] = 6 },
				[8]  = { ["CLSID"] = "{GBU-38}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
				[11] = { ["CLSID"] = "{AN_ASQ_213}", ["num"] = 10 },
			},
			["tasks"] = { [1] = 32, [2] = 33 },
		},
		[12] = {
			["displayName"] = "Retribution OCA/Aircraft",
			["name"] = "Retribution OCA/Aircraft",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[5]  = { ["CLSID"] = "{GBU-31V3B}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{GBU-31V3B}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "{GBU-38}", ["num"] = 6 },
				[8]  = { ["CLSID"] = "{GBU-38}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
				[11] = { ["CLSID"] = "{AN_ASQ_213}", ["num"] = 10 },
			},
			["tasks"] = { [1] = 32 },
		},
		[13] = {
			["displayName"] = "Retribution OCA/Runway",
			["name"] = "Retribution OCA/Runway",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[5]  = { ["CLSID"] = "{GBU-31V3B}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{GBU-31V3B}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "{GBU-31V3B}", ["num"] = 6 },
				[8]  = { ["CLSID"] = "{GBU-31V3B}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
				[11] = { ["CLSID"] = "{AN_ASQ_213}", ["num"] = 10 },
			},
			["tasks"] = { [1] = 34 },
		},
		[14] = {
			-- F-16C has no Harpoon in DCS; use JSOW-A as best anti-surface standoff option
			["displayName"] = "Retribution Anti-ship",
			["name"] = "Retribution Anti-ship",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 2 },
				[5]  = { ["CLSID"] = "{BRU57_2*AGM-154A}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{BRU57_2*AGM-154A}", ["num"] = 3 },
				[7]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "ALQ_184", ["num"] = 5 },
				[10] = { ["CLSID"] = "{AN_AAQ_33}", ["num"] = 11 },
				[11] = { ["CLSID"] = "{AN_ASQ_213}", ["num"] = 10 },
			},
			["tasks"] = { [1] = 30 },
		},
	},
	["unitType"] = "F-16C_50",
}
return unitPayloads
