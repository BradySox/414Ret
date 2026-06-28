local unitPayloads = {
	["name"]="vwv_ra-5",
	["payloads"]=
	{
		[1]=
		{
			["displayName"]="Retribution Armed Recon",
			["name"]="Retribution Armed Recon",
			["pylons"]=
			{
			},
			["tasks"]=
			{
				[1]=17
			}
		},
		[2]=
		{
			["displayName"]="Retribution Strike",
			["name"]="Retribution Strike",
			["pylons"]=
			{
			},
			["tasks"]=
			{
				[1]=31,
				[2]=32,
				[3]=33
			}
		},
		[3]=
		{
			["displayName"]="Retribution Intercept",
			["name"]="Retribution Intercept",
			["pylons"]=
			{
			},
			["tasks"]=
			{
				[1]=10
			}
		},
		[4]=
		{
			-- 414th TARPS photo-recon overflight: built-in cameras, no external stores.
			-- Loadout is matched by name ("Retribution TARPS"); the runtime recon task
			-- is set by aircraftbehavior.configure_tarps, so the tasks tag is only the
			-- ME role-menu placement (mirrors the recon Armed Recon entry).
			["displayName"]="Retribution TARPS",
			["name"]="Retribution TARPS",
			["pylons"]=
			{
			},
			["tasks"]=
			{
				[1]=17
			}
		}
	},
	["unitType"]="vwv_ra-5"
}
return unitPayloads