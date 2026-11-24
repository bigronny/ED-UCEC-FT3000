"""Journals for the test scenarios, timestamped relative to now (so expiries, 'fresh' events
and the like behave as they would in a real session)."""
from harness import ago, ahead, DOCKED_FLAGS, SC_FLAGS

HIP = "HIP 20277"
HIP_POS = [106.4375, -95.6875, -0.1875]
CARTHAGE_POS = [100.34375, -102.125, 7.34375]


def _start(t, ship="Krait_MkII"):
    return [
        {"timestamp": ago(t), "event": "Fileheader", "part": 1},
        {"timestamp": ago(t), "event": "Commander", "Name": "Deckard"},
        {"timestamp": ago(t - 1), "event": "LoadGame", "Commander": "Deckard", "Ship": ship, "ShipName": "Night Owl",
         "ShipIdent": "BR-49K", "GameMode": "Solo", "Credits": 120000000},
    ]


def _location(t, docked=True):
    e = {"timestamp": ago(t), "event": "Location", "StarSystem": HIP, "SystemAddress": 102, "StarPos": HIP_POS,
         "Docked": docked, "Body": HIP, "BodyType": "Star",
         "SystemAllegiance": "Empire", "SystemGovernment_Localised": "Patronage", "SystemSecurity_Localised": "Medium Security",
         "SystemEconomy_Localised": "Industrial", "SystemSecondEconomy_Localised": "Refinery", "Population": 5400000,
         "ControllingPower": "Aisling Duval", "PowerplayState": "Exploited", "SystemFaction": {"Name": "HIP 20277 Party"},
         "Factions": [
             {"Name": "HIP 20277 Party", "Influence": 0.41, "FactionState": "Boom", "MyReputation": 55.0,
              "ActiveStates": [{"State": "Boom"}], "PendingStates": [{"State": "Expansion"}]},
             {"Name": "Ovid Vision & Co", "Influence": 0.33, "FactionState": "War", "MyReputation": 12.0,
              "ActiveStates": [{"State": "War"}]},
             {"Name": "Black Sun Crew", "Influence": 0.26, "FactionState": "War", "MyReputation": -40.0,
              "ActiveStates": [{"State": "War"}, {"State": "PirateAttack"}]},
         ],
         "Conflicts": [{"WarType": "war", "Status": "active", "Faction1": {"Name": "Ovid Vision & Co", "WonDays": 2},
                        "Faction2": {"Name": "Black Sun Crew", "WonDays": 1}}]}
    if docked:
        e.update(StationName="Fabian City", StationType="Coriolis")
    return e


def _accept(t, mid, name, loc, **kw):
    e = {"timestamp": ago(t), "event": "MissionAccepted", "Faction": kw.pop("Faction", "HIP 20277 Party"), "Name": name,
         "LocalisedName": loc, "MissionID": mid, "Influence": kw.pop("Influence", "++"), "Reputation": kw.pop("Reputation", "++"),
         "Reward": kw.pop("Reward", 0), "Wing": kw.pop("Wing", False)}
    e.update(kw)
    return e


