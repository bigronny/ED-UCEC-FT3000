"""Test harness: runs the real board (a copy of the script, in a temporary folder) against
generated journals, with a simulated UFC and a stand-in for SimApp Pro, and no network.

Everything is checked from the outside - the web API, the UFC event stream, what the UFC
display is sent, and (in test_page.py) what the page shows - so the tests don't care how
the code is arranged inside."""
from __future__ import annotations

import difflib
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
GOLDEN = HERE / "golden"
SCRIPT = Path(os.environ.get("EDTB_SCRIPT") or HERE.parent / "ed_target_board.py").resolve()
UPDATE_GOLDEN = os.environ.get("EDTB_UPDATE_GOLDEN") == "1"
KEEP = os.environ.get("EDTB_KEEP") == "1"
NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # talk to the board directly

SC_FLAGS = 16777240           # in main ship, supercruise, shields up (as Status.json writes it)
DOCKED_FLAGS = 16842765       # in main ship, docked, landing gear down, shields up


def now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def ago(seconds):
    return iso(now() - timedelta(seconds=seconds))


def ahead(hours):
    return iso(now() + timedelta(hours=hours))


def free_port(kind=socket.SOCK_STREAM):
    s = socket.socket(socket.AF_INET, kind)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class SimApp(threading.Thread):
    """Stands in for WinWing SimApp Pro: keeps the last UFC text the board sent."""

    def __init__(self):
        super().__init__(daemon=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(0.2)
        self.port = self.sock.getsockname()[1]
        self.fields, self.count, self.running = {}, 0, True

    def run(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(65536)
            except (socket.timeout, OSError):
                continue
            try:
                msg = json.loads(data.decode("utf-8"))
            except ValueError:
                continue
            text = (msg.get("args") or {}).get("FA-18C_hornet") if isinstance(msg.get("args"), dict) else None
            if not text:
                continue
            parts = text.split("-----------------------------------------\n")
            fields = {}
            for p in parts:
                lines = p.split("\n")
                if len(lines) >= 2 and lines[0]:
                    fields[lines[0]] = lines[1]
            self.fields, self.count = fields, self.count + 1

    def display(self):
        """{'options': [...5], 'com1', 'com2', 'cue': option number with ':' or None, 'scratch': the scratchpad's
        number, 's1' / 's2': its two letter fields}"""
        f = self.fields
        cue = next((i for i in range(1, 6) if f.get(f"UFC_OptionCueing{i}") == ":"), None)
        return {"options": [f.get(f"UFC_OptionDisplay{i}", "") for i in range(1, 6)],
                "com1": f.get("UFC_Comm1Display", ""), "com2": f.get("UFC_Comm2Display", ""), "cue": cue,
                "scratch": f.get("UFC_ScratchPadNumberDisplay", ""), "s1": f.get("UFC_ScratchPadString1Display", ""),
                "s2": f.get("UFC_ScratchPadString2Display", "")}

    def stop(self):
        self.running = False
        self.sock.close()


class PageStub(threading.Thread):
    """Stands in for an open page, as far as the UFC is concerned: holds the event stream open and says the
    board is showing (so the displays show the menu, as they would under a real page)."""

    def __init__(self, url, pid="harness"):
        super().__init__(daemon=True)
        self.url, self.pid, self.conn, self.sock, self.ready = url, pid, None, None, threading.Event()

    def run(self):
        import http.client
        host, port = self.url.split("//", 1)[1].split(":")
        try:
            self.conn = http.client.HTTPConnection(host, int(port), timeout=60)
            self.conn.request("GET", f"/api/events?page={self.pid}")
            self.sock = self.conn.sock   # (the response keeps it, but the connection lets go of it)
            resp = self.conn.getresponse()
            self.ready.set()
            while resp.read1(4096):
                pass
        except Exception:
            pass
        finally:
            self.ready.set()

    def close(self):
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except Exception:
            pass


class Board:
    """One running board. Use as a context manager, or call start() / stop(). With the UFC on, a stand-in
    page keeps its displays on the menu (stub_page=False: no page open, so they stay blank); a test that
    opens a real page calls unstub() first, so the displays follow that page instead."""

    def __init__(self, name, journal=(), status=None, navroute=None, edsm=("hip 20277",), ocor=False,
                 coords=None, no_edsm=False, ufc=True, extra_args=(), stub_page=True, edsm_age=0.0, env=None, ai=False):
        self.name, self.journal, self.status, self.navroute = name, list(journal), status, navroute
        self.edsm, self.ocor, self.coords, self.no_edsm, self.ufc = edsm, ocor, coords or {}, no_edsm, ufc
        self.extra_args = list(extra_args)
        self.proc, self.simapp, self.dir = None, None, None
        self.stub_page, self.stub = stub_page, None
        self.edsm_age, self.env = edsm_age, dict(env or {})   # how long ago the seeded EDSM copy was fetched; extra environment
        self.ai = ai   # True: subject files written by the stand-in AI (fakeai/claude: ai_replies() queues its replies, ai_calls() what it was asked)

    # ---- setting up ----
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()

    def _write_files(self):
        self.dir = Path(tempfile.mkdtemp(prefix=f"edtb_{self.name}_"))
        shutil.copy2(SCRIPT, self.dir / SCRIPT.name)
        web = SCRIPT.parent / "web"
        if web.is_dir():
            shutil.copytree(web, self.dir / "web")
        if self.ufc:
            shutil.copy2(FIX / "ufc_axes.json", self.dir / "ufc_axes.json")
        if (FIX / "schematics").is_dir():   # settlement layout plans (the four Tourism ones)
            shutil.copytree(FIX / "schematics", self.dir / "schematics")
        if self.edsm:   # the system data cache, as if fetched edsm_age ago: EDSM's five parts and Spansh's record
            data = json.loads((FIX / "edsm.json").read_text(encoding="utf-8"))
            spansh = json.loads((FIX / "spansh.json").read_text(encoding="utf-8"))
            t = time.time() - self.edsm_age
            cache = {s: dict({part: {"t": t, "data": v} for part, v in data[s].items()}, spansh={"t": t, "data": spansh[s]},
                             _uplink={"t": t}) for s in self.edsm}
            (self.dir / "edsm_cache.json").write_text(json.dumps(cache), encoding="utf-8")
        if self.ocor:
            raw = (FIX / "ocor_briefing.txt").read_text(encoding="utf-8")
            (self.dir / "ocor_briefing.json").write_text(json.dumps({"pasted": ago(3600), "raw": raw}), encoding="utf-8")
        if self.coords:
            db = sqlite3.connect(str(self.dir / "star_coords.sqlite"))
            db.execute("CREATE TABLE IF NOT EXISTS systems (key TEXT PRIMARY KEY, name TEXT NOT NULL, "
                       "x REAL, y REAL, z REAL, source TEXT, checked REAL NOT NULL) WITHOUT ROWID")
            for name, pos in self.coords.items():
                key = " ".join(name.split()).casefold()
                if pos is None:   # EDSM didn't know it
                    db.execute("INSERT INTO systems (key, name, checked) VALUES (?, ?, ?)", (key, name, time.time()))
                else:
                    db.execute("INSERT INTO systems VALUES (?, ?, ?, ?, ?, 'test', ?)", (key, name, *pos, time.time()))
            db.commit()
            db.close()
        self.jdir = self.dir / "journal"
        self.jdir.mkdir()
        files = self.journal if self.journal and isinstance(self.journal[0], tuple) else [("Journal.2026-10-28T000000.01.log", self.journal)]
        for i, item in enumerate(files):   # (name, events) or (name, events, age in seconds)
            fname, events = item[0], item[1]
            path = self.jdir / fname
            path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
            stamp = time.time() - (item[2] if len(item) > 2 else (len(files) - i) * 60)   # older files first
            os.utime(path, (stamp, stamp))
            self.jfile = path
        if self.status is not None:
            self.write_status(self.status)
        if self.navroute is not None:
            (self.jdir / "NavRoute.json").write_text(json.dumps(self.navroute), encoding="utf-8")
        self.cmds = self.dir / "cmds.txt"
        self.cmds.write_text("", encoding="utf-8")

    def start(self, wait_syst=True):
        self._write_files()
        self.simapp = SimApp()
        self.simapp.start()
        self.port = free_port()
        return self._launch(wait_syst)

    def restart(self):
        """Stop the script and run it again in the same folder, on the same port - as when you
        close it and start it again with a page still open."""
        if self.stub:
            self.stub.close()
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(5)
        self.logf.close()
        self.cmds.write_text("", encoding="utf-8")   # the simulated UFC starts afresh
        return self._launch(wait_syst=False)

    def start_again(self):
        """Run the script again in the same folder, on the same port, with this copy still running - as when its page was
        closed without Exit and you start it again. The first copy is kept as self.old (stopped with the rest)."""
        if self.stub:
            self.stub.close()
            self.stub = None
        self.old = self.proc
        self.logf.close()
        self.cmds.write_text("", encoding="utf-8")
        return self._launch(wait_syst=False)

    def _launch(self, wait_syst=True):
        dead = "http://127.0.0.1:9"   # no internet: anything that tries EDSM or Spansh fails at once
        env = dict(os.environ, UFC_CMDS=str(self.cmds), EDTB_SIMAPP_PORT=str(self.simapp.port), PYTHONUNBUFFERED="1",
                   FT3000_DATA=str(self.dir),   # (its data beside it, as before 3.01.42 - not in this PC's Saved Games)
                   https_proxy=dead, HTTPS_PROXY=dead, http_proxy=dead, HTTP_PROXY=dead, no_proxy="", NO_PROXY="")
        if self.ai:
            env["FAKE_AI_DIR"] = str(self.dir / "fakeai")
        env.update(self.env)
        if self.ufc:
            env["PYTHONPATH"] = str(HERE / "fakehid") + os.pathsep + env.get("PYTHONPATH", "")
        args = [sys.executable, str(self.dir / SCRIPT.name)] + self.options()
        mark = len(self.log())   # a restart adds to the same log
        self.logf = open(self.dir / "server.log", "a", encoding="utf-8")
        self.proc = subprocess.Popen(args + self.extra_args, cwd=str(self.dir), env=env, stdout=self.logf, stderr=subprocess.STDOUT)
        self.url = f"http://127.0.0.1:{self.port}"
        self.wait(lambda: (self.state() or {}).get("note") == "", timeout=20, what="the journal to load")
        if self.edsm and not self.no_edsm and wait_syst:
            self.wait(lambda: ((self.state() or {}).get("syst") or {}).get("status") in ("ok", "stale", "empty"), timeout=20,
                      what="the System tab data")
        if self.ufc:
            self.wait(lambda: "UFC connected" in self.log()[mark:], timeout=10, what="the UFC")
            if self.stub_page:
                self.stub_open()
        return self

    def ai_replies(self, *replies):
        """The stand-in AI's next replies, in order (text, or an object sent as JSON) - after them, ones that fit."""
        (self.dir / "fakeai").mkdir(exist_ok=True)
        (self.dir / "fakeai" / "replies.json").write_text(json.dumps(list(replies)), encoding="utf-8")

    def ai_calls(self):
        """What the stand-in AI has been asked: [{"instruction", "system", "input"}]."""
        try:
            return [json.loads(x) for x in (self.dir / "fakeai" / "calls.jsonl").read_text(encoding="utf-8").splitlines() if x]
        except OSError:
            return []

    def options(self):
        """The command line it's started with (a subclass can start it otherwise - with its settings deciding, say)."""
        engine = ["--engine", "claude", "--cli-path", str(HERE / "fakeai" / "claude")] if self.ai else ["--engine", "none"]
        args = engine + ["--journal-dir", str(self.jdir), "--port", str(self.port), "--no-browser",
                         "--bindings-dir", str(FIX / "bindings")]
        if not self.ufc:
            args.append("--no-ufc")
        if self.no_edsm:   # no online lookups at all (EDSM or Spansh)
            args += ["--no-edsm", "--no-spansh"]
        return args

    def stub_open(self, pid="harness"):
        """A stand-in page opens: the UFC shows its menu (and it comes back after a restart)."""
        if self.stub:
            self.stub.close()
        self.stub_page, self.stub = True, PageStub(self.url, pid)
        self.stub.start()
        self.stub.ready.wait(5)
        self.post("/api/bootfx", {"fx": "", "page": pid})
        self.wait(lambda: self.display()["options"] != [""] * 5 or None, timeout=5, what="the UFC menu")

    def unstub(self):
        """The stand-in page closes for good (the displays follow a real page, or blank, once the board stops
        counting it)."""
        self.stub_page = False
        if self.stub:
            self.stub.close()
            self.stub = None

    def stop(self):
        if self.stub:
            self.stub.close()
        old = getattr(self, "old", None)
        if old and old.poll() is None:
            old.kill()
            old.wait(5)
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.simapp:
            self.simapp.stop()
        if getattr(self, "logf", None):
            self.logf.close()
        if self.dir and not KEEP:
            shutil.rmtree(self.dir, ignore_errors=True)

    # ---- talking to it ----
    def get(self, path, timeout=5):
        with NO_PROXY.open(self.url + path, timeout=timeout) as r:
            return r.status, r.read()

    def state(self):
        try:
            return json.loads(self.get("/api/state")[1])
        except Exception:
            return None

    def post(self, path, body=None):
        req = urllib.request.Request(self.url + path, data=json.dumps(body or {}).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with NO_PROXY.open(req, timeout=5) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def bus(self):
        """The UFC event stream's current record (its first message)."""
        with NO_PROXY.open(self.url + "/api/events", timeout=5) as r:
            for raw in r:
                line = raw.decode("utf-8").strip()
                if line.startswith("data: "):
                    return json.loads(line[6:])
        return None

    def ufc_cmd(self, *cmds, pause=0.35):
        """Simulated UFC: 'press NAME', 'pulse NAME', 'hold NAME SECONDS', 'dial OFFSET VALUE'."""
        for c in cmds:
            with open(self.cmds, "a", encoding="utf-8") as f:
                f.write(c + "\n")
            time.sleep(pause)

    def display(self):
        return self.simapp.display()

    def add(self, *events):
        """Append live events to the newest journal file (timestamped now unless given)."""
        with open(self.jfile, "a", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps(dict({"timestamp": iso(now())}, **e)) + "\n")

    def write_status(self, data):
        tmp = self.jdir / "Status.tmp"
        tmp.write_text(json.dumps(dict({"timestamp": iso(now()), "event": "Status"}, **data)), encoding="utf-8")
        os.replace(tmp, self.jdir / "Status.json")

    def log(self):
        try:
            return (self.dir / "server.log").read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def wait(self, pred, timeout=10.0, step=0.15, what="the condition"):
        end = time.time() + timeout
        last = None
        while time.time() < end:
            try:
                last = pred()
            except Exception:
                last = None
            if last:
                return last
            if self.proc and self.proc.poll() is not None:
                raise AssertionError(f"the board stopped while waiting for {what}:\n{self.log()[-3000:]}")
            time.sleep(step)
        raise AssertionError(f"timed out waiting for {what}\n--- server log ---\n{self.log()[-3000:]}")


# ---- golden files: what the board said last time, so a change in behaviour shows up ----
_TS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?")
_VOLATILE = {"now", "live", "updated", "fetched", "ages", "pasted", "journal", "checked", "t", "age", "uplink", "uplinking",
             "incept"}   # (a subject file's incept date: so many days before its contract was accepted, so it moves with the day the test runs)


def normalise(x, key=None):
    """Times (which depend on when the test ran) become placeholders; everything else stays."""
    if key in _VOLATILE and x not in (None, "", {}, []):
        return "<varies>"
    if isinstance(x, dict):
        return {k: normalise(v, k) for k, v in x.items()}
    if isinstance(x, list):
        return [normalise(v) for v in x]
    if isinstance(x, str):
        return _TS.sub("<time>", x)
    if isinstance(x, float):
        return round(x, 4)
    return x


def check_golden(test, name, data):
    path = GOLDEN / f"{name}.json"
    text = json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    if UPDATE_GOLDEN or not path.exists():
        GOLDEN.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return
    old = path.read_text(encoding="utf-8")
    if old != text:
        diff = "".join(difflib.unified_diff(old.splitlines(True), text.splitlines(True), f"golden/{name}.json", "now", n=2))
        test.fail(f"{name} differs from its golden file:\n{diff[:6000]}")
