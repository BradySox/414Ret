-- F-15E Strike Eagle loadouts for 414th Retribution
-- Pylon layout:
--   15, 1  = outer wingtips      (AIM-9X)
--   14, 2  = outer wing pylons   (tank, bombs, HARMs)
--   13, 3  = inner wing pylons   (AAMs, bombs, HARMs)
--   12, 4  = CFT shoulder        (bombs, HARMs)
--   11,10,5,6 = CFT mid stations (AIM-120, bombs)
--   9      = LANTIRN nav pod
--   8      = centerline tank
--   7      = LANTIRN TGP
-- CLSID reference:
--   AIM-9X:             {5CE2FF2A-645A-4197-B48D-8720AC69394F}
--   AIM-9M:             {6CEB49FC-DED8-4DED-B053-E1F033FF72D3}
--   AIM-120C:           {40EF17B7-F508-45de-8566-6FFECC0C1AB8}
--   AGM-88C HARM:       {B06DD79A-F21E-4EB9-BD9D-AB3844618C93}
--   AGM-154A JSOW-A:    {AGM-154A}
--   GBU-31(V)1/B JDAM:  {GBU-31}
--   GBU-31(V)3/B pen:   {GBU-31V3B}
--   CFT 2xGBU-31V1B:    {CFT_L_GBU_31_x_2} / {CFT_R_GBU_31_x_2}
--   CFT 2xGBU-31V3B:    {CFT_L_GBU_31V3B_x_2} / {CFT_R_GBU_31V3B_x_2}
--   GBU-38 JDAM:        {GBU-38}
--   GBU-54 LJDAM:       {GBU_54_V_1B}
--   CBU-105 x3 CFT:     {CFT_L_CBU_105_x_3} / {CFT_R_CBU_105_x_3}
--   BLU-107 x6 CFT:     {CFT_L_BLU107_x_6} / {CFT_R_BLU107_x_6}
--   LANTIRN nav:        {F-15E_AAQ-13_LANTIRN}
--   LANTIRN TGP:        {F-15E_AAQ-14_LANTIRN}
--   Ext tank:           {F15E_EXTTANK}
local unitPayloads = {
	["name"] = "F-15ESE",
	["payloads"] = {
		[1] = {
			["displayName"] = "Retribution BARCAP",
			["name"] = "Retribution BARCAP",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 14 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 13 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 11 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 10 },
				[6]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[7]  = { ["CLSID"] = "<CLEAN>", ["num"] = 8 },
				[8]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[9]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[10] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 5 },
				[11] = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 3 },
				[12] = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 2 },
				[13] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 11, [2] = 10 },
		},
		[2] = {
			["displayName"] = "Retribution TARCAP",
			["name"] = "Retribution TARCAP",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 14 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 13 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 11 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 10 },
				[6]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[7]  = { ["CLSID"] = "<CLEAN>", ["num"] = 8 },
				[8]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[9]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[10] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 5 },
				[11] = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 3 },
				[12] = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 2 },
				[13] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 11, [2] = 10 },
		},
		[3] = {
			["displayName"] = "Retribution Escort",
			["name"] = "Retribution Escort",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 14 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 13 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 11 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 10 },
				[6]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[7]  = { ["CLSID"] = "<CLEAN>", ["num"] = 8 },
				[8]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[9]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[10] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 5 },
				[11] = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 3 },
				[12] = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 2 },
				[13] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 18 },
		},
		[4] = {
			["displayName"] = "Retribution Fighter Sweep",
			["name"] = "Retribution Fighter Sweep",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 14 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 13 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 11 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 10 },
				[6]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[7]  = { ["CLSID"] = "<CLEAN>", ["num"] = 8 },
				[8]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[9]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[10] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 5 },
				[11] = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 3 },
				[12] = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 2 },
				[13] = { ["CLSID"] = "{5CE2FF2A-645A-4197-B48D-8720AC69394F}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 19 },
		},
		[5] = {
			["displayName"] = "Retribution SEAD",
			["name"] = "Retribution SEAD",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 14 },
				[3]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 13 },
				[4]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 12 },
				[5]  = { ["CLSID"] = "<CLEAN>", ["num"] = 11 },
				[6]  = { ["CLSID"] = "<CLEAN>", ["num"] = 10 },
				[7]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[8]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 8 },
				[9]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[10] = { ["CLSID"] = "<CLEAN>", ["num"] = 6 },
				[11] = { ["CLSID"] = "<CLEAN>", ["num"] = 5 },
				[12] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 4 },
				[13] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 3 },
				[14] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 2 },
				[15] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 29 },
		},
		[6] = {
			["displayName"] = "Retribution SEAD Sweep",
			["name"] = "Retribution SEAD Sweep",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 14 },
				[3]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 13 },
				[4]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 12 },
				[5]  = { ["CLSID"] = "<CLEAN>", ["num"] = 11 },
				[6]  = { ["CLSID"] = "<CLEAN>", ["num"] = 10 },
				[7]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[8]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 8 },
				[9]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[10] = { ["CLSID"] = "<CLEAN>", ["num"] = 6 },
				[11] = { ["CLSID"] = "<CLEAN>", ["num"] = 5 },
				[12] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 4 },
				[13] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 3 },
				[14] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 2 },
				[15] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 29 },
		},
		[7] = {
			["displayName"] = "Retribution SEAD Escort",
			["name"] = "Retribution SEAD Escort",
			-- 4x HARM on wing + 2x HARM on CFT shoulder; inner CFTs carry AAMs for self-defense
			["pylons"] = {
				[1]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 14 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 13 },
				[4]  = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 12 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 11 },
				[6]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 10 },
				[7]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[8]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 8 },
				[9]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[10] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 6 },
				[11] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 5 },
				[12] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 4 },
				[13] = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 3 },
				[14] = { ["CLSID"] = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", ["num"] = 2 },
				[15] = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 29 },
		},
		[8] = {
			["displayName"] = "Retribution DEAD",
			["name"] = "Retribution DEAD",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 13 },
				[4]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 3 },
				[5]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[6]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[7]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 8 },
				[8]  = { ["CLSID"] = "{AGM-154A}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "{AGM-154A}", ["num"] = 12 },
				[10] = { ["CLSID"] = "{AGM-154A}", ["num"] = 14 },
				[11] = { ["CLSID"] = "{AGM-154A}", ["num"] = 2 },
			},
			["tasks"] = { [1] = 32 },
		},
		[9] = {
			["displayName"] = "Retribution CAS",
			["name"] = "Retribution CAS",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 13 },
				[4]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 3 },
				[5]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[6]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 8 },
				[7]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[8]  = { ["CLSID"] = "{CFT_L_CBU_105_x_3}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "{GBU_54_V_1B}", ["num"] = 14 },
				[10] = { ["CLSID"] = "{CFT_R_CBU_105_x_3}", ["num"] = 12 },
				[11] = { ["CLSID"] = "{GBU_54_V_1B}", ["num"] = 2 },
			},
			["tasks"] = { [1] = 31 },
		},
		[10] = {
			["displayName"] = "Retribution BAI",
			["name"] = "Retribution BAI",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[2]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 8 },
				[3]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[4]  = { ["CLSID"] = "{CFT_L_CBU_105_x_3}", ["num"] = 4 },
				[5]  = { ["CLSID"] = "{CFT_R_CBU_105_x_3}", ["num"] = 12 },
				[6]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 15 },
				[7]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 13 },
				[8]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 3 },
				[9]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 1 },
				[10] = { ["CLSID"] = "{GBU-38}", ["num"] = 14 },
				[11] = { ["CLSID"] = "{GBU-38}", ["num"] = 2 },
			},
			["tasks"] = { [1] = 32 },
		},
		[11] = {
			["displayName"] = "Retribution Strike",
			["name"] = "Retribution Strike",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 13 },
				[4]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 3 },
				[5]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[6]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 8 },
				[7]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[8]  = { ["CLSID"] = "{CFT_L_GBU_31_x_2}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "{GBU-31}", ["num"] = 2 },
				[10] = { ["CLSID"] = "{GBU-31}", ["num"] = 14 },
				[11] = { ["CLSID"] = "{CFT_R_GBU_31_x_2}", ["num"] = 12 },
			},
			["tasks"] = { [1] = 32, [2] = 33 },
		},
		[12] = {
			["displayName"] = "Retribution OCA/Aircraft",
			["name"] = "Retribution OCA/Aircraft",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 1 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 13 },
				[4]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 3 },
				[5]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[6]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 8 },
				[7]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[8]  = { ["CLSID"] = "{GBU-31V3B}", ["num"] = 14 },
				[9]  = { ["CLSID"] = "{GBU-31V3B}", ["num"] = 2 },
				[10] = { ["CLSID"] = "{CFT_R_GBU_31V3B_x_2}", ["num"] = 12 },
				[11] = { ["CLSID"] = "{CFT_L_GBU_31V3B_x_2}", ["num"] = 4 },
			},
			["tasks"] = { [1] = 32 },
		},
		[13] = {
			["displayName"] = "Retribution OCA/Runway",
			["name"] = "Retribution OCA/Runway",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 13 },
				[3]  = { ["CLSID"] = "{CFT_R_BLU107_x_6}", ["num"] = 12 },
				[4]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[5]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{CFT_L_BLU107_x_6}", ["num"] = 4 },
				[7]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 8 },
				[8]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 1 },
				[9]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 3 },
			},
			["tasks"] = { [1] = 34 },
		},
	},
	["tasks"] = {},
	["unitType"] = "F-15ESE",
}
return unitPayloads