def contracts():
    """Every kind of mission, over two sessions, with the login list tidying up."""
    old = _start(90000) + [
        _location(89990),
        _accept(89000, 1001, "Mission_Massacre", "Kill Black Sun Crew faction Pirates", Faction="Ovid Vision & Co", KillCount=24,
                TargetFaction="Black Sun Crew", TargetType="$MissionUtil_FactionTag_Pirate;", TargetType_Localised="Pirates",
                DestinationSystem="Carthage", Expiry=ahead(60), Reward=4200000),
        _accept(88900, 1002, "Mission_MassacreWing", "Kill Black Sun Crew faction Pirates", KillCount=30, TargetFaction="Black Sun Crew",
                TargetType_Localised="Pirates", DestinationSystem="Carthage", Expiry=ahead(70), Reward=6100000, Wing=True),
        _accept(88000, 1003, "Mission_Mining_name", "Mine 30 units of Bertrandite", Commodity="$Bertrandite_Name;",
                Commodity_Localised="Bertrandite", Count=30, DestinationSystem=HIP, DestinationStation="Fabian City",
                Expiry=ahead(20), Reward=1800000),
        _accept(87000, 1004, "Mission_Delivery_name", "Deliver 12 units of Gold", Commodity_Localised="Gold", Count=12,
                DestinationSystem="Maia", DestinationStation="Obsidian Orbital", Expiry=ahead(5), Reward=300000),
    ]
    new = _start(3000)[0:1] + _start(3000)[1:] + [
        {"timestamp": ago(2998), "event": "Missions",
         "Active": [{"MissionID": 1001, "Name": "Mission_Massacre", "PassengerMission": False, "Expires": 216000},
                    {"MissionID": 1002, "Name": "Mission_MassacreWing", "PassengerMission": False, "Expires": 250000},
                    {"MissionID": 999, "Name": "Mission_Salvage_Planet_name", "PassengerMission": False, "Expires": 40000}],
         "Failed": [], "Complete": [{"MissionID": 1003, "Name": "Mission_Mining_name", "PassengerMission": False, "Expires": 70000}]},
        _location(2990),
        {"timestamp": ago(2900), "event": "MissionRedirected", "MissionID": 1003, "Name": "Mission_Mining_name",
         "NewDestinationStation": "Fabian City", "OldDestinationStation": "Fabian City", "NewDestinationSystem": HIP, "OldDestinationSystem": HIP},
        _accept(2800, 2001, "Mission_Assassinate_Legal_Corporate", "Take out known pirate: Kirsten Vance", Faction="Carthage Defence Force",
                Target="Kirsten Vance", TargetType="$MissionUtil_FactionTag_PirateLord;", TargetType_Localised="Pirate lord",
                TargetFaction="Black Sun Crew", DestinationSystem="Carthage", Expiry=ahead(30), Reward=950000),
        _accept(2700, 2002, "Mission_Delivery_Agriculture", "Agricultural supply run: 240 units of Tea", Commodity="$Tea_Name;",
                Commodity_Localised="Tea", Count=240, TargetFaction="Ovid Vision & Co", DestinationSystem="Carthage",
                DestinationStation="New Carthage Hub", Expiry=ahead(44), Reward=2686155, Wing=True),
        {"timestamp": ago(2650), "event": "CargoDepot", "MissionID": 2002, "UpdateType": "Collect", "CargoType": "Tea", "Count": 96,
         "StartMarketID": 1, "EndMarketID": 2, "ItemsCollected": 96, "ItemsDelivered": 0, "TotalItemsToDeliver": 240, "Progress": 0.4},
        _accept(2600, 2003, "Mission_Collect_Industrial", "Source and return 6 units of Progenitor Cells", Commodity="$ProgenitorCells_Name;",
                Count=6, DestinationSystem=HIP, DestinationStation="Fabian City", Expiry=ahead(120), Reward=1450000),
        _accept(2500, 2004, "Mission_PassengerVIP_Tourist_BOOM_name", "Transport Ellie Watts and party to see Maia", PassengerCount=4,
                PassengerVIPs=True, PassengerWanted=False, PassengerType="Tourist", DestinationSystem="Maia",
                DestinationStation="Obsidian Orbital", Expiry=ahead(48), Reward=3200000),
        _accept(2400, 2005, "Mission_Courier_Elections_name", "Courier job: election data to Carthage", DestinationSystem="Carthage",
                DestinationStation="New Carthage Hub", Expiry=ahead(9), Reward=210000, Influence="+++"),
        _accept(2300, 2006, "Mission_OnFoot_Salvage_MB_name", "Recover the lost data chip from Bradley Agricultural Hub",
                DestinationSystem=HIP, DestinationSettlement="Bradley Agricultural Hub", Expiry=ahead(26), Reward=640000),
        _accept(2200, 2007, "Mission_AltruismCredits_name", "Donate 1,250,000 credits to the relief fund", Donation="1250000",
                Expiry=ahead(160), Reward=0, Influence="+++++"),
        _accept(2100, 2008, "Mission_Courier_name", "Data courier job to Fabian City", DestinationSystem=HIP,
                DestinationStation="Fabian City", Expiry=ahead(12), Reward=90000),
        {"timestamp": ago(2050), "event": "MissionCompleted", "MissionID": 2008, "Name": "Mission_Courier_name", "Faction": "HIP 20277 Party", "Reward": 90000},
        _accept(2000, 2009, "Mission_Delivery_name", "Deliver 8 units of Silver", Commodity_Localised="Silver", Count=8,
                DestinationSystem="Maia", Expiry=ahead(12), Reward=120000),
        {"timestamp": ago(1950), "event": "MissionAbandoned", "MissionID": 2009, "Name": "Mission_Delivery_name"},
        {"timestamp": ago(1900), "event": "ShipTargeted", "TargetLocked": True, "Ship": "python", "ScanStage": 3,
         "PilotName": "$npc_name_decorate:#name=Kirsten Vance;", "PilotName_Localised": "Kirsten Vance", "PilotRank": "Deadly",
         "ShieldHealth": 64.0, "HullHealth": 88.5, "LegalStatus": "Wanted", "Bounty": 950000},
    ]
    return {"journal": [("Journal.2026-10-27T010000.01.log", old), ("Journal.2026-10-28T000000.01.log", new)],
            "status": {"Flags": DOCKED_FLAGS, "Fuel": {"FuelMain": 30.0, "FuelReservoir": 0.5}, "Cargo": 96.0}}


