-- F-15E Strike Eagle loadouts for 414th Retribution
-- Preset set matches resources/units/aircraft/F-15ESE.yaml tasks:
--   BARCAP TARCAP Escort "Fighter sweep" DEAD CAS BAI Strike OCA/Aircraft OCA/Runway
-- The DCS F-15E is NOT a Wild Weasel: no AGM-88 HARM, no SEAD task. DEAD is done
-- with AGM-154A JSOW standoff against known emitters, not reactive HARM.
-- Pylon layout (num):
--   15,1  = wingtips     (AIM-9M / AIM-120 only -- NO AIM-9X on this airframe)
--   14,2  = external wing (tank, JDAM, JSOW, CBU, GBU-54)
--   13,3  = inner wing    (AAMs)
--   12,4  = CFT shoulder  (CBU-87/97 x3, JSOW, GBU-31 x2, BLU-107 x6)
--   11,10,5,6 = CFT mid    (AIM-120, bombs)
--   9     = LANTIRN nav pod
--   8     = centerline tank
--   7     = LANTIRN TGP
-- All CLSIDs verified against pydcs F_15ESE pylon tables.
local unitPayloads = {
	["name"] = "F-15ESE",
	["payloads"] = {
		[1] = {
			["displayName"] = "Retribution BARCAP",
			["name"] = "Retribution BARCAP",
			-- 4x AIM-120C (11/10/6/5) + 4x AIM-9M (13/3 inner, 15/1 tips) + 2 tanks
			["pylons"] = {
				[1]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 15 },
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
				[13] = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 11, [2] = 10 },
		},
		[2] = {
			["displayName"] = "Retribution TARCAP",
			["name"] = "Retribution TARCAP",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 15 },
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
				[13] = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 11, [2] = 10 },
		},
		[3] = {
			["displayName"] = "Retribution Escort",
			["name"] = "Retribution Escort",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 15 },
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
				[13] = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 18 },
		},
		[4] = {
			["displayName"] = "Retribution Fighter sweep",
			["name"] = "Retribution Fighter sweep",
			["pylons"] = {
				[1]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 15 },
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
				[13] = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 1 },
			},
			["tasks"] = { [1] = 19 },
		},
		[5] = {
			["displayName"] = "Retribution DEAD",
			["name"] = "Retribution DEAD",
			-- 2x AGM-154A JSOW standoff (CFT shoulders 4/12) + 2x 610gal wing tanks
			-- + 2x AIM-120C + AIM-9M tips + LANTIRN
			["pylons"] = {
				[1]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 14 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 1 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 5 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 10 },
				[6]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[7]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[8]  = { ["CLSID"] = "{AGM-154A}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "{AGM-154A}", ["num"] = 12 },
				[10] = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 2 },
			},
			["tasks"] = { [1] = 32 },
		},
		[6] = {
			["displayName"] = "Retribution CAS",
			["name"] = "Retribution CAS",
			-- 6x CBU-97 SFW (CFT shoulders 4/12 x3 each) + 2x 610gal wing tanks
			-- + 2x AIM-120C + AIM-9M tips + LANTIRN
			["pylons"] = {
				[1]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 14 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 1 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 5 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 10 },
				[6]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[7]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[8]  = { ["CLSID"] = "{CFT_L_CBU_97_x_3}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "{CFT_R_CBU_97_x_3}", ["num"] = 12 },
				[10] = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 2 },
			},
			["tasks"] = { [1] = 31 },
		},
		[7] = {
			["displayName"] = "Retribution BAI",
			["name"] = "Retribution BAI",
			-- 6x GBU-38 JDAM (CFT shoulders 4/12 x3 each) + 2x 610gal wing tanks
			-- + 2x AIM-120C + AIM-9M tips + LANTIRN
			["pylons"] = {
				[1]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 14 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 1 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 5 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 10 },
				[6]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[7]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[8]  = { ["CLSID"] = "{CFT_L_GBU_38_x_3}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "{CFT_R_GBU_38_x_3}", ["num"] = 12 },
				[10] = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 2 },
			},
			["tasks"] = { [1] = 32 },
		},
		[8] = {
			["displayName"] = "Retribution Strike",
			["name"] = "Retribution Strike",
			-- 4x GBU-31 2000lb JDAM (CFT shoulders 4/12 x2 each) + 2x 610gal wing tanks
			-- + 2x AIM-120C + AIM-9M tips + LANTIRN
			["pylons"] = {
				[1]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 14 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 1 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 5 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 10 },
				[6]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[7]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[8]  = { ["CLSID"] = "{CFT_L_GBU_31_x_2}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "{CFT_R_GBU_31_x_2}", ["num"] = 12 },
				[10] = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 2 },
			},
			["tasks"] = { [1] = 33 },
		},
		[9] = {
			["displayName"] = "Retribution OCA/Aircraft",
			["name"] = "Retribution OCA/Aircraft",
			-- 4x GBU-31(V)3 penetrator (CFT shoulders 4/12 x2 each) for hardened shelters
			-- + 2x 610gal wing tanks + 2x AIM-120C + AIM-9M tips + LANTIRN
			["pylons"] = {
				[1]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 14 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 1 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 5 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 10 },
				[6]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[7]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[8]  = { ["CLSID"] = "{CFT_L_GBU_31V3B_x_2}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "{CFT_R_GBU_31V3B_x_2}", ["num"] = 12 },
				[10] = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 2 },
			},
			["tasks"] = { [1] = 32 },
		},
		[10] = {
			["displayName"] = "Retribution OCA/Runway",
			["name"] = "Retribution OCA/Runway",
			-- 12x BLU-107 Durandal anti-runway (CFT shoulders 4/12 x6 each)
			-- + 2x 610gal wing tanks + 2x AIM-120C + AIM-9M tips + LANTIRN
			["pylons"] = {
				[1]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 15 },
				[2]  = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 14 },
				[3]  = { ["CLSID"] = "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", ["num"] = 1 },
				[4]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 5 },
				[5]  = { ["CLSID"] = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", ["num"] = 10 },
				[6]  = { ["CLSID"] = "{F-15E_AAQ-13_LANTIRN}", ["num"] = 9 },
				[7]  = { ["CLSID"] = "{F-15E_AAQ-14_LANTIRN}", ["num"] = 7 },
				[8]  = { ["CLSID"] = "{CFT_L_BLU107_x_6}", ["num"] = 4 },
				[9]  = { ["CLSID"] = "{CFT_R_BLU107_x_6}", ["num"] = 12 },
				[10] = { ["CLSID"] = "{F15E_EXTTANK}", ["num"] = 2 },
			},
			["tasks"] = { [1] = 34 },
		},
	},
	["tasks"] = {},
	["unitType"] = "F-15ESE",
}
return unitPayloads
