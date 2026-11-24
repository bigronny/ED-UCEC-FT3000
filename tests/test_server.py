"""The board seen from outside: the web API, the UFC event stream and the UFC display."""
import json
import socket
import math
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
import unittest

import journals
from harness import Board, check_golden, normalise, ago, ahead, SC_FLAGS, DOCKED_FLAGS

PAGE_LABELS = ["HOME", "NAV", "CTRS", "DSG", "MK"]


def ufc_num(n):
    """How the UFC's COMM windows show a number (SimApp shows 10-19 as `0-`9)."""
    return "`" + str(n % 10) if 10 <= n < 20 else str(n)


def part(state, *keys):
    return {k: state.get(k) for k in keys}


class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Board("contracts", **journals.contracts()).start()

    @classmethod
    def tearDownClass(cls):
        cls.b.stop()

    def test_1_state(self):
        s = self.b.state()
        keys = [c["key"] for c in s["contracts"]]
        self.assertEqual(len(keys), 10)
        self.assertIn("kirsten vance", keys)
        self.assertIn("black sun crew", keys)
        self.assertNotIn("m:1004", keys)   # dropped by the login list
        self.assertNotIn("m:2008", keys)   # completed
        check_golden(self, "contracts_state", normalise(part(s, "contracts", "log", "commander", "system", "note", "engine", "cmdr")))

    def test_2_backstories_only_for_targets(self):
        self.assertEqual(self.b.post("/api/regenerate", {"key": "m:2002"})[0], 409)

    def test_3_live_changes(self):
        b = self.b
        b.add({"event": "MissionAccepted", "Faction": "F", "Name": "Mission_Salvage_name", "LocalisedName": "Recover 3 black boxes",
               "Commodity_Localised": "Black Box", "Count": 3, "MissionID": 3001, "Influence": "+", "Reputation": "+", "Reward": 500000,
               "Wing": False, "Expiry": ahead(6), "DestinationSystem": "HIP 20277", "DestinationStation": "Fabian City"},
              {"event": "CargoDepot", "MissionID": 2002, "UpdateType": "Deliver", "CargoType": "Tea", "Count": 96,
               "ItemsCollected": 96, "ItemsDelivered": 96, "TotalItemsToDeliver": 240, "Progress": 0},
              {"event": "MissionCompleted", "MissionID": 2007, "Name": "Mission_AltruismCredits_name", "Faction": "F", "Reward": 0})
        s = b.wait(lambda: (lambda s: s if any(c["key"] == "m:3001" for c in s["contracts"]) else None)(b.state()), what="the new mission")
        names = {c["key"]: c["name"] for c in s["contracts"]}
        self.assertEqual(names["m:3001"], "3 × Black Box")
        self.assertNotIn("m:2007", names)
        tea = next(c for c in s["contracts"] if c["key"] == "m:2002")["missions"][0]
        self.assertEqual(tea["depot"], {"collected": 96, "delivered": 96, "total": 240})
        self.assertEqual([e["tag"] for e in s["log"]][-2:], ["ACCEPT", "DONE"])

    def test_4_ufc_contract_cursor(self):
        b = self.b
        b.post("/api/select", {"tab": "contracts", "sub": 1})
        b.ufc_cmd("press ILS")
        d = b.wait(lambda: b.display() if b.display()["options"] == PAGE_LABELS else None, what="the page menu on the UFC")
        self.assertEqual(d["cue"], 3)                 # ':' beside CTRS
        keys = [c["key"] for c in b.state()["contracts"]]
        bus = b.bus()
        self.assertEqual(bus["menu"], "PAGE")
        start = keys.index(bus["cursors"]["targets"])
        want = keys[min(len(keys) - 1, start + 2)]
        b.ufc_cmd("pulse COMM1_CW", "pulse COMM1_CW")
        b.wait(lambda: b.bus()["cursors"]["targets"] == want or None, what="the cursor to move")
        b.wait(lambda: b.display()["com1"] == ufc_num(keys.index(want) + 1) or None, what="COM1 to show the position")
        self.assertEqual(b.display()["com2"], ufc_num(len(keys)))
        b.ufc_cmd("press COMM1_PULL")
        bus = b.wait(lambda: (lambda u: u if u["pick_n"] >= 1 else None)(b.bus()), what="the pull")
        self.assertEqual(bus["pick"], {"list": "targets", "key": want})
        b.ufc_cmd("pulse COMM2_CW", "pulse COMM2_CW", "pulse COMM2_CCW")
        self.assertEqual(b.wait(lambda: b.bus()["scroll_pos"] == 1 or None, what="COMM2 scroll"), True)
        # the function buttons: navigation on D/L, the wing menu on BCN, the page menu (above) on ILS
        b.ufc_cmd("press DL")
        b.wait(lambda: b.display()["options"] == ["GXY", "SYS", "NEXT", "CRUI", "JUMP"] or None, what="navigation on D/L")
        self.assertEqual(b.bus()["menu"], "NAV")
        b.ufc_cmd("press BCN")
        b.wait(lambda: b.display()["options"] == ["WG-1", "WG-2", "WG-3", "WGNV", "WG-T"] or None, what="the wing menu on BCN")
        b.ufc_cmd("press ILS")
        b.wait(lambda: b.display()["options"] == PAGE_LABELS or None, what="the page menu back on ILS")


class Controls(unittest.TestCase):
    """4 Setup > Controls: each of the UFC's jobs on a button or dial of any game controller - the UFC's own layout by
    default; ASSIGN learns the next button pressed (or dial turned end to end) on any of them, from what the controller
    says its parts are (a button, a hat's direction, an axis) or, if it won't, from what changed; one button, one job;
    CLEAR, RESTORE DEFAULTS; what Elite also does with that button. The simulated UFC, and a button box beside it."""

    def view(self, b):
        return json.loads(b.get("/api/controls")[1])

    def job(self, v, job):
        return next(j for j in v["jobs"] if j["job"] == job)

    def assign(self, b, job, *cmds, pause=0.6):
        n = ((self.view(b).get("result") or {}).get("n") or 0)
        self.assertEqual(b.post("/api/controls", {"op": "learn", "job": job})[0], 200)
        time.sleep(0.8)   # (past its settling moment)
        b.ufc_cmd(*cmds, pause=pause)
        v = b.wait(lambda: (lambda v: v if (v.get("result") or {}).get("n", 0) > n else None)(self.view(b)), timeout=15, what=f"{job} learned")
        return v["result"]

    def test_defaults_assign_move_restore(self):
        j = journals.syst()
        with Board("controls", journal=j["journal"], status=j["status"]) as b:
            v = self.view(b)
            self.assertTrue(v["on"])
            self.assertFalse(v["custom"])
            self.assertEqual(len(v["jobs"]), 34)   # (the UFC's buttons with jobs, and its three dials)
            self.assertTrue(all(x["default"] and x["bind"]["name"] == "WINWING UFC1" for x in v["jobs"]))
            self.assertEqual(self.job(v, "ILS")["bind"]["label"], "UFC I/L/S")
            self.assertEqual([g["id"] for g in v["groups"]], ["comm", "opt", "menu", "keypad", "dial"])
            devs = b.wait(lambda: (lambda d: d if len(d) == 2 and all(x["open"] for x in d) else None)(self.view(b)["devices"]),
                          what="both controllers open while the page asks")
            self.assertEqual({d["name"]: (d["bound"], d["described"]) for d in devs},
                             {"WINWING UFC1": (True, False), "SIM BUTTON BOX": (False, True)})   # (not the keyboard)
            # the box's button 3 for COMM1 pull (Elite has it too: Cycle Next Target)
            r = self.assign(b, "COMM1_PULL", "box press 3")
            self.assertEqual((r["ok"], r["label"], r["name"], r["moved"]), (True, "Button 3", "SIM BUTTON BOX", []))
            v = self.view(b)
            x = self.job(v, "COMM1_PULL")
            self.assertEqual((x["default"], x["bind"]["label"], x["elite"]), (False, "Button 3", ["Cycle Next Target"]))
            saved = json.loads((b.dir / "controls.json").read_text(encoding="utf-8"))["jobs"]
            self.assertEqual(saved["COMM1_PULL"], {"byte": 0, "mask": 4, "value": 4, "label": "Button 3", "joy": "Joy_3",
                                                   "dev": "1234:ABCD", "name": "SIM BUTTON BOX", "rid": None})
            # the box's button 5 for the NAV menu: pressing it picks the menu
            self.assertTrue(self.assign(b, "DL", "box press 5")["ok"])
            b.ufc_cmd("box press 5")
            b.wait(lambda: b.display()["options"] == ["GXY", "SYS", "NEXT", "CRUI", "JUMP"] or None, what="the NAV menu, from the box")
            b.ufc_cmd("press ILS")   # (the UFC's own buttons still work)
            b.wait(lambda: b.display()["options"] == ["HOME", "NAV", "CTRS", "DSG", "MK"] or None, what="the PAGE menu, from the UFC")
            # a hat's direction for COMM2 right
            r = self.assign(b, "COMM2_CW", "box hat 2", "box hat 15")
            self.assertEqual((r["ok"], r["label"]), (True, "Hat 1 right"))
            # one button, one job: the UFC's I/L/S for option 5 - the PAGE menu loses it
            r = self.assign(b, "Opt5", "press ILS")
            self.assertEqual((r["ok"], r["label"], r["moved"]), (True, "UFC I/L/S", ["ILS"]))
            v = self.view(b)
            self.assertIsNone(self.job(v, "ILS")["bind"])
            self.assertFalse(self.job(v, "ILS")["default"])
            # a dial: the box's axis for COMM1 volume - turned end to end, and back
            n = self.view(b)["result"]["n"]
            self.assertEqual(b.post("/api/controls", {"op": "learn", "job": "comm1_volume"})[0], 200)
            time.sleep(0.8)
            b.ufc_cmd(*[f"box axis {a}" for a in (2048, 3000, 4095, 3000, 2048, 1000, 0, 1000, 2048)], pause=0.4)
            v = b.wait(lambda: (lambda v: v if v["result"]["n"] > n else None)(self.view(b)), timeout=15, what="the dial learned")
            self.assertEqual((v["result"]["ok"], v["result"]["label"]), (True, "X axis"))
            b.ufc_cmd("box axis 4095")
            b.wait(lambda: b.bus()["dials"].get("comm1_volume") == 1.0 or None, what="the box's axis as COMM1 volume")
            b.ufc_cmd("box axis 0")
            b.wait(lambda: b.bus()["dials"].get("comm1_volume") == 0.0 or None, what="... the other end")
            # lit while held: a setup tried out on the page
            b.ufc_cmd("box hold 3 1.5", pause=0.3)
            self.assertIn("COMM1_PULL", self.view(b)["lit"])
            # CLEAR, then RESTORE DEFAULTS
            self.assertEqual(b.post("/api/controls", {"op": "clear", "job": "DL"})[0], 200)
            self.assertIsNone(self.job(self.view(b), "DL")["bind"])
            self.assertEqual(b.post("/api/controls", {"op": "clear", "job": "Nope"})[0], 400)
            self.assertEqual(b.post("/api/controls", {"op": "restore"})[0], 200)
            v = self.view(b)
            self.assertTrue(all(x["default"] for x in v["jobs"]) and not v["custom"])
            self.assertFalse((b.dir / "controls.json").exists())
            b.ufc_cmd("press DL")
            b.wait(lambda: b.display()["options"] == ["GXY", "SYS", "NEXT", "CRUI", "JUMP"] or None, what="the UFC's D/L again")
            # ASSIGN cancelled: nothing changes
            self.assertEqual(b.post("/api/controls", {"op": "learn", "job": "Ent"})[0], 200)
            self.assertEqual(self.view(b)["learning"]["job"], "Ent")
            b.post("/api/controls", {"op": "cancel"})
            v = self.view(b)
            self.assertEqual((v["learning"], v["result"]["ok"], v["result"]["why"]), (None, False, "Cancelled"))
            self.assertEqual(b.post("/api/controls", {"op": "learn", "job": "Nope"})[0], 400)

    def test_kept_and_learned_without_a_descriptor(self):
        """A controller that won't say what its parts are: learned from what changed (a bit, the hat's byte, a dial's
        bytes). Assignments are kept for the next start."""
        j = journals.syst()
        with Board("controls_raw", journal=j["journal"], status=j["status"], env={"FAKEHID_NODESC": "1"}) as b:
            b.wait(lambda: any(d["open"] and d["name"] == "SIM BUTTON BOX" for d in self.view(b)["devices"]) or None, what="the box")
            r = self.assign(b, "ON_OFF", "box press 10")
            self.assertEqual((r["ok"], r["label"]), (True, "Byte 1 bit 1"))
            r = self.assign(b, "COMM1_CCW", "box hat 6", "box hat 15")
            self.assertEqual((r["ok"], r["label"]), (True, "Byte 2 = 0x06"))
            n = self.view(b)["result"]["n"]
            b.post("/api/controls", {"op": "learn", "job": "brightness"})
            time.sleep(0.8)
            b.ufc_cmd(*[f"box axis {a}" for a in (2048, 3000, 4095, 3000, 2048, 1000, 0, 1000, 2048)], pause=0.4)
            v = b.wait(lambda: (lambda v: v if v["result"]["n"] > n else None)(self.view(b)), timeout=15, what="the dial learned")
            self.assertEqual((v["result"]["ok"], v["result"]["label"]), (True, "Byte 3 (16-bit)"))
            b.start_again()
            v = self.view(b)
            self.assertEqual({x["job"]: x["bind"]["label"] for x in v["jobs"] if not x["default"]},
                             {"ON_OFF": "Byte 1 bit 1", "COMM1_CCW": "Byte 2 = 0x06", "brightness": "Byte 3 (16-bit)"})
            b.wait(lambda: any(d["open"] and d["bound"] and d["name"] == "SIM BUTTON BOX" for d in self.view(b)["devices"]) or None,
                   what="the box open again: it has jobs")
            b.ufc_cmd("box press 10")
            b.wait(lambda: b.display()["options"] == ["CARG", "NVG", "LAND", "HUD", "MODE"] or None, what="the toggles menu, from the box")

    def test_off(self):
        """Without the UFC (--no-ufc) the page still shows the jobs, but can't assign."""
        j = journals.syst()
        with Board("controls_off", journal=j["journal"], status=j["status"], ufc=False) as b:
            v = self.view(b)
            self.assertEqual((v["on"], v["why"], len(v["jobs"])), (False, "Off: started with --no-ufc", 34))
            code, a = b.post("/api/controls", {"op": "learn", "job": "Ent"})
            self.assertEqual((code, a["ok"]), (409, False))


class DataFolder(unittest.TestCase):
    """Your data lives apart from the program (Saved Games\\UCEC FT3000; here FT3000_DATA): the first start copies what
    an earlier version kept in the program's folder across, once, leaving the old copies; everything's saved there."""

    def test_first_start_copies_it_across(self):
        import tempfile, shutil
        data = Path(tempfile.mkdtemp(prefix="edtb_data_")) / "UCEC FT3000"
        try:
            j = journals.syst()
            with Board("data_folder", journal=j["journal"], status=j["status"], env={"FT3000_DATA": str(data)}) as b:
                self.assertIn(f"Your data now lives in {data}: copied 2 files there", b.log())   # (the system cache and the UFC's dials)
                self.assertIn(f"Your data: {data}", b.log())
                self.assertEqual(sorted(p.name for p in data.iterdir() if p.suffix == ".json"), ["edsm_cache.json", "ufc_axes.json"])
                self.assertTrue((b.dir / "edsm_cache.json").exists(), "the old copy left where it was")
                self.assertEqual(b.state()["syst"]["status"], "ok", "the system from the copied cache")
                code, a = b.post("/api/tgt", {"op": "add", "body": "HIP 20277 3 b", "lat": -13.1, "lon": 34.9, "method": "manual"})
                self.assertEqual(code, 200)
                b.wait(lambda: (data / "ft3000.pid").exists() or None, what="the PID file in the data folder")
                self.assertTrue((data / "star_coords.sqlite").exists() and not (b.dir / "star_coords.sqlite").exists(),
                                "the waypoint saved in the data folder")
                b.start_again()
                self.assertNotIn("Your data now lives in", b.log().split("UCEC FT3000 3.")[-1], "copied once")
                self.assertEqual(len(json.loads(b.get("/api/state")[1])["syst"]["tgts"]), 1, "the waypoint, kept")
        finally:
            shutil.rmtree(data.parent, ignore_errors=True)


class SettingsBoard(Board):
    """A board whose data folder already holds settings.json (as kept from 4 Setup > Settings) when it starts."""

    def __init__(self, *a, settings=None, **kw):
        super().__init__(*a, **kw)
        self.settings = settings or {}

    def _write_files(self):
        super()._write_files()
        (self.dir / "settings.json").write_text(json.dumps(self.settings), encoding="utf-8")


class Settings(unittest.TestCase):
    """4 Setup > Settings: what the FT3000 starts with, kept in settings.json in the data folder as it's changed; each
    takes effect at the next start - RESTART closes it and starts it again - and an option on the command line wins."""

    def view(self, b):
        return json.loads(b.get("/api/settings")[1])

    def test_kept_checked_and_overridden(self):
        j = journals.syst()
        with Board("settings", journal=j["journal"], status=j["status"]) as b:
            v = self.view(b)
            S = v["settings"]
            self.assertEqual({k: r["value"] for k, r in S.items()},
                             {"journal_dir": "", "engine": "auto", "model": "", "lan": False, "controllers": True, "open_page": True})
            # the harness starts it with --engine none, --journal-dir and --no-browser: those win, and say so
            self.assertEqual({k: r["flag"] for k, r in S.items() if r["flag"]},
                             {"journal_dir": "--journal-dir", "engine": "--engine", "open_page": "--no-browser"})
            self.assertEqual((S["engine"]["running"], S["journal_dir"]["running"], S["lan"]["running"], S["controllers"]["running"]),
                             ("none", str(b.jdir), False, True))
            self.assertFalse(v["pending"])
            self.assertEqual((v["about"]["version"], v["about"]["bindings"]), (script_version(), ["TestBinds.4.0.binds"]))
            self.assertEqual(Path(v["about"]["data"]), b.dir)
            # changed: kept at once, and waiting for a restart
            code, a = b.post("/api/settings", {"key": "lan", "value": True})
            self.assertEqual((code, a["ok"]), (200, True))
            self.assertTrue(a["view"]["settings"]["lan"]["pending"] and a["view"]["pending"])
            code, a = b.post("/api/settings", {"key": "journal_dir", "value": f'  "{b.jdir}"  '})   # (pasted with its quotes)
            self.assertEqual((code, a["view"]["settings"]["journal_dir"]["value"], a["view"]["settings"]["journal_dir"]["found"]), (200, str(b.jdir), 1))
            self.assertFalse(a["view"]["settings"]["journal_dir"]["pending"], "--journal-dir wins: no restart would change it")
            b.post("/api/settings", {"key": "model", "value": "haiku"})
            self.assertEqual(json.loads((b.dir / "settings.json").read_text(encoding="utf-8")),
                             {"journal_dir": str(b.jdir), "engine": "auto", "model": "haiku", "lan": True, "controllers": True, "open_page": True})
            self.assertIn("Setting changed on the web page: lan = True (from the next start).", b.log())
            # refused: kept as it was
            for body, why in (({"key": "journal_dir", "value": str(b.dir / "nowhere")}, "There's no such folder"),
                              ({"key": "engine", "value": "gemini"}, "Auto, Claude, ChatGPT or none"),
                              ({"key": "lan", "value": "yes"}, "On or off"),
                              ({"key": "model", "value": "haiku; rm -rf"}, "A model's name: letters, digits and . - _ : only"),
                              ({"key": "port", "value": 80}, "No such setting")):
                code, a = b.post("/api/settings", body)
                self.assertEqual((code, a["ok"], a["why"]), (400, False, why), body)
            self.assertEqual(self.view(b)["settings"]["journal_dir"]["value"], str(b.jdir))
            # back to the default folder
            self.assertEqual(b.post("/api/settings", {"key": "journal_dir", "value": ""})[1]["view"]["settings"]["journal_dir"]["value"], "")

    def test_started_with_them(self):
        """Started without the options a setting covers: the settings decide (here: other devices may open the page)."""
        j = journals.syst()
        with SettingsBoard("settings_start", journal=j["journal"], status=j["status"], ufc=False,
                           settings={"lan": True, "model": "haiku", "engine": "claude", "bogus": 1, "controllers": "maybe"}) as b:
            v = self.view(b)
            S = v["settings"]
            self.assertTrue(S["lan"]["running"], "listening for other devices too")
            self.assertIn("Other devices on your network can open the page too: http://", b.log())
            self.assertEqual((S["lan"]["flag"], S["lan"]["pending"], S["model"]["value"], S["controllers"]["value"]), ("", False, "haiku", True),
                             "a setting that can't be (controllers: \"maybe\") is the default")
            self.assertEqual(S["engine"]["flag"], "--engine", "the harness's --engine none still wins")

    def test_restart(self):
        """RESTART: closes as Exit does, then starts again with the same options - a new run, on the same port, with the
        settings as they are now."""
        import signal
        j = journals.syst()
        with Board("settings_restart", journal=j["journal"], status=j["status"]) as b:
            first, run = b.proc, self.view(b)["run"]
            b.post("/api/settings", {"key": "lan", "value": True})
            self.assertEqual(b.post("/api/restart", {}), (200, {"ok": True}))
            first.wait(10)
            child = None
            try:
                end = time.time() + 20   # (not b.wait: that stops when the first copy has)
                while time.time() < end and not child:
                    try:
                        pid = json.loads((b.dir / "ft3000.pid").read_text())["pid"]
                        child = pid if pid != first.pid else None
                    except (OSError, ValueError):
                        pass
                    time.sleep(0.2)
                self.assertTrue(child, f"the new start's PID file\n{b.log()[-2000:]}")
                end = time.time() + 20
                v = None
                while time.time() < end:
                    try:
                        v = self.view(b)
                        break
                    except Exception:
                        time.sleep(0.2)
                self.assertIsNotNone(v, "the new start answers on the same port")
                self.assertNotEqual(v["run"], run)
                self.assertTrue(v["settings"]["lan"]["running"] and not v["pending"], "started with the new settings")
                log = b.log()
                self.assertIn("Restart pressed on the web page - closing, to start again.", log)
                self.assertIn("Starting again...", log)
                self.assertNotIn("is still running on port", log, "the first had closed before the second started")
                end = time.time() + 10
                while time.time() < end and b.log().count("UFC connected") < 2:
                    time.sleep(0.2)
                self.assertEqual(b.log().count("UFC connected"), 2, "the UFC again")
            finally:
                if child:
                    os.kill(child, signal.SIGTERM)
                    end = time.time() + 5
                    while time.time() < end and Path(f"/proc/{child}").exists():
                        time.sleep(0.1)