def home():
    """A session's worth of events for the Home tab: case file, local situation and the log."""
    j = _start(4000) + [
        {"timestamp": ago(3990), "event": "Rank", "Combat": 6, "Trade": 5, "Explore": 4, "Federation": 3, "Empire": 9},
        {"timestamp": ago(3990), "event": "Progress", "Combat": 47, "Trade": 10},
        {"timestamp": ago(3990), "event": "Reputation", "Empire": 75.0, "Federation": 20.0, "Alliance": 0.0},
        {"timestamp": ago(3989), "event": "Statistics", "Combat": {"Bounties_Claimed": 1234, "Bounty_Hunting_Profit": 456789000,
                                                                   "Assassinations": 77, "Highest_Single_Reward": 12500000}},
        {"timestamp": ago(3989), "event": "Powerplay", "Power": "Aisling Duval", "Rank": 3},
        {"timestamp": ago(3988), "event": "Loadout", "Ship": "krait_mkii", "ShipName": "Night Owl", "ShipIdent": "BR-49K", "MaxJumpRange": 30.4,
         "UnladenMass": 457.2, "FuelCapacity": {"Main": 32.0, "Reserve": 0.63}, "CargoCapacity": 32,
         "Modules": [{"Slot": "FrameShiftDrive", "Item": "int_hyperdrive_size5_class5", "On": True, "Priority": 0, "Health": 1.0}]},
        _location(3985),
        {"timestamp": ago(3900), "event": "Undocked", "StationName": "Fabian City"},
        {"timestamp": ago(3500), "event": "Bounty", "Target": "python", "Target_Localised": "Python", "TotalReward": 350000,
         "VictimFaction": "Black Sun Crew", "PilotName_Localised": "Ana Diaz"},
        {"timestamp": ago(3400), "event": "FactionKillBond", "Reward": 80000, "VictimFaction": "Black Sun Crew"},
        {"timestamp": ago(3300), "event": "Interdicted", "Submitted": False, "Interdictor": "Bo Rix", "IsPlayer": False},
        {"timestamp": ago(3290), "event": "EscapeInterdiction", "Interdictor": "Bo Rix"},
        {"timestamp": ago(3200), "event": "CommitCrime", "CrimeType": "collidedAtSpeedInNoFireZone", "Fine": 400},
        {"timestamp": ago(3100), "event": "Promotion", "Combat": 7},
        {"timestamp": ago(3000), "event": "Docked", "StationName": "Fabian City", "StationType": "Coriolis"},
        {"timestamp": ago(2990), "event": "RedeemVoucher", "Type": "bounty", "Amount": 350000},
    ]
    return {"journal": j, "status": {"Flags": DOCKED_FLAGS, "Fuel": {"FuelMain": 32.0, "FuelReservoir": 0.6}}}


def syst():
    """Docked at Fabian City in HIP 20277 (the EDSM data comes from fixtures/edsm.json)."""
    return {"journal": _start(600) + [_location(590)], "status": {"Flags": DOCKED_FLAGS, "Fuel": {"FuelMain": 30.0, "FuelReservoir": 0.5}}}


NEAR_HAO = {"Flags": 16777216 | (1 << 21) | 8, "Flags2": 0, "BodyName": "HIP 20277 3 b",
            "Latitude": -13.1, "Longitude": 34.9, "Altitude": 4200, "Heading": 90, "PlanetRadius": 1500000.0}


