"""Print all preset sentinel unit type IDs used by MizCampaignLoader."""

from dcs.vehicles import AirDefence, Armor
from dcs.statics import Fortification, Warehouse

print("LONG_RANGE_SAM:")
print(f"  S_300PS_5P85C_ln: '{AirDefence.S_300PS_5P85C_ln.id}'")
print(f"  S_300PS_5P85D_ln: '{AirDefence.S_300PS_5P85D_ln.id}'")

print("MEDIUM_RANGE_SAM:")
print(f"  Hawk_ln:          '{AirDefence.Hawk_ln.id}'")
print(f"  S_75M_Volhov:     '{AirDefence.S_75M_Volhov.id}'")
print(f"  x_5p73_s_125_ln:  '{AirDefence.x_5p73_s_125_ln.id}'")

print("SHORT_RANGE_SAM:")
print(f"  x_2S6_Tunguska:   '{AirDefence.x_2S6_Tunguska.id}'")

print("AAA:")
print(f"  ZSU_23_4_Shilka:  '{AirDefence.ZSU_23_4_Shilka.id}'")

print("FACTORY (static):")
print(f"  Workshop_A:       '{Fortification.Workshop_A.id}'")

print("AMMO DEPOT (static):")
print(f"  _Ammunition_depot: '{Warehouse._Ammunition_depot.id}'")
