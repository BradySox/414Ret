local unitPayloads = {
	["name"] = "F-14A",
	["payloads"] = {
		[1] = {
			["name"] = "CAS",
			["pylons"] = {
				[1] = {
					["CLSID"] = "{LAU-138 wtip - AIM-9M}",
					["num"] = 10,
				},
				[2] = {
					["CLSID"] = "{LAU-138 wtip - AIM-9M}",
					["num"] = 1,
				},
				[3] = {
					["CLSID"] = "{PHXBRU3242_2*LAU10 RS}",
					["num"] = 9,
				},
				[4] = {
					["CLSID"] = "{PHXBRU3242_2*LAU10 LS}",
					["num"] = 2,
				},
				[5] = {
					["CLSID"] = "{F14-300gal}",
					["num"] = 8,
				},
				[6] = {
					["CLSID"] = "{F14-300gal}",
					["num"] = 3,
				},
				[7] = {
					["CLSID"] = "{BRU-32 MK-82}",
					["num"] = 7,
				},
				[8] = {
					["CLSID"] = "{BRU-32 MK-82}",
					["num"] = 4,
				},
				[9] = {
					["CLSID"] = "{BRU-32 MK-82}",
					["num"] = 6,
				},
				[10] = {
					["CLSID"] = "{BRU-32 MK-82}",
					["num"] = 5,
				},
			},
			["tasks"] = {
				[1] = 10,
			},
		},
		[2] = {
			-- Export (Iranian) F-14A had no LANTIRN/PGM capability, so Strike uses iron
			-- bombs (Mk-82) rather than the Late variant's LGBs.
			["name"] = "STRIKE",
			["pylons"] = {
				[1] = {
					["CLSID"] = "{LAU-138 wtip - AIM-9M}",
					["num"] = 10,
				},
				[2] = {
					["CLSID"] = "{LAU-138 wtip - AIM-9M}",
					["num"] = 1,
				},
				[3] = {
					["CLSID"] = "{SHOULDER AIM-7MH}",
					["num"] = 9,
				},
				[4] = {
					["CLSID"] = "{SHOULDER AIM-7MH}",
					["num"] = 2,
				},
				[5] = {
					["CLSID"] = "{F14-300gal}",
					["num"] = 8,
				},
				[6] = {
					["CLSID"] = "{F14-300gal}",
					["num"] = 3,
				},
				[7] = {
					["CLSID"] = "{BRU-32 MK-82}",
					["num"] = 7,
				},
				[8] = {
					["CLSID"] = "{BRU-32 MK-82}",
					["num"] = 4,
				},
				[9] = {
					["CLSID"] = "{BRU-32 MK-82}",
					["num"] = 6,
				},
				[10] = {
					["CLSID"] = "{BRU-32 MK-82}",
					["num"] = 5,
				},
			},
			["tasks"] = {
				[1] = 10,
			},
		},
		[3] = {
			["name"] = "CAP",
			["pylons"] = {
				[1] = {
					["CLSID"] = "{LAU-138 wtip - AIM-9M}",
					["num"] = 10,
				},
				[2] = {
					["CLSID"] = "{LAU-138 wtip - AIM-9M}",
					["num"] = 1,
				},
				[3] = {
					["CLSID"] = "{SHOULDER AIM-7MH}",
					["num"] = 2,
				},
				[4] = {
					["CLSID"] = "{SHOULDER AIM-7MH}",
					["num"] = 9,
				},
				[5] = {
					["CLSID"] = "{F14-300gal}",
					["num"] = 8,
				},
				[6] = {
					["CLSID"] = "{F14-300gal}",
					["num"] = 3,
				},
				[7] = {
					["CLSID"] = "{AIM_54A_Mk47}",
					["num"] = 7,
				},
				[8] = {
					["CLSID"] = "{AIM_54A_Mk47}",
					["num"] = 4,
				},
				[9] = {
					["CLSID"] = "{BELLY AIM-7MH}",
					["num"] = 5,
				},
			},
			["tasks"] = {
				[1] = 10,
			},
		},
		[4] = {
			["name"] = "BAI",
			["pylons"] = {
				[1] = {
					["CLSID"] = "{LAU-138 wtip - AIM-9M}",
					["num"] = 10,
				},
				[2] = {
					["CLSID"] = "{LAU-138 wtip - AIM-9M}",
					["num"] = 1,
				},
				[3] = {
					["CLSID"] = "{PHXBRU3242_2*LAU10 RS}",
					["num"] = 9,
				},
				[4] = {
					["CLSID"] = "{PHXBRU3242_2*LAU10 LS}",
					["num"] = 2,
				},
				[5] = {
					["CLSID"] = "{F14-300gal}",
					["num"] = 8,
				},
				[6] = {
					["CLSID"] = "{F14-300gal}",
					["num"] = 3,
				},
				[7] = {
					["CLSID"] = "{BRU-32 MK-20}",
					["num"] = 7,
				},
				[8] = {
					["CLSID"] = "{BRU-32 MK-20}",
					["num"] = 4,
				},
				[9] = {
					["CLSID"] = "{BRU-32 MK-20}",
					["num"] = 6,
				},
				[10] = {
					["CLSID"] = "{BRU-32 MK-20}",
					["num"] = 5,
				},
			},
			["tasks"] = {
				[1] = 10,
			},
		},
		[5] = {
			["displayName"] = "Retribution OCA/Runway",
			["name"] = "Retribution OCA/Runway",
			["pylons"] = {
				[1] = {
					["CLSID"] = "{LAU-138 wtip - AIM-9M}",
					["num"] = 10,
				},
				[2] = {
					["CLSID"] = "{SHOULDER AIM-7MH}",
					["num"] = 9,
				},
				[3] = {
					["CLSID"] = "{F14-300gal}",
					["num"] = 8,
				},
				[4] = {
					["CLSID"] = "{MAK79_MK82 4}",
					["num"] = 7,
				},
				[5] = {
					["CLSID"] = "{MAK79_MK82 4}",
					["num"] = 4,
				},
				[6] = {
					["CLSID"] = "{F14-300gal}",
					["num"] = 3,
				},
				[7] = {
					["CLSID"] = "{SHOULDER AIM-7MH}",
					["num"] = 2,
				},
				[8] = {
					["CLSID"] = "{LAU-138 wtip - AIM-9M}",
					["num"] = 1,
				},
				[9] = {
					["CLSID"] = "{MAK79_MK82 3R}",
					["num"] = 6,
				},
				[10] = {
					["CLSID"] = "{MAK79_MK82 3L}",
					["num"] = 5,
				},
			},
			["tasks"] = {
				[1] = 32,
				[2] = 31,
				[3] = 34,
				[4] = 33,
			},
		},
	},
	["unitType"] = "F-14A-95-GR",
}
return unitPayloads
