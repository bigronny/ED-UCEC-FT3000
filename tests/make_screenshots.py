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


def east(m, lat0=-13.1, lon0=34.9):
    return round(lon0 + m / (R * math.cos(math.radians(lat0))) * 180 / math.pi, 6)


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

        # 2 Nav: the system map; the HSI flying a flight plan, with a target
        with ShotBoard("shot_nav", **journals.syst()) as b:
            page = open_page(b)
            go(page, "nav", 1)
            page.click('#syst-rail .syview button[data-view="map"]')
            settle(page, 4)
            save(page, "system-map")
            b.add({"event": "Undocked", "StationName": "Fabian City"})
            ws = [b.post("/api/tgt", {"op": "add", "body": PLANET, "lat": la, "lon": lo, "method": "manual"})[1]["tgt"]
                  for la, lo in ((-13.1, east(1500)), (-13.06, east(5000)), (-13.13, east(9000)))]
            for w in ws:
                b.post("/api/nav", {"op": "seq", "seq": 1, "act": "ins", "id": w["id"]})
            b.post("/api/nav", {"op": "setseq", "seq": "1"})
            go(page, "nav", 4)
            for i in range(5):   # east at 150 m/s, 800 m up
                b.write_status(dict(journals.NEAR_HAO, Latitude=-13.1, Longitude=east(150 * i), Altitude=800, Heading=90))
                time.sleep(1.0)
            page.wait_for_function("() => ED.hsiSolve().fix && ED.hsiSolve().dist != null", timeout=10000)
            b.ufc_cmd("press ILS", "press Opt4")   # DSG: the steer-to point, the target
            page.evaluate("() => { ED.hsi.zoom = 20000; }")
            settle(page)
            save(page, "hsi")
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

        # the terminal starting up (its BIOS screen)
        with ShotBoard("shot_boot", **journals.syst()) as b:
            page = open_page(b, intro=True)
            page.wait_for_function("() => /Detecting input signal.*(Found|None)/.test(document.getElementById('bt-text').textContent)", timeout=30000)
            save(page, "boot", crop=(0, 0, W, 330))   # (switched on, warmed up, the BIOS's checks done: the game found)
            page.close()
        browser.close()


if __name__ == "__main__":
    main()
