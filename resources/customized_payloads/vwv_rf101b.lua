local unitPayloads = {
	["name"]="vwv_rf101b",
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
				[1]=31
			}
		},
		[2]=
		{
			-- 414th TARPS photo-recon overflight: built-in cameras, no external stores.
			-- Loadout is matched by name ("Retribution TARPS"); the runtime recon task
			-- is set by aircraftbehavior.configure_tarps, so the tasks tag is only the
			-- ME role-menu placement (mirrors the Armed Recon entry).
			["displayName"]="Retribution TARPS",
			["name"]="Retribution TARPS",
			["pylons"]=
			{
			},
			["tasks"]=
			{
				[1]=31
			}
		}
	},
	["unitType"]="vwv_rf101b"
}
return unitPayloads