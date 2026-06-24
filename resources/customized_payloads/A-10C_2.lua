-- A-10C II Warthog loadouts for 414th Retribution
-- Preset set matches resources/units/aircraft/A-10C_2.yaml tasks:
--   CAS BAI Strike OCA/Aircraft OCA/Runway
--   (NO DEAD / Anti-ship / SEAD: the A-10C has no HARM and Retribution does not
--    task it for those roles.)
-- Pylon layout (num 1-11): 1 outboard (ECM), 3/9 inner Maverick stations,
--   4-5 / 7-8 wing body (bombs/rockets), 10 Litening TGP, 11 AIM-9M pair.
-- All CLSIDs verified against pydcs A_10C_2 pylon tables.
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
			["tasks"] = { [1] = 33 },
		},
		[4] = {
			["displayName"] = "Retribution OCA/Aircraft",
			["name"] = "Retribution OCA/Aircraft",
			-- 2x CBU-105 WCMD SFW (4/8) + 2x GBU-38 (5/7) + Maverick vs parked aircraft
			["pylons"] = {
				[1]  = { ["CLSID"] = "ALQ_184", ["num"] = 1 },
				[2]  = { ["CLSID"] = "{69DC8AE7-8F77-427B-B8AA-B19D3F478B66}", ["num"] = 3 },
				[3]  = { ["CLSID"] = "{CBU_105}", ["num"] = 4 },
				[4]  = { ["CLSID"] = "{GBU-38}", ["num"] = 5 },
				[5]  = { ["CLSID"] = "{GBU-38}", ["num"] = 7 },
				[6]  = { ["CLSID"] = "{CBU_105}", ["num"] = 8 },
				[7]  = { ["CLSID"] = "{69DC8AE7-8F77-427B-B8AA-B19D3F478B66}", ["num"] = 9 },
				[8]  = { ["CLSID"] = "{A111396E-D3E8-4b9c-8AC9-2432489304D5}", ["num"] = 10 },
				[9]  = { ["CLSID"] = "{DB434044-F5D0-4F1F-9BA9-B73027E18DD3}", ["num"] = 11 },
			},
			["tasks"] = { [1] = 32 },
		},
		[5] = {
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
	},
	["unitType"] = "A-10C_2",
}
return unitPayloads