class OwnPage(unittest.TestCase):
    """The board answers its own page (however it's opened) and programs that aren't browsers - not another website
    open in the same browser (its Origin or Sec-Fetch-Site), nor a name pointed at this PC (its Host: DNS rebinding)."""

    def ask(self, b, method, path, headers=None, body=None):
        import http.client
        port = int(b.url.rsplit(":", 1)[1])
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        h = dict(headers or {})
        conn.putrequest(method, path, skip_host="Host" in h, skip_accept_encoding=True)
        for k, v in h.items():
            conn.putheader(k, v)
        data = json.dumps(body).encode("utf-8") if body is not None else b""
        if method == "POST":
            conn.putheader("Content-Type", "text/plain")   # (a "simple" request: a browser sends it cross-site without asking first)
            conn.putheader("Content-Length", str(len(data)))
        conn.endheaders(data if method == "POST" else None)
        r = conn.getresponse()
        out = r.status, r.read()
        conn.close()
        return out

    def test_only_its_own_page(self):
        j = journals.syst()
        with Board("own_page", journal=j["journal"], status=j["status"], ufc=False) as b:
            port = int(b.url.rsplit(":", 1)[1])
            me = f"127.0.0.1:{port}"
            start = {"op": "ctl"}   # (the HSI timer: started, if it's acted on)
            # its own page, however it's opened; programs (no Origin)
            for host in (me, f"localhost:{port}", f"[::1]:{port}", f"192.168.1.20:{port}", f"{socket.gethostname()}:{port}"):
                self.assertEqual(self.ask(b, "GET", "/api/state", {"Host": host})[0], 200, host)
            self.assertEqual(self.ask(b, "GET", "/", {"Host": me, "Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate"})[0], 200,
                             "a link to the page from elsewhere")
            self.assertEqual(self.ask(b, "POST", "/api/timer", {"Host": me, "Origin": f"http://{me}", "Sec-Fetch-Site": "same-origin"},
                                      {"op": "sel"})[0], 200)
            b.wait(lambda: b.bus()["timer"]["mode"] == "cd" or None, what="its own page's request acted on (SEL: the countdown)")
            self.assertEqual(self.ask(b, "POST", "/api/timer", {"Host": me}, {"op": "sel"})[0], 200, "a program")
            b.wait(lambda: b.bus()["timer"]["mode"] == "et" or None, what="a program's acted on (SEL again: the stopwatch)")
            # another website: refused, and nothing done
            for h in ({"Host": me, "Origin": "http://evil.example"}, {"Host": me, "Origin": "null"},
                      {"Host": me, "Origin": f"http://127.0.0.1:{port + 1}"}, {"Host": me, "Sec-Fetch-Site": "cross-site"},
                      {"Host": me, "Sec-Fetch-Site": "same-site"}):
                code, body = self.ask(b, "POST", "/api/timer", h, start)
                self.assertEqual(code, 403, h)
                self.assertIn("Refused", json.loads(body)["why"])
            self.assertEqual(self.ask(b, "POST", "/api/quit", {"Host": me, "Origin": "http://evil.example"}, {})[0], 403)
            self.assertEqual(self.ask(b, "POST", "/api/restart", {"Host": me, "Origin": "http://evil.example"}, {})[0], 403)
            self.assertEqual(self.ask(b, "POST", "/api/settings", {"Host": me, "Sec-Fetch-Site": "cross-site"}, {"key": "lan", "value": True})[0], 403)
            self.assertEqual(self.ask(b, "GET", "/api/state", {"Host": me, "Sec-Fetch-Site": "cross-site"})[0], 403)
            # a name pointed at this PC (DNS rebinding): refused, the page too
            for path in ("/api/state", "/", "/style.css"):
                self.assertEqual(self.ask(b, "GET", path, {"Host": f"evil.example:{port}"})[0], 403, path)
            self.assertEqual(self.ask(b, "POST", "/api/timer", {"Host": f"evil.example:{port}", "Origin": f"http://evil.example:{port}"}, start)[0], 403)
            time.sleep(0.5)
            self.assertFalse(b.bus()["timer"]["run"], "nothing done for them")
            self.assertIn("Refused a request that didn't come from the FT3000's page", b.log())
            self.assertTrue(b.state(), "still running")


class Home(unittest.TestCase):
    def test_home_state(self):
        with Board("home", **journals.home()) as b:
            s = b.state()
            check_golden(self, "home_state", normalise(part(s, "cmdr", "sit", "log", "commander", "system", "jump_range", "star_pos", "body")))
            self.assertEqual([e["tag"] for e in s["log"]],
                             ["LOGIN", "UNDOCK", "KILL", "BOND", "INTRDCT", "ESCAPE", "CRIME", "PROMO", "DOCK", "CASH"])


class Vehicles(unittest.TestCase):
    """Changing vehicle, and loading in (which waits for Status.json to show you in game)."""

    def test_vehicle_changes(self):
        j = journals.syst()
        with Board("vehicles", journal=j["journal"], status={"Flags": 0}, edsm=(), no_edsm=True, ufc=False) as b:
            boot0 = b.state()["boot"]
            self.assertEqual(boot0["id"], "")             # nothing plays for history
            b.add({"event": "Fileheader", "part": 1}, {"event": "LoadGame", "Commander": "Deckard", "Ship": "Krait_MkII", "GameMode": "Solo"})
            time.sleep(2.5)
            self.assertEqual(b.state()["boot"]["id"], "", "the start-up must wait for Status.json")
            b.write_status({"Flags": DOCKED_FLAGS})
            boot = b.wait(lambda: (lambda x: x if x["id"] else None)(b.state()["boot"]), what="the loading-in boot")
            self.assertEqual((boot["from"], boot["to"]), ("", "ship"))
            seq = []
            for ev, expect in [({"event": "Disembark", "SRV": False, "Taxi": False, "Multicrew": False, "OnStation": True}, ("ship", "foot")),
                               ({"event": "Embark", "SRV": False, "Taxi": False, "Multicrew": False}, ("", "ship")),
                               ({"event": "LaunchSRV", "SRVType": "testbuggy", "SRVType_Localised": "SRV Scarab", "Loadout": "starter", "PlayerControlled": True}, ("ship", "srv")),
                               ({"event": "DockSRV", "SRVType": "testbuggy"}, ("srv", "ship")),
                               ({"event": "LaunchFighter", "Loadout": "four", "PlayerControlled": True}, ("ship", "fighter")),
                               ({"event": "DockFighter"}, ("fighter", "ship"))]:
                last = b.state()["boot"]["id"]
                b.add(ev)
                bt = b.wait(lambda: (lambda x: x if x["id"] != last else None)(b.state()["boot"]), what=f"the boot after {ev['event']}")
                seq.append((bt["from"], bt["to"], bt["label"]))
                self.assertEqual((bt["from"], bt["to"]), expect)
            check_golden(self, "vehicle_sequence", seq)

    def test_loading_in_fallback_text(self):
        # the one-minute fallback is long for a test; check the message is there in the code path instead
        with Board("vehicles2", journal=journals.syst()["journal"], status={"Flags": 0}, edsm=(), no_edsm=True, ufc=False) as b:
            b.add({"event": "LoadGame", "Commander": "Deckard", "Ship": "Krait_MkII", "GameMode": "Solo"})
            b.write_status({"Flags": 0, "Flags2": 1})   # on foot counts as in game
            bt = b.wait(lambda: (lambda x: x if x["id"] else None)(b.state()["boot"]), what="the boot")
            self.assertEqual(bt["to"], "ship")


