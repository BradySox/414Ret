# Requires UK Military Assets for DCS by Currenthill:
# https://www.currenthill.com/uk
#


from dcs import unittype

from game.modsupport import shipmod, vehiclemod


@vehiclemod
class CH_Ajax(unittype.VehicleType):
    id = "CH_Ajax"
    name = "[CH] Ajax CRV"
    detection_range = 0
    threat_range = 4000
    air_weapon_dist = 4000
    eplrs = True


@vehiclemod
class CH_AS90(unittype.VehicleType):
    id = "CH_AS90"
    name = "[CH] AS-90 SPG"
    detection_range = 0
    threat_range = 25000
    air_weapon_dist = 25000
    eplrs = True


@vehiclemod
class CH_Challenger2(unittype.VehicleType):
    id = "CH_Challenger2"
    name = "[CH] Challenger 2 MBT"
    detection_range = 0
    threat_range = 3500
    air_weapon_dist = 1200
    eplrs = True


@vehiclemod
class CH_Challenger3(unittype.VehicleType):
    id = "CH_Challenger3"
    name = "[CH] Challenger 3 MBT"
    detection_range = 0
    threat_range = 8000
    air_weapon_dist = 1200
    eplrs = True


@vehiclemod
class CH_LandRoverWolf(unittype.VehicleType):
    id = "CH_LandRoverWolf"
    name = "[CH] Land Rover Wolf LUV"
    detection_range = 0
    threat_range = 0
    air_weapon_dist = 0


@vehiclemod
class CH_LandRoverWMIK_M2(unittype.VehicleType):
    id = "CH_LandRoverWMIK_M2"
    name = "[CH] Land Rover WMIK (M2)"
    detection_range = 0
    threat_range = 1800
    air_weapon_dist = 1800
    eplrs = True


@vehiclemod
class CH_LandRoverWMIK_MK19(unittype.VehicleType):
    id = "CH_LandRoverWMIK_MK19"
    name = "[CH] Land Rover WMIK (MK19)"
    detection_range = 0
    threat_range = 2000
    air_weapon_dist = 2000
    eplrs = True


@vehiclemod
class CH_Scimitar(unittype.VehicleType):
    id = "CH_Scimitar"
    name = "[CH] FV107 Scimitar CRV"
    detection_range = 6000
    threat_range = 2500
    air_weapon_dist = 2500
    eplrs = True


@vehiclemod
class CH_Scorpion(unittype.VehicleType):
    id = "CH_Scorpion"
    name = "[CH] FV101 Scorpion LT"
    detection_range = 6000
    threat_range = 6000
    air_weapon_dist = 1200
    eplrs = True


@vehiclemod
class CH_SkySabreC2(unittype.VehicleType):
    id = "CH_SkySabreC2"
    name = "[CH] Sky Sabre C2 (HX)"
    detection_range = 0
    threat_range = 0
    air_weapon_dist = 0
    eplrs = True


@vehiclemod
class CH_SkySabreGiraffe(unittype.VehicleType):
    id = "CH_SkySabreGiraffe"
    name = "[CH] Sky Sabre Giraffe AMB STR (HX)"
    detection_range = 150000
    threat_range = 0
    air_weapon_dist = 0
    eplrs = True


@vehiclemod
class CH_SkySabreLN(unittype.VehicleType):
    id = "CH_SkySabreLN"
    name = "[CH] Sky Sabre iLauncher LN (HX)"
    detection_range = 0
    threat_range = 25000
    air_weapon_dist = 25000
    eplrs = True


@vehiclemod
class CH_StormerHVM(unittype.VehicleType):
    id = "CH_StormerHVM"
    name = "[CH] Stormer HVM VSHORAD"
    detection_range = 18000
    threat_range = 7500
    air_weapon_dist = 7500
    eplrs = True


@vehiclemod
class CH_Warrior(unittype.VehicleType):
    id = "CH_Warrior"
    name = "[CH] FV510 Warrior IFV"
    detection_range = 6000
    threat_range = 2500
    air_weapon_dist = 2500
    eplrs = True


@shipmod
class CH_Type26(unittype.ShipType):
    id = "CH_Type26"
    name = "[CH] Type 26 Frigate"
    helicopter_num = 1
    parking = 1
    detection_range = 200000
    threat_range = 30000
    air_weapon_dist = 30000


@shipmod
class Type45(unittype.ShipType):
    id = "Type45"
    name = "[CH] Type 45 Destroyer"
    helicopter_num = 1
    parking = 1
    detection_range = 400000
    threat_range = 120000
    air_weapon_dist = 120000