def jump():
    """Ready to jump from HIP 20277 to Carthage: drive, fuel history, the arrival scan, a plotted route."""
    unladen, opt, lin, pw = 457.2, 1050, 12, 2.45
    j = _start(900) + [
        {"timestamp": ago(899), "event": "Loadout", "Ship": "krait_mkii", "MaxJumpRange": 30.4, "UnladenMass": unladen,
         "FuelCapacity": {"Main": 32.0, "Reserve": 0.63}, "CargoCapacity": 32,
         "Modules": [{"Slot": "FrameShiftDrive", "Item": "int_hyperdrive_size5_class5", "On": True, "Priority": 0, "Health": 1.0}]},
        {"timestamp": ago(898), "event": "Cargo", "Vessel": "Ship", "Count": 16, "Inventory": []},
    ]
    fuel = 32.0
    for i, (name, pos, d) in enumerate([("Calennero", [108.0, -97.0, -7.0], 9.4), ("ICZ CQ-Y d119", [104.0, -90.0, -4.0], 7.9), (HIP, HIP_POS, 6.8)]):
        used = round(0.82 * lin * 0.001 * (d * (unladen + fuel + 16) / opt) ** pw, 6)   # an engineered drive burns a bit less
        fuel = round(fuel - used, 6)
        j.append({"timestamp": ago(800 - i * 60), "event": "FSDJump", "StarSystem": name, "SystemAddress": 100 + i, "StarPos": pos,
                  "JumpDist": d, "FuelUsed": used, "FuelLevel": fuel, "Body": name, "BodyType": "Star"})
    j += [
        {"timestamp": ago(658), "event": "Scan", "ScanType": "AutoScan", "BodyName": HIP, "StarSystem": HIP, "DistanceFromArrivalLS": 0.0,
         "StarType": "K", "Subclass": 2, "StellarMass": 0.777344, "Radius": 0.876709 * 695700000, "SurfaceTemperature": 4864.0,
         "Luminosity": "V", "RotationPeriod": 3.630536 * 86400, "AxialTilt": 0.002821},
        {"timestamp": ago(300), "event": "FSDTarget", "Name": "Carthage", "SystemAddress": 999, "StarClass": "B", "RemainingJumpsInRoute": 1},
    ]
    route = {"timestamp": ago(300), "event": "NavRoute", "Route": [
        {"StarSystem": HIP, "SystemAddress": 102, "StarPos": HIP_POS, "StarClass": "K"},
        {"StarSystem": "Carthage", "SystemAddress": 999, "StarPos": CARTHAGE_POS, "StarClass": "B"}]}
    return {"journal": j, "navroute": route, "edsm": ("hip 20277", "carthage"),
            "status": {"Flags": SC_FLAGS, "Fuel": {"FuelMain": fuel, "FuelReservoir": 0.5}, "Cargo": 16.0}, "fuel": fuel}


def ocor():
    """In HIP 20277 with the test briefing loaded and coordinates for its systems cached."""
    return {"journal": _start(600) + [
                {"timestamp": ago(599), "event": "Loadout", "Ship": "krait_mkii", "MaxJumpRange": 30.4, "Modules": []},
                _location(590)],
            "status": {"Flags": DOCKED_FLAGS}, "ocor": True,
            "coords": {"Carthage": CARTHAGE_POS, "Maia": [-81.78125, -149.4375, -343.375], "Test Sector AB-C d1-2": [120.0, -80.0, 15.0],
                       "Nowhere Known AA-A h0": None}}