class Syst(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Board("syst", **journals.syst()).start()

    @classmethod
    def tearDownClass(cls):
        cls.b.stop()

    def test_1_model(self):
        y = self.b.state()["syst"]
        self.assertEqual(y["status"], "ok")
        self.assertEqual(y["auto"], {"key": y["docked"], "why": "docked"})
        check_golden(self, "syst_model", normalise(y))

    def test_2_near_planet(self):
        b = self.b
        b.add({"event": "Undocked", "StationName": "Fabian City"})
        b.write_status(journals.NEAR_HAO)
        y = b.wait(lambda: (lambda y: y if (y.get("auto") or {}).get("why") == "nearest" else None)(b.state()["syst"]), what="Auto to pick the nearest site")
        names = {e["key"]: e["name"] for e in y["entries"]}
        self.assertEqual(names[y["auto"]["key"]], "Hao Extraction Prospect")
        check_golden(self, "syst_near", normalise({k: y[k] for k in ("me", "near", "auto", "docked")}))

    def test_3_ufc(self):
        b = self.b
        b.ufc_cmd("press ILS", "press Opt2")
        b.wait(lambda: b.bus()["view"] == {"tab": "nav", "sub": 1} or None, what="the UFC to pick the Nav tab (Syst)")
        b.post("/api/select", {"tab": "nav", "sub": 1})   # as the page does when it follows
        d = b.wait(lambda: b.display() if b.display()["cue"] == 2 else None, what="the ':' beside NAV")
        y = b.state()["syst"]
        list_keys = [e["key"] for e in y["entries"]]
        self.assertEqual(d["com2"], ufc_num(len(list_keys)))
        before = b.bus()["cursors"]["syst"]
        b.ufc_cmd("pulse COMM1_CW")
        after = b.wait(lambda: (lambda c: c if c != before else None)(b.bus()["cursors"]["syst"]), what="the System cursor")
        self.assertEqual(list_keys.index(after), list_keys.index(before) + 1)
        b.ufc_cmd("press COMM1_PULL")
        bus = b.wait(lambda: (lambda u: u if u["pick_n"] >= 1 else None)(b.bus()), what="the pull")
        self.assertEqual(bus["pick"], {"list": "syst", "key": after})
        n = bus["view_n"]
        b.ufc_cmd("press 1")   # the keypad's 1 again: Syst's other page, the map
        bus = b.wait(lambda: (lambda u: u if u["view_n"] == n + 1 else None)(b.bus()), what="the list/map flip")
        self.assertEqual(bus["view"], {"tab": "nav", "sub": 2})
        b.post("/api/select", {"tab": "nav", "sub": 2})
        map_keys = y["map"]["order"]
        b.ufc_cmd("pulse COMM1_CW")
        cur = b.wait(lambda: (lambda c: c if c in map_keys else None)(b.bus()["cursors"]["syst"]), what="the map cursor")
        self.assertIn(cur, map_keys)
        c2, cl = bus["c2pull_n"], bus["c2long_n"]
        b.ufc_cmd("press COMM2_PULL")
        self.assertTrue(b.wait(lambda: b.bus()["c2pull_n"] == c2 + 1 or None, what="the COMM2 pull"))
        b.ufc_cmd("hold COMM2_PULL 2.4", pause=3.0)
        self.assertTrue(b.wait(lambda: b.bus()["c2long_n"] == cl + 1 or None, what="the long pull"))
        # the dials: where each sits, 0 (anticlockwise) to 1, for the page to use as a speed (the middle holds)
        self.assertEqual(b.bus()["dials"], {"brightness": 0.5, "comm2_volume": 0.5, "comm1_volume": 0.5})
        b.ufc_cmd("dial 7 3000", "dial 9 800")
        b.wait(lambda: b.bus()["dials"] == {"brightness": 0.5, "comm2_volume": 0.75, "comm1_volume": 0.2} or None, what="the dials")
        # the page's dial cue shows on the scratchpad (page menu only)
        b.post("/api/dialcue", {"page": "harness", "z": "Z-", "t": ">>"})
        b.wait(lambda: (b.display()["s1"], b.display()["s2"]) == ("Z-", ">>") or None, what="the dial cue")
        self.assertEqual(b.post("/api/dialcue", {"page": "harness", "z": "", "t": ""}), (200, {"ok": True}))
        b.wait(lambda: (b.display()["s1"], b.display()["s2"]) == ("B", "C") or None, what="the menu letters back")
        b.ufc_cmd("press DL")
        b.wait(lambda: b.display()["options"][0] == "GXY" or None, what="navigation")


class Signal(unittest.TestCase):
    """Whether you're in the game - the page's input signal: a load gives it (once Status.json shows
    you in), the main menu, closing the game or starting it again take it away."""

    def game(self, b):
        return b.state()["game"]

    def test_live(self):
        j = journals.syst()   # the journal's history ends with you in your ship
        with Board("signal", journal=j["journal"], status=j["status"], edsm=(), no_edsm=True, ufc=False) as b:
            self.assertEqual(b.wait(lambda: self.game(b)["in"] and self.game(b), what="the signal from history"),
                             {"in": True, "vehicle": "ship", "label": ""})
            b.add({"event": "Music", "MusicTrack": "Supercruise"}, {"event": "Fileheader", "part": 2})   # still playing
            time.sleep(1.2)
            self.assertTrue(self.game(b)["in"])
            b.add({"event": "Music", "MusicTrack": "MainMenu"})
            b.wait(lambda: not self.game(b)["in"] or None, what="the main menu to take the signal away")
            b.add({"event": "LoadGame", "Commander": "Deckard", "Ship": "testbuggy", "Ship_Localised": "SRV Scarab", "GameMode": "Solo"})
            time.sleep(1.5)
            self.assertFalse(self.game(b)["in"], "still on the loading screen: Status.json hasn't shown you in yet")
            b.write_status({"Flags": 1 << 26})   # in the SRV
            g = b.wait(lambda: self.game(b)["in"] and self.game(b), what="the signal after loading in")
            self.assertEqual((g["vehicle"], g["label"]), ("srv", "SRV Scarab"))
            self.assertTrue(b.state()["boot"]["id"].endswith(">srv"))
            b.add({"event": "Shutdown"})
            b.wait(lambda: not self.game(b)["in"] or None, what="closing the game to take it away")

    def test_from_history(self):
        cases = [("ended at the main menu", [{"event": "Music", "MusicTrack": "MainMenu"}], False),
                 ("closed", [{"event": "Shutdown"}], False),
                 ("started again, not loaded yet", [{"event": "Fileheader", "part": 1}, {"event": "Commander", "Name": "Deckard"}], False)]
        for what, tail, expect in cases:
            with self.subTest(what):
                j = journals.syst()
                with Board("signal_h", journal=j["journal"] + [dict(e, timestamp=ago(20)) for e in tail], status={"Flags": 0},
                           edsm=(), no_edsm=True, ufc=False) as b:
                    time.sleep(1.0)
                    self.assertEqual(self.game(b)["in"], expect)


def load_script():
    """The script as a module, for checking single parts of it directly."""
    import importlib.util
    from harness import SCRIPT
    spec = importlib.util.spec_from_file_location("edtb_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.log = lambda *a, **k: None   # quiet
    return mod


class Parts(unittest.TestCase):
    """Single parts of the script, checked directly."""

    @classmethod
    def setUpClass(cls):
        cls.m = load_script()

    def test_docking_stops_if_elite_loses_focus(self):
        m = self.m

        class Binds:
            def refresh(self):
                pass

            def lookup(self, action):
                return ((), "Key_A")

        for front, expect in (([True] * 9, len(m.DOCKING_MACRO)),   # Elite in front throughout: every key
                              ([True, True, False] + [True] * 6, 2)):   # switched away after the second key: the rest held back
            keys = m.KeySender(Binds(), dry_run=True)
            answers = iter(front)
            keys.elite_in_front = lambda: next(answers)
            taps = []
            keys._tap = lambda combo, hold: taps.append(combo)
            keys._do("Request docking", m.DOCKING_MACRO, m.MACRO_HOLD, 0)
            self.assertEqual(len(taps), expect)

    def test_cancelled_jump_isnt_surveyed(self):
        import tempfile
        from pathlib import Path
        m = self.m
        for started, flags, surveyed in ((5, m.F_FSD_CHARGING, True),   # counting down
                                         (40, m.F_FSD_JUMP, True),      # in hyperspace
                                         (40, 0, False),                # cancelled: the drive has stopped
                                         (200, m.F_FSD_JUMP, False)):   # never arrived: given up on
            with self.subTest(started=started, flags=flags):
                board = m.BoardState(Path(tempfile.mkdtemp()) / "cache.json")
                board.live = True
                board.set_status({"timestamp": ago(1), "Flags": flags})
                board.apply({"timestamp": ago(started), "event": "StartJump", "JumpType": "Hyperspace", "StarSystem": "Carthage", "StarClass": "B"})
                self.assertEqual(board.jumps.target() is not None, surveyed)
                self.assertEqual(board.jumps.view() is not None, surveyed)

    def test_schematic_categories_and_tidying(self):
        m = self.m
        self.assertEqual([m.schematic_category(x) for x in ("Tourism", "tourist", "High Tech", "high-tech", "High-Tech / Bio", "")],
                         ["tourism", "tourism", "hightech", "hightech", "hightech", ""])
        plan = m.tidy_plan({"category": "Tourist", "id": "t-9", "buildings": [{"outline": [[0, 0], [10, 0], [10, 10]], "height_m": 6},
                                                                             {"outline": [[0, 0]]}],
                            "details": [{"id": "notes", "notes": "not a shape"}],
                            "points": [{"type": "tip", "at": [5, 5], "scope": "map_ui"},
                                       {"type": "terminal_lo", "at": [3, 4], "icon": {"text": ""}, "access": 0}]}, "file")
        self.assertEqual((plan["category"], len(plan["buildings"]), plan["details"]), ("tourism", 1, []))
        self.assertEqual(plan["points"], [{"type": "terminal_lo", "at": [3.0, 4.0], "text": None, "access": 0}])
        self.assertEqual(plan["bounds"], [0.0, 0.0, 10.0, 10.0])
        labelled = m.tidy_plan({"category": "military", "buildings": [{"id": "cmd", "label": "CMD", "outline": [[0, 0], [9, 0], [9, 9]]}],
                                "printed_labels": [{"text": "SEC", "at": [2, 3], "building": "cmd"}, {"text": "", "at": [1, 1]}]}, "m-5")
        self.assertEqual(labelled["labels"], [{"text": "SEC", "at": [2.0, 3.0], "building": "cmd"}])   # where room names are printed
        self.assertEqual(labelled["buildings"][0]["id"], "cmd")
        shared = m.tidy_plan({"category": "industrial", "buildings": [   # a roof shared by several names, given on the building
            {"id": "ind", "label": "IND", "outline": [[0, 0], [9, 0], [9, 9]],
             "printed_labels": ["LAB", "IND"], "printed_label_positions": [{"text": "LAB", "at": [2, 2]}, {"text": "IND", "at": [7, 7]}]},
            {"id": "pwr", "label": "PWR", "outline": [[20, 0], [29, 0], [29, 9]], "printed_labels": ["PWR", "LAB", "PWR"]}]}, "i-2")
        self.assertEqual(shared["labels"], [{"text": "LAB", "at": [2.0, 2.0], "building": "ind"}, {"text": "IND", "at": [7.0, 7.0], "building": "ind"}])
        self.assertEqual(shared["buildings"][1]["label"], "PWR/LAB")   # no positions: one name for both
        # edges the map picture cut off: along its border, or named by the plan (by number, or by their two ends)
        cut = m.tidy_plan({"category": "military", "source": {"width": 1644, "height": 925, "map_area": [0, 40, 1644, 875]},
                           "buildings": [{"id": "top", "outline": [[100, 40], [200, 40], [200, 90], [100, 90]]},
                                         {"id": "inside", "outline": [[300, 300], [400, 300], [400, 400], [300, 400]]},
                                         {"id": "said", "outline": [[500, 500], [600, 500], [600, 600], [500, 600]]}],
                           "pads": [{"id": "pad", "outline": [[700, 800], [900, 800], [900, 874], [700, 874]]}],
                           "clipped_edges": {"said": [{"edge_index": 1}, {"from": [500, 600], "to": [500, 500]}]}}, "m-9")
        self.assertEqual([b["cut"] for b in cut["buildings"]], [[0], [], [1, 3]])
        self.assertEqual(cut["pads"][0]["cut"], [2])
        with self.assertRaises(ValueError):
            m.tidy_plan({"category": "", "buildings": []}, "file")
        # a plan fitted to SrvSurvey (site_m): drawn in metres with the y axis turned down the page, its pads
        # numbered, each icon given its toggle, colour and letters (a ^ a floor up), the map's tips none
        site = m.tidy_plan({"category": "High-Tech / Bio", "id": "high-tech-9", "name": "Chronos", "layout": 1, "buildings": [], "site_m": {
            "buildings": [{"id": "hab", "kind": "hab", "label": "HAB", "outline_m": [[0, 0], [10, 0], [10, 20]], "height_m": 8}],
            "pads": [{"outline_m": [[-10, -10], [-5, -10], [-5, -3], [-10, -3]], "pad_number": 2, "size": "large"}],
            "walkways": [{"kind": "open", "line_m": [[0, 0], [5, 5]], "width_m": 3}],
            "points": [{"type": "airlock", "at_m": [1, 2], "access": 1, "floor": 2, "source": "plan+srvsurvey"},
                       {"type": "loot", "item": "Medkit", "at_m": [2, 2], "access": 0, "floor": 1, "source": "srvsurvey"},
                       {"type": "loot", "item": "Sample Containment Unit", "at_m": [3, 3], "floor": 1, "source": "srvsurvey"},
                       {"type": "cz_point", "name": "P", "at_m": [4, 4], "floor": 0, "source": "srvsurvey"},
                       {"type": "terminal", "function": "turrets", "at_m": [5, 5], "access": 2, "floor": 1, "source": "srvsurvey"},
                       {"type": "tip", "at_m": [6, 6], "icon": {"text": "i"}, "source": "plan"}]}}, "file")
        self.assertEqual((site["category"], site["name"], site["m_per_px"]), ("hightech", "Chronos", 1.0))
        self.assertEqual(site["buildings"][0]["outline"], [[0.0, 0.0], [10.0, 0.0], [10.0, -20.0]])
        self.assertEqual((site["pads"][0]["num"], site["pads"][0]["size"], site["walkways"][0]["w"]), (2, "L", 3.0))
        self.assertEqual((site["pads"][0]["rot"], site["pads"][0]["rec"]), (0.0, False))   # pad 2 with no rotation: its direction isn't known
        self.assertEqual([(p["g"], p["k"], p["text"]) for p in site["points"]],
                         [("door", "lock", "1^"), ("exp", "exp", "+"), ("loot", "loot", "U"), ("cz", "czp", "P"),
                          ("term", "term2", "TU"), (None, None, "i")])
        self.assertEqual(site["bounds"], [-10.0, -20.0, 10.0, 10.0])

    def test_spansh_records(self):
        """Spansh's system record: market prices, modules and ships thrown away; turned into the tab's shape -
        settlements as Odyssey settlements with their pads, position and economies, ring radii in km,
        barycentres left out, a surface site of no type a settlement of some kind; EDSM filling its gaps."""
        import tempfile
        from pathlib import Path
        m = self.m
        rec = {"id64": 5, "name": "Testia", "bodyCount": 3, "factions": [{"name": "A"}], "stations": [
                   {"id": 1, "name": "High Dock", "type": "Coriolis Starport", "distanceToArrival": 50.0, "primaryEconomy": "Industrial",
                    "economies": {"Industrial": 100.0, "Refinery": 60.0, "Tourism": 10.0}, "controllingFaction": "Testia Party",
                    "landingPads": {"large": 6, "medium": 10, "small": 8}, "services": ["Dock", "Market", "Shipyard", "Refuel", "Missions Generated"],
                    "market": {"commodities": [{"name": "Gold"}] * 500, "prohibitedCommodities": [], "updateTime": "2026-10-30T01:02:03Z"},
                    "shipyard": {"ships": [{"name": "Python"}], "updateTime": "2026-10-29T00:00:00Z"}, "updateTime": "2026-10-30T01:00:00Z"},
                   {"id": 2, "name": "XYZ-123", "type": "Drake-Class Carrier", "distanceToArrival": 9.0}],
               "bodies": [{"name": "Testia barycentre 1", "type": "Barycentre", "bodyId": 1},
                          {"name": "Testia A", "type": "Star", "bodyId": 2, "mainStar": True, "spectralClass": "K3", "subType": "K (Yellow-Orange) Star",
                           "belts": [{"name": "Testia A Belt", "type": "Rocky", "innerRadius": 9.0e8, "outerRadius": 2.0e9, "signals": {}}]},
                          {"name": "Testia 1", "type": "Planet", "bodyId": 3, "id64": 77, "parents": [{"Star": 2}], "atmosphereType": None,
                           "isLandable": True, "radius": 900.0, "updateTime": "2026-10-20T01:35:42Z", "stations": [
                               {"id": 3, "name": "Kessel Works", "type": "Settlement", "latitude": -31.37, "longitude": 154.06,
                                "primaryEconomy": "Industrial", "economies": {"Industrial": 140.0}, "landingPads": {"large": 0, "medium": 1, "small": 0},
                                "services": ["Dock", "Market", "Contacts"], "market": {"commodities": [{"name": "Tea"}], "updateTime": "2026-10-30T08:57:07Z"}},
                               {"id": 4, "name": "Fenwick Prospect", "latitude": 1.5, "longitude": 2.5, "updateTime": "2023-02-19T13:44:36Z"}]}]}
        kept = m.strip_spansh(rec)
        self.assertNotIn("factions", kept)
        self.assertEqual(kept["stations"][0]["market"], {"updateTime": "2026-10-30T01:02:03Z"})   # no prices
        self.assertEqual(kept["stations"][0]["shipyard"], {"updateTime": "2026-10-29T00:00:00Z"})
        self.assertEqual(kept["bodies"][2]["stations"][0]["market"], {"updateTime": "2026-10-30T08:57:07Z"})
        raw = m.spansh_raw(kept)
        self.assertEqual([b["name"] for b in raw["bodies"]["bodies"]], ["Testia A", "Testia 1"])   # (no barycentre)
        star, planet = raw["bodies"]["bodies"]
        self.assertEqual((star["isMainStar"], star["isScoopable"], star["belts"][0]["innerRadius"], "signals" in star["belts"][0]),
                         (True, True, 900000.0, False))
        self.assertEqual((planet["atmosphereType"], planet["updateTime"], planet["_from"]), ("No atmosphere", "2026-10-20 01:35:42", "spansh"))
        st = {s["name"]: s for s in raw["stations"]["stations"]}
        dock = st["High Dock"]
        self.assertEqual((dock["marketId"], dock["economy"], dock["secondEconomy"], dock["haveMarket"], dock["haveShipyard"], dock["haveOutfitting"]),
                         (1, "Industrial", "Refinery", True, True, False))
        self.assertEqual((dock["otherServices"], dock["controllingFaction"], dock["landingPads"]),
                         (["Refuel"], {"name": "Testia Party"}, {"small": 8, "medium": 10, "large": 6}))
        self.assertEqual(dock["updateTime"], {"information": "2026-10-30 01:00:00", "market": "2026-10-30 01:02:03",
                                              "shipyard": "2026-10-29 00:00:00", "outfitting": None})
        self.assertNotIn("body", dock)   # (Spansh doesn't say which body a station orbits)
        self.assertEqual(st["XYZ-123"]["type"], "Fleet Carrier")
        works = st["Kessel Works"]
        self.assertEqual((works["type"], works["body"], works["landingPads"]),
                         ("Odyssey Settlement", {"id": 77, "name": "Testia 1", "latitude": -31.37, "longitude": 154.06}, {"small": 0, "medium": 1, "large": 0}))
        self.assertEqual(st["Fenwick Prospect"]["type"], "Settlement")   # only approached: of no known kind
        model, _ = m.build_syst("Testia", raw, {})
        e = {x["name"]: x for x in model["entries"]}
        self.assertEqual((e["Kessel Works"]["src"], e["Kessel Works"]["surface"], e["Kessel Works"]["settlement"]["category"]), ("spansh", True, "industrial"))
        self.assertIn(["Landing pads", "0 small · 1 medium · 0 large", True], e["Kessel Works"]["rows"])
        self.assertTrue(e["Fenwick Prospect"]["settlement"]["unsure"])
        self.assertIn(["Spansh updated", m._edsm_time("2026-10-20 01:35:42"), True], e["Testia 1"]["rows"])
        self.assertEqual((e["1 fleet carrier"]["lab"], e["1 fleet carrier"]["src"]), ("Fleet carriers seen here (Spansh)", "spansh"))
        # the system's address: from your journal, else Spansh's search; Spansh not knowing it is an answer, not a failure
        tmp = Path(tempfile.mkdtemp())
        board = m.BoardState(tmp / "cache.json")
        f = m.EdsmFetcher(board, tmp, m.EdsmCache(tmp / "edsm.json"))
        asked = []

        def fake(path):
            asked.append(path)
            if path.startswith("search/"):
                return {"results": [{"name": "Testia Major", "id64": 1}, {"name": "Testia", "id64": 5}]}
            return {"system": rec} if path == "dump/5" else None
        f._spansh = fake
        self.assertEqual(f._id64("Testia"), 5)
        self.assertEqual(f._get_spansh("Testia")["name"], "Testia")
        self.assertEqual(asked, ["search/systems?q=Testia", "dump/5"])   # (searched once: remembered)
        board.apply({"timestamp": ago(5), "event": "FSDJump", "StarSystem": "Nowhere", "SystemAddress": 42})
        self.assertEqual(f._id64("Nowhere"), 42)
        self.assertEqual(f._get_spansh("Nowhere"), {})   # 404: Spansh doesn't know it
        self.assertEqual(asked[-1], "dump/42")
        # the toggles: Spansh then EDSM - EDSM's bodies and stations only where Spansh has nothing
        self.assertEqual(f._parts("Testia"), ["spansh", "bodies", "stations", "traffic", "deaths", "estimated-value"])   # (nothing cached yet)
        f.cache.put("Testia", "spansh", kept)
        self.assertEqual(f._parts("Testia"), ["spansh", "traffic", "deaths", "estimated-value"])
        f.cache.put("Testia", "bodies", {"bodies": [{"name": "Testia 9", "type": "Planet"}]})
        self.assertEqual([b["name"] for b in f._raw("Testia")["bodies"]["bodies"]], ["Testia A", "Testia 1"])   # Spansh's
        ups = m.UplinkSettings(tmp / "uplinks.json")
        g = m.EdsmFetcher(board, tmp, f.cache, uplinks=ups)
        heard = []
        ups.listeners.append(lambda: heard.append(ups.view()))
        ups.set("spansh", False)
        self.assertEqual((g._parts("Testia"), g.source("Testia")), (["bodies", "stations", "traffic", "deaths", "estimated-value"], "EDSM"))
        self.assertEqual([b["name"] for b in g._raw("Testia")["bodies"]["bodies"]], ["Testia 9"])   # EDSM's
        self.assertEqual(heard, [{"spansh": False, "edsm": True}])
        self.assertEqual(json.loads((tmp / "uplinks.json").read_text()), {"spansh": False, "edsm": True})   # kept
        self.assertEqual(m.UplinkSettings(tmp / "uplinks.json").view(), {"spansh": False, "edsm": True})
        self.assertEqual(m.UplinkSettings(tmp / "uplinks.json", edsm_off=True).view(), {"spansh": False, "edsm": False})   # --no-edsm: this run
        ups.set("edsm", False)
        self.assertTrue(g.offline)
        self.assertEqual((g._parts("Testia"), g._raw("Testia")), ([], {}))

    def test_journal_wins(self):
        """Your journal over Spansh's (or EDSM's) records: a body you've scanned takes your figures (and is marked
        as yours); a station takes your journal's type, pads and position always, its faction, economy and
        services only if your journal's are newer; Spansh's signals go at the bottom of a planet's details."""
        m = self.m
        raw = m.spansh_raw({"id64": 5, "name": "Testia", "bodies": [
            {"name": "Testia A", "type": "Star", "bodyId": 0, "mainStar": True, "spectralClass": "K3"},
            {"name": "Testia 1", "type": "Planet", "bodyId": 1, "parents": [{"Star": 0}], "radius": 900.0, "gravity": 0.05,
             "signals": {"signals": {"$SAA_SignalType_Human;": 3, "$SAA_SignalType_Biological;": 2, "$PlanetaryMiningLocation_Name;": 7},
                         "genuses": ["$Codex_Ent_Bacterial_Genus_Name;", "$Codex_Ent_Shrubs_Genus_Name;"]},
             "stations": [{"id": 3, "name": "Kessel Works", "type": "Settlement", "latitude": 1.0, "longitude": 2.0,
                           "controllingFaction": "Old Owners", "government": "Anarchy", "primaryEconomy": "Industrial",
                           "landingPads": {"small": 9, "medium": 9, "large": 9}, "updateTime": "2026-10-20T00:00:00Z"},
                          {"id": 4, "name": "New Town", "type": "Planetary Outpost", "latitude": 5.0, "longitude": 6.0,
                           "controllingFaction": "Fresh Faction", "government": "Democracy", "updateTime": "2026-10-29T00:00:00Z"}]},
            {"name": "Testia 2", "type": "Planet", "bodyId": 2, "parents": [{"Star": 0}], "radius": 4000.0}]})
        rec = {"bodies": [{"name": "Testia 1", "type": "Planet", "bodyId": 1, "radius": 912.5, "gravity": 0.06, "subType": "Icy body",
                           "_journal": True, "_seen": "2026-10-01T00:00:00Z"}],
               "stations": [{"name": "Kessel Works", "marketId": 3, "type": "Odyssey Settlement", "controllingFaction": {"name": "New Owners"},
                             "government": "Corporate", "landingPads": {"small": 0, "medium": 1, "large": 0}, "_journal": True,
                             "_seen": "2026-10-25T00:00:00Z", "body": {"name": "Testia 1", "latitude": 1.25, "longitude": 2.5}},
                            {"name": "New Town", "marketId": 4, "type": "Planetary Outpost", "controllingFaction": {"name": "Stale Faction"},
                             "government": "Anarchy", "landingPads": {"small": 4, "medium": 2, "large": 2}, "_journal": True,
                             "_seen": "2026-10-10T00:00:00Z"}]}
        model, _ = m.build_syst("Testia", m.merge_records(raw, rec), {})
        e = {x["name"]: x for x in model["entries"]}
        rows = lambda n: {r[0]: r[1] for r in e[n]["rows"]}
        p1 = rows("Testia 1")
        self.assertEqual((p1["Radius"], p1["Gravity"], p1["Type"]), ("912 km", "0.06 g", "Icy body"))   # your scan's
        self.assertEqual((e["Testia 1"]["mine"], e["Testia 1"]["src"], e["Testia 2"]["mine"]), (True, "spansh+journal", False))
        self.assertIn({"t": "Scanned by you"}, e["Testia 1"]["chips"])
        self.assertEqual([r[0] for r in e["Testia 1"]["rows"]][-2:], ["Signals", "Biology"])   # at the bottom
        self.assertEqual((p1["Signals"], p1["Biology"]), ("Biological 2 · Human 3 · Mining 7", "Bacterium · Frutexa"))
        self.assertEqual({b["name"]: b["mine"] for b in model["map"]["bodies"]}, {"Testia A": False, "Testia 1": True, "Testia 2": False})
        kw = rows("Kessel Works")   # your journal's newer: all yours
        self.assertEqual((kw["Faction"], kw["Government"], kw["Landing pads"], kw["Position (your journal)"]),
                         ("New Owners", "Corporate", "0 small · 1 medium · 0 large", "1.25, 2.50"))
        nt = rows("New Town")   # Spansh's newer: its faction and government, your pads
        self.assertEqual((nt["Faction"], nt["Government"], nt["Landing pads"]), ("Fresh Faction", "Democracy", "4 small · 2 medium · 2 large"))
        self.assertEqual(e["New Town"]["src"], "spansh+journal")
        # the journal's Docked gives the pads
        st = m.station_from_event({"timestamp": ago(1), "event": "Docked", "StationName": "Gregory Town", "StationType": "Dodec",
                                   "MarketID": 9, "LandingPads": {"Small": 17, "Medium": 18, "Large": 9}})
        self.assertEqual(st["landingPads"], {"small": 17, "medium": 18, "large": 9})

    def test_system_archive(self):
        """The systems you've been in: their last answers kept for good - the cache drops them after a week, the
        archive doesn't."""
        import tempfile
        from pathlib import Path
        m = self.m
        tmp = Path(tempfile.mkdtemp())
        arch = m.SystemArchive(tmp / "archive.sqlite")
        cache = m.EdsmCache(tmp / "cache.json", arch)
        old = time.time() - 30 * 86400
        cache.put("Testia", "spansh", {"name": "Testia", "bodies": [{"name": "Testia A"}]}, old)
        cache.keep("Testia", ["spansh"])
        cache.save()   # a month old: out of the cache...
        self.assertEqual(json.loads((tmp / "cache.json").read_text()), {})
        again = m.EdsmCache(tmp / "cache.json", m.SystemArchive(tmp / "archive.sqlite"))
        self.assertEqual(again.get("testia", "spansh"), (old, {"name": "Testia", "bodies": [{"name": "Testia A"}]}))   # ... still there
        self.assertIsNone(again.get("Elsewhere", "spansh"))

    def test_settlement_headings(self):
        """Which way a settlement faces: from your ship's heading docked on a pad whose direction is recorded
        (heading less the pad's turn), or set with Align Settlement - which, after a docking, locks it: later
        dockings there are ignored, until its layout changes. Kept in settlements.sqlite."""
        import tempfile
        from pathlib import Path
        from harness import FIX
        m = self.m
        tmp = Path(tempfile.mkdtemp())
        board = m.BoardState(tmp / "cache.json")
        board.settlements = m.SettlementLayouts(tmp / "settlements.sqlite")
        board.schematics = m.SchematicStore(FIX / "schematics")   # the four Tourism layouts
        board.live = True
        key, mid = "m:3814631936", 3814631936
        layouts = board.settlements
        self.assertTrue(layouts.save(key, "tourist-4", "HIP 20277", "Dhaenens's Lodgings", "Tourism"))   # Gelos: pad 2 turned 270°
        pads = {p["num"]: (p["rot"], p["rec"]) for p in board.schematics.plan("tourist-4")["pads"]}
        self.assertEqual(pads, {1: (0.0, True), 2: (270.0, True)})

        def dock(pad, heading, ago_s=20):
            board.apply({"timestamp": ago(ago_s + 5), "event": "DockingGranted", "MarketID": mid, "LandingPad": pad, "StationName": "Dhaenens's Lodgings"})
            board.apply({"timestamp": ago(ago_s), "event": "Docked", "MarketID": mid, "StationName": "Dhaenens's Lodgings",
                         "StationType": "OnFootSettlement", "StarSystem": "HIP 20277"})
            board.set_status({"timestamp": ago(ago_s - 2), "Flags": 1 | 8 | (1 << 21) | (1 << 24), "Heading": heading,
                              "Latitude": 58.7693, "Longitude": 51.4311, "Altitude": 0, "BodyName": "HIP 20277 3 a"})
            board.apply({"timestamp": ago(ago_s - 10), "event": "Undocked", "MarketID": mid, "StationName": "Dhaenens's Lodgings"})
            board.set_status({"timestamp": ago(ago_s - 11), "Flags": 8 | (1 << 21) | (1 << 24), "Heading": heading + 90})   # lifted off

        def heading():
            return layouts.headings_for([key]).get(key)

        dock(2, 300)   # 300 - 270
        self.assertEqual(heading(), {"layout": "tourist-4", "h": 30.0, "src": "dock", "locked": False, "pad": 2})
        dock(1, 31.5)   # a later docking replaces it
        self.assertEqual(heading()["h"], 31.5)
        self.assertTrue(layouts.save_heading(key, "tourist-4", 45, "manual", name="Dhaenens's Lodgings"))   # aligned by hand: locked
        self.assertEqual(heading(), {"layout": "tourist-4", "h": 45.0, "src": "manual", "locked": True, "pad": None})
        dock(1, 100)   # ignored now
        self.assertEqual(heading()["h"], 45.0)
        self.assertEqual(layouts.dockings[key]["ship"], 100.0)   # (the docking itself is kept)
        self.assertTrue(layouts.save_heading(key, "tourist-4", 50, "manual"))
        self.assertEqual((heading()["h"], heading()["locked"]), (50.0, True))   # still locked
        # a different layout confirmed: its heading from the last docking (pad 1 on Fufluns), unlocked again
        self.assertTrue(layouts.save(key, "tourist-1"))
        self.assertEqual(m.heading_from_docking(layouts, board.schematics, key), 100.0)
        self.assertEqual(heading(), {"layout": "tourist-1", "h": 100.0, "src": "dock", "locked": False, "pad": 1})
        dock(2, 200)   # Fufluns' pad 2 has no recorded direction: no change
        self.assertEqual(heading()["h"], 100.0)
        # aligned by hand with no docking since: dockings still count
        other = "m:3814632448"
        layouts.save(other, "tourist-2")
        layouts.save_heading(other, "tourist-2", 12, "manual")
        self.assertFalse(layouts.headings_for([other])[other]["locked"])
        # a docking read back at start-up only counts if you're still on that pad (Status.json newer than it)
        b2 = m.BoardState(tmp / "cache2.json")
        b2.settlements, b2.schematics = layouts, board.schematics
        b2.apply({"timestamp": ago(4000), "event": "DockingGranted", "MarketID": 3814632448, "LandingPad": 1})
        b2.apply({"timestamp": ago(3990), "event": "Docked", "MarketID": 3814632448, "StationType": "OnFootSettlement", "StationName": "Preece"})
        b2.set_status({"timestamp": ago(3999), "Flags": 1, "Heading": 5})   # (not live yet, and older)
        self.assertEqual(layouts.headings_for([other])[other]["h"], 12.0)
        b2.live = True
        b2.set_status({"timestamp": ago(1), "Flags": 1 | (1 << 21), "Heading": 77})
        self.assertEqual(layouts.headings_for([other])[other], {"layout": "tourist-2", "h": 77.0, "src": "dock", "locked": False, "pad": 1})
        b2.apply({"timestamp": ago(0), "event": "Undocked"})
        # kept for good
        again = m.SettlementLayouts(tmp / "settlements.sqlite")
        self.assertEqual(again.headings_for([key, other]), layouts.headings_for([key, other]))
        self.assertEqual(again.dockings[key], {"pad": 2, "ship": 200.0, "system": "HIP 20277", "name": "Dhaenens's Lodgings"})

    def test_people_to_meet_are_not_targets(self):
        """On foot, 'take a package to' / 'secure a package from' name a person (Target) as assassinations do:
        they're contacts - an ordinary contract with no backstory - and every on-foot mission shows its settlement."""
        import tempfile
        from pathlib import Path
        m = self.m
        board = m.BoardState(Path(tempfile.mkdtemp()) / "cache.json")
        common = {"event": "MissionAccepted", "Faction": "Test Faction", "DestinationSystem": "Test Sector AB-C d1-2",
                  "Expiry": ahead(600), "Reward": 50000, "Commodity": "$CastFossil_Name;", "Commodity_Localised": "Cast Fossil", "Count": 1}
        board.apply(dict(common, timestamp=ago(30), Name="Mission_OnFoot_Delivery_Contact_MB", MissionID=71, Target="Ada Okafor",
                         LocalisedName="Take a package to Ada Okafor", DestinationSettlement="Kessel Depot"))
        board.apply(dict(common, timestamp=ago(20), Name="Mission_OnFoot_Collect_Contact_MB", MissionID=72, Target="Rui Tanaka",
                         LocalisedName="Secure a package from Rui Tanaka", DestinationSettlement="Orrin Works"))
        board.apply({"timestamp": ago(10), "event": "MissionAccepted", "Faction": "Test Faction", "Name": "Mission_OnFoot_Assassination_MB",
                     "LocalisedName": "Kill Bo Lindqvist", "MissionID": 73, "Target": "Bo Lindqvist", "Expiry": ahead(900),
                     "DestinationSystem": "Test Sector AB-C d1-2", "DestinationSettlement": "Kessel Depot", "Reward": 90000})
        got = {c["missions"][0]["id"]: c for c in board.contracts.view()}
        self.assertEqual([(got[i]["kind"], got[i]["name"], got[i]["missions"][0]["contact"]) for i in (71, 72, 73)],
                         [("contract", "Package to Ada Okafor", "Ada Okafor"), ("contract", "Package from Rui Tanaka", "Rui Tanaka"),
                          ("person", "Bo Lindqvist", "")])
        self.assertIsNone(board.contracts.for_backstory(got[71]["key"]))   # no backstory for a contact...
        self.assertIsNotNone(board.contracts.for_backstory(got[73]["key"]))   # ...only for someone to hunt
        self.assertIn("Last known whereabouts: Kessel Depot, Test Sector AB-C d1-2",
                      m.build_details(board.contracts.for_backstory(got[73]["key"])))

    def test_done_missions_from_the_login_list(self):
        import tempfile
        from pathlib import Path
        m = self.m
        board = m.BoardState(Path(tempfile.mkdtemp()) / "cache.json")
        # accepted before the journals read: the game's login list is all there is
        board.apply({"timestamp": ago(60), "event": "Missions", "Failed": [],
                     "Active": [{"MissionID": 41, "Name": "Mission_Courier_name", "PassengerMission": False, "Expires": 7200}],
                     "Complete": [{"MissionID": 42, "Name": "Mission_Delivery_name", "PassengerMission": False, "Expires": 0}]})
        got = {c["key"]: c["missions"][0] for c in board.contracts.view()}
        self.assertEqual(set(got), {"m:41", "m:42"})
        self.assertEqual((got["m:42"]["status"], got["m:42"]["partial"], got["m:42"]["expiry"]), ("redirected", True, ""))
        self.assertEqual(got["m:41"]["status"], "active")
        self.assertTrue(got["m:41"]["expiry"])


class Settlements(unittest.TestCase):
    """Odyssey settlements: their layout plans (schematics folder) and the layout you confirm for each."""

    LODGINGS = "m:3814631936"   # Dhaenens's Lodgings, a Tourism settlement in HIP 20277 (fixtures/edsm.json)

    def test_plans_and_confirmed_layouts(self):
        j = journals.syst()
        with Board("settlements", journal=j["journal"], status=j["status"], ufc=False) as b:
            s = b.state()
            self.assertEqual(s["schematics"], {"tourism": 4})
            lodge = next(e for e in s["syst"]["entries"] if e["name"] == "Dhaenens's Lodgings")
            self.assertEqual(lodge["settlement"], {"key": self.LODGINGS, "economy": "Tourism", "category": "tourism", "guess": "tourism"})
            port = next(e for e in s["syst"]["entries"] if e["name"] == "Fabian City")
            self.assertNotIn("settlement", port)   # a starport isn't an Odyssey settlement
            code, body = b.get("/api/schematics?category=tourist")   # however the economy is written
            plans = json.loads(body)["layouts"]
            self.assertEqual([p["id"] for p in plans], ["tourist-1", "tourist-2", "tourist-3", "tourist-4"])
            for p in plans:   # tidied for drawing
                self.assertTrue(all(pt["text"] != "" for pt in p["points"]))
                self.assertTrue(all("outline" in d for d in p["details"]))
                self.assertEqual(len(p["bounds"]), 4)
            self.assertNotIn([19.0, 58.0], [pt["at"] for pt in plans[0]["points"]])   # the map website's "i" button
            self.assertEqual(plans[3]["details"], [])   # Tourist 4's notes entries aren't shapes
            for bad in ({"key": self.LODGINGS, "layout": "tourist-9"}, {"key": "nonsense", "layout": "tourist-2"}, {"layout": "tourist-2"}):
                self.assertEqual(b.post("/api/settlement-layout", bad)[0], 400)
            self.assertEqual(b.post("/api/settlement-layout", {"key": self.LODGINGS, "layout": "tourist-3", "system": "HIP 20277",
                                                               "name": "Dhaenens's Lodgings", "economy": "Tourism"}), (200, {"ok": True}))
            self.assertEqual(b.state()["syst"]["layouts"], {self.LODGINGS: "tourist-3"})
            # the schematic type can be picked for any settlement ("" = back to the data's), kept like a layout
            self.assertEqual(b.post("/api/settlement-type", {"key": self.LODGINGS, "category": "industrial", "name": "Dhaenens's Lodgings"}),
                             (200, {"ok": True}))
            self.assertEqual(b.post("/api/settlement-type", {"key": self.LODGINGS, "category": "High Tech!"})[0], 400)
            self.assertEqual(b.state()["syst"]["types"], {self.LODGINGS: "industrial"})
            b.restart()   # kept for good
            self.assertEqual(b.wait(lambda: b.state()["syst"].get("layouts"), what="the layouts after a restart"), {self.LODGINGS: "tourist-3"})
            self.assertEqual(b.state()["syst"]["types"], {self.LODGINGS: "industrial"})
            self.assertEqual(b.post("/api/settlement-type", {"key": self.LODGINGS, "category": ""}), (200, {"ok": True}))
            self.assertEqual(b.state()["syst"]["types"], {})

    def check_pad(self, pad, h):   # Tourist 4's pad 2 (the fixture's SrvSurvey frame: y up), turned by the settlement's heading
        with open(Path(__file__).parent / "fixtures" / "schematics" / "tourist-4.json") as f:
            o = json.load(f)["site_m"]["pads"][1]["outline_m"]
        x, up, a = sum(q[0] for q in o) / 4, sum(q[1] for q in o) / 4, math.radians(h)
        self.assertEqual((pad["key"], pad["num"]), (self.LODGINGS, 2))
        self.assertAlmostEqual(pad["e"], x * math.cos(a) + up * math.sin(a), delta=0.11)
        self.assertAlmostEqual(pad["n"], -x * math.sin(a) + up * math.cos(a), delta=0.11)

    def test_headings(self):
        """Docking on a settlement pad gives its heading (live, from Status.json); Align Settlement's own heading
        (POST /api/settlement-heading) then takes over for good; both reach the page with your heading."""
        j = journals.syst()
        with Board("headings", journal=j["journal"], status=j["status"], ufc=False) as b:
            name = "Dhaenens's Lodgings"
            self.assertEqual(b.post("/api/settlement-layout", {"key": self.LODGINGS, "layout": "tourist-4", "name": name})[0], 200)
            self.assertEqual(b.state()["syst"]["headings"], {})
            b.add({"event": "Undocked", "StationName": "Fabian City"},
                  {"event": "DockingGranted", "MarketID": 3814631936, "LandingPad": 2, "StationName": name},
                  {"event": "Docked", "MarketID": 3814631936, "StationName": name, "StationType": "OnFootSettlement", "StarSystem": "HIP 20277"})
            b.write_status({"Flags": 1 | 8 | (1 << 21) | (1 << 24), "BodyName": "HIP 20277 3 a", "Latitude": 58.7693, "Longitude": 51.4311,
                            "Altitude": 0, "Heading": 300, "PlanetRadius": 2400000.0})
            got = b.wait(lambda: b.state()["syst"]["headings"].get(self.LODGINGS), what="the heading from the docking")
            self.assertEqual(got, {"layout": "tourist-4", "h": 30.0, "src": "dock", "locked": False, "pad": 2})   # 300 - pad 2's 270
            me = b.state()["syst"]["me"]
            self.assertEqual((me["hdg"], me["r"]), (300, 2400000.0))
            for bad in ({"key": self.LODGINGS, "layout": "tourist-4", "heading": 361}, {"key": self.LODGINGS, "layout": "tourist-4", "heading": "45"},
                        {"key": self.LODGINGS, "layout": "tourist-4", "heading": True}, {"key": self.LODGINGS, "layout": "tourist-9", "heading": 45},
                        {"key": "nonsense", "layout": "tourist-4", "heading": 45}, {"key": self.LODGINGS, "heading": 45}):
                self.assertEqual(b.post("/api/settlement-heading", bad)[0], 400, bad)
            self.assertEqual(b.post("/api/settlement-heading", {"key": self.LODGINGS, "layout": "tourist-4", "heading": 45.04, "name": name}),
                             (200, {"ok": True, "heading": {"layout": "tourist-4", "h": 45.0, "src": "manual", "locked": True, "pad": None}}))
            b.restart()   # kept for good
            self.assertEqual(b.wait(lambda: b.state()["syst"].get("headings"), what="the headings after a restart"),
                             {self.LODGINGS: {"layout": "tourist-4", "h": 45.0, "src": "manual", "locked": True, "pad": None}})

    def test_granted_pad(self):
        """For Nav > Traj: the pad you've been given at a settlement and - with its layout confirmed and the heading
        known for that layout - where it is (metres east and north of the settlement's position); gone once you've
        docked, or left."""
        j = journals.syst()
        with Board("granted_pad", journal=j["journal"], status=j["status"], ufc=False) as b:
            name = "Dhaenens's Lodgings"
            grant = {"event": "DockingGranted", "MarketID": 3814631936, "LandingPad": 2, "StationName": name, "StationType": "OnFootSettlement"}
            self.assertEqual(b.post("/api/settlement-layout", {"key": self.LODGINGS, "layout": "tourist-4", "name": name})[0], 200)
            self.assertEqual(b.post("/api/settlement-heading", {"key": self.LODGINGS, "layout": "tourist-4", "heading": 45, "name": name})[0], 200)
            self.assertIsNone(b.state()["syst"]["pad"])
            b.add({"event": "Undocked", "StationName": "Fabian City"}, grant)
            pad = b.wait(lambda: b.state()["syst"]["pad"], what="the pad granted")
            self.check_pad(pad, 45.0)
            self.assertEqual(b.post("/api/settlement-layout", {"key": self.LODGINGS, "layout": "tourist-3", "name": name})[0], 200)
            self.assertEqual(b.state()["syst"]["pad"], {"key": self.LODGINGS, "num": 2})   # another layout: its heading isn't known
            self.assertEqual(b.post("/api/settlement-layout", {"key": self.LODGINGS, "layout": "tourist-4", "name": name})[0], 200)
            self.check_pad(b.state()["syst"]["pad"], 45.0)
            b.add({"event": "Docked", "MarketID": 3814631936, "StationName": name, "StationType": "OnFootSettlement", "StarSystem": "HIP 20277"})
            b.wait(lambda: b.state()["syst"]["pad"] is None or None, what="the pad done with once docked")
            b.add({"event": "Undocked", "StationName": name}, grant)
            b.wait(lambda: b.state()["syst"]["pad"], what="granted again")
            b.add({"event": "SupercruiseEntry", "StarSystem": "HIP 20277"})
            b.wait(lambda: b.state()["syst"]["pad"] is None or None, what="the pad forgotten in supercruise")

    def test_construction_sites(self):
        """A construction site goes by its own name (its kind after); a planetary one has schematics, starting
        on the type its name points to where its economy ("Colony") has none."""
        m = load_script()
        raw = {"bodies": {"bodies": [{"name": "Testia 2", "bodyId": 2, "type": "Planet", "subType": "Rocky body", "isLandable": True,
                                      "distanceToArrival": 500, "radius": 2000}]},
               "stations": {"stations": [
                   {"name": "Planetary Construction Site: Qiao Hydroponics Range", "marketId": 4400000001, "type": "Planetary Outpost",
                    "economy": "Colony", "distanceToArrival": 500, "body": {"name": "Testia 2", "latitude": 10.0, "longitude": 20.0}},
                   {"name": "Orbital Construction Site: Wenn Ring", "marketId": 4400000002, "type": "Planetary Outpost",
                    "economy": "Colony", "distanceToArrival": 500, "body": {"name": "Testia 2"}}]}}
        model, _ = m.build_syst("Testia", raw, {})
        e = {x["label"]: x for x in model["entries"]}
        self.assertEqual(sorted(e), ["2 Rocky", "Qiao Hydroponics Range", "Wenn Ring"])
        site, ring = e["Qiao Hydroponics Range"], e["Wenn Ring"]
        self.assertTrue(site["lab"].startswith("Planetary construction site · Testia 2 surface"))
        self.assertEqual((site["name"], site["surface"], site["icon"]), ("Qiao Hydroponics Range", True, "construction"))
        self.assertEqual(site["settlement"], {"key": "m:4400000001", "economy": "Colony", "category": "colony", "guess": "agriculture"})
        self.assertTrue(ring["lab"].startswith("Orbital construction site"))
        self.assertNotIn("settlement", ring)   # in orbit: no settlement layouts
        self.assertEqual((m.settlement_guess("Miyamoto Military Bastion"), m.settlement_guess("Nakayama's Nursery"),
                          m.settlement_guess("Gutierrez Deposits"), m.settlement_guess("Somewhere")),
                         ("military", "agriculture", "extraction", ""))


class Records(unittest.TestCase):
    """Your journals' own records of systems (bodies, stations, where settlements are), kept for good and
    used wherever EDSM has nothing. All names here are made up."""

    SYS = "Test Sector AB-C d1-2"

    @classmethod
    def setUpClass(cls):
        cls.m = load_script()

    def visit(self, t):   # one visit: the star and a planet scanned, a settlement approached and docked at
        sys_ = {"StarSystem": self.SYS, "SystemAddress": 5551}
        return [
            dict(sys_, timestamp=ago(t), event="FSDJump", StarPos=[1.0, 2.0, 3.0], Body=self.SYS, BodyType="Star"),
            dict(sys_, timestamp=ago(t - 5), event="Scan", ScanType="AutoScan", BodyName=self.SYS, BodyID=0, StarType="K", Subclass=3,
                 StellarMass=0.7, Radius=520000000.0, Age_MY=4000, SurfaceTemperature=4400.0, Luminosity="Va", DistanceFromArrivalLS=0.0,
                 RotationPeriod=200000.0, AxialTilt=0.0, Rings=[{"Name": self.SYS + " A Belt", "RingClass": "eRingClass_Rocky",
                                                                  "MassMT": 1.0, "InnerRad": 1e9, "OuterRad": 2e9}]),
            dict(sys_, timestamp=ago(t - 6), event="Scan", ScanType="AutoScan", BodyName=self.SYS + " 3", BodyID=3,
                 Parents=[{"Star": 0}], DistanceFromArrivalLS=1094.1, PlanetClass="Icy body", Landable=True, Radius=1800000.0,
                 SurfaceGravity=1.2, SurfaceTemperature=90.0, SurfacePressure=0.0, Atmosphere="", Volcanism="minor water magma volcanism",
                 TerraformState="", TidalLock=True, RotationPeriod=86400.0 * 3, OrbitalPeriod=86400.0 * 30,
                 Materials=[{"Name": "iron", "Percent": 18.5}, {"Name": "sulphur", "Percent": 20.1}]),
            dict(sys_, timestamp=ago(t - 7), event="FSSSignalDiscovered", SignalName="Nav Beacon", SignalType="NavBeacon"),
            dict(sys_, timestamp=ago(t - 7), event="FSSSignalDiscovered", SignalName="WIDE AWAKE X1Y-2Z3", SignalType="FleetCarrier", IsStation=True),
            dict(sys_, timestamp=ago(t - 8), event="ApproachSettlement", Name="Kessel Depot", MarketID=4300000001,
                 StationFaction={"Name": "Test Faction"}, StationGovernment_Localised="Corporate", StationAllegiance="Empire",
                 StationEconomy_Localised="Industrial", BodyName=self.SYS + " 3", BodyID=3, Latitude=-48.98, Longitude=-55.36),
            dict(sys_, timestamp=ago(t - 9), event="Docked", StationName="Kessel Depot", StationType="OnFootSettlement",
                 MarketID=4300000001, DistFromStarLS=1094.1, StationServices=["dock", "commodities", "refuel", "contacts"]),
        ]

    def test_reading_and_merging(self):
        m = self.m
        import tempfile
        from pathlib import Path
        star = m.body_from_scan(self.visit(100)[1])
        self.assertEqual((star["type"], star["subType"], star["spectralClass"], star["isMainStar"], star["isScoopable"]),
                         ("Star", "K (Yellow-Orange) Star", "K3", True, True))
        self.assertEqual(star["belts"], [{"name": self.SYS + " A Belt", "type": "Rocky"}])
        planet = m.body_from_scan(self.visit(100)[2])
        self.assertEqual((planet["subType"], planet["isLandable"], planet["radius"], round(planet["gravity"], 3), planet["rotationalPeriod"]),
                         ("Icy body", True, 1800.0, 0.122, 3.0))
        self.assertEqual(list(planet["materials"]), ["Sulphur", "Iron"])   # most first, as EDSM lists them
        self.assertEqual((planet["volcanismType"], planet["atmosphereType"]), ("Minor water magma volcanism", "No atmosphere"))
        recs = m.JournalRecords(Path(tempfile.mkdtemp()) / "records.sqlite")
        for ev in self.visit(100):
            recs.note(ev)
        # a station first seen as an FSS signal (by name) is folded into its market ID record later
        recs.note({"timestamp": ago(50), "event": "FSSSignalDiscovered", "SystemAddress": 5551, "SignalName": "Orrin Works",
                   "SignalType": "StationCoriolis", "IsStation": True})
        recs.note({"timestamp": ago(40), "event": "Docked", "StarSystem": self.SYS, "SystemAddress": 5551, "StationName": "Orrin Works",
                   "StationType": "Coriolis", "MarketID": 3200000002, "DistFromStarLS": 12.5})
        got = recs.for_system(self.SYS.lower())
        self.assertEqual(sorted(b["name"] for b in got["bodies"]), [self.SYS, self.SYS + " 3"])
        st = {s["name"]: s for s in got["stations"]}
        self.assertEqual(sorted(st), ["Kessel Depot", "Nav Beacon", "Orrin Works"])   # carriers move: not kept
        self.assertEqual((st["Kessel Depot"]["type"], st["Kessel Depot"]["body"]["latitude"], st["Kessel Depot"]["haveMarket"]),
                         ("Odyssey Settlement", -48.98, True))
        self.assertEqual((st["Orrin Works"]["marketId"], st["Orrin Works"]["type"]), (3200000002, "Coriolis Starport"))
        # EDSM lists the settlement without its planet or position: the journal places it
        raw = {"stations": {"stations": [{"name": "Kessel Depot", "type": "Odyssey Settlement", "marketId": 4300000001, "body": None,
                                          "distanceToArrival": 1094.1}]}}
        model, index = m.build_syst(self.SYS, m.merge_records(raw, got), {})
        e = {x["name"]: x for x in model["entries"]}
        self.assertEqual((e["Kessel Depot"]["surface"], e["Kessel Depot"]["pic"]["lat"], e["Kessel Depot"]["icon"]), (True, -48.98, "settlement"))
        self.assertIn(["Position (your journal)", "-48.98, -55.36", True], e["Kessel Depot"]["rows"])
        self.assertEqual([s["name"] for s in e[self.SYS + " 3"]["pic"]["sites"]], ["Kessel Depot"])
        self.assertEqual((e[self.SYS]["icon"], e[self.SYS + " 3"]["icon"], e["Orrin Works"]["icon"], e["Nav Beacon"]["icon"]),
                         ("star", "landable", "coriolis", "beacon"))
        self.assertTrue(any(r[0] == "From your journal" for r in e["Orrin Works"]["rows"]))
        self.assertEqual((e["Kessel Depot"]["src"], e["Orrin Works"]["src"], e[self.SYS]["src"]), ("edsm+journal", "journal", "journal"))
        self.assertIn("Information updated", [r[0] for r in e["Kessel Depot"]["rows"]])   # EDSM's own dates for it
        # a settlement on a planet nobody lists still shows on it (a stand-in planet); a megaship seen long ago has moved on
        lone = {"stations": [{"name": "Far Post", "marketId": 9, "type": "Odyssey Settlement", "_journal": True, "_seen": ago(10),
                              "body": {"name": "Elsewhere 2", "latitude": 1.0, "longitude": 2.0}},
                             {"name": "Old Megaship", "type": "Mega ship", "_journal": True, "_seen": ago(30 * 86400)}], "bodies": []}
        model, _ = m.build_syst("Elsewhere", m.merge_records({}, lone), {})
        self.assertEqual([(x["name"], x["kind"]) for x in model["entries"]], [("Elsewhere 2", "planet"), ("Far Post", "station")])

    def test_settlement_of_no_known_type(self):
        """A surface station only your journal knows, from approaching it (no type): offered as a settlement, but
        unsure (it may be a planetary port or outpost); docking there gives its type and it's an ordinary one."""
        m = self.m
        import tempfile
        from pathlib import Path
        recs = m.JournalRecords(Path(tempfile.mkdtemp()) / "records.sqlite")
        visit = self.visit(100)
        for ev in visit[:-1]:   # approached, not docked
            recs.note(ev)
        model, _ = m.build_syst(self.SYS, m.merge_records({}, recs.for_system(self.SYS.lower())), {})
        e = {x["name"]: x for x in model["entries"]}
        self.assertEqual(e["Kessel Depot"]["settlement"], {"key": "m:4300000001", "economy": "Industrial", "category": "industrial",
                                                           "guess": "", "unsure": True})
        recs.note(visit[-1])   # docked: an Odyssey settlement
        model, _ = m.build_syst(self.SYS, m.merge_records({}, recs.for_system(self.SYS.lower())), {})
        e = {x["name"]: x for x in model["entries"]}
        self.assertNotIn("unsure", e["Kessel Depot"]["settlement"])
        # EDSM listing it (whatever it says) settles it too
        raw = {"stations": {"stations": [{"name": "Kessel Depot", "type": "Planetary Outpost", "marketId": 4300000001}]}}
        rec = {"stations": [s for s in recs.for_system(self.SYS.lower())["stations"] if s["name"] == "Kessel Depot"]}
        for s in rec["stations"]:
            s.pop("type", None)
        model, _ = m.build_syst(self.SYS, m.merge_records(raw, rec), {})
        e = {x["name"]: x for x in model["entries"]}
        self.assertNotIn("settlement", e["Kessel Depot"])

    def test_a_system_edsm_has_nothing_on(self):
        old = [{"timestamp": ago(40 * 86400), "event": "Fileheader", "part": 1}] + self.visit(40 * 86400 - 10)
        now = journals._start(600) + [{"timestamp": ago(500), "event": "FSDJump", "StarSystem": self.SYS, "SystemAddress": 5551,
                                       "StarPos": [1.0, 2.0, 3.0], "Body": self.SYS, "BodyType": "Star"}]
        # EDSM switched off, and the visit is in a journal older than the board reads (--days 2): only the records have it
        with Board("records", journal=[("Journal.2026-09-18T100000.01.log", old, 40 * 86400), ("Journal.2026-10-28T100000.01.log", now)],
                   edsm=(), no_edsm=True, ufc=False, extra_args=["--days", "2"]) as b:
            y = b.wait(lambda: (lambda y: y if y.get("source") == "journal" else None)(b.state()["syst"]), timeout=20, what="the system from the records")
            self.assertEqual(y["system"], self.SYS)
            got = [(x["name"], x["icon"]) for x in y["entries"]]
            self.assertEqual(got, [(self.SYS, "star"), (self.SYS + " 3", "landable"), ("Kessel Depot", "settlement"), ("Nav Beacon", "beacon")])
            self.assertEqual(y["entries"][1]["pic"]["sites"][0]["lat"], -48.98)
            self.assertIn("Journal records: read 2 journal files", b.log())
            self.assertTrue((b.dir / "journal_records.sqlite").exists())


class Latency(unittest.TestCase):
    """The page's delays that are the board's own: Status.json and the journal being written are read within a
    tenth of a second or so, and the event stream says so at once (state_n), so pages fetch the state then."""
    def test_status_and_journal_reach_the_event_stream_at_once(self):
        with Board("latency", **journals.syst()) as b:
            for i in range(3):
                n, lat = b.bus()["state_n"], round(-13.1 + 0.05 * (i + 1), 2)
                t0 = time.time()
                b.write_status(dict(journals.NEAR_HAO, Latitude=lat))
                b.wait(lambda: b.bus()["state_n"] > n, timeout=3, step=0.02, what="state_n to go up after Status.json changed")
                self.assertLess(time.time() - t0, 0.7, "Status.json took too long to reach the event stream")
                self.assertEqual((b.state()["syst"].get("me") or {}).get("lat"), lat)
            n, t0 = b.bus()["state_n"], time.time()
            b.add({"event": "Undocked", "StationName": "Fabian City"})   # a line in the journal being written
            b.wait(lambda: b.bus()["state_n"] > n, timeout=3, step=0.02, what="state_n to go up after a journal line")
            self.assertLess(time.time() - t0, 0.7, "the journal line took too long to reach the event stream")
            self.assertIsNone(b.state()["sit"]["docked"] or None)
            time.sleep(0.5)
            n = b.bus()["state_n"]
            time.sleep(0.6)
            self.assertEqual(b.bus()["state_n"], n, "nothing new, yet the pages were told to fetch again")


class Traj(unittest.TestCase):
    """What Nav > Traj needs: when each Status.json reading was written (and how long ago that was), what the altitude
    is measured from, glide, and the HUD target wherever you are; the UFC's keypad and NAV button reach the page."""
    def test_reading_target_and_ufc(self):
        with Board("traj", **journals.syst()) as b:
            b.add({"event": "Undocked", "StationName": "Fabian City"})
            b.write_status(dict(journals.NEAR_HAO, Destination={"Body": 12, "Name": "Hao Extraction Prospect"}))
            y = b.wait(lambda: (lambda y: y if y.get("target") else None)(b.state()["syst"]), what="the HUD target")
            names = {e["key"]: e["name"] for e in y["entries"]}
            self.assertEqual(names[y["target"]], "Hao Extraction Prospect")
            me = y["me"]
            self.assertGreater(me["t"], time.time() - 60)
            self.assertTrue(0 <= me["age"] < 5, me)
            self.assertEqual((me["avg"], me["glide"], me["sc"], me["landed"]), (False, False, False, False))
            (b.jdir / "Status.json").write_text("", encoding="utf-8")   # the game emptying it, an instant before it writes it
            time.sleep(0.6)
            self.assertIsNotNone(b.state()["syst"]["me"], "an empty Status.json is mid-write, not one with no position")
            b.write_status(dict(journals.NEAR_HAO, Flags=journals.NEAR_HAO["Flags"] | (1 << 29), Flags2=1 << 12, Altitude=15000))
            me = b.wait(lambda: (lambda m: m if m and m.get("glide") else None)(b.state()["syst"]["me"]), what="glide")
            self.assertTrue(me["avg"])   # high up: from the average radius
            self.assertEqual(me["alt"], 15000)
            self.assertIsNone(b.state()["syst"]["target"])
            # the UFC: NAV, the keypad's 2 - Traj; NAV again - round to Syst
            b.ufc_cmd("press ILS", "press Opt2")
            b.wait(lambda: (b.bus()["view"] or {}).get("tab") == "nav" or None, what="the UFC to pick Nav")
            b.ufc_cmd("press 2")
            b.wait(lambda: b.bus()["view"] == {"tab": "nav", "sub": 3} or None, what="Traj from the keypad")
            b.post("/api/select", {"tab": "nav", "sub": 3})   # as the page does when it follows
            # COMM1 on Traj: its clicks and pulls go straight to the page (not a list's cursor)
            u0 = b.bus()
            b.ufc_cmd("pulse COMM1_CW", "pulse COMM1_CW", "pulse COMM1_CCW", "press COMM1_PULL")
            b.wait(lambda: b.bus()["c1pull_n"] == u0["c1pull_n"] + 1 or None, what="the COMM1 pull")
            u = b.bus()
            self.assertEqual(u["knob1_pos"], u0["knob1_pos"] + 1)
            self.assertEqual(u["cursors"], u0["cursors"])
            for sub, what in ((4, "Wpt after Traj"), (5, "HSI after Wpt"), (6, "Atk after HSI"), (7, "Hist after Atk")):
                b.ufc_cmd("press Opt2")
                b.wait(lambda: b.bus()["view"] == {"tab": "nav", "sub": sub} or None, what=what)
                b.post("/api/select", {"tab": "nav", "sub": sub})
            b.ufc_cmd("press Opt2")
            b.wait(lambda: b.bus()["view"]["sub"] in (1, 2) or None, what="Syst after Hist")
            b.post("/api/select", {"tab": "nav", "sub": 1})
            b.ufc_cmd("pulse COMM1_CW", "press COMM1_PULL")   # elsewhere COMM1 is the list's again
            time.sleep(0.8)
            self.assertEqual((b.bus()["knob1_pos"], b.bus()["c1pull_n"]), (u["knob1_pos"], u["c1pull_n"]))


class Targets(unittest.TestCase):
    """2 Nav > Wpt: your own waypoints on a body's surface - kept for good, numbered within their system, listed in
    Syst under their body (and on its picture); the body your HUD target is on; the keypad typing on the page."""

    def test_targets(self):
        j = journals.syst()
        with Board("targets", journal=j["journal"], status=j["status"]) as b:
            y = b.state()["syst"]
            planet = next(e for e in y["entries"] if e["kind"] == "planet")
            star = next(e for e in y["entries"] if e["kind"] == "star")
            short = planet["name"][len(y["system"]) + 1:] if planet["name"].lower().startswith(y["system"].lower() + " ") else planet["name"]
            add = lambda **kw: b.post("/api/tgt", dict({"op": "add", "body": planet["name"], "lat": 26.970711, "lon": -59.741985, "method": "overfly"}, **kw))
            code, got = add()
            self.assertEqual(code, 200)
            t1 = got["tgt"]
            self.assertEqual((t1["name"], t1["num"], t1["lat"], t1["lon"], t1["method"]), (f"WPT 1 - {short}", 1, 26.970711, -59.741985, "overfly"))
            for bad, why in (({"body": star["name"]}, "body"), ({"body": "Nowhere 1"}, "body"), ({"lat": 91}, "position"),
                             ({"lon": -180.5}, "position"), ({"lat": "26"}, "position"), ({"method": "magic"}, "position")):
                self.assertEqual(add(**bad), (400, {"ok": False, "why": why}), bad)
            code, got = add(lat=-5.5, lon=120.25, method="manual")
            self.assertEqual(got["tgt"]["name"], f"WPT 2 - {short}")
            # named (tidied), or not (a control character); edited (a blank name: the usual one again); HUD desig
            self.assertEqual(add(name="bad\x07name"), (400, {"ok": False, "why": "name"}))
            code, named = add(name="  Crash   site ", method="desig")
            self.assertEqual((code, named["tgt"]["name"], named["tgt"]["num"], named["tgt"]["method"]), (200, "Crash site", 3, "desig"))
            code, ed = b.post("/api/tgt", {"op": "edit", "id": named["tgt"]["id"], "name": "Wreck", "lat": 1.5, "lon": -2.25})
            self.assertEqual((code, ed["tgt"]["name"], ed["tgt"]["lat"], ed["tgt"]["lon"]), (200, "Wreck", 1.5, -2.25))
            code, ed = b.post("/api/tgt", {"op": "edit", "id": named["tgt"]["id"], "name": "", "lat": 1.5, "lon": -2.25})
            self.assertEqual(ed["tgt"]["name"], f"WPT 3 - {short}")
            self.assertEqual(b.post("/api/tgt", {"op": "edit", "id": named["tgt"]["id"], "name": "x", "lat": 95, "lon": 0}), (400, {"ok": False, "why": "position"}))
            self.assertEqual(b.post("/api/tgt", {"op": "delete", "id": named["tgt"]["id"]}), (200, {"ok": True}))
            # in Syst: under the body (after its stations), a surface site with a position; on the body's picture
            y = b.wait(lambda: (lambda y: y if len(y.get("tgts") or []) == 2 else None)(b.state()["syst"]), what="the targets in the state")
            keys = [e["key"] for e in y["entries"]]
            i = keys.index(planet["key"])
            rows = [e for e in y["entries"] if e["kind"] == "tgt"]
            self.assertEqual([e["key"] for e in rows], [t1["key"], got["tgt"]["key"]])
            self.assertEqual(rows[0]["pic"], {"kind": "surface", "body": planet["name"], "lat": 26.970711, "lon": -59.741985})
            self.assertEqual(rows[0]["depth"], planet["depth"] + 1)
            between = y["entries"][i + 1:keys.index(t1["key"])]
            self.assertTrue(all(e["kind"] == "station" and e["body"] == planet["name"] for e in between), "only the body's own stations before them")
            body = y["entries"][i]
            self.assertEqual([t["key"] for t in body["pic"]["tgts"]], [t1["key"], got["tgt"]["key"]])
            # kept for good; deleting one, the next number is the next free one
            b.restart()
            y = b.wait(lambda: (lambda y: y if y.get("tgts") else None)(b.state()["syst"]), what="the targets after a restart")
            self.assertEqual([t["name"] for t in y["tgts"]], [f"WPT 1 - {short}", f"WPT 2 - {short}"])
            self.assertEqual(b.post("/api/tgt", {"op": "delete", "id": got["tgt"]["id"]}), (200, {"ok": True}))
            self.assertEqual(b.post("/api/tgt", {"op": "delete", "id": got["tgt"]["id"]})[0], 400)
            self.assertEqual(add()[1]["tgt"]["name"], f"WPT 2 - {short}")
            # the body your HUD target is on (a mission's crash site has no position, only its body)
            b.write_status(dict(j["status"], Destination={"System": y["id64"], "Body": planet["bodyId"],
                                                          "Name": "$POIScenario_Watson_Wrecks_Sidewinder_01_Salvage_Easy; $USS_ThreatLevel:#threatLevel=1;",
                                                          "Name_Localised": "Crash Site [Threat&NBSP;1]"}))
            y = b.wait(lambda: (lambda y: y if y.get("target_body") else None)(b.state()["syst"]), what="the HUD target's body")
            self.assertEqual((y["target_body"], y["target_name"], y["target"]), (planet["key"], "Crash Site [Threat 1]", None))

    def test_keypad_to_the_page(self):
        """While a page says it's typing (on a page that does: Wpt), the keypad's keys go to it - not the sub-tabs -
        and the scratchpad shows what it's typed; otherwise the digits pick sub-tabs as ever."""
        j = journals.syst()
        with Board("keypad", journal=j["journal"], status=j["status"]) as b:
            b.ufc_cmd("press ILS", "press Opt2", "press 3")
            b.wait(lambda: b.bus()["view"] == {"tab": "nav", "sub": 4} or None, what="Wpt from the keypad")
            b.post("/api/select", {"tab": "nav", "sub": 4})
            self.assertEqual(b.post("/api/keypad", {"page": "harness", "on": True, "s1": "N", "num": "26.9"})[0], 200)
            b.wait(lambda: (lambda d: d if d["scratch"] == "26.9" and d["s1"] == "N" else None)(b.display()), what="the scratchpad")
            n = b.bus()["key_n"]
            b.ufc_cmd("press 7", "press 1", "press Clr", "press Ent")
            b.wait(lambda: b.bus()["key_n"] == n + 4 or None, what="the keys")
            self.assertEqual([k for _, k in b.bus()["keys"][-4:]], ["7", "1", "Clr", "Ent"])
            self.assertEqual(b.bus()["view"], {"tab": "nav", "sub": 4}, "typing doesn't change the sub-tab")
            b.post("/api/keypad", {"page": "harness", "on": False})
            b.ufc_cmd("press 4")
            b.wait(lambda: b.bus()["view"] == {"tab": "nav", "sub": 5} or None, what="the keypad back on the sub-tabs (HSI)")
            self.assertEqual(b.bus()["key_n"], n + 4)


    def test_timer(self):
        """The HSI's timer (the T-6A's clock), kept by the board and pushed to every page with the board's clock: SEL the
        stopwatch or the countdown (not while it runs - past zero: the alarm seen), CTL start / reset (a countdown with no
        time: asked for one), SET a countdown's time, CLR none; a UFC press's op done once, however many pages send it.
        On the HSI the keypad's ENT and CLR go to the page; its digits only while it says it's typing."""
        j = journals.syst()
        with Board("timer", journal=j["journal"], status=j["status"]) as b:
            op = lambda **body: b.post("/api/timer", body)[1]
            u = b.bus()
            self.assertEqual(u["timer"], {"mode": "et", "run": False, "t0": None, "cd": None, "ack": False})
            self.assertAlmostEqual(u["t"], time.time(), delta=2, msg="the board's clock, with the push")
            a = op(op="ctl", u="c1.7.0")
            self.assertEqual((a["ok"], a["did"], a["timer"]["run"]), (True, "start", True))
            again = op(op="ctl", u="c1.7.0")   # (the other page, answering the same pull)
            self.assertEqual((again["did"], again["timer"]["run"]), ("already", True))
            self.assertTrue(b.bus()["timer"]["run"], "started once - not started and reset")
            self.assertEqual(op(op="sel")["why"], "running")
            self.assertEqual(op(op="ctl")["did"], "reset")
            self.assertEqual(b.bus()["timer"], {"mode": "et", "run": False, "t0": None, "cd": None, "ack": False})
            self.assertEqual(op(op="sel")["timer"]["mode"], "cd")
            self.assertEqual(op(op="ctl")["why"], "set")
            self.assertEqual(b.post("/api/timer", {"op": "set", "cd": 0})[0], 400)
            self.assertEqual(b.post("/api/timer", {"op": "set", "cd": 99 * 3600 + 3600})[0], 400)
            self.assertEqual(op(op="set", cd=2)["timer"], {"mode": "cd", "run": False, "t0": None, "cd": 2, "ack": False})
            t = op(op="ctl")["timer"]
            self.assertTrue(t["run"] and abs(t["t0"] - time.time()) < 2)
            self.assertEqual(op(op="sel")["why"], "running", "counting down: SEL doesn't change it")
            time.sleep(2.3)
            a = op(op="sel")   # past zero: SEL - the alarm seen, still counting up
            self.assertEqual((a["did"], a["timer"]["ack"], a["timer"]["run"]), ("ack", True, True))
            a = op(op="ctl")
            self.assertEqual((a["did"], a["timer"]["run"], a["timer"]["cd"]), ("reset", False, None))
            op(op="set", cd=90)
            self.assertIsNone(op(op="clr")["timer"]["cd"])
            # the keypad on the HSI: ENT and CLR to the page; the digits pick sub-tabs unless it says it's typing
            b.ufc_cmd("press ILS", "press Opt2", "press 4")
            b.wait(lambda: b.bus()["view"] == {"tab": "nav", "sub": 5} or None, what="the HSI")
            b.post("/api/select", {"tab": "nav", "sub": 5})
            k = b.bus()["key_n"]
            b.ufc_cmd("press Ent", "press Clr")
            b.wait(lambda: b.bus()["key_n"] == k + 2 or None, what="ENT and CLR to the HSI")
            b.post("/api/keypad", {"page": "harness", "on": True, "s1": "CD", "num": "00:01"})
            b.wait(lambda: (lambda d: d if (d["s1"], d["scratch"]) == ("CD", "00:01") else None)(b.display()), what="the countdown being typed")
            b.ufc_cmd("press 3")
            b.wait(lambda: b.bus()["key_n"] == k + 3 or None, what="a digit, to the page")
            self.assertEqual(b.bus()["view"], {"tab": "nav", "sub": 5})
            b.post("/api/keypad", {"page": "harness", "on": False})

    def test_scratchpad_from_atk(self):
        """Atk's countdown on the scratchpad while Atk shows (page menu) - not on another page."""
        j = journals.syst()
        with Board("scratch", journal=j["journal"], status=j["status"]) as b:
            b.ufc_cmd("press ILS", "press Opt2", "press 5")
            b.wait(lambda: b.bus()["view"] == {"tab": "nav", "sub": 6} or None, what="Atk from the keypad")
            b.post("/api/select", {"tab": "nav", "sub": 6})
            self.assertEqual(b.post("/api/scratch", {"page": "harness", "s1": "RL", "num": "12.4"})[0], 200)
            b.wait(lambda: (lambda d: d if (d["s1"], d["scratch"]) == ("RL", "12.4") else None)(b.display()), what="the countdown")
            b.post("/api/scratch", {"page": "harness", "num": "RELEASE"})
            b.wait(lambda: b.display()["scratch"] == "RELEASE" or None, what="RELEASE")
            b.ufc_cmd("press 2")   # Traj: not Atk's to show
            b.wait(lambda: b.bus()["view"] == {"tab": "nav", "sub": 3} or None, what="Traj")
            b.post("/api/select", {"tab": "nav", "sub": 3})
            b.wait(lambda: b.display()["scratch"] == "" or None, what="the scratchpad its own again")


class Nav(unittest.TestCase):
    """2 Nav's waypoint system (NavBoard): marks MK1-MK9 rolling round, the SEQ 1-3 flight plans (one body each, a waypoint
    once each), the steer-to point and AUTO sequencing, designation (a waypoint, then its offset aimpoint, then nothing; a
    mark; a site in 1 Syst), Atk's attack plan built round the target (the card's geometry, heights and calls) and its plan
    code (a wingman loading it flies the other role), all kept for good; the UFC's DSG and MK, and the pages' sub-levels."""
    PLANET = "HIP 20277 3 b"

    def nav(self, b):
        return b.state()["syst"]["nav"]

    def test_cross_bearings(self):
        """HUD X-B's bearings: kept by the board, on the body they're taken on (one on another body starts again), up to 10
        (an 11th: the oldest goes); each deleted, or all cleared; a UFC press's taken once; its mark (method xb) as any."""
        j = journals.syst()
        with Board("nav_xb", journal=j["journal"], status=j["status"]) as b:
            nav = lambda **kw: b.post("/api/nav", kw)
            take = lambda i, **kw: nav(**dict({"op": "xb", "act": "take", "body": self.PLANET, "lat": -13.3 + i * 0.01, "lon": 34.7, "brg": 160 + i}, **kw))
            self.assertEqual(self.nav(b)["xb"], {"body": "", "list": [], "max": 10})
            self.assertEqual(take(0, body="Nowhere")[0], 400)
            self.assertEqual(take(0, brg="160")[0], 400)
            self.assertEqual(take(0, lat=95)[0], 400)
            code, a = take(0, u="c2.3.0")
            self.assertEqual((code, a["id"], a["fresh"], a["dropped"]), (200, 1, False, 0))
            self.assertEqual(take(0, u="c2.3.0")[1]["did"], "already")   # (the other page, answering the same pull)
            self.assertEqual(len(self.nav(b)["xb"]["list"]), 1, "taken once")
            for i in range(1, 11):
                code, a = take(i)
            self.assertEqual(a["dropped"], 1)
            xb = self.nav(b)["xb"]
            self.assertEqual((xb["body"], [x["id"] for x in xb["list"]]), (self.PLANET, list(range(2, 12))), "10 kept: the oldest gone")
            self.assertEqual(xb["list"][0], {"id": 2, "lat": -13.29, "lon": 34.7, "brg": 161, "saved": xb["list"][0]["saved"]})
            self.assertEqual(nav(op="xb", act="del", id=5)[0], 200)
            self.assertEqual(nav(op="xb", act="del", id=5)[0], 400)
            self.assertNotIn(5, [x["id"] for x in self.nav(b)["xb"]["list"]])
            code, a = take(0, body="HIP 20277 3")   # another body: a fresh set
            self.assertTrue(a["fresh"])
            xb = self.nav(b)["xb"]
            self.assertEqual((xb["body"], [x["id"] for x in xb["list"]]), ("HIP 20277 3", [12]))
            self.assertEqual(nav(op="xb", act="clr")[0], 200)
            self.assertEqual(self.nav(b)["xb"]["list"], [])
            self.assertEqual(nav(op="xb", act="nope")[0], 400)
            code, a = nav(op="mark", body=self.PLANET, lat=-13.4, lon=34.73, method="xb", dsg=True)
            self.assertEqual((code, self.nav(b)["marks"][0]["method"], self.nav(b)["tgt"]["key"]), (200, "xb", a["mark"]["key"]))
            code, a = nav(op="mkstor", slot=1)
            self.assertEqual((code, a["tgt"]["method"]), (200, "xb"))

    def test_marks_plans_and_designation(self):
        j = journals.syst()
        with Board("nav", journal=j["journal"], status=j["status"]) as b:
            add = lambda **kw: b.post("/api/tgt", dict({"op": "add", "body": self.PLANET, "lat": -13.1, "lon": 34.9, "method": "manual"}, **kw))[1]["tgt"]
            w1, w2, w3 = add(), add(lat=-13.0, lon=35.0), add(lat=-12.9, lon=35.1)
            other = add(body="HIP 20277 3", lat=1.0, lon=2.0)
            nav = lambda **kw: b.post("/api/nav", kw)
            # marks: MK1-MK9, then round to MK1 again
            for i in range(10):
                code, got = nav(op="mark", body=self.PLANET, lat=round(-13.0 + i * 0.01, 4), lon=35.0, alt=500, method="overfly")
                self.assertEqual((code, got["mark"]["name"]), (200, f"MK{i % 9 + 1}"))
            n = self.nav(b)
            self.assertEqual(([m["slot"] for m in n["marks"]], n["next"]), (list(range(1, 10)), 2))
            self.assertEqual(n["marks"][0]["lat"], -12.91)   # MK1: the tenth mark, over the first
            for bad, why in (({"body": "HIP 20277 1 x"}, "body"), ({"lat": 91}, "position"), ({"method": "x"}, "method")):
                self.assertEqual(nav(**dict({"op": "mark", "body": self.PLANET, "lat": 1, "lon": 1, "method": "overfly"}, **bad)), (400, {"ok": False, "why": why}))
            self.assertEqual(nav(op="mkedit", slot=2, lat=-13.5, lon=35.5)[0], 200)
            code, st = nav(op="mkstor", slot=2)   # a mark kept as a waypoint
            self.assertEqual((code, st["tgt"]["lat"], st["tgt"]["lon"], st["tgt"]["method"], st["tgt"]["num"]), (200, -13.5, 35.5, "overfly", 5))
            self.assertEqual(nav(op="mkdel", slot=2)[0], 200)
            self.assertNotIn(2, [m["slot"] for m in self.nav(b)["marks"]])
            # SEQ 1: in order, INS after one, once each, on one body
            ins = lambda w, s=1, **kw: nav(op="seq", seq=s, act="ins", id=w["id"], **kw)
            self.assertEqual(ins(w1)[1]["seq"], [w1["key"]])
            self.assertEqual(ins(w3)[1]["seq"], [w1["key"], w3["key"]])
            self.assertEqual(ins(w2, after=w1["id"])[1]["seq"], [w1["key"], w2["key"], w3["key"]])
            self.assertEqual(ins(w2), (400, {"ok": False, "why": "already in it"}))
            self.assertEqual(ins(other), (400, {"ok": False, "why": "another body"}))
            self.assertEqual(ins(other, s=2)[0], 200)
            self.assertEqual(ins(w2, s=3)[0], 200)
            self.assertEqual(ins(w3, s=3, after=0)[1]["seq"], [w3["key"], w2["key"]])   # (after 0: at the start)
            self.assertEqual(nav(op="seq", seq=3, act="del", id=w3["id"])[1]["seq"], [w2["key"]])
            self.assertEqual(nav(op="seq", seq=3, act="clr")[1]["seq"], [])
            self.assertEqual(nav(op="seq", seq=4, act="clr")[0], 400)
            # the steer-to point: the flight plan's first; AUTO steps it on from the one you've reached (not from another)
            self.assertEqual(nav(op="setseq", seq="1")[0], 200)
            n = self.nav(b)
            self.assertEqual((n["seq"], n["steer"], n["auto"]), ("1", w1["key"], True))
            self.assertEqual(nav(op="auto", **{"from": w2["key"]})[1]["did"], "nothing")
            self.assertEqual(nav(op="auto", **{"from": w1["key"]})[1]["steer"], w2["key"])
            nav(op="automode", on=False)
            self.assertEqual(nav(op="auto", **{"from": w2["key"]})[1]["did"], "nothing")
            nav(op="automode", on=True)
            self.assertEqual(nav(op="steer", key="mk3")[0], 200)
            self.assertEqual(nav(op="steer", key="t999"), (400, {"ok": False, "why": "point"}))
            self.assertEqual(nav(op="setseq", seq="atk"), (200, {"ok": True}))   # (nothing built: no point to steer to in it)
            nav(op="setseq", seq="1")
            # deleting a waypoint takes it out of its flight plans
            b.post("/api/tgt", {"op": "delete", "id": w2["id"]})
            self.assertEqual(self.nav(b)["seqs"]["1"], [w1["key"], w3["key"]])
            # designation: a waypoint; again: its offset aimpoint (450 m due east of it); again: nothing
            self.assertEqual(nav(op="oap", id=w1["id"], rng=450, brg=90)[0], 200)
            self.assertEqual(nav(op="oap", id=w1["id"], rng=450, brg=None)[0], 400)
            o = self.nav(b)["oaps"][w1["key"] + "o"]
            self.assertAlmostEqual(o["lat"], -13.1, places=4)
            self.assertGreater(o["lon"], 34.9)
            self.assertEqual([nav(op="dsg", key=w1["key"])[1]["tgt"] for _ in range(3)], [w1["key"], w1["key"] + "o", None])
            self.assertEqual(nav(op="dsg", key="mk3")[1]["tgt"], "mk3")
            t = self.nav(b)["tgt"]
            self.assertEqual((t["key"], t["src"], t["label"]), ("mk3", "mk", "MK3"))
            nav(op="mkedit", slot=3, lat=-14.0, lon=36.0)
            self.assertEqual(self.nav(b)["tgt"]["lat"], -14.0, "the target follows its mark")
            y = b.state()["syst"]
            hao = next(e for e in y["entries"] if e["name"] == "Hao Extraction Prospect")
            star = next(e for e in y["entries"] if e["kind"] == "star")
            self.assertEqual(nav(op="dsg", key=hao["key"])[1]["tgt"], hao["key"])   # a site in 1 Syst
            self.assertEqual((self.nav(b)["tgt"]["name"], self.nav(b)["tgt"]["src"]), ("Hao Extraction Prospect", "site"))
            self.assertEqual(nav(op="dsg", key=star["key"])[0], 400)
            self.assertEqual(nav(op="dsg", key="atk:1:IP")[0], 400)
            # the UFC's DSG answered by two pages: acted on once
            self.assertEqual(nav(op="dsg", key=w3["key"], n=7)[1]["tgt"], w3["key"])
            self.assertEqual(nav(op="dsg", key=w3["key"], n=7)[1]["did"], "already")
            self.assertEqual(self.nav(b)["tgt"]["key"], w3["key"])
            # kept for good
            b.restart()
            n = b.wait(lambda: (lambda y: y["nav"] if (y.get("nav") or {}).get("marks") else None)(b.state()["syst"]), what="the nav state after a restart")
            self.assertEqual((n["seqs"]["1"], n["tgt"]["key"], len(n["marks"]), list(n["oaps"])), ([w1["key"], w3["key"]], w3["key"], 8, [w1["key"] + "o"]))

    def test_attack_plan_and_code(self):
        j = journals.syst()
        with Board("nav_atk", journal=j["journal"], status=j["status"]) as b:
            nav = lambda **kw: b.post("/api/nav", kw)
            self.assertEqual(nav(op="build"), (400, {"ok": False, "why": "no target - designate one"}))
            w = b.post("/api/tgt", {"op": "add", "body": self.PLANET, "lat": -13.1, "lon": 34.9, "method": "manual"})[1]["tgt"]
            nav(op="dsg", key=w["key"])
            self.assertEqual(nav(op="build"), (400, {"ok": False, "why": "set ATK HDG (AUTO needs you on the target's body)"}))
            for bad in ({"hdg": 400}, {"kts": 10}, {"role": 3}, {"cs": "w k"}, {"profile": "x"}, {"base": -1}):
                self.assertEqual(nav(op="plan", **bad)[0], 400, bad)
            self.assertEqual(nav(op="plan", hdg=0, kts=480, base=300, step=300, role=1, cs="wk5")[0], 200)
            self.assertEqual(nav(op="build"), (200, {"ok": True, "hdg": 0}))
            n = self.nav(b)
            built = n["built"]
            self.assertEqual((n["seq"], n["steer"], n["seqs"]["atk"][0]), ("atk", "atk:1:START", "atk:1:START"))
            self.assertEqual([p["id"] for p in built["roles"]["1"]], ["START", "IP", "OFFSET", "IN", "TGT", "OFF", "EGRESS", "EXIT"])
            self.assertEqual([p["id"] for p in built["roles"]["2"]], ["START", "SPLIT", "TURN", "JOIN", "IN", "TGT", "OFF", "EXIT"])
            p1, p2 = ({p["id"]: p for p in built["roles"][r]} for r in ("1", "2"))
            # ATK HDG 000: the IP 10 NM south of the target, START 20 NM; #1 pops in from the south and comes off north, #2 from
            # the east and off west - the calls the card makes
            self.assertEqual((p1["IP"]["e"], p1["IP"]["n"], p1["START"]["n"]), (0.0, -18520.0, -37040.0))
            self.assertEqual((p1["IN"]["call"], p1["OFF"]["call"]), ("WK51, IN SOUTH", "WK51, OFF NORTH"))
            self.assertEqual((p2["IN"]["call"], p2["OFF"]["call"]), ("WK52, IN EAST", "WK52, OFF WEST, VISUAL/BLIND"))
            self.assertEqual((p1["IP"]["hdg"], p2["IN"]["hdg"], p2["SPLIT"]["hdg"]), (0.0, 270.0, 90.0))
            # heights: #1 attacks at BASE and comes off at Base+1, #2 the other way round
            self.assertEqual((p1["IP"]["alt"], p1["IN"]["alt"], p1["OFF"]["alt"], p2["IN"]["alt"], p2["OFF"]["alt"]), (300, 300, 600, 600, 300))
            # #2 runs 18 s past #1's track (and the 1.5 NM to it) at 480 KTAS; over the target 30-45 s after #1
            self.assertAlmostEqual(p2["SPLIT"]["secs"], 3.9 * 7.5, delta=0.2)
            self.assertTrue(30 < built["tot"]["2"] - built["tot"]["1"] < 45, built["tot"])
            # the points on the body: the IP 18.5 km due south of the target
            r = next(e for e in b.state()["syst"]["entries"] if e["name"] == self.PLANET)["radius"] * 1000
            dlat = math.radians(p1["IP"]["lat"] - w["lat"])
            self.assertAlmostEqual(abs(dlat) * r, 18520, delta=2)
            self.assertAlmostEqual(p1["IP"]["lon"], w["lon"], places=5)
            # twice the speed: twice the distances, the same times
            nav(op="plan", kts=960)
            nav(op="build")
            b2 = self.nav(b)["built"]
            self.assertEqual({p["id"]: p for p in b2["roles"]["1"]}["IP"]["n"], -37040.0)
            self.assertEqual(b2["tot"], built["tot"])
            # the plan code: a wingman loading it flies #2, round the same target
            code = b2["code"]
            self.assertTrue(code.startswith("FT1/HIP 20277 3 b/-13.10000/34.90000/000/960/300/300/POP2/WK51/"), code)
            self.assertEqual(nav(op="load", code=code.replace("/000/", "/001/"))[1]["why"], "check failed - mistyped?")
            self.assertEqual(nav(op="load", code="hello")[1]["why"], "not a plan code")
            nav(op="dsg", off=True)
            self.assertEqual(nav(op="load", code=code.lower())[0], 200)   # (any case)
            n = self.nav(b)
            self.assertEqual((n["plan"]["role"], n["tgt"]["src"], n["tgt"]["lat"], n["steer"], n["plan"]["kts"]), (2, "plan", -13.1, "atk:2:START", 960))
            self.assertTrue(n["built"]["code"].endswith(n["built"]["code"][-4:]) and "/WK52/" in n["built"]["code"])
            # from the clipboard (the copy button puts it there)
            self.assertEqual(b.post("/api/clip", {"text": code})[0], 200)
            self.assertEqual(nav(op="load", clip=True)[0], 200)
            # the other role: the steer-to point follows to its point of the same name
            nav(op="steer", key="atk:2:IN")
            nav(op="plan", role=1)
            self.assertEqual(self.nav(b)["steer"], "atk:1:IN")
            # AUTO: the bearing you have to the target when you build (here: from the north-west), kept as the plan's
            nav(op="dsg", key=w["key"])
            nav(op="plan", hdg=None)
            b.write_status(dict(journals.NEAR_HAO, Latitude=-13.0, Longitude=34.8))
            b.wait(lambda: (b.state()["syst"].get("me") or {}).get("lat") == -13.0 or None, what="the position")
            code, got = nav(op="build")
            self.assertEqual(code, 200)
            self.assertTrue(130 < got["hdg"] < 140, got)
            self.assertEqual(self.nav(b)["plan"]["hdg"], got["hdg"])

    def test_points_gone_tokens_and_steps(self):
        """A target or steer-to point on a mark, or on an offset aimpoint, goes with it (a mark's slot reused, deleted; the
        offset cleared); a UFC press that two pages answer is acted on once, both given the same answer (its token, u);
        the HSI's arrows step the steer-to point on the board; a plan code's figures must be within the plan's limits."""
        j = journals.syst()
        with Board("nav_review", journal=j["journal"], status=j["status"]) as b:
            nav = lambda **kw: b.post("/api/nav", kw)
            add = lambda **kw: b.post("/api/tgt", dict({"op": "add", "body": self.PLANET, "lat": -13.1, "lon": 34.9, "method": "manual"}, **kw))
            w1, w2 = add()[1]["tgt"], add(lat=-13.0)[1]["tgt"]
            mark = lambda **kw: nav(**dict({"op": "mark", "body": self.PLANET, "lat": -13.05, "lon": 35.0, "method": "overfly"}, **kw))
            for _ in range(9):
                mark()
            # MK1 designated and steered to; MK1's slot reused by the tenth mark: neither follows it to the new mark
            nav(op="dsg", key="mk1")
            nav(op="steer", key="mk1")
            mark()
            n = self.nav(b)
            self.assertEqual((n["tgt"], n["steer"]), (None, None))
            # ...unless the new mark is designated as it's made (DESIG)
            nav(op="dsg", key="mk2")
            self.assertEqual(mark(dsg=True)[1]["mark"]["name"], "MK2")
            self.assertEqual(self.nav(b)["tgt"]["key"], "mk2")
            # a mark deleted: the target on it goes
            nav(op="steer", key="mk2")
            nav(op="mkdel", slot=2)
            n = self.nav(b)
            self.assertEqual((n["tgt"], n["steer"]), (None, None))
            # an offset aimpoint cleared: the target on it goes (the waypoint itself not designated)
            nav(op="oap", id=w1["id"], rng=300, brg=0)
            nav(op="dsg", key=w1["key"])
            self.assertEqual(nav(op="dsg", key=w1["key"])[1]["tgt"], w1["key"] + "o")
            nav(op="oap", id=w1["id"], rng=0)
            self.assertIsNone(self.nav(b)["tgt"])
            # the HSI's COMM2: none activated (SEQ NONE, at first) - all the waypoints, then the marks; round again
            self.assertEqual(self.nav(b)["seq"], "none")
            marks = [m["key"] for m in self.nav(b)["marks"]]
            order = [w1["key"], w2["key"]] + marks
            nav(op="steer", key=w1["key"])
            got = [nav(op="steer", step=1)[1]["steer"] for _ in range(len(order))]
            self.assertEqual(got, order[1:] + order[:1])
            self.assertEqual(nav(op="steer", step=-2)[1]["steer"], order[-2])
            nav(op="steer", key=None)
            self.assertEqual(nav(op="steer", step=-1)[1]["steer"], marks[-1])   # (from nothing: back from the start)
            self.assertEqual(nav(op="steer", step=0)[0], 400)
            # ... a flight plan activated: its points only (SEQ 1: WP2, WP1), round again
            nav(op="seq", seq=1, act="ins", id=w2["id"])
            nav(op="seq", seq=1, act="ins", id=w1["id"])
            nav(op="setseq", seq="1")
            self.assertEqual(self.nav(b)["steer"], w2["key"])
            self.assertEqual([nav(op="steer", step=1)[1]["steer"] for _ in range(3)], [w1["key"], w2["key"], w1["key"]])
            self.assertEqual(nav(op="steer", step=-3)[1]["steer"], w2["key"])
            nav(op="steer", key=marks[0])   # (off the plan - a click on it: on to the plan's first)
            self.assertEqual(nav(op="steer", step=1)[1]["steer"], w2["key"])
            # ... NONE again: the steer-to point stays; stepping goes through all of them again
            self.assertEqual(nav(op="setseq", seq="none"), (200, {"ok": True}))
            n = self.nav(b)
            self.assertEqual((n["seq"], n["steer"]), ("none", w2["key"]))
            self.assertEqual(nav(op="steer", step=1)[1]["steer"], marks[0])
            nav(op="setseq", seq="1")
            # a UFC press answered by two pages: acted on once, the second page given the first's answer
            before = len(self.nav(b)["marks"])
            first = nav(op="steer", step=1, u="k1.7.0")[1]
            again = nav(op="steer", step=1, u="k1.7.0")[1]
            self.assertEqual((again["steer"], again["did"]), (first["steer"], "already"))
            self.assertEqual(self.nav(b)["steer"], first["steer"])
            self.assertEqual(nav(op="steer", step=1, u="k1.8.0")[1]["steer"] != first["steer"], True)   # (the next click)
            a1, a2 = add(lat=-12.5, u="c2.4.0"), add(lat=-12.5, u="c2.4.0")
            self.assertEqual((a1[0], a2[0], a2[1]["tgt"], a2[1]["did"]), (200, 200, a1[1]["tgt"], "already"))
            self.assertEqual(len(b.state()["syst"]["tgts"]), 3, "one waypoint for the one press")
            self.assertEqual(add(lat=-12.4)[0], 200)   # (no token - a click: as ever)
            self.assertEqual(add(lat=-12.4)[0], 200)
            self.assertEqual(len(b.state()["syst"]["tgts"]), 5)
            self.assertEqual(len(self.nav(b)["marks"]), before)
            # a failed press isn't kept: answered again, it's acted on
            self.assertEqual(nav(op="mark", body="nowhere", lat=1, lon=1, method="overfly", u="c2.9.0")[0], 400)
            self.assertEqual(mark(u="c2.9.0")[0], 200)
            # a plan code with figures outside the plan's limits (its check right): refused
            import zlib
            for kts, base, step in ((5000, 300, 300), (480, 30000, 300), (480, 300, 9000), (10, 300, 300)):
                head = f"FT1/{self.PLANET}/-13.10000/34.90000/090/{kts}/{base}/{step}/POP2/WK51"
                code = f"{head}/{zlib.crc32(head.upper().encode('utf-8')) & 0xFFFF:04X}"
                self.assertEqual(nav(op="load", code=code), (400, {"ok": False, "why": "not a plan this board knows"}), code)
            head = f"FT1/{self.PLANET}/-13.10000/34.90000/090/480/300/300/POP2/WK51"
            self.assertEqual(nav(op="load", code=f"{head}/{zlib.crc32(head.upper().encode('utf-8')) & 0xFFFF:04X}")[0], 200)

    def test_numbers_and_moves(self):
        """A system's waypoints are numbered 1 up with no gaps: deleting one moves those after it down one (a name of the
        usual kind - WPT 4 - 3 b - follows its number; your own names stay), as at start-up for gaps from before; a flight
        plan's waypoint moved up and down it (to a place: the same move twice is one move)."""
        j = journals.syst()
        with Board("nav_numbers", journal=j["journal"], status=j["status"]) as b:
            nav = lambda **kw: b.post("/api/nav", kw)
            add = lambda **kw: b.post("/api/tgt", dict({"op": "add", "body": self.PLANET, "lat": -13.1, "lon": 34.9, "method": "manual"}, **kw))[1]["tgt"]
            w1, w2, w3, w4 = add(), add(), add(name="IP"), add()
            short = w1["name"].split(" - ", 1)[1]
            for w in (w1, w2, w3, w4):
                nav(op="seq", seq=1, act="ins", id=w["id"])
            self.assertEqual(b.post("/api/tgt", {"op": "delete", "id": w2["id"]})[0], 200)
            got = [(t["key"], t["num"], t["name"]) for t in b.state()["syst"]["tgts"]]
            self.assertEqual(got, [(w1["key"], 1, f"WPT 1 - {short}"), (w3["key"], 2, "IP"), (w4["key"], 3, f"WPT 3 - {short}")])
            self.assertEqual(self.nav(b)["seqs"]["1"], [w1["key"], w3["key"], w4["key"]], "the plan follows its waypoints")
            self.assertEqual(add()["num"], 4)
            # moved up and down the plan: to a place in it (held at the ends)
            mv = lambda w, to: nav(op="seq", seq=1, act="mv", id=w["id"], to=to)
            self.assertEqual(mv(w4, 0)[1]["seq"], [w4["key"], w1["key"], w3["key"]])
            self.assertEqual(mv(w4, 0)[1]["seq"], [w4["key"], w1["key"], w3["key"]], "the same move again: no change")
            self.assertEqual(mv(w1, 99)[1]["seq"], [w4["key"], w3["key"], w1["key"]])
            self.assertEqual(mv(w3, -3)[1]["seq"], [w3["key"], w4["key"], w1["key"]])
            self.assertEqual(mv(w2, 0), (400, {"ok": False, "why": "not in it"}))
            self.assertEqual(nav(op="seq", seq=1, act="mv", id=w1["id"]), (400, {"ok": False, "why": "place"}))
            # gaps from before (deleted before 3.01.30): closed at start-up
            b.proc.terminate()
            b.proc.wait(5)
            db = sqlite3.connect(str(b.dir / "settlements.sqlite"))
            db.execute("UPDATE targets SET num = num + 4, name = 'WPT ' || (num + 4) || ' - ' || ? WHERE name LIKE 'WPT %'", (short,))
            db.execute("UPDATE targets SET num = num + 4 WHERE name NOT LIKE 'WPT %'")
            db.commit()
            db.close()
            b.restart()
            y = b.wait(lambda: (lambda y: y if y.get("tgts") else None)(b.state()["syst"]), what="the waypoints after a restart")
            self.assertEqual([(t["num"], t["name"]) for t in y["tgts"]],
                             [(1, f"WPT 1 - {short}"), (2, "IP"), (3, f"WPT 3 - {short}"), (4, f"WPT 4 - {short}")])

    def test_time_on_target(self):
        """Each flight plan's time on target, as the Hornet's HSI DATA / WYPT: its own TGT (one of its waypoints - apart from
        the target you designate), TOT (Zulu, seconds into the day) and GSPD (the IP > TGT leg); TOT and GSPD only with a TGT;
        plans sharing waypoints keep their own; the TGT goes if it's taken out of the plan."""
        j = journals.syst()
        with Board("nav_tot", journal=j["journal"], status=j["status"]) as b:
            nav = lambda **kw: b.post("/api/nav", kw)
            add = lambda **kw: b.post("/api/tgt", dict({"op": "add", "body": self.PLANET, "lat": -13.1, "lon": 34.9, "method": "manual"}, **kw))[1]["tgt"]
            w1, w2, w3, w4 = add(), add(lat=-13.0), add(lat=-12.9), add(lat=-12.8)
            for s, ws in ((1, (w1, w2, w3)), (2, (w2, w3, w4))):
                for w in ws:
                    nav(op="seq", seq=s, act="ins", id=w["id"])
            tots = lambda: self.nav(b)["tots"]
            self.assertEqual(tots()["1"], {"tgt": None, "tot": None, "gspd": None})
            self.assertEqual(nav(op="tot", seq=1, tot=3600), (400, {"ok": False, "why": "set the TGT first"}))
            self.assertEqual(nav(op="tot", seq=1, gspd=420), (400, {"ok": False, "why": "set the TGT first"}))
            self.assertEqual(nav(op="tot", seq=1, tgt=w4["id"]), (400, {"ok": False, "why": "not in it"}))
            self.assertEqual(nav(op="tot", seq=1, tgt=w3["id"])[1]["tot"], {"tgt": w3["key"], "tot": None, "gspd": None})
            self.assertEqual(nav(op="tot", seq=1, tot=50400 + 330, gspd=420)[1]["tot"], {"tgt": w3["key"], "tot": 50730, "gspd": 420})
            for bad, why in (({"tot": 86400}, "tot"), ({"tot": -1}, "tot"), ({"tot": "14:05"}, "tot"), ({"gspd": 10}, "gspd"), ({"seq": 4}, "seq")):
                self.assertEqual(nav(**dict({"op": "tot", "seq": 1}, **bad)), (400, {"ok": False, "why": why}), bad)
            # SEQ 2 shares WP3 but keeps its own; designating (DSG) doesn't touch either
            nav(op="tot", seq=2, tgt=w3["id"], tot=60000)
            nav(op="dsg", key=w4["key"])
            t = tots()
            self.assertEqual((t["1"], t["2"]), ({"tgt": w3["key"], "tot": 50730, "gspd": 420}, {"tgt": w3["key"], "tot": 60000, "gspd": None}))
            self.assertEqual(self.nav(b)["tgt"]["key"], w4["key"])
            # cleared field by field; the TGT taken out of the plan: gone (the TOT and GSPD kept for the next)
            self.assertEqual(nav(op="tot", seq=2, tot=None)[1]["tot"], {"tgt": w3["key"], "tot": None, "gspd": None})
            nav(op="seq", seq=1, act="del", id=w3["id"])
            self.assertEqual(tots()["1"], {"tgt": None, "tot": 50730, "gspd": 420})
            nav(op="seq", seq=1, act="ins", id=w3["id"])
            self.assertIsNone(tots()["1"]["tgt"], "not back by itself")
            nav(op="tot", seq=1, tgt=w2["id"])
            self.assertEqual(nav(op="tot", seq=1, tgt=None)[1]["tot"]["tgt"], None)
            # kept for good
            nav(op="tot", seq=1, tgt=w3["id"])
            b.restart()
            n = b.wait(lambda: (lambda y: y["nav"] if (y.get("nav") or {}).get("tots", {}).get("1", {}).get("tgt") else None)(b.state()["syst"]), what="the TOT after a restart")
            self.assertEqual(n["tots"]["1"], {"tgt": w3["key"], "tot": 50730, "gspd": 420})

    def test_ufc_dsg_mk_and_sub_levels(self):
        j = journals.syst()
        with Board("nav_ufc", journal=j["journal"], status=j["status"]) as b:
            b.write_status(dict(journals.NEAR_HAO))
            b.ufc_cmd("press ILS")
            b.wait(lambda: b.display()["options"] == PAGE_LABELS or None, what="DSG and MK on the page menu")
            u = b.bus()
            # MK with no page to answer (only the harness's stand-in): Status.json's position, a moment later
            b.ufc_cmd("press Opt5")
            b.wait(lambda: b.bus()["mk_n"] == u["mk_n"] + 1 or None, what="MK")
            n = b.wait(lambda: (lambda n: n if n["marks"] else None)(self.nav(b)), timeout=6, what="the mark, from Status.json")
            m = n["marks"][0]
            self.assertEqual((m["name"], m["lat"], m["lon"], m["body"]), ("MK1", journals.NEAR_HAO["Latitude"], journals.NEAR_HAO["Longitude"], self.PLANET))
            # DSG: a count for the page showing to act on
            b.ufc_cmd("press Opt4")
            b.wait(lambda: b.bus()["dsg_n"] == u["dsg_n"] + 1 or None, what="DSG")
            # a page's UFC sub-level: its fields in the option windows (':' on the one typed); the option buttons and keys to it
            b.ufc_cmd("press Opt2", "press 3")
            b.wait(lambda: b.bus()["view"] == {"tab": "nav", "sub": 4} or None, what="Wpt")
            b.post("/api/select", {"tab": "nav", "sub": 4})
            k = b.bus()["key_n"]
            b.ufc_cmd("press Ent")   # (not typing: on Wpt, ENT is the page's - it opens the sub-level)
            b.wait(lambda: b.bus()["key_n"] == k + 1 and b.bus()["keys"][-1][1] == "Ent" or None, what="ENT to the page")
            b.post("/api/keypad", {"page": "harness", "on": True, "s1": "WP", "s2": "3", "num": "", "opts": ["POSN", "NAME", "O/S", "DEL", ""], "cue": 2})
            d = b.wait(lambda: (lambda d: d if d["options"] == ["POSN", "NAME", "O/S", "DEL", ""] else None)(b.display()), what="the sub-level's fields")
            self.assertEqual((d["cue"], d["s1"], d["s2"]), (2, "WP", "3"))
            b.ufc_cmd("press Opt1", "press 4")
            b.wait(lambda: [x for _, x in b.bus()["keys"][-2:]] == ["Opt1", "4"] or None, what="the option button and the digit to the page")
            self.assertEqual(b.bus()["view"], {"tab": "nav", "sub": 4}, "no tab, no sub-tab")
            b.post("/api/keypad", {"page": "harness", "on": False})
            b.wait(lambda: b.display()["options"] == PAGE_LABELS or None, what="the page menu back")
            # the HSI: its own COM windows and scratchpad
            b.ufc_cmd("press 4")
            b.wait(lambda: b.bus()["view"] == {"tab": "nav", "sub": 5} or None, what="HSI")
            b.post("/api/select", {"tab": "nav", "sub": 5})
            b.post("/api/scratch", {"page": "harness", "s1": "WP", "s2": "1", "num": "4.2KM", "com1": "1", "com2": "2"})
            b.wait(lambda: (lambda d: d if (d["com1"], d["com2"], d["scratch"], d["s1"]) == ("1", "2", "4.2KM", "WP") else None)(b.display()),
                   what="the HSI's COM windows and scratchpad")


def project_url():
    import re
    from harness import SCRIPT
    return re.search(r'^PROJECT_URL = "([^"]+)"', SCRIPT.read_text(encoding="utf-8"), re.M).group(1)


def script_version():
    import re
    from harness import SCRIPT
    return re.search(r'^VERSION = "([^"]+)"', SCRIPT.read_text(encoding="utf-8"), re.M).group(1)


class OneCopy(unittest.TestCase):
    """A copy of the board still running from before (its page closed without Exit) is closed as the next starts: asked
    to stop as Exit does if it answers on the port, ended if it's hung - only if ft3000.pid shows it's the FT3000 this
    folder started; another program given its process number is left alone."""

    def hello(self, b):
        return json.loads(b.get("/api/hello")[1])

    def test_closed_as_exit_does(self):
        j = journals.syst()
        with Board("one_copy", journal=j["journal"], status=j["status"]) as b:
            first = b.proc
            self.assertEqual(self.hello(b), {"app": "UCEC FT3000", "version": script_version(), "pid": first.pid})
            rec = json.loads((b.dir / "ft3000.pid").read_text())
            self.assertEqual((rec["pid"], rec["port"]), (first.pid, b.port))
            b.start_again()
            self.assertIsNotNone(first.poll(), "the first copy closed")
            self.assertEqual(self.hello(b)["pid"], b.proc.pid)
            log = b.log()
            self.assertIn(f"UCEC FT3000 {script_version()} is still running on port {b.port} - closing it, as Exit does.", log)
            self.assertIn("Exit pressed on the web page - stopping.", log)   # (the first copy's own words: it closed as Exit does)
            self.assertEqual(json.loads((b.dir / "ft3000.pid").read_text())["pid"], b.proc.pid)
            # Exit: the PID file goes with it
            b.post("/api/quit", {})
            b.proc.wait(10)
            self.assertFalse((b.dir / "ft3000.pid").exists())

    def test_hung_copy_ended(self):
        import signal
        j = journals.syst()
        with Board("one_copy_hung", journal=j["journal"], status=j["status"]) as b:
            first = b.proc
            os.kill(first.pid, signal.SIGSTOP)   # (hung: it can't answer)
            b.start_again()
            first.wait(5)
            self.assertEqual(self.hello(b)["pid"], b.proc.pid)
            self.assertIn(f"(process {first.pid}) is still running but not answering - ending it.", b.log())

    def test_another_program_left_alone(self):
        j = journals.syst()
        with Board("one_copy_other", journal=j["journal"], status=j["status"]) as b:
            other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            try:
                time.sleep(0.5)
                b.proc.terminate()
                b.proc.wait(5)
                started = float(Path(f"/proc/{other.pid}/stat").read_text().rsplit(")", 1)[1].split()[19])   # (only to match the file's)
                boot = next(float(x.split()[1]) for x in Path("/proc/stat").read_text().splitlines() if x.startswith("btime "))
                (b.dir / "ft3000.pid").write_text(json.dumps({"pid": other.pid, "port": b.port, "version": "3.01.34",
                                                              "started": boot + started / os.sysconf("SC_CLK_TCK")}))
                b.restart()
                self.assertIsNone(other.poll(), "not the FT3000: left alone")
                self.assertNotIn("not answering - ending it", b.log())
                self.assertEqual(json.loads((b.dir / "ft3000.pid").read_text())["pid"], b.proc.pid)
            finally:
                other.kill()
                other.wait(5)


class Remote(unittest.TestCase):
    """1 Syst's CURRENT SYSTEM / REMOTE: a system picked to look at and plan in - 1 Syst (and the Nav pages, which
    follow it) show it, not where you are - from a list (your route's destination, your missions' systems, OCOR, where
    you've been lately, what you've picked lately) or a name (MANUAL: matches from what you know of, and Spansh); it
    stays through jumps elsewhere until CURRENT SYSTEM, or until you arrive there; kept through a restart."""

    def test_remote_system(self):
        j = journals.jump()
        j.pop("fuel")
        j["journal"] = j["journal"] + [journals._accept(100, 9101, "Mission_Delivery", "Deliver tea to Carthage",
                                                        DestinationSystem="Carthage", Expiry=ahead(3600))]
        with Board("remote", **j) as b:
            items = json.loads(b.get("/api/remote")[1])["items"]
            have = {(i["g"], i["name"]) for i in items}
            for want in (("route", "Carthage"), ("missions", "Carthage"), ("hist", "Calennero"), ("hist", "ICZ CQ-Y d119")):
                self.assertIn(want, have)
            self.assertNotIn("HIP 20277", [i["name"] for i in items], "where you are isn't listed")
            route = next(i for i in items if i["g"] == "route")
            self.assertTrue(route["ly"] and 10 < route["ly"] < 13, route)   # (from the route's own positions)
            # MANUAL's matches: two letters at least; what you know of (Spansh unreachable here)
            self.assertEqual(json.loads(b.get("/api/sysfind?q=c")[1])["items"], [])
            self.assertEqual([m["name"] for m in json.loads(b.get("/api/sysfind?q=cal")[1])["items"]], ["Calennero"])
            # picked (any case: as it's known): 1 Syst shows it - you're not there, so nothing live
            self.assertEqual(b.post("/api/remote", {"system": "carthage"}), (200, {"ok": True, "system": "Carthage"}))
            y = b.wait(lambda: (lambda y: y if y["system"] == "Carthage" and y["status"] == "ok" else None)(b.state()["syst"]), what="Carthage in 1 Syst")
            self.assertEqual((y["remote"]["on"], y["remote"]["system"], y["remote"]["here"]), (True, "Carthage", "HIP 20277"))
            self.assertEqual(b.state()["remote"]["system"], "Carthage")
            self.assertEqual((y["me"], y["docked"], y["near"], y["auto"]["why"]), (None, None, {}, "remote"))
            self.assertIn("Cho", [e["name"] for e in y["entries"]])
            # planned there: a waypoint on Cho, in a flight plan - Carthage's, not where you are
            t = b.post("/api/tgt", {"op": "add", "body": "Cho", "lat": -24.1, "lon": 61.2, "method": "manual"})[1]["tgt"]
            self.assertEqual((t["system"], t["num"]), ("Carthage", 1))
            self.assertEqual(b.post("/api/nav", {"op": "seq", "seq": 1, "act": "ins", "id": t["id"]})[0], 200)
            # a jump elsewhere: still Carthage; CURRENT SYSTEM: where you are, without Carthage's waypoint
            b.add({"event": "FSDJump", "StarSystem": "Calennero", "SystemAddress": 100, "StarPos": [108.0, -97.0, -7.0], "JumpDist": 9.4,
                   "Body": "Calennero", "BodyType": "Star"})
            b.wait(lambda: b.state()["remote"]["here"] == "Calennero" or None, what="the jump")
            self.assertEqual((b.state()["remote"]["system"], b.state()["syst"]["system"]), ("Carthage", "Carthage"))
            self.assertEqual(b.post("/api/remote", {"off": True})[0], 200)
            y = b.wait(lambda: (lambda y: y if y["system"] == "Calennero" else None)(b.state()["syst"]), what="the current system again")
            self.assertEqual((y["remote"]["on"], y.get("tgts") or []), (False, []))
            # kept through a restart - even one your old journals pass through on the way (you were there before)
            self.assertEqual(b.post("/api/remote", {"system": "icz cq-y d119"})[1]["system"], "ICZ CQ-Y d119")
            b.restart()
            b.wait(lambda: (b.state().get("remote") or {}).get("system") == "ICZ CQ-Y d119" or None, what="REMOTE after a restart")
            time.sleep(1.5)
            self.assertEqual(b.state()["remote"]["system"], "ICZ CQ-Y d119")
            self.assertNotIn("Arrived in ICZ CQ-Y d119", b.log())
            # picked again; arriving there: it's simply the current system - its plan waiting
            b.post("/api/remote", {"system": "Carthage"})
            b.wait(lambda: b.state()["syst"]["system"] == "Carthage" or None, what="Carthage again")
            b.add({"event": "FSDJump", "StarSystem": "Carthage", "SystemAddress": 999, "StarPos": [100.34375, -102.125, 7.34375],
                   "JumpDist": 11.0, "Body": "Carthage", "BodyType": "Star"})
            y = b.wait(lambda: (lambda y: y if y["remote"]["here"] == "Carthage" and y["system"] == "Carthage" and y.get("tgts") else None)(b.state()["syst"]),
                       what="arrived in Carthage")
            self.assertEqual((y["remote"]["on"], y["nav"]["seqs"]["1"], b.state()["remote"]["on"]), (False, [t["key"]], False))
            self.assertIn("Arrived in Carthage: 1 Syst is on the current system again.", b.log())
            items = json.loads(b.get("/api/remote")[1])["items"]
            self.assertNotIn("Carthage", [i["name"] for i in items], "where you are isn't listed - now Carthage")
            # a name nothing knows (Spansh unreachable here: taken as typed - its data, when it can be fetched); not a name
            self.assertEqual(b.post("/api/remote", {"system": "Nowhere  Known"}), (200, {"ok": True, "system": "Nowhere Known"}))
            b.wait(lambda: b.state()["syst"]["system"] == "Nowhere Known" or None, what="the unknown system")
            self.assertEqual(b.post("/api/remote", {"system": "bad\x07name"})[0], 400)
            self.assertEqual(b.post("/api/remote", {"system": "carthage"})[1].get("current"), True, "where you are: the current system")
            self.assertFalse(b.state()["remote"]["on"])

    def test_ufc_switch(self):
        """COMM1's first stop on the System list is the switch: a pull opens the page's list (the page's pick); on a
        remote system, back to the current one; the keypad and COMM1 are the page's while it says the list is open."""
        j = journals.jump()
        j.pop("fuel")
        with Board("remote_ufc", **j) as b:
            b.ufc_cmd("press ILS", "press Opt2")
            b.wait(lambda: b.bus()["view"]["tab"] == "nav" or None, what="Nav")
            b.post("/api/select", {"tab": "nav", "sub": 1})
            b.ufc_cmd(*["pulse COMM1_CCW"] * 40, pause=0.02)
            b.wait(lambda: b.bus()["cursors"]["syst"] == "remote" or None, what="COMM1 on the switch")
            n = b.bus()["pick_n"]
            b.ufc_cmd("press COMM1_PULL")
            b.wait(lambda: b.bus()["pick_n"] == n + 1 or None, what="the pull")
            self.assertEqual(b.bus()["pick"], {"list": "syst", "key": "remote"})
            # the page's list open: the keypad and COMM1 are its
            b.post("/api/keypad", {"page": "harness", "on": True, "s1": "RM", "num": "MANUAL", "knob1": True})
            k1, keys = b.bus()["knob1_pos"], b.bus()["key_n"]
            b.ufc_cmd("pulse COMM1_CW", "press 3")
            b.wait(lambda: b.bus()["knob1_pos"] == k1 + 1 and b.bus()["key_n"] == keys + 1 or None, what="COMM1 and the keypad to the page")
            self.assertEqual((b.bus()["cursors"]["syst"], b.bus()["view"]["sub"]), ("remote", 1), "not the list's cursor, not a sub-tab")
            b.wait(lambda: (lambda d: d if (d["s1"], d["scratch"]) == ("RM", "MANUAL") else None)(b.display()), what="the scratchpad")
            b.post("/api/keypad", {"page": "harness", "on": False})
            # on a remote system: the pull is back to the current one
            b.post("/api/remote", {"system": "Carthage"})
            b.wait(lambda: b.state()["syst"]["system"] == "Carthage" or None, what="Carthage")
            b.ufc_cmd(*["pulse COMM1_CCW"] * 5, "press COMM1_PULL", pause=0.05)
            b.wait(lambda: not b.state()["remote"]["on"] or None, what="CURRENT SYSTEM from the UFC")


class Jump(unittest.TestCase):
    def test_jump(self):
        j = journals.jump()
        fuel = j.pop("fuel")
        with Board("jump", **j) as b:
            self.assertIsNone(b.state()["jump"])
            b.write_status({"Flags": SC_FLAGS | (1 << 17), "Fuel": {"FuelMain": fuel, "FuelReservoir": 0.5}, "Cargo": 16.0})
            time.sleep(1.2)
            n = b.bus()["jump_n"]
            b.add({"event": "StartJump", "JumpType": "Hyperspace", "StarSystem": "Carthage", "SystemAddress": 999, "StarClass": "B"})
            jv = b.wait(lambda: (lambda x: x if x and x["survey"]["status"] == "ok" else None)(b.state()["jump"]), what="the jump and its survey")
            self.assertGreater(b.bus()["jump_n"], n)
            self.assertEqual(jv["to_star"]["source"], "spansh")
            self.assertEqual(jv["dep_star"]["source"], "journal")
            self.assertEqual(jv["fuel_how"], "measured")
            check_golden(self, "jump_under_way", normalise(dict({k: v for k, v in jv.items() if k != "survey"}, survey={k: v for k, v in jv["survey"].items() if k != "map"})))
            b.write_status({"Flags": SC_FLAGS | (1 << 30), "Fuel": {"FuelMain": fuel, "FuelReservoir": 0.5}, "Cargo": 16.0})
            b.add({"event": "FSDJump", "StarSystem": "Carthage", "SystemAddress": 999, "StarPos": journals.CARTHAGE_POS, "JumpDist": 11.63,
                   "FuelUsed": 0.6712, "FuelLevel": round(fuel - 0.6712, 4), "Body": "Carthage", "BodyType": "Star"})
            jv = b.wait(lambda: (lambda x: x if x and x["arrived"] else None)(b.state()["jump"]), what="arrival")
            self.assertEqual((jv["fuel_used"], jv["ly"]), (0.6712, 11.63))
            s = b.wait(lambda: (lambda s: s if s["syst"].get("system") == "Carthage" and s["syst"]["status"] == "ok" else None)(b.state()), what="Carthage on the System tab")
            self.assertEqual(s["system"], "Carthage")


class Ocor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Board("ocor", **journals.ocor()).start()

    @classmethod
    def tearDownClass(cls):
        cls.b.stop()

    def test_1_briefing(self):
        s = self.b.state()
        o = s["ocor"]
        self.assertEqual([x["done"] for x in o["objectives"]], [False, True, False, False, False])
        check_golden(self, "ocor_state", normalise(o))

    def test_2_ufc(self):
        b = self.b
        b.ufc_cmd("press ILS", "press Opt3", "press 3")
        b.wait(lambda: b.bus()["view"] == {"tab": "contracts", "sub": 3} or None, what="Contracts' OCOR page")
        b.post("/api/select", {"tab": "contracts", "sub": 3})
        ids = [x["id"] for x in b.state()["ocor"]["objectives"] if not x["done"]]
        b.wait(lambda: b.bus()["cursors"]["ocor"] in ids or None, what="the OCOR cursor")
        start = ids.index(b.bus()["cursors"]["ocor"])
        b.ufc_cmd("pulse COMM1_CW")
        cur = b.wait(lambda: (lambda c: c if c != ids[start] else None)(b.bus()["cursors"]["ocor"]), what="the cursor to move")
        self.assertEqual(cur, ids[start + 1])   # struck-out objectives are skipped
        self.assertEqual(b.display()["com2"], ufc_num(len(ids)))
        b.ufc_cmd("press COMM1_PULL")
        bus = b.wait(lambda: (lambda u: u if u["pick_n"] >= 1 else None)(b.bus()), what="the pull")
        self.assertEqual(bus["pick"], {"list": "ocor", "key": cur})

    def test_3_paste(self):
        code, j = self.b.post("/api/ocor", {"text": "nothing useful here"})
        self.assertEqual(code, 400)
        self.assertIn("No objectives", j["error"])
        text = (__import__("harness").FIX / "ocor_briefing.txt").read_text(encoding="utf-8")
        code, j = self.b.post("/api/ocor", {"text": text})
        self.assertEqual((code, j["count"]), (200, 5))


class History(unittest.TestCase):
    """Nav › Hist and Contracts › History: every journal read (once) for where you've been and the missions you've
    finished; each page's toggles kept by the board, so the UFC's knob steps through what the page shows."""

    def hist(self, b, page):
        return json.loads(b.get(f"/api/hist?page={page}")[1])

    def item(self, b, page, key):
        from urllib.parse import quote
        return json.loads(b.get(f"/api/hist/item?page={page}&key={quote(key)}")[1])

    def test_history(self):
        j = journals.history()
        with Board("history", journal=j["journal"], status=j["status"], edsm=("hip 20277",)) as b:
            b.wait(lambda: (b.state().get("hist") or {}).get("ready") or None, timeout=20, what="the old journals read")
            nav = self.hist(b, "nav")
            self.assertEqual([(r["d"], r["t"], r["n"]) for r in nav["rows"]], [
                (0, "jump", "HIP 20277"), (1, "dock", "Fabian City"),
                (0, "jump", "Carthage"), (1, "dock", "New Carthage Hub"),
                (0, "here", "HIP 20277"), (1, "orbit", "3 b"), (1, "near", "Hao Extraction Prospect"), (1, "land", "3 b"),
                (0, "jump", "Maia"), (1, "dock", "Obsidian Orbital"),   # two months ago: older than the days the board reads at start-up
                (0, "jump", "Pleione")])
            self.assertEqual(nav["totals"], {"systems": 4, "stations": 3, "planetary": 2})
            self.assertEqual([r["i"] for r in nav["rows"][:2]], ["star", "coriolis"])
            # Systems off: the places alone, newest first, each with its system
            self.assertEqual(b.post("/api/histfilter", {"page": "nav", "name": "systems", "on": False}), (200, {"ok": True}))
            flat = self.hist(b, "nav")
            self.assertEqual([(r["t"], r["n"], r.get("s")) for r in flat["rows"][:3]],
                             [("dock", "Fabian City", "HIP 20277"), ("dock", "New Carthage Hub", "Carthage"), ("land", "3 b", "HIP 20277")])
            b.post("/api/histfilter", {"page": "nav", "name": "planetary", "on": False})
            self.assertEqual([r["n"] for r in self.hist(b, "nav")["rows"]], ["Fabian City", "New Carthage Hub", "Obsidian Orbital"])
            self.assertEqual(b.post("/api/histfilter", {"page": "nav", "name": "bogus", "on": True})[0], 400)
            for name in ("systems", "planetary"):
                b.post("/api/histfilter", {"page": "nav", "name": name, "on": True})
            # a place's details: its kind, the copy button's system, the facts from the journal, your visits
            site = self.item(b, "nav", "site|hip 20277|m:3950102530")
            self.assertEqual((site["name"], site["lab"], site["chips"], site["copy"]),
                             ("Hao Extraction Prospect", "Settlement · HIP 20277 3 b", ["1 visit", "Landed"], "HIP 20277"))
            self.assertEqual([x[1] for x in site["log"]], ["Landed nearby · -13.05, 34.95", "Came within range"])
            self.assertEqual(site["pic"]["hl"], "Hao Extraction Prospect")
            maia = self.item(b, "nav", "sys|maia|")
            self.assertIn(["Faction", "Maia Corp", False], maia["rows"])
            self.assertEqual(maia["log"], [[maia["log"][0][0], "Jumped in · 3.20 ly"]])
            hip = self.item(b, "nav", "sys|hip 20277|")
            self.assertEqual(hip["chips"], ["2 visits"])
            # Contracts › History: completed only to start with; each outcome's total either way
            c = self.hist(b, "contracts")
            self.assertEqual([(r["o"], r["c"], r["n"]) for r in c["rows"]], [("completed", "Delivery", "12 × Gold")])
            self.assertEqual(c["totals"], {"completed": 1, "failed": 1, "abandoned": 1})
            b.post("/api/histfilter", {"page": "contracts", "name": "abandoned", "on": True})
            self.assertEqual([r["o"] for r in self.hist(b, "contracts")["rows"]], ["abandoned", "completed"])
            m = self.item(b, "contracts", "h:3001")
            self.assertEqual((m["outcome"], m["paid"], m["dest"], m["copy"]), ("Completed", "310,000 CR", "Obsidian Orbital, Maia", "Maia"))
            self.assertIn(["Rewards", "310,000 CR · 2 × Grid Resistors", True], m["rows"])
            failed = self.item(b, "contracts", "h:2900")   # accepted before the journals begin: what its end said
            self.assertEqual((failed["outcome"], failed["name"], failed["partial"]), ("Failed", "Courier job: data to Maia", True))
            # the UFC: NAV, then the keypad's 6 (Hist); COMM1 steps through its rows; a pull picks
            b.ufc_cmd("press ILS", "press Opt2", "press 6")
            b.wait(lambda: b.bus()["view"] == {"tab": "nav", "sub": 7} or None, what="Nav's Hist from the keypad")
            keys = [r["k"] for r in self.hist(b, "nav")["rows"]]
            b.wait(lambda: b.bus()["cursors"]["hist"] == keys[0] or None, what="the Hist cursor on the newest")
            b.ufc_cmd("pulse COMM1_CW", "pulse COMM1_CW")
            b.wait(lambda: b.bus()["cursors"]["hist"] == keys[2] or None, what="the Hist cursor to move")
            b.wait(lambda: b.display()["com2"] == ufc_num(len(keys)) or None, what="COM2: how many rows")
            b.ufc_cmd("press COMM1_PULL")
            bus = b.wait(lambda: (lambda u: u if u["pick_n"] >= 1 else None)(b.bus()), what="the pull")
            self.assertEqual(bus["pick"], {"list": "hist", "key": keys[2]})
            b.ufc_cmd("press Opt3", "press 2")   # Contracts, the keypad's 2: History
            b.wait(lambda: b.bus()["view"] == {"tab": "contracts", "sub": 2} or None, what="Contracts' History")
            b.wait(lambda: b.bus()["cursors"]["chist"] == "h:3101" or None, what="the History cursor")
            # live: a new jump is on the list at once
            b.add({"event": "FSDJump", "StarSystem": "Maia", "SystemAddress": 8, "JumpDist": 7.0})
            b.wait(lambda: (self.hist(b, "nav")["rows"][0]["n"], self.hist(b, "nav")["totals"]["systems"]) == ("Maia", 4) or None,
                   what="the live jump on the list")
            # kept: after a restart nothing is read again, and it's all still there (the toggles as they start)
            b.restart()
            b.wait(lambda: (b.state().get("hist") or {}).get("ready") or None, timeout=20, what="the history after a restart")
            self.assertEqual(b.log().count("History: read 2 journal files"), 1)
            again = self.hist(b, "nav")
            self.assertEqual((again["rows"][0]["n"], len(again["rows"])), ("Maia", len(nav["rows"]) + 1))
            self.assertEqual(self.hist(b, "contracts")["filters"], {"completed": True, "failed": False, "abandoned": False})


class NoJournal(unittest.TestCase):
    def test_missing_folder(self):
        b = Board("nojournal", journal=journals.syst()["journal"], edsm=(), no_edsm=True, ufc=False,
                  extra_args=["--journal-dir", "/no/such/folder/anywhere"])
        b._write_files()
        try:
            # start by hand: the board never finishes loading a journal here
            import subprocess, sys, os
            from harness import SCRIPT, FIX, free_port, SimApp
            b.simapp = SimApp(); b.simapp.start()
            b.port = free_port()
            b.url = f"http://127.0.0.1:{b.port}"
            b.logf = open(b.dir / "server.log", "w")
            b.proc = subprocess.Popen([sys.executable, str(b.dir / SCRIPT.name), "--engine", "none", "--journal-dir", "/no/such/folder/anywhere",
                                       "--port", str(b.port), "--no-browser", "--no-ufc", "--no-edsm"], cwd=str(b.dir), stdout=b.logf, stderr=subprocess.STDOUT,
                                      env=dict(os.environ, https_proxy="http://127.0.0.1:9", HTTPS_PROXY="http://127.0.0.1:9"))
            s = b.wait(lambda: (lambda s: s if s and "not found" in (s.get("note") or "") else None)(b.state()), timeout=15, what="the note")
            self.assertIn("Journal folder not found", s["note"])
            self.assertEqual(s["contracts"], [])
        finally:
            b.stop()


if __name__ == "__main__":
    unittest.main()


class FakeEdsm:
    """Stands in for EDSM's and Spansh's APIs on this machine: answers from the fixtures, counts what's asked
    ("dump" for Spansh's system record), or fails."""

    def __init__(self):
        import http.server
        import threading
        from pathlib import Path
        fix = Path(__file__).parent / "fixtures"
        data = json.loads((fix / "edsm.json").read_text(encoding="utf-8"))
        spansh = {str(v["id64"]): v for v in json.loads((fix / "spansh.json").read_text(encoding="utf-8")).values()}
        fake = self
        self.asked, self.fail, self.agents = [], False, set()

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                from urllib.parse import urlparse, parse_qs
                u = urlparse(self.path)
                fake.agents.add(self.headers.get("User-Agent") or "")
                if u.path.startswith("/spansh/"):   # Spansh: /spansh/dump/<id64>
                    fake.asked.append("dump")
                    rec = spansh.get(u.path.rsplit("/", 1)[-1])
                    code, body = (500, b"") if fake.fail else (200, json.dumps({"system": rec}).encode()) if rec else \
                        (404, b'{"error": "Could not find record"}')
                    self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers()
                    self.wfile.write(body)
                    return
                part, system = u.path.rsplit("/", 1)[-1], (parse_qs(u.query).get("systemName") or [""])[0]
                fake.asked.append(part)
                if fake.fail:
                    self.send_response(500); self.end_headers(); return
                body = json.dumps((data.get(system.lower()) or {}).get(part) or {}).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.env = {"EDTB_EDSM_API": f"http://127.0.0.1:{self.srv.server_address[1]}/api-system-v1/",
                    "EDTB_SPANSH_API": f"http://127.0.0.1:{self.srv.server_address[1]}/spansh/",
                    "no_proxy": "127.0.0.1", "NO_PROXY": "127.0.0.1"}

    def close(self):
        self.srv.shutdown()


class Uplink(unittest.TestCase):
    """A system's parts - Spansh's record, EDSM's traffic, deaths and value - fetched together, at most once an
    hour; System Data Uplink Synchronise fetches them now (from a page or the UFC's last COMM1 stop on the System
    list), once a minute at most."""

    PARTS = ["dump", "traffic", "deaths", "estimated-value"]

    def setUp(self):
        self.edsm = FakeEdsm()

    def tearDown(self):
        self.edsm.close()

    def test_arrival_fetch_and_ufc_press(self):
        j = journals.syst()
        with Board("uplink_a", journal=j["journal"], status=j["status"], edsm=(), env=self.edsm.env) as b:
            y = b.wait(lambda: (lambda y: y if y.get("status") == "ok" and y.get("entries") else None)(b.state()["syst"]),
                       timeout=20, what="the arrival fetch")
            self.assertEqual(self.edsm.asked, self.PARTS)   # all together
            self.assertEqual(self.edsm.agents, {f"UCEC-FT3000/{script_version()} (Elite Dangerous companion; +{project_url()})"},
                             "it says what it is, and where to find it")
            first = y["uplink"]
            self.assertTrue(first)
            self.assertFalse(y["uplinking"]["busy"] or y["uplinking"]["off"])
            keys = [e["key"] for e in y["entries"]]
            b.post("/api/select", {"pick": {"syst": keys[-1]}})   # the last row picked on the page
            b.ufc_cmd("press ILS", "press Opt2")
            b.wait(lambda: b.bus()["view"] == {"tab": "nav", "sub": 1} or None, what="the UFC to pick the Nav tab (Syst)")
            b.post("/api/select", {"tab": "nav", "sub": 1})   # as the page does when it follows
            b.wait(lambda: b.bus()["cursors"]["syst"] == keys[-1] or None, what="the cursor on the last row")
            b.ufc_cmd("pulse COMM1_CW")   # one more: the uplink button
            b.wait(lambda: b.bus()["cursors"]["syst"] == "uplink" or None, what="the cursor on the uplink button")
            d = b.wait(lambda: b.display() if b.display()["com1"] == "" else None, what="COM1 blank on the button")
            self.assertEqual(d["com2"], ufc_num(len(keys)))   # the button isn't counted
            t0 = time.time()
            b.ufc_cmd("press COMM1_PULL", pause=0.05)
            b.wait(lambda: b.state()["syst"]["uplinking"]["busy"] or None, timeout=3, what="uplink in progress")
            y = b.wait(lambda: (lambda y: y if not y["uplinking"]["busy"] else None)(b.state()["syst"]), timeout=10, what="the uplink done")
            self.assertGreaterEqual(time.time() - t0, 1.0, "in progress for a moment, however fast EDSM is")
            self.assertEqual((y["uplinking"]["result"], self.edsm.asked), ("ok", self.PARTS * 2))
            self.assertGreater(y["uplink"], first)
            code, answer = b.post("/api/uplink")
            self.assertEqual((code, answer["why"]), (429, "wait"))   # once a minute
            self.assertGreater(answer["wait"], 40)

    def test_fresh_copy_kept_and_failed_uplink(self):
        j = journals.syst()
        self.edsm.fail = True
        with Board("uplink_b", journal=j["journal"], status=j["status"], env=self.edsm.env, ufc=False) as b:
            time.sleep(2.5)
            self.assertEqual(self.edsm.asked, [], "fetched under an hour ago: not asked again")
            y0 = b.state()["syst"]
            self.assertEqual(b.post("/api/uplink")[0], 202)
            y = b.wait(lambda: (lambda y: y if y["uplinking"]["result"] else None)(b.state()["syst"]), timeout=10, what="the uplink to fail")
            self.assertEqual(y["uplinking"]["result"], "error")
            self.assertEqual(self.edsm.asked, ["dump", "bodies"])   # (Spansh failed: EDSM's turn, and it stops at its first failure)
            self.assertEqual((y["uplink"], len(y["entries"]), y["status"]), (y0["uplink"], len(y0["entries"]), "stale"))   # the copy stays

    def test_toggles_and_unknown_systems(self):
        """Spansh Uplink / EDSM Uplink: both on, EDSM's bodies and stations are fetched only where Spansh has nothing
        (a system Spansh doesn't know is an answer, not a failure); Spansh off, EDSM's are used at once; the toggles
        are kept (and the UFC's last two COMM1 stops on the System list flip them)."""
        j = journals.syst()
        with Board("uplink_toggles", journal=j["journal"], status=j["status"], edsm=(), env=self.edsm.env) as b:
            y = b.wait(lambda: (lambda y: y if y.get("status") == "ok" and y.get("entries") else None)(b.state()["syst"]),
                       timeout=20, what="the arrival fetch")
            self.assertEqual(self.edsm.asked, ["dump", "traffic", "deaths", "estimated-value"])   # Spansh had it: no EDSM bodies
            self.assertEqual((y["uplinking"]["spansh"], y["uplinking"]["edsm"]), (True, True))
            self.assertEqual(b.post("/api/uplink-source", {"source": "spansh", "on": False}), (200, {"ok": True, "sources": {"spansh": False, "edsm": True}}))
            y = b.wait(lambda: (lambda y: y if y.get("source") == "edsm" else None)(b.state()["syst"]), timeout=15, what="EDSM's bodies and stations")
            fabian = next(e for e in y["entries"] if e["name"] == "Fabian City")
            self.assertEqual((fabian["src"], fabian["right"]), ("edsm", ""))   # EDSM says which planet it orbits
            self.assertIn("bodies", self.edsm.asked)
            self.assertEqual(json.loads((b.dir / "uplink_settings.json").read_text()), {"spansh": False, "edsm": True})
            self.assertEqual(b.post("/api/uplink-source", {"source": "nope"})[0], 400)
            # the UFC: past the last row and the uplink button, the two toggles; a COMM1 pull flips one
            keys = [e["key"] for e in y["entries"]]
            b.post("/api/select", {"pick": {"syst": keys[-1]}})
            b.ufc_cmd("press ILS", "press Opt2")
            b.wait(lambda: b.bus()["view"] == {"tab": "nav", "sub": 1} or None, what="the UFC to pick the Nav tab")
            b.post("/api/select", {"tab": "nav", "sub": 1})
            b.wait(lambda: b.bus()["cursors"]["syst"] == keys[-1] or None, what="the cursor on the last row")
            b.ufc_cmd("pulse COMM1_CW", "pulse COMM1_CW")
            b.wait(lambda: b.bus()["cursors"]["syst"] == "src:spansh" or None, what="the cursor on Spansh Uplink")
            self.assertEqual(b.display()["com2"], ufc_num(len(keys)))   # (the buttons aren't counted)
            b.ufc_cmd("press COMM1_PULL")
            b.wait(lambda: b.state()["syst"]["uplinking"]["spansh"] or None, what="the pull to switch Spansh Uplink back on")
            b.wait(lambda: b.state()["syst"].get("source") == "spansh" or None, timeout=15, what="Spansh's bodies and stations again")
        self.edsm.asked.clear()
        lone = journals._start(600) + [{"timestamp": ago(500), "event": "FSDJump", "StarSystem": "Nowhere Sector AB-C d1", "SystemAddress": 55,
                                        "StarPos": [1.0, 2.0, 3.0], "Body": "Nowhere Sector AB-C d1", "BodyType": "Star"}]
        with Board("uplink_unknown", journal=lone, edsm=(), env=self.edsm.env, ufc=False) as b:
            y = b.wait(lambda: (lambda y: y if y.get("status") in ("empty", "error", "ok") else None)(b.state()["syst"]),
                       timeout=20, what="the system's answer")
            self.assertEqual((y["status"], y["system"]), ("empty", "Nowhere Sector AB-C d1"))
            self.assertEqual(self.edsm.asked, ["dump", "bodies", "stations", "traffic", "deaths", "estimated-value"])   # Spansh then EDSM

    def test_hour_old_copy_fetched_again(self):
        j = journals.syst()
        with Board("uplink_c", journal=j["journal"], status=j["status"], env=self.edsm.env, edsm_age=3700, ufc=False) as b:
            b.wait(lambda: self.edsm.asked == self.PARTS or None, timeout=10, what="the hour-old copy fetched again")
        with Board("uplink_d", journal=j["journal"], status=j["status"], edsm=(), no_edsm=True, ufc=False) as b:
            self.assertEqual(b.post("/api/uplink"), (409, {"ok": False, "why": "offline"}))
            self.assertTrue(b.state()["syst"]["uplinking"]["off"])


class OcorFormats(unittest.TestCase):
    """The briefing's other layout: bold names, bars in `code`, the score line naming the faction, and a
    "Priority ONE!" section first - as copied with Copy Text (markdown) or as plain selected text."""

    @classmethod
    def setUpClass(cls):
        cls.m = load_script()
        from pathlib import Path
        cls.text = (Path(__file__).parent / "fixtures" / "ocor_briefing_priority.txt").read_text(encoding="utf-8")

    def check(self, b):
        got = [(o["section"], o["system"], o["task"], o["faction"], o["gov"], o["enemy"], o["dir"], o["pct"], o["score"])
               for o in b["objectives"]]
        self.assertEqual(got, [
            ("Priority One", "Test Sector AB-C d1-2", "raise", "Sample Cartel", "Anarchy", "", "▲", "9.0", ""),
            ("War", "Test Sector AB-C d1-2", "war", "Example Legion", "Patronage", "Rival Liberal Command", "", "", "0-0 (Tied)"),
            ("Influence Work", "Maia", "reduce", "Rival Liberal Command", "Corporate", "", "▼", "15.3", ""),
            ("Influence Work", "HIP 20277", "raise", "Example Legion", "Patronage", "", "▲", "16.2", ""),
        ])
        self.assertEqual(b["date"], "28 October 2026")
        self.assertEqual([n["text"][:13] for n in b["notes"][:2]], ["BOUNTIES only", "Never turn in"])

    def test_copy_text(self):
        b = self.m.parse_ocor(self.text)
        self.check(b)
        self.assertEqual(b["objectives"][0]["bar"], "▓░░░░░░░░░")
        self.assertEqual(b["objectives"][0]["url"], "https://inara.cz/elite/starsystem/?search=Test%20Sector%20AB-C%20d1-2")

    def test_plain_text(self):   # as selected and copied: no markdown, no heading marks
        import re
        plain = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", self.text)
        plain = re.sub(r"<[^>]+>|\*|`|^#\s+", "", plain, flags=re.M)
        self.check(self.m.parse_ocor(plain))


class CopyButton(unittest.TestCase):
    """The copy / paste button beside a system's name: the 1st press copies it to the PC's clipboard, a 2nd
    press for the same name pastes it into Elite (Ctrl+V); a UFC pull counts once, however many pages answer it."""

    def test_copy_then_paste(self):
        j = journals.syst()
        with Board("clip", journal=j["journal"], status=j["status"], edsm=(), no_edsm=True) as b:
            self.assertEqual(b.post("/api/clip", {"text": "Col 285 Sector CT-D a28-3", "pull": 7}), (200, {"ok": True, "did": "copy", "why": ""}))
            self.assertEqual(b.post("/api/clip", {"text": "Col 285 Sector CT-D a28-3", "pull": 7})[1]["did"], "already")   # a 2nd page, same pull
            self.assertEqual(b.bus()["clip"]["state"], "copied")
            self.assertEqual(b.post("/api/clip", {"text": "Col 285 Sector CT-D a28-3", "pull": 8}), (200, {"ok": True, "did": "paste", "why": ""}))
            b.wait(lambda: "UFC: Paste Col 285 Sector CT-D a28-3 -> LeftControl+V" in b.log() or None, what="Ctrl+V sent")
            self.assertEqual(b.bus()["clip"]["state"], "pasted")
            self.assertEqual(b.post("/api/clip", {"text": "Maia"})[1]["did"], "copy")   # another name: copied
            self.assertEqual(b.post("/api/clip", {"text": "  "})[0], 400)
        with Board("clip_noufc", journal=j["journal"], status=j["status"], edsm=(), no_edsm=True, ufc=False) as b:
            b.post("/api/clip", {"text": "Maia"})
            code, answer = b.post("/api/clip", {"text": "Maia"})
            self.assertEqual((code, answer["did"], answer["ok"]), (200, "paste", False))   # no UFC: nothing to send keys with
            self.assertIn("UFC is off", answer["why"])


class TimingLog(unittest.TestCase):
    """--timing-log: the board notes when each Status.json reading was written, seen and sent, and how long that
    took, in timing_log.jsonl beside the script; the page's records (POST /api/timing) go in with them. Off: no file,
    and nothing taken."""

    def _recs(self, b):
        path = b.dir / "timing_log.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else None

    def test_timing_log(self):
        j = journals.syst()
        with Board("timing", journal=j["journal"], status=j["status"], edsm=(), no_edsm=True, ufc=False, extra_args=["--timing-log"]) as b:
            self.assertIn("Timing log on", b.log())
            for i in range(2):
                b.write_status(dict(journals.NEAR_HAO, Altitude=1000 + 10 * i))
                time.sleep(0.4)
            s = b.state()
            self.assertIs(s.get("timing"), True)
            code, got = b.post("/api/timing", {"pn": 1234.5, "dn": 1700000000000,
                                              "recs": [{"k": "p.fr", "w": 1700000000000.5, "g": 16.7, "d": 1}, "not a record", {"k": "p.ref", "f": 3.2}]})
            self.assertEqual((code, got), (200, {"ok": True}))
            self.assertEqual(b.post("/api/timing", {"recs": "nope"})[0], 400)
            recs = b.wait(lambda: (lambda r: r if r and any(x["k"] == "api" and x.get("mt") for x in r) else None)(self._recs(b)),
                          what="the timing log")
            kinds = [r["k"] for r in recs]
            self.assertEqual(kinds[0], "start")
            for k in ("st", "chg", "api", "batch", "p.fr", "p.ref"):
                self.assertIn(k, kinds)
            st = [r for r in recs if r["k"] == "st" and r["pos"]]
            self.assertTrue(st and all(r["seen"] >= r["m"] - 1 and r["ok"] == 1 for r in st), st)
            api = [r for r in recs if r["k"] == "api" and r.get("mt")][-1]
            self.assertTrue(api["kb"] > 0 and api["build"] >= 0 and api["age"] >= 0, api)
            batch = next(r for r in recs if r["k"] == "batch")
            self.assertEqual((batch["n"], batch["pn"], batch["dn"]), (2, 1234.5, 1700000000000))   # (the stray string left out)

    def test_off(self):
        j = journals.syst()
        with Board("timing_off", journal=j["journal"], status=j["status"], edsm=(), no_edsm=True, ufc=False) as b:
            self.assertNotIn("timing", b.state())
            self.assertEqual(b.post("/api/timing", {"recs": [{"k": "p.fr"}]})[0], 404)
            self.assertIsNone(self._recs(b))
