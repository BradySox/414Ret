from dcs.unittype import VehicleType

from game.modsupport import vehiclemod


@vehiclemod
class Iron_Dome_David_Sling_CP(VehicleType):
    id = "Iron_Dome_David_Sling_CP"
    name = "SAM IDF Iron Dome/David's Sling C2"
    detection_range = 0
    threat_range = 0
    air_weapon_dist = 0
    eplrs = True


@vehiclemod
class IRON_DOME_LN(VehicleType):
    id = "IRON_DOME_LN"
    name = "SAM IDF Iron Dome LN"
    detection_range = 0
    threat_range = 70000
    air_weapon_dist = 70000


@vehiclemod
class DAVID_SLING_LN(VehicleType):
    id = "DAVID_SLING_LN"
    name = "SAM IDF David's Sling LN"
    detection_range = 0
    threat_range = 300000
    air_weapon_dist = 300000


@vehiclemod
class ELM2084_MMR_AD_RT(VehicleType):
    id = "ELM2084_MMR_AD_RT"
    name = "SAM IDF EL/M-2084 STR (Rotating Mode)"
    detection_range = 475000
    threat_range = 0
    air_weapon_dist = 0


@vehiclemod
class ELM2084_MMR_AD_SC(VehicleType):
    id = "ELM2084_MMR_AD_SC"
    name = "SAM IDF EL/M-2084 STR (Sector Mode)"
    detection_range = 650000
    threat_range = 0
    air_weapon_dist = 0


@vehiclemod
class ELM2084_MMR_WLR(VehicleType):
    id = "ELM2084_MMR_WLR"
    name = "SAM IDF EL/M-2084WLR STR"
    detection_range = 160000
    threat_range = 0
    air_weapon_dist = 0
