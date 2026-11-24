"""The README's screenshots (docs/*.png), taken from the real board and page with the tests' made-up journals
(CMDR Deckard), a simulated UFC and no internet - so anyone can take them again after a change to the look:

    python tests/make_screenshots.py              (needs Playwright, as the page tests do)

Each is taken at 1920 x 1080 and saved with a small palette (the terminal's few greens), to keep the files small."""
from __future__ import annotations

import json
import math
import os
import stat
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import journals   # noqa: E402
from harness import Board, FIX, iso, now   # noqa: E402

OUT = HERE.parent / "docs"
W, H = 1920, 1080
R = 1500000.0   # HIP 20277 3 b's radius (journals.NEAR_HAO)
PLANET = "HIP 20277 3 b"
HAO = "Hao Extraction Prospect"

STORY = ("Kirsten Vance learned to fly in the debris rings over Carthage, running salvage for a scrap-dealer uncle who "
         "paid in ration chits and bruises. When the Black Sun Crew bought out his yard she went with it - first as a "
         "spotter, then as the one who did the cutting. Six years on she flies a Python she calls Lullaby, keeps a "
         "ledger of every hull she's opened, and has never once been late to an ambush. The Carthage Defence Force has "
         "posted nine bounties on her. She has collected two of them herself, under other names.")

FAKE_CLI = '''#!/usr/bin/env python3
# Stands in for Claude Code: logged in with a subscription; writes a short backstory for anyone asked about.
import json, sys
if sys.argv[1:3] == ["auth", "status"]:
    print(json.dumps({"loggedIn": True, "authMethod": "claude.ai"}))
else:
    sys.stdin.read()
    print("A name on a bounty board, and not much else yet - a pilot who keeps moving and pays in cash.")
'''


class ShotBoard(Board):
    """A board started as someone would start it: its settings deciding (here: the test journals, AUTO with a stand-in
    Claude Code), and backstories already written for some targets."""

    def __init__(self, *a, stories=None, **kw):
        super().__init__(*a, **kw)
        self.stories = stories or {}

    def _write_files(self):
        super()._write_files()
        cli = self.dir / "claude"
        cli.write_text(FAKE_CLI, encoding="utf-8")
        cli.chmod(cli.stat().st_mode | stat.S_IEXEC)
        (self.dir / "settings.json").write_text(json.dumps({"journal_dir": str(self.jdir), "engine": "auto", "open_page": False}),
                                                encoding="utf-8")
        if self.stories:
            t = iso(now())
            (self.dir / "target_backstories.json").write_text(json.dumps(
                {k: {"name": n, "status": "done", "updated": t, "text": v} for k, (n, v) in self.stories.items()}), encoding="utf-8")

    def options(self):
        return ["--port", str(self.port), "--bindings-dir", str(FIX / "bindings"), "--cli-path", str(self.dir / "claude")]


def save(page, name, crop=None):
    from PIL import Image
    OUT.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp()) / "shot.png"
    page.screenshot(path=str(tmp))
    img = Image.open(tmp).convert("RGB")
    if crop:
        img = img.crop(crop)
    img = img.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    img.save(OUT / f"{name}.png", optimize=True)
    print(f"docs/{name}.png  {(OUT / f'{name}.png').stat().st_size // 1024} KB")


def settle(page, secs=2.5):
    time.sleep(secs)   # (text effects and the screen's pull settle)