def history():
    """Two months of travel and missions for Nav › Hist and Contracts › History: an old journal (older than the
    days the board reads at start-up, so only the history's own reading of every journal finds it) and today's."""
    d60 = 60 * 86400
    old = _start(d60 + 600) + [
        {"timestamp": ago(d60 + 590), "event": "Location", "StarSystem": "Sol", "SystemAddress": 10477373803, "Docked": True,
         "StationName": "Abraham Lincoln", "StationType": "Orbis", "MarketID": 128016640},
        _accept(d60 + 500, 3001, "Mission_Delivery_name", "Deliver 12 units of Gold", Commodity_Localised="Gold", Count=12,
                DestinationSystem="Maia", DestinationStation="Obsidian Orbital", Expiry=ahead(-1000), Reward=300000),
        {"timestamp": ago(d60 + 400), "event": "FSDJump", "StarSystem": "Pleione", "SystemAddress": 7, "JumpDist": 18.4,
         "SystemAllegiance": "Independent", "SystemGovernment_Localised": "Democracy", "SystemSecurity_Localised": "Low Security",
         "SystemEconomy_Localised": "Tourism", "Population": 120000, "SystemFaction": {"Name": "Pleione Union"}},
        {"timestamp": ago(d60 + 300), "event": "FSDJump", "StarSystem": "Maia", "SystemAddress": 8, "JumpDist": 3.2,
         "SystemAllegiance": "Federation", "SystemGovernment_Localised": "Corporate", "SystemSecurity_Localised": "High Security",
         "SystemEconomy_Localised": "High Tech", "Population": 4000000, "SystemFaction": {"Name": "Maia Corp"}},
        {"timestamp": ago(d60 + 200), "event": "Docked", "StarSystem": "Maia", "SystemAddress": 8, "StationName": "Obsidian Orbital",
         "StationType": "Coriolis", "MarketID": 3229009152, "StationFaction": {"Name": "Maia Corp"}, "StationGovernment_Localised": "Corporate",
         "StationAllegiance": "Federation", "StationEconomies": [{"Name": "$economy_HighTech;", "Name_Localised": "High Tech", "Proportion": 1.0}],
         "StationServices": ["dock", "commodities", "refuel", "repair", "shipyard", "outfitting"], "DistFromStarLS": 1210.5},
        {"timestamp": ago(d60 + 190), "event": "MissionCompleted", "MissionID": 3001, "Name": "Mission_Delivery_name", "Faction": "Sol Workers",
         "Commodity_Localised": "Gold", "Count": 12, "DestinationSystem": "Maia", "DestinationStation": "Obsidian Orbital", "Reward": 310000,
         "MaterialsReward": [{"Name": "gridresistors", "Name_Localised": "Grid Resistors", "Category": "$MICRORESOURCE_CATEGORY_Manufactured;", "Count": 2}]},
        {"timestamp": ago(d60 + 100), "event": "MissionFailed", "MissionID": 2900, "Name": "Mission_Courier_name", "LocalisedName": "Courier job: data to Maia"},
    ]
    today = _start(3000) + [
        _location(2990),   # docked at Fabian City, HIP 20277
        {"timestamp": ago(2900), "event": "Undocked", "StationName": "Fabian City"},
        {"timestamp": ago(2800), "event": "ApproachBody", "StarSystem": HIP, "SystemAddress": 102, "Body": "HIP 20277 3 b", "BodyID": 12},
        {"timestamp": ago(2700), "event": "ApproachSettlement", "SystemAddress": 102, "Name": "Hao Extraction Prospect", "MarketID": 3950102530,
         "BodyName": "HIP 20277 3 b", "BodyID": 12, "Latitude": -13.04, "Longitude": 34.92, "StationFaction": {"Name": "Lavigny's Legion"},
         "StationGovernment_Localised": "Patronage", "StationAllegiance": "Empire",
         "StationEconomies": [{"Name": "$economy_Extraction;", "Name_Localised": "Extraction", "Proportion": 1.0}]},
        {"timestamp": ago(2600), "event": "Touchdown", "StarSystem": HIP, "SystemAddress": 102, "Body": "HIP 20277 3 b", "BodyID": 12,
         "Latitude": -13.05, "Longitude": 34.95, "NearestDestination": "$SETTLEMENT_x;", "NearestDestination_Localised": "Hao Extraction Prospect",
         "PlayerControlled": True, "OnStation": False, "OnPlanet": True},
        _accept(2500, 3101, "Mission_Collect_Industrial", "Source and return 6 units of Progenitor Cells", Commodity="$ProgenitorCells_Name;",
                Count=6, DestinationSystem=HIP, DestinationStation="Fabian City", Expiry=ahead(120), Reward=1450000),
        {"timestamp": ago(2400), "event": "MissionAbandoned", "MissionID": 3101, "Name": "Mission_Collect_Industrial"},
        {"timestamp": ago(2300), "event": "FSDJump", "StarSystem": "Carthage", "SystemAddress": 999, "JumpDist": 11.2, "StarPos": CARTHAGE_POS,
         "SystemAllegiance": "Empire", "SystemGovernment_Localised": "Feudal", "SystemSecurity_Localised": "Medium Security",
         "SystemEconomy_Localised": "Military", "Population": 2500000, "SystemFaction": {"Name": "Carthage Defence Force"}},
        {"timestamp": ago(2200), "event": "Docked", "StarSystem": "Carthage", "SystemAddress": 999, "StationName": "New Carthage Hub",
         "StationType": "Ocellus", "MarketID": 3221234176, "StationFaction": {"Name": "Carthage Defence Force"},
         "StationServices": ["dock", "commodities", "refuel"], "DistFromStarLS": 512.0},
        {"timestamp": ago(2100), "event": "FSDJump", "StarSystem": HIP, "SystemAddress": 102, "JumpDist": 11.2, "StarPos": HIP_POS,
         "SystemAllegiance": "Empire", "SystemGovernment_Localised": "Patronage", "SystemSecurity_Localised": "Medium Security",
         "SystemEconomy_Localised": "Industrial", "Population": 5400000, "SystemFaction": {"Name": "HIP 20277 Party"}},
        {"timestamp": ago(2000), "event": "Docked", "StarSystem": HIP, "SystemAddress": 102, "StationName": "Fabian City", "StationType": "Coriolis",
         "MarketID": 3700012345},
    ]
    return {"journal": [("Journal.2026-08-29T100000.01.log", old, d60), ("Journal.2026-10-28T000000.01.log", today, 60)],
            "status": {"Flags": DOCKED_FLAGS, "Fuel": {"FuelMain": 30.0, "FuelReservoir": 0.5}}}
