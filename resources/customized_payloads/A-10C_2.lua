-- A-10C II Warthog loadouts for 414th Retribution
-- Pylon layout (1-11):
--   1        = left outboard  (ECM pod or AIM-9)
--   2        = left mid-outboard
--   3        = left inboard   (Maverick inner station)
--   4-5      = left wing body (bombs/rockets)
--   6        = centerline (rarely used)
--   7-8      = right wing body (bombs/rockets)
--   9        = right inboard  (Maverick inner station)
--   10       = right mid-outboard (Litening TGP)
--   11       = right outboard (AIM-9M pair)
-- CLSID reference:
--   AIM-9M 2-pack:    {DB434044-F5D0-4F1F-9BA9-B73027E18DD3}
--   ALQ-184 ECM:      ALQ_184
--   Litening TGP:     {A111396E-D3E8-4b9c-8AC9-2432489304D5}
--   AGM-65K Mav:      {69DC8AE7-8F77-427B-B8AA-B19D3F478B66}
--   AGM-65G Mav:      LAU_117_AGM_65G
--   AGM-65D 2-pack:   {E6A6262A-CA08-4B3D-B030-E1A993B98452} / ...453
--   GBU-10 LGB:       {51F9AAE5-964F-4D21-83FB-502E3BFE5F8A}
--   GBU-31V1B JDAM:   {GBU-31}
--   GBU-31V3B pen:    {GBU-31V3B}
--   GBU-38 JDAM:      {GBU-38}
--   GBU-54 LJDAM:     {GBU_54_V_1B}
--   APKWS M282 pod:   {LAU-131 - 7 AGR-20 M282}
--   APKWS A pod:      {LAU-131 - 7 AGR-20A}
local unitPayloads = {
	["name"] = "A-10C II",
	["payloads"] = {
		[1] = {
			["displayName"] = "Retribution CAS",
			["name"] = "Retribution CAS",
			["pylons"] = {
				[1]  = { ["CLSID"] = "ALQ_184", ["num"] = 1 },
				[2]  = { ["CLSID"] = "{E6A6262A-CA08-4B3D-B030-E1A993B98453}", ["num"] = 9 },
				[3]  = { ["CLSID"] = "{LAU-131 - 7 AGR-20 M282}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{GBU_54_V_1B}", ["num"] = 7 },
				[5]  = { ["CLSID"] = "{GBU_54_V_1B}", ["num"] = 5 },
				[6]  = { ["CLSID"] = "{LAU-131 - 7 AGR-20 M282}", ["num"] = 4 },
				[7]  = { ["CLSID"] = "{E6A6262A-CA08-4B3D-B030-E1A993B98452}", ["num"] = 3 },
				[8]  = { ["CLSID"] = "{LAU-131 - 7 AGR-20A}", ["num"] = 2 },
				[9]  = { ["CLSID"] = "{A111396E-D3E8-4b9c-8AC9-2432489304D5}", ["num"] = 10 },
				[10] = { ["CLSID"] = "{DB434044-F5D0-4F1F-9BA9-B73027E18DD3}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 31 },
		},
		[2] = {
			["displayName"] = "Retribution BAI",
			["name"] = "Retribution BAI",
			["pylons"] = {
				[1]  = { ["CLSID"] = "ALQ_184", ["num"] = 1 },
				[2]  = { ["CLSID"] = "{69DC8AE7-8F77-427B-B8AA-B19D3F478B66}", ["num"] = 3 },
				[3]  = { ["CLSID"] = "{GBU-38}", ["num"] = 4 },
				[4]  = { ["CLSID"] = "{GBU-38}", ["num"] = 5 },
				[5]  = { ["CLSID"] = "{GBU-38}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{GBU-38}", ["num"] = 8 },
				[7]  = { ["CLSID"] = "{69DC8AE7-8F77-427B-B8AA-B19D3F478B66}", ["num"] = 9 },
				[8]  = { ["CLSID"] = "{A111396E-D3E8-4b9c-8AC9-2432489304D5}", ["num"] = 10 },
				[9]  = { ["CLSID"] = "{DB434044-F5D0-4F1F-9BA9-B73027E18DD3}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 32 },
		},
		[3] = {
			["displayName"] = "Retribution Strike",
			["name"] = "Retribution Strike",
			["pylons"] = {
				[1]  = { ["CLSID"] = "ALQ_184", ["num"] = 1 },
				[2]  = { ["CLSID"] = "{GBU-38}", ["num"] = 5 },
				[3]  = { ["CLSID"] = "{GBU-31}", ["num"] = 4 },
				[4]  = { ["CLSID"] = "{GBU-31}", ["num"] = 8 },
				[5]  = { ["CLSID"] = "{GBU-38}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{A111396E-D3E8-4b9c-8AC9-2432489304D5}", ["num"] = 10 },
				[7]  = { ["CLSID"] = "{DB434044-F5D0-4F1F-9BA9-B73027E18DD3}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 32, [2] = 33 },
		},
		[4] = {
			["displayName"] = "Retribution OCA/Runway",
			["name"] = "Retribution OCA/Runway",
			["pylons"] = {
				[1]  = { ["CLSID"] = "ALQ_184", ["num"] = 1 },
				[2]  = { ["CLSID"] = "{GBU-31V3B}", ["num"] = 4 },
				[3]  = { ["CLSID"] = "{GBU-31V3B}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{A111396E-D3E8-4b9c-8AC9-2432489304D5}", ["num"] = 10 },
				[5]  = { ["CLSID"] = "{DB434044-F5D0-4F1F-9BA9-B73027E18DD3}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 34 },
		},
		[5] = {
			["displayName"] = "Retribution DEAD",
			["name"] = "Retribution DEAD",
			["pylons"] = {
				[1]  = { ["CLSID"] = "ALQ_184", ["num"] = 1 },
				[2]  = { ["CLSID"] = "{GBU-31}", ["num"] = 4 },
				[3]  = { ["CLSID"] = "{GBU-31}", ["num"] = 8 },
				[4]  = { ["CLSID"] = "{A111396E-D3E8-4b9c-8AC9-2432489304D5}", ["num"] = 10 },
				[5]  = { ["CLSID"] = "{DB434044-F5D0-4F1F-9BA9-B73027E18DD3}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 32 },
		},
		[6] = {
			-- A-10 anti-ship: Maverick against small vessels, GBU-10 for larger targets
			["displayName"] = "Retribution Anti-ship",
			["name"] = "Retribution Anti-ship",
			["pylons"] = {
				[1]  = { ["CLSID"] = "ALQ_184", ["num"] = 1 },
				[2]  = { ["CLSID"] = "LAU_117_AGM_65G", ["num"] = 3 },
				[3]  = { ["CLSID"] = "{51F9AAE5-964F-4D21-83FB-502E3BFE5F8A}", ["num"] = 4 },
				[4]  = { ["CLSID"] = "{51F9AAE5-964F-4D21-83FB-502E3BFE5F8A}", ["num"] = 8 },
				[5]  = { ["CLSID"] = "LAU_117_AGM_65G", ["num"] = 9 },
				[6]  = { ["CLSID"] = "{A111396E-D3E8-4b9c-8AC9-2432489304D5}", ["num"] = 10 },
				[7]  = { ["CLSID"] = "{DB434044-F5D0-4F1F-9BA9-B73027E18DD3}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 30 },
		},
	},
	["unitType"] = "A-10C_2",
}
return unitPayloads