def main():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        def open_page(b, intro=False):
            b.unstub()
            page = browser.new_page(viewport={"width": W, "height": H})
            page.goto(b.url + "/")
            page.wait_for_function("() => document.querySelector('.tab.on') !== null", timeout=10000)
            if not intro:
                page.click("#boot")
                page.wait_for_function("() => document.getElementById('boot').hidden", timeout=5000)
            return page

        def go(page, tab, key=None):
            page.click(f'.tab[data-tab="{tab}"]')
            page.wait_for_function(f"() => ED.view.tab === {json.dumps(tab)}")
            if key:
                page.click(f'#subtabs .stab[data-key="{key}"]')
                page.wait_for_function(f"() => document.querySelector('#subtabs .stab.on').dataset.key === '{key}'")

        # 1 Home: the case file, the local situation, the session's log
        with ShotBoard("shot_home", **journals.home()) as b:
            page = open_page(b)
            go(page, "home")
            settle(page)
            save(page, "home")
            page.close()

        # 3 Contracts: the missions, a target's dossier and backstory
        with ShotBoard("shot_contracts", stories={"kirsten vance": ("Kirsten Vance", STORY)}, **journals.contracts()) as b:
            page = open_page(b)
            go(page, "contracts", 1)
            page.click('#list .item[data-key="kirsten vance"]')
            settle(page, 3.5)
            save(page, "contracts")
            page.close()

        def pick(page, name):   # (2 Nav > 1 Syst's list)
            key = page.evaluate(f"() => ED.S.data.syst.entries.find(e => e.name === {json.dumps(name)}).key")
            page.click(f'#sy-list .srow[data-key="{key}"]')
            page.wait_for_function(f"() => document.getElementById('sy-name').textContent === {json.dumps(name)}")

        # 2 Nav > 1 Syst: the list (a planet), the map, and a settlement's schematic (its layout confirmed, its heading
        # known; maximised, with its terminals, doors and expendables shown)
        lodge, lodge_key = "Dhaenens's Lodgings", "m:3814631936"
        with ShotBoard("shot_syst", **journals.syst()) as b:
            b.post("/api/settlement-layout", {"key": lodge_key, "layout": "tourist-4", "name": lodge})
            b.post("/api/settlement-heading", {"key": lodge_key, "layout": "tourist-4", "heading": 45, "name": lodge})
            page = open_page(b)
            go(page, "nav", 1)
            pick(page, PLANET)
            settle(page, 4)
            save(page, "syst-list")
            pick(page, lodge)
            page.click("#sy-max")
            settle(page, 0.5)
            page.click("#sy-sch")
            settle(page, 3)
            for icons in ("term", "door", "exp"):
                page.click(f'#sy-icons button[data-ic="{icons}"]')
            settle(page, 2)
            save(page, "schematic")
            page.click('#syst-rail .syview button[data-view="map"]')
            settle(page, 4)
            save(page, "system-map")
            page.close()

        # 2 Nav > 2 Traj: gliding in towards Hao Extraction Prospect (ENTRY 1)
        with ShotBoard("shot_traj", **journals.syst()) as b:
            page = open_page(b)
            b.add({"event": "Undocked", "StationName": "Fabian City"})
            go(page, "nav", 2)
            for i in range(5):
                b.write_status(dict(journals.NEAR_HAO, Latitude=round(-13.1 - 0.004 * i, 6), Longitude=round(34.9 - 0.002 * i, 6),
                                    Altitude=4200 - 250 * i, Flags2=1 << 12, Destination={"Name": HAO}))   # (Flags2: gliding)
                time.sleep(1.0)
            page.wait_for_function("() => ED.trajGuide().ok", timeout=10000)
            settle(page, 1.5)
            save(page, "traj")
            page.close()

        # 2 Nav > 3 Wpt, 4 HSI, 5 Atk (PLAN, then ATTACK: the mine-release computer): three waypoints in a flight plan and a
        # mark, then Hao designated and an attack plan built round it, on a level run in towards it
        with ShotBoard("shot_nav", **journals.syst()) as b:
            page = open_page(b)
            y = b.state()["syst"]
            hao = next(e for e in y["entries"] if e["name"] == HAO)
            lat0, lon0 = hao["pic"]["lat"], hao["pic"]["lon"]
            from_hao = lambda n, e: (round(lat0 + n / R * 180 / math.pi, 6), round(lon0 + e / (R * math.cos(math.radians(lat0))) * 180 / math.pi, 6))
            b.add({"event": "Undocked", "StationName": "Fabian City"})
            ws = [b.post("/api/tgt", {"op": "add", "body": PLANET, "lat": la, "lon": lo, "method": "manual", "name": name})[1]["tgt"]
                  for (la, lo), name in ((from_hao(-400, -2800), "Dry riverbed"), (from_hao(700, -1200), "IP Hao"),
                                         (from_hao(2500, 3500), "Ridge gap"))]
            for w in ws:
                b.post("/api/nav", {"op": "seq", "seq": 1, "act": "ins", "id": w["id"]})
            b.post("/api/nav", {"op": "setseq", "seq": "1"})
            la, lo = from_hao(-1500, -6500)
            b.post("/api/nav", {"op": "mark", "body": PLANET, "lat": la, "lon": lo, "method": "overfly"})
            go(page, "nav", 3)
            page.click(f'#tg-list [data-key="{ws[1]["key"]}"]')
            settle(page, 2)
            save(page, "wpt")
            # flying east at 150 m/s, 1,000 m up, 60 m north of Hao's line, towards the release point
            grav = next(e for e in y["entries"] if e["name"] == PLANET)["gravity"]
            throw = 150 * min(10, math.sqrt(2 * 1000 / (grav * 9.80665)))

            def reading(i):
                la, lo = from_hao(60, -throw - 2400 + 150 * i)
                b.write_status(dict(journals.NEAR_HAO, Latitude=la, Longitude=lo, Altitude=1000, Heading=90))
            for i in range(3):
                reading(i)
                time.sleep(1.0)
            go(page, "nav", 4)
            page.wait_for_function("() => ED.hsiSolve().fix && ED.hsiSolve().dist != null", timeout=10000)
            page.evaluate("() => { ED.hsi.zoom = 20000; }")
            settle(page)
            save(page, "hsi")
            b.post("/api/nav", {"op": "dsg", "key": hao["key"]})
            go(page, "nav", 5)
            page.click("#ak-build")
            settle(page, 0.5)
            page.click("#ak-build")   # (twice: BUILD, then CONFIRM)
            page.wait_for_function("() => ED.S.data.syst.nav.built", timeout=5000)
            settle(page, 2)
            save(page, "atk-plan")
            page.click('#ak-mode button[data-v="atk"]')
            for i in range(3, 9):
                reading(i)
                time.sleep(1.0)
            page.wait_for_function("() => ED.atkSolve().ok && ED.atkSolve().track && ED.atkSolve().tau > 2", timeout=10000)
            save(page, "ccrp")
            page.close()

        # 2 Nav > 6 Hist: everywhere you've been
        j = journals.history()
        with ShotBoard("shot_hist", journal=j["journal"], status=j["status"]) as b:
            b.wait(lambda: (b.state().get("hist") or {}).get("ready") or None, timeout=20, what="the old journals read")
            page = open_page(b)
            go(page, "nav", 6)
            settle(page, 3)
            save(page, "hist")
            page.close()

        # 4 Setup: Controls, Settings
        with ShotBoard("shot_setup", **journals.syst()) as b:
            page = open_page(b)
            go(page, "setup", 1)
            page.wait_for_function("() => document.querySelectorAll('#ct-jobs .ctrow').length > 30")
            settle(page)
            save(page, "controls")
            def windows_paths(route):   # (this runs where the tests do: the folders shown as they'd be on a PC)
                try:
                    v = route.fetch().json()
                except Exception:   # (the board closing)
                    route.abort()
                    return
                me = "C:\\Users\\Deckard"
                j = v["settings"]["journal_dir"]
                j.update(value="", found=412, folder=me + "\\Saved Games\\Frontier Developments\\Elite Dangerous",
                         default=me + "\\Saved Games\\Frontier Developments\\Elite Dangerous", running=me + "\\Saved Games\\Frontier Developments\\Elite Dangerous")
                v["about"].update(program=me + "\\Documents\\UCEC FT3000", data=me + "\\Saved Games\\UCEC FT3000", bindings=["Custom.4.0.binds"])
                route.fulfill(json=v)
            page.route("**/api/settings", windows_paths)
            go(page, "setup", 2)
            page.wait_for_function("() => /CLAUDE/i.test(document.getElementById('st-einfo').textContent)")
            settle(page)
            save(page, "settings")
            page.close()

        # the UFC diagram (docs/ufc-controls.html), in the terminal's typeface
        import base64
        html = (OUT / "ufc-controls.html").read_text(encoding="utf-8")
        font = base64.b64encode((HERE.parent / "web" / "vga.woff").read_bytes()).decode("ascii")
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        page.set_content(html.replace('url("../web/vga.woff")', f'url("data:font/woff;base64,{font}")'))
        page.evaluate("() => document.fonts.ready")
        settle(page, 0.5)
        save(page, "ufc-controls")
        page.close()

        # the terminal starting up (its BIOS screen)
        with ShotBoard("shot_boot", **journals.syst()) as b:
            page = open_page(b, intro=True)
            page.wait_for_function("() => /Detecting input signal.*(Found|None)/.test(document.getElementById('bt-text').textContent)", timeout=30000)
            save(page, "boot", crop=(0, 0, W, 330))   # (switched on, warmed up, the BIOS's checks done: the game found)
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
