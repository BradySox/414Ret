local unitPayloads = {
	["name"]="Su-24MR",
	["payloads"]=
	{
		[1]=
		{
			-- Verbatim splice of the DCS-shipped "SHPIL,ETHER,R-60M*2,Fuel*2" fit:
			-- Shpil-2 recon pod, ETHER ELINT pod, an R-60M pair for self-defence and
			-- two 3000L bags. Matched by name, so without this entry a TARPS-tasked
			-- Su-24MR falls through every candidate name and spawns Empty.
			["displayName"]="Retribution TARPS",
			["name"]="Retribution TARPS",
			["pylons"]=
			{
				[1]=
				{
					["CLSID"]="{B0DBC591-0F52-4F7D-AD7B-51E67725FB81}",
					["num"]=1
				},
				[2]=
				{
					["CLSID"]="{7D7EC917-05F6-49D4-8045-61FC587DD019}",
					["num"]=2
				},
				[3]=
				{
					["CLSID"]="{0519A263-0AB6-11d6-9193-00A0249B6F00}",
					["num"]=5
				},
				[4]=
				{
					["CLSID"]="{7D7EC917-05F6-49D4-8045-61FC587DD019}",
					["num"]=7
				},
				[5]=
				{
					["CLSID"]="{0519A261-0AB6-11d6-9193-00A0249B6F00}",
					["num"]=8
				}
			},
			["tasks"]=
			{
				[1]=17
			}
		}
	},
	["unitType"]="Su-24MR"
}
return unitPayloads