"""python tests/fixtures/make_spansh_fixture.py tests/fixtures  -  builds tests/fixtures/spansh.json: made-up Spansh system records (the shape of Spansh's /api/dump), drawn
from the made-up EDSM fixture so both describe the same systems. Orbital stations go at system level (Spansh
doesn't say which body they orbit), surface ones under their planet with a position; every station gets
landing pads; one surface site is left with no type (only approached), as Spansh has some."""
import json, sys
from pathlib import Path

FIX = Path(sys.argv[1])
edsm = json.loads((FIX / "edsm.json").read_text(encoding="utf-8"))
ADDR = {"hip 20277": 102, "carthage": 999}   # the made-up journals' SystemAddress for them
SURFACE = ("odyssey settlement", "planetary outpost", "planetary port", "settlement", "planetary construction depot")
PADS = {"odyssey settlement": (2, 0, 1), "outpost": (2, 1, 0), "planetary outpost": (4, 2, 2), "planetary port": (8, 8, 6),
        "fleet carrier": (4, 4, 8), "mega ship": (2, 2, 2)}
TYPES = {"odyssey settlement": "Settlement", "fleet carrier": "Drake-Class Carrier"}


def iso(t):
    return t.replace(" ", "T") + "Z" if t else None


def body(b):
    out = {k: v for k, v in b.items() if k not in ("id", "discovery", "isMainStar", "isScoopable", "updateTime", "rings", "belts")}
    out["mainStar"] = bool(b.get("isMainStar"))
    out["updateTime"] = iso(b.get("updateTime"))
    if out.get("atmosphereType") == "No atmosphere":
        out["atmosphereType"] = None
    for k in ("rings", "belts"):
        if b.get(k):
            out[k] = [dict(r, innerRadius=r["innerRadius"] * 1000.0, outerRadius=r["outerRadius"] * 1000.0) for r in b[k]]
    out["stations"] = []
    return out


def station(s, surface):
    t = str(s.get("type") or "")
    econ = {s["economy"]: 100.0} if s.get("economy") else {}
    if s.get("secondEconomy") and s["secondEconomy"] != s.get("economy"):
        econ[s["secondEconomy"]] = 50.0
    services = ["Dock", "Autodock"] + (["Market"] if s.get("haveMarket") else []) + (["Shipyard"] if s.get("haveShipyard") else []) + \
               (["Outfitting"] if s.get("haveOutfitting") else []) + list(s.get("otherServices") or []) + ["Flight Controller", "Station Operations"]
    pads = PADS.get(t.lower(), (8, 10, 6) if "starport" in t.lower() else (2, 1, 0))
    upd = s.get("updateTime") or {}
    out = {"id": s.get("marketId"), "name": s["name"], "type": TYPES.get(t.lower(), t), "distanceToArrival": s.get("distanceToArrival"),
           "allegiance": s.get("allegiance"), "government": s.get("government"), "primaryEconomy": s.get("economy"), "economies": econ,
           "controllingFaction": (s.get("controllingFaction") or {}).get("name"), "controllingFactionState": None,
           "landingPads": {"small": pads[0], "medium": pads[1], "large": pads[2]}, "services": services,
           "updateTime": iso(upd.get("information"))}
    for part, have in (("market", "haveMarket"), ("shipyard", "haveShipyard"), ("outfitting", "haveOutfitting")):
        if s.get(have):
            out[part] = {"updateTime": iso(upd.get(part))}
    if surface:
        out["latitude"], out["longitude"] = (s.get("body") or {}).get("latitude"), (s.get("body") or {}).get("longitude")
    if s["name"] == "Dhaenens's Lodgings":
        out["landingPads"] = {"small": 2, "medium": 0, "large": 2}
    return {k: v for k, v in out.items() if v is not None}


out = {}
for name, parts in edsm.items():
    bodies = [body(b) for b in parts["bodies"]["bodies"]]
    by_name = {b["name"]: b for b in bodies}
    top = []
    for s in parts["stations"]["stations"]:
        bname = (s.get("body") or {}).get("name")
        surface = any(w == str(s.get("type") or "").lower() for w in SURFACE) and bname in by_name
        if surface:
            by_name[bname]["stations"].append(station(s, True))
        else:
            top.append(station(s, False))
    if name == "hip 20277":   # signals on two moons (made up)
        by_name["HIP 20277 3 a"]["signals"] = {"genuses": [], "signals": {"$PlanetaryMiningLocation_Name;": 15, "$SAA_SignalType_Geological;": 3,
                                                                           "$SAA_SignalType_Human;": 3}, "updateTime": "2026-10-20T22:37:30Z"}
        by_name["HIP 20277 4 c"]["signals"] = {"genuses": ["$Codex_Ent_Conchas_Genus_Name;", "$Codex_Ent_Bacterial_Genus_Name;"],
                                               "signals": {"$SAA_SignalType_Biological;": 2, "$SAA_SignalType_Human;": 6}, "updateTime": "2026-09-22T02:53:51Z"}
    if name == "hip 20277":   # a surface site someone only flew past: no type, no services
        by_name["HIP 20277 7 a"]["stations"].append({"id": 3516368896, "name": "Fenwick Prospect", "latitude": -15.9, "longitude": -32.87,
                                                     "updateTime": "2023-02-19T13:44:36Z"})
    out[name] = {"id64": ADDR[name], "name": parts["bodies"]["name"], "bodyCount": len(bodies), "date": "2026-10-28T04:20:26Z",
                 "bodies": bodies, "stations": top}
(FIX / "spansh.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
print({k: (len(v["bodies"]), len(v["stations"]), sum(len(b["stations"]) for b in v["bodies"])) for k, v in out.items()})
