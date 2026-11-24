"""The page in a real browser (Chromium via Playwright), against a running board.
What each tab shows is compared with golden files (times blanked out), and every
interaction checks the page reacts - clicks, the simulated UFC, jumps, start-ups.
Skipped if Playwright isn't installed (pip install playwright; playwright install chromium)."""
import json
import math
import re
import time
import unittest

import journals
from harness import Board, check_golden, SC_FLAGS, DOCKED_FLAGS, ahead, ago

try:
    from playwright.sync_api import sync_playwright
except ImportError:   # pragma: no cover
    sync_playwright = None

W, H = 1920, 1080
_TIME_PATTERNS = [
    (re.compile(r"\b\d+[smhd] ago\b", re.I), "# ago"),
    (re.compile(r"\b(\d+d )?(\d+h )?\d+m\b", re.I), "#t"),
    (re.compile(r"\b\d+d \d+h\b", re.I), "#t"),
    (re.compile(r"\b\d{2}:\d{2}(:\d{2})?\b"), "#:#"),
    (re.compile(r"\b\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", re.I), "# Mon"),
    (re.compile(r"\b\d+s\b(?! ago)", re.I), "#s"),
]

FINGERPRINT_JS = r"""() => {
  const vis = (el) => !!el && el.offsetParent !== null && getComputedStyle(el).visibility !== 'hidden';
  const txt = (sel) => { const el = Array.from(document.querySelectorAll(sel)).find(vis); return el ? el.innerText : null; };
  const app = document.getElementById('app');
  const tab = document.querySelector('.tab.on');
  const view = document.querySelector('#syst-rail .syview button.on') || document.querySelector('.smtop .syview button.on');
  return {
    tab: tab ? tab.dataset.tab : null,
    sub: txt('#subtabs'),
    view: view ? view.dataset.view : null,
    app: Array.from(app.classList).filter(c => ['idle', 'ocor', 'syst', 'symap', 'hyper'].includes(c)).sort(),   // the layout
    strip: txt('.strip'),
    rail: txt('nav.rail'),
    panel: txt('main.panel'),
    map: vis(document.getElementById('symap')) ? (txt('#sm-lab') + ' | ' + txt('#sm-info')) : null,
    hyper: vis(document.getElementById('hyper')),
    boot: !document.getElementById('boot').hidden,
    halt: !document.getElementById('halt').hidden,
  };
}"""

CANVAS_INK_JS = r"""(id) => {
  const cv = document.getElementById(id);
  if (!cv || !cv.width) return 0;
  const ctx = cv.getContext('2d'), d = ctx.getImageData(0, 0, cv.width, cv.height).data;
  let ink = 0;
  for (let i = 0; i < d.length; i += 4 * 97) if (d[i] + d[i + 1] + d[i + 2] > 120) ink++;
  // a pixelated canvas has fewer, bigger pixels: count as if it were drawn at full resolution
  const r = devicePixelRatio || 1, full = cv.clientWidth * r * cv.clientHeight * r;
  return Math.round(ink * Math.max(1, full / (cv.width * cv.height)));
}"""


def norm(text):
    if text is None:
        return None
    for rx, rep in _TIME_PATTERNS:
        text = rx.sub(rep, text)
    return text


def norm_fp(fp):
    return {k: norm(v) if isinstance(v, str) else v for k, v in fp.items()}


@unittest.skipIf(sync_playwright is None, "Playwright isn't installed")
class PageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def open(self, board, path="/", intro=False, viewport=(W, H)):
        board.unstub()   # the UFC follows this page now
        page = self.browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})
        self.errors = []
        page.on("pageerror", lambda e: self.errors.append(f"page error: {e}"))
        page.on("console", lambda m: self.errors.append(f"console: {m.text}")
                if m.type == "error" and "status of 400" not in m.text else None)   # a rejected paste answers 400 on purpose
        page.goto(board.url + path)
        page.wait_for_function("() => document.querySelector('.tab.on') !== null", timeout=10000)
        if not intro and "#" not in path:   # the terminal powers on first: tap to skip it (a #preview replaces it)
            self.skip_intro(page)
        return page

    def skip_intro(self, page):
        page.click("#boot")
        page.wait_for_function("() => document.getElementById('boot').hidden", timeout=5000)

    def fp(self, page, settle=True):
        """What the page shows, once it has stopped changing (text effects take a moment)."""
        last = None
        end = time.time() + 6
        while time.time() < end:
            cur = norm_fp(page.evaluate(FINGERPRINT_JS))
            if settle and cur != last:
                last = cur
                time.sleep(0.7)
                continue
            return cur
        return last

    def until(self, page, js, timeout=10, what="the page"):
        try:
            page.wait_for_function(js, timeout=timeout * 1000)
        except Exception:
            self.fail(f"timed out waiting for {what}: {js}")

    def no_errors(self):
        self.assertEqual(self.errors, [], "the page reported errors")

    def go(self, page, tab, key=None):
        """Click a tab, and one of its sub-tabs (1 Syst, 2 Traj, 3 Wpt, 4 HSI, 5 Atk, 6 Hist; 1 Active, 2 History, 3 OCOR)."""
        page.click(f'.tab[data-tab="{tab}"]')
        self.until(page, f"() => ED.view.tab === {json.dumps(tab)}", what=f"the {tab} tab")
        if key:
            page.click(f'#subtabs .stab[data-key="{key}"]')
            self.until(page, f"() => document.querySelector('#subtabs .stab.on').dataset.key === '{key}'", what=f"sub-tab {key}")

    def on(self, page, tab, sub, what="the page"):
        self.until(page, f"() => ED.view.tab === {json.dumps(tab)} && ED.view.sub === {sub}", what=what)


class Contracts(PageTest):
    def test_contracts(self):
        with Board("p_contracts", **journals.contracts()) as b:
            page = self.open(b)
            first = self.fp(page)
            self.assertEqual(first["tab"], "contracts")   # there are contracts: start on them
            check_golden(self, "page_contracts_first", first)
            keys = page.eval_on_selector_all("#list .item", "els => els.map(e => e.dataset.key)")
            panels = {}
            for k in keys:
                page.click(f'#list .item[data-key="{k}"]')
                self.until(page, f"""() => document.querySelector('#list .item.sel').dataset.key === {json.dumps(k)}""")
                panels[k] = self.fp(page)["panel"]
            check_golden(self, "page_contracts_panels", panels)
            self.assertIn("SHIELDS", panels["kirsten vance"].upper())
            # the UFC: ILS (the page menu), turn the knob, pull to select
            b.ufc_cmd("press ILS", "pulse COMM1_CW", "pulse COMM1_CW")
            self.until(page, "() => document.querySelector('#list .item.cur') !== null", what="the UFC highlight")
            cur = page.eval_on_selector("#list .item.cur", "e => e.dataset.key")
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, f"() => document.querySelector('#list .item.sel').dataset.key === {json.dumps(cur)}", what="the pull to select")
            # the copy button beside Location: a COMM2 pull copies the contract's system
            page.click('#list .item[data-key="m:2005"]')   # the courier job to Carthage
            self.until(page, "() => document.getElementById('f-clip').dataset.clip === 'Carthage'", what="the copy button for Carthage")
            sys_ = "Carthage"
            b.ufc_cmd("press COMM2_PULL")
            b.wait(lambda: f"Copy button: {sys_} - copied" in b.log() or None, what="the system copied")
            self.until(page, "() => /PASTE/i.test(document.getElementById('f-clip').textContent)", what="Paste next")
            # tabs from the UFC: the option buttons pick a tab (again: its next sub-tab), the keypad a sub-tab
            for btn, tab, sub in (("Opt1", "home", 1), ("Opt2", "nav", 1), ("2", "nav", 3), ("1", "nav", 1), ("1", "nav", 2),
                                  ("Opt2", "nav", 3), ("Opt2", "nav", 4), ("Opt2", "nav", 5), ("Opt2", "nav", 6), ("Opt2", "nav", 7), ("Opt2", "nav", 2),
                                  ("3", "nav", 4), ("4", "nav", 5), ("5", "nav", 6), ("6", "nav", 7), ("1", "nav", 2), ("Opt3", "contracts", 1), ("3", "contracts", 3),
                                  ("Opt3", "contracts", 1), ("2", "contracts", 2), ("9", "contracts", 2), ("Opt1", "home", 1),
                                  ("Opt3", "contracts", 2)):
                b.ufc_cmd(f"press {btn}")
                self.on(page, tab, sub, what=f"{btn}: {tab} page {sub}")
                self.until(page, f"() => document.querySelector('.tab.on').dataset.tab === '{tab}'", what=f"the {tab} tab")
            self.no_errors()


class Home(PageTest):
    def test_home(self):
        with Board("p_home", **journals.home()) as b:
            page = self.open(b)
            fp = self.fp(page)
            self.assertEqual(fp["tab"], "home")
            check_golden(self, "page_home", fp)
            self.go(page, "contracts", 1)
            fp = self.fp(page)
            self.assertIn("NO CONTRACTS", (fp["rail"] or "").upper())
            check_golden(self, "page_home_contracts_empty", fp)
            self.no_errors()


class Ocor(PageTest):
    def test_ocor(self):
        with Board("p_ocor", **journals.ocor()) as b:
            page = self.open(b)
            self.go(page, "contracts", 3)
            self.until(page, "() => document.querySelector('#ob-list .item .ly') !== null", what="the distances")
            check_golden(self, "page_ocor", self.fp(page))
            page.click('#ob-list .item[data-oid="o4"]')
            check_golden(self, "page_ocor_o4", self.fp(page)["panel"])
            # fetch a briefing again through the paste box
            page.click("#ob-paste")
            self.until(page, "() => !document.getElementById('paste').hidden", what="the paste box")
            page.fill("#pd-text", "no objectives in this")
            page.click("#pd-load")
            self.until(page, "() => /No objectives/.test(document.getElementById('pd-msg').textContent)", what="the error")
            text = (__import__("harness").FIX / "ocor_briefing.txt").read_text(encoding="utf-8")
            page.fill("#pd-text", text)
            page.click("#pd-load")
            self.until(page, "() => document.getElementById('paste').hidden", what="the paste box to close")
            self.until(page, "() => document.querySelectorAll('#ob-list .item').length === 5", what="the new briefing")
            self.no_errors()


class Syst(PageTest):
    def test_syst(self):
        with Board("p_syst", **journals.syst()) as b:
            page = self.open(b)
            self.go(page, "nav", 1)
            self.until(page, "() => document.querySelector('#sy-list .srow.sel') !== null", what="the list")
            fp = self.fp(page)
            self.assertEqual(fp["view"], "list")
            check_golden(self, "page_syst_list", fp)
            # every entry has its icon (icons.js): a pixel picture, not a character
            n = page.evaluate("() => [document.querySelectorAll('#sy-list .srow').length, document.querySelectorAll('#sy-list .srow svg.ico path').length]")
            self.assertEqual(n[0], n[1])
            self.assertEqual(page.evaluate("() => ED.icon('star') === ED.icon('star') && ED.icon('star') !== ED.icon('planet') && !!ED.ICONS.megaship"), True)
            docked = page.eval_on_selector("#sy-list .srow.sel", "e => e.dataset.key")
            # where the selected item comes from (top right), and the uplink button under Commanders here
            self.assertEqual(page.inner_text("#sy-age").upper(), "SPANSH")
            self.assertEqual(page.inner_text("#sy-up").upper().split(), "SYSTEM DATA UPLINK SYNCHRONISE".split())
            self.assertRegex(page.inner_text("#sy-upt").upper(), r"^LAST UPLINK \d{1,2} [A-Z]{3} \d{4} \d\d:\d\d$")
            page.click("#sy-up")   # no internet here: it tries for a moment, then fails (keeping what's shown)
            self.until(page, "() => /IN PROGRESS/i.test(document.getElementById('sy-up').innerText)", timeout=3, what="uplink in progress")
            self.until(page, "() => /FAILED/i.test(document.getElementById('sy-up').innerText)", timeout=10, what="uplink failed")
            self.assertIn("SPANSH UNREACHABLE", page.inner_text("#sy-upt").upper())
            self.until(page, "() => document.getElementById('sy-up').classList.contains('wait')", timeout=10, what="dimmed until it can be pressed again")
            self.assertTrue(page.evaluate("() => document.getElementById('sy-up').disabled"))
            # pick a planet yourself: Manual; AUTO goes back to where you are
            planet = next(e["key"] for e in b.state()["syst"]["entries"] if e["name"] == "HIP 20277 3 b")
            page.click(f'#sy-list .srow[data-key="{planet}"]')
            self.until(page, "() => document.getElementById('sy-man').classList.contains('on')", what="Manual")
            check_golden(self, "page_syst_planet", self.fp(page)["panel"])
            page.click("#sy-auto")
            self.until(page, f"() => document.querySelector('#sy-list .srow.sel').dataset.key === {json.dumps(docked)}", what="Auto")
            # the picture: COMM2 moves the focus to it, the dials grab and turn it
            b.ufc_cmd("press ILS")   # the page menu
            self.until(page, "() => document.getElementById('sy-sw').classList.contains('focus')", what="the switch focus")
            b.ufc_cmd("pulse COMM2_CW")
            self.until(page, "() => document.getElementById('sy-pic').classList.contains('focus')", what="the picture focus")
            rot = page.evaluate("() => ED.S.syRot")
            b.ufc_cmd("dial 7 3900")   # COMM2 VOLUME well clockwise: it spins the planet (the other way, and fast)
            self.until(page, f"() => Math.abs(((ED.S.syRot - {rot} + 540) % 360) - 180) > 20", what="the dial to spin the picture")
            self.assertFalse(page.evaluate("() => document.getElementById('sy-pic').classList.contains('grab')"), "a dial doesn't grab it")
            b.ufc_cmd("dial 7 2000")   # back to the middle: it stays where it was left
            time.sleep(0.4)
            rot = page.evaluate("() => ED.S.syRot")
            time.sleep(0.8)
            self.assertAlmostEqual(page.evaluate("() => ED.S.syRot"), rot, places=3, msg="no spin of its own once turned")
            # the map: the keypad's 1 again (Syst showing) flips to it
            b.ufc_cmd("press 1")
            self.until(page, "() => document.getElementById('app').classList.contains('symap')", what="the map")
            time.sleep(1.0)
            self.assertGreater(page.evaluate(CANVAS_INK_JS, "sm-cv"), 200, "the map canvas is empty")
            marks = page.evaluate("""() => ED.S.map.lay.flat.filter(n => n.t === 'station' || n.t === 'carrier')
                                       .map(n => [n.t === 'carrier' ? 'carrier' : n.d.icon, !!n.drawR])""")
            self.assertTrue(marks and all(icon for icon, _ in marks) and any(drawn for _, drawn in marks), marks)   # their list icon, in a circle (those in view)
            self.assertIn("carrier", [m[0] for m in marks])
            fp = self.fp(page)
            self.assertEqual(fp["view"], "map")
            check_golden(self, "page_syst_map", fp)
            info0 = fp["map"]
            b.ufc_cmd("pulse COMM1_CW")
            self.until(page, f"() => document.getElementById('sm-info').innerText !== {json.dumps(info0.split(' | ', 1)[1])}", what="the map cursor")
            uz = page.evaluate("() => ED.S.map.uz")
            b.ufc_cmd("dial 9 3800")   # COMM1 VOLUME turned: zooms the map in, and keeps on while it's turned
            self.until(page, f"() => ED.S.map.uz > {uz} * 1.5", what="COMM1 VOLUME to zoom the map")
            b.ufc_cmd("dial 9 2000")   # the middle: it holds
            b.ufc_cmd("press COMM1_PULL")   # pick it: back to the list with its details
            self.until(page, "() => !document.getElementById('app').classList.contains('symap')", what="the list after a pick on the map")
            self.until(page, "() => document.getElementById('sy-man').classList.contains('on')", what="Manual after the pick")
            # the page's own List / Map buttons
            page.click('#syst-rail .syview button[data-view="map"]')
            self.until(page, "() => document.getElementById('app').classList.contains('symap')", what="the map button")
            page.click('#sm-keyb')
            self.until(page, "() => document.getElementById('symap').classList.contains('key')", what="the key")
            page.click('.smtop .syview button[data-view="list"]')
            self.until(page, "() => !document.getElementById('app').classList.contains('symap')", what="the list button")
            self.no_errors()


class Uplinks(PageTest):
    def test_toggles_ticks_and_signals(self):
        """Spansh Uplink / EDSM Uplink at the bottom of the System list (Spansh off: EDSM's bodies and stations); a
        body you've scanned is ticked in the list and on the map, and says so; Spansh's signals at the bottom of a
        planet's details."""
        j = journals.syst()
        j["journal"].append({"timestamp": ago(400), "event": "Scan", "ScanType": "Detailed", "BodyName": "HIP 20277 3 b", "BodyID": 12,
                             "StarSystem": "HIP 20277", "SystemAddress": 102, "PlanetClass": "Rocky body", "Radius": 781000.0,
                             "SurfaceGravity": 0.9, "Landable": True, "DistanceFromArrivalLS": 942.0})
        with Board("p_uplinks", journal=j["journal"], status=j["status"], ufc=False) as b:
            page = self.open(b)
            self.go(page, "nav", 1)
            self.until(page, "() => document.querySelector('#sy-list .srow.sel') !== null", what="the list")
            ticks = page.evaluate("() => [...document.querySelectorAll('#sy-list .srow')].filter(r => r.querySelector('.mine')).map(r => r.textContent)")
            self.assertEqual(len(ticks), 1)
            self.assertIn("3 B", ticks[0].upper())
            self.assertEqual(page.evaluate("() => ED.S.data.syst.map.bodies.filter(x => x.mine).map(x => x.name)"), ["HIP 20277 3 b"])
            key = page.evaluate("() => ED.S.data.syst.entries.find(e => e.name === 'HIP 20277 3 b').key")
            page.click(f'#sy-list .srow[data-key="{key}"]')
            self.until(page, "() => /SCANNED BY YOU/i.test(document.getElementById('sy-chips').textContent)", what="Scanned by you")
            self.assertEqual(page.inner_text("#sy-age").upper(), "SPANSH + YOUR JOURNAL")
            key = page.evaluate("() => ED.S.data.syst.entries.find(e => e.name === 'HIP 20277 4 c').key")
            page.click(f'#sy-list .srow[data-key="{key}"]')
            self.until(page, "() => /BIOLOGY/i.test(document.getElementById('sy-grid').textContent)", what="the signals")
            cells = page.evaluate("() => [...document.querySelectorAll('#sy-grid .cell')].map(c => c.innerText.replace(/\\s+/g, ' ').trim())")
            self.assertEqual([c.split(" ")[0].upper() for c in cells[-2:]], ["SIGNALS", "BIOLOGY"])   # at the bottom
            self.assertIn("Biological 2", cells[-2])
            self.assertIn("Concha", cells[-1])
            # the toggles: both on; Spansh off - EDSM's (which places Fabian City on its planet); and back
            self.assertEqual(page.evaluate("() => ['spansh', 'edsm'].map(k => document.getElementById('sy-src-' + k).classList.contains('on'))"), [True, True])
            self.assertEqual(page.inner_text("#sy-src-spansh").upper(), "SPANSH UPLINK")
            page.click("#sy-src-spansh")
            b.wait(lambda: b.state()["syst"]["uplinking"]["spansh"] is False or None, what="Spansh Uplink off")
            self.until(page, "() => ED.S.data.syst.source === 'edsm'", what="EDSM's bodies and stations")
            self.assertFalse(page.evaluate("() => document.getElementById('sy-src-spansh').classList.contains('on')"))
            fabian = page.evaluate("() => ED.S.data.syst.entries.find(e => e.name === 'Fabian City').key")
            page.click(f'#sy-list .srow[data-key="{fabian}"]')
            self.until(page, "() => document.getElementById('sy-age').textContent.toUpperCase() === 'EDSM'", what="EDSM, top right")
            page.click("#sy-src-spansh")
            self.until(page, "() => ED.S.data.syst.source === 'spansh' && document.getElementById('sy-src-spansh').classList.contains('on')",
                       what="Spansh again")
            self.no_errors()


class Jump(PageTest):
    def run_jump(self, b, page, fuel):
        b.write_status({"Flags": SC_FLAGS | (1 << 17), "Fuel": {"FuelMain": fuel, "FuelReservoir": 0.5}, "Cargo": 16.0})
        time.sleep(1.2)
        b.add({"event": "StartJump", "JumpType": "Hyperspace", "StarSystem": "Carthage", "SystemAddress": 999, "StarClass": "B"})
        self.until(page, "() => document.getElementById('app').classList.contains('hyper')", timeout=6, what="the hyperspace overlay")
        self.until(page, "() => /B8 V/.test(document.getElementById('hy-dst-sub').textContent)", timeout=8, what="the destination star from Spansh")
        ft = page.inner_text("#hy-ft")
        self.assertIn("0.67", ft)
        time.sleep(2.0)
        self.assertGreater(page.evaluate(CANVAS_INK_JS, "hy-cv"), 200, "the hyperspace canvas is empty")
        b.write_status({"Flags": SC_FLAGS | (1 << 30), "Fuel": {"FuelMain": fuel, "FuelReservoir": 0.5}, "Cargo": 16.0})
        time.sleep(9)
        b.add({"event": "FSDJump", "StarSystem": "Carthage", "SystemAddress": 999, "StarPos": journals.CARTHAGE_POS, "JumpDist": 11.63,
               "FuelUsed": 0.6712, "FuelLevel": round(fuel - 0.6712, 4), "Body": "Carthage", "BodyType": "Star"})
        b.write_status({"Flags": SC_FLAGS, "Fuel": {"FuelMain": round(fuel - 0.6712, 4), "FuelReservoir": 0.5}, "Cargo": 16.0})
        self.until(page, "() => !document.getElementById('hy-arrive').hidden", timeout=6, what="the arrival screen")
        self.assertIn("USED 0.67", page.inner_text("#hy-ft").upper())
        self.assertEqual(page.inner_text("#hy-arrive-to").upper(), "CARTHAGE")   # in the map's corner, the map left clear
        self.assertEqual(page.evaluate("getComputedStyle(document.getElementById('hy-arrive')).backgroundColor"), "rgba(0, 0, 0, 0)")
        arrive_to = page.inner_text("#hy-arrive-back")
        self.until(page, "() => !document.getElementById('app').classList.contains('hyper')", timeout=8, what="the overlay to close")
        return arrive_to

    def test_jump_from_map(self):
        j = journals.jump()
        fuel = j.pop("fuel")
        with Board("p_jump", **j) as b:
            page = self.open(b)
            self.go(page, "nav", 1)
            page.click('#syst-rail .syview button[data-view="map"]')
            self.until(page, "() => document.getElementById('app').classList.contains('symap')", what="the map")
            arrive_to = self.run_jump(b, page, fuel)
            self.assertEqual(arrive_to.upper(), "BACK TO 2 NAV · SYST MAP")
            fp = self.fp(page)
            self.assertEqual((fp["tab"], fp["view"]), ("nav", "map"))
            self.until(page, "() => /CARTHAGE/i.test(document.getElementById('sm-lab').innerText)", what="Carthage on the map")
            self.no_errors()

    def test_jump_from_home(self):
        j = journals.jump()
        fuel = j.pop("fuel")
        with Board("p_jump2", **j) as b:
            page = self.open(b)
            page.click('.tab[data-tab="home"]')
            arrive_to = self.run_jump(b, page, fuel)
            self.assertEqual(arrive_to.upper(), "BACK TO 1 HOME")
            self.assertEqual(self.fp(page)["tab"], "home")
            self.no_errors()


class Latency(PageTest):
    def test_status_reaches_the_page_at_once(self):
        """A change to Status.json shows on the page well inside the old 1 s read + 2 s fetch."""
        with Board("p_latency", **journals.syst()) as b:
            page = self.open(b)
            self.until(page, "() => ED.S.data && ED.S.data.syst", what="the first state")
            for i in range(3):
                lat = round(-13.1 + 0.05 * (i + 1), 2)
                t0 = time.time()
                b.write_status(dict(journals.NEAR_HAO, Latitude=lat))
                self.until(page, f"() => ((ED.S.data.syst || {{}}).me || {{}}).lat === {lat}", timeout=4, what="the new position")
                self.assertLess(time.time() - t0, 1.0, "the page took too long to show Status.json's new position")
                time.sleep(0.3)
            self.no_errors()


class Traj(PageTest):
    """2 Nav > Traj: guidance down to a planetary facility - the destination, the phase and its scale, the three
    panels, and setting the course, the view and the destination with the mouse and with the UFC's COMM1."""
    HAO = "Hao Extraction Prospect"
    GLIDE = 1 << 12   # Flags2
    SC = 1 << 4       # Flags: supercruise (orbital cruise, near a planet)

    def reading(self, b, i, **kw):   # one reading, coming down towards Hao Extraction Prospect
        b.write_status(dict(journals.NEAR_HAO, **dict({"Latitude": round(-13.1 - 0.004 * i, 6), "Longitude": round(34.9 - 0.002 * i, 6),
                                                       "Altitude": 4200 - 250 * i, "Destination": {"Name": self.HAO}}, **kw)))

    def descend(self, b, n=4, **kw):   # readings a second apart
        for i in range(n):
            self.reading(b, i, **kw)
            time.sleep(1.0)

    def course(self, page):
        return page.evaluate("() => ED.traj.crs[ED.traj.dest.key]")

    def test_page_and_mouse(self):
        with Board("p_traj", **journals.syst()) as b:
            page = self.open(b)
            b.add({"event": "Undocked", "StationName": "Fabian City"})
            self.descend(b)
            self.go(page, "nav", "2")
            self.on(page, "nav", 3, what="Traj")
            self.until(page, "() => ED.trajGuide().ok", what="guidance")
            g = page.evaluate("""() => { const g = ED.trajGuide(); return {dist: g.dist, th: g.th, crs: g.crs, de: g.de, auto: g.auto,
                                 clos: g.clos, vv: g.vv, name: g.d.name, phase: g.phase, scale: g.scale}; }""")
            self.assertEqual(g["name"], self.HAO)   # Syst's pick (in AUTO, the nearest site)
            self.assertTrue(7000 < g["dist"] < 10000, g)
            self.assertTrue(10 < g["th"] < 30, g)   # well below the 50 deg path
            self.assertTrue(g["auto"], g)           # no course set: AUTO, the bearing you have to it
            self.assertEqual(g["de"], 0, g)
            self.assertEqual((g["phase"], g["scale"]), ("flight", 30000), g)   # flying, under 30 km out: the 30 km scale
            self.assertGreater(g["clos"], 50, g)    # closing on it...
            self.assertGreater(g["vv"], 150, g)     # ... coming down about 250 m/s
            time.sleep(0.6)
            for cv in ("tr-plan", "tr-prof"):
                self.assertGreater(page.evaluate(CANVAS_INK_JS, cv), 5, f"#{cv} is empty")   # (thin, dim lines: not much is lit)
            # two panels, half each (the ILS and highway are off); the top row: Dest left, the name and phase, the profiles right
            self.assertTrue(page.evaluate("() => document.getElementById('tr-mid').hidden"))
            wl, wr = page.evaluate("() => Array.from(document.querySelectorAll('#pg-traj .trside')).map(e => e.getBoundingClientRect().width)")
            self.assertLess(abs(wl - wr), 3, (wl, wr))
            boxes = page.evaluate("""() => ['tr-dest', 'tr-dname', 'tr-entry1'].map(id => document.getElementById(id).getBoundingClientRect())
                                         .map(r => [r.left, r.right])""")
            mid = page.evaluate("() => { const r = document.getElementById('pg-traj').getBoundingClientRect(); return r.left + r.width / 2; }")
            self.assertLess(boxes[0][1], mid)   # Dest: over the top-down view
            self.assertGreater(boxes[2][0], mid)   # the profiles: over the side profile
            self.assertNotIn("HIP 20277 3 B", page.inner_text("#pg-traj .trtop").upper())   # the name only, no body
            text = page.inner_text("#pg-traj").upper()
            for want in ("ENTRY 1", "1 SYST SEL", "DEST", self.HAO.upper(), "LOW", "VERTICAL VELOCITY", "BOUNDS", "AUTO"):
                self.assertIn(want, text)
            self.assertTrue(page.evaluate("() => document.getElementById('tr-wait').hidden"), "no waiting box with a position")
            # the mouse: grab the course box, scroll it (from AUTO's bearing), let go; then > twice
            crs0 = g["crs"]
            page.click("#tr-crs")
            self.until(page, "() => document.getElementById('tr-crs').classList.contains('grab')", what="the course box grabbed")
            page.hover("#tr-crs")
            page.mouse.wheel(0, -100)
            self.until(page, f"() => ED.traj.crs[ED.traj.dest.key] === {(crs0 + 1) % 360}", what="a scroll up to turn the course 1 deg")
            page.click("#tr-crs")
            self.until(page, "() => !document.getElementById('tr-crs').classList.contains('grab')", what="the course box let go")
            page.click("#tr-crsp")
            page.click("#tr-crsp")
            self.until(page, f"() => ED.traj.crs[ED.traj.dest.key] === {(crs0 + 3) % 360}", what="> twice")
            self.until(page, f"() => /{(crs0 + 3) % 360:03d}/.test(document.getElementById('tr-crsv').textContent)", what="the course box to show it")
            self.assertFalse(page.evaluate("() => ED.trajGuide().auto"))
            # the switches: course up; the HUD target (the same place, from Status.json's Destination)
            page.click('#tr-view button[data-v="C"]')
            self.until(page, "() => ED.traj.view === 'C'", what="course up")
            page.click('#tr-dest button[data-v="hud"]')
            self.until(page, f"() => ED.traj.mode === 'hud' && ED.trajGuide().ok && ED.trajGuide().d.name === '{self.HAO}'", what="the HUD target")
            # the scale: the wheel on either picture zooms both, from 300 m to 10,000 km; Reset scale goes back to the phase's
            self.assertEqual(page.inner_text("#tr-zoom").upper(), "AUTO")
            page.hover("#tr-prof-svg")
            page.mouse.wheel(0, -300)
            self.until(page, "() => ED.traj.zoom && ED.trajGuide().scale < 25000", what="the wheel to zoom in")
            self.until(page, "() => /MANUAL/i.test(document.getElementById('tr-zoom').textContent)", what="MANUAL")
            page.hover("#tr-plan-svg")
            page.mouse.wheel(0, 20000)
            self.until(page, "() => ED.traj.zoom === 1e7", what="out to 10,000 km and no further")
            self.until(page, "() => /10,000 km/.test(document.getElementById('tr-scale').textContent)", what="the scale shown")
            page.mouse.wheel(0, -20000)
            self.until(page, "() => ED.traj.zoom === 300", what="in to 300 m and no further")
            time.sleep(0.3)
            for cv in ("tr-plan", "tr-prof"):
                self.assertGreater(page.evaluate(CANVAS_INK_JS, cv), 5, f"#{cv} is empty zoomed in")
            page.click("#tr-reset")
            self.until(page, "() => ED.traj.zoom === null && ED.trajGuide().scale === 30000", what="Reset scale")
            page.hover("#tr-prof-svg")
            page.mouse.wheel(0, 300)
            self.until(page, "() => ED.traj.zoom > 30000", what="zoomed out")
            b.write_status(dict(journals.NEAR_HAO, Latitude=-13.112, Longitude=34.894, Altitude=3200,
                                Destination={"Name": "Dhaenens's Lodgings"}))   # a new destination: the phase's scale again
            self.until(page, "() => ED.traj.dest && ED.traj.dest.name === \"Dhaenens's Lodgings\" && ED.traj.zoom === null", what="the zoom gone with a new destination")
            b.write_status(dict(journals.NEAR_HAO, Latitude=-13.112, Longitude=34.894, Altitude=3200))   # no target any more
            self.until(page, "() => !ED.trajGuide().ok && /NO DEST/i.test(document.getElementById('tr-dsub').textContent)", what="no DEST")
            self.until(page, "() => /NO DESTINATION/i.test(document.getElementById('tr-wait').textContent)", what="NO DESTINATION")
            # what 1 Syst has selected, where Traj can't use it: a body, something in orbit, a surface site no one has placed
            page.click('#tr-dest button[data-v="pick"]')
            for key, title, why in (("b5", "NOT A SURFACE TARGET", "BODY SELECTED - PLANETARY TARGET REQUIRED"),
                                    ("s3224777216", "NOT A SURFACE TARGET", "ORBITAL STATION")):
                page.evaluate(f"() => {{ ED.S.syMode = 'manual'; ED.S.sySel = '{key}'; ED.render(ED.S.data); }}")
                self.until(page, f"() => /{title}/i.test(document.getElementById('tr-wait').textContent) && "
                                 f"/{why}/i.test(document.getElementById('tr-wait').textContent)", what=why)
            page.evaluate("""() => { const y = ED.S.data.syst, body = y.entries.find(e => e.kind === 'planet').name;
                y.entries.push({key: 's-nopos', kind: 'station', name: 'Nowhere Outpost', label: 'Nowhere Outpost', icon: 'surface', depth: 1,
                                lab: 'Planetary Outpost', chips: [], rows: [], right: '', src: 'spansh', surface: false,
                                body: body, pic: {kind: 'surface', body: body, lat: null, lon: null}});
                ED.S.sySel = 's-nopos'; ED.render(ED.S.data); }""")
            text = page.inner_text("#tr-wait").upper()
            self.assertIn("TARGET POSITION UNKNOWN", text)
            self.assertIn("NO SURFACE COORDINATES - RECON REQUIRED", text)
            self.no_errors()

    def test_phases_and_the_course(self):
        """No position yet: the panels behind "No state vector", and the course can be set; the bearing at the
        glide becomes the course (until you're back in orbital cruise); orbital cruise dims ENTRY 1; a silence
        means you've stopped; inside 3 km, the final approach at 3 km."""
        with Board("p_traj_phases", **journals.syst()) as b:
            page = self.open(b)
            b.add({"event": "Undocked", "StationName": "Fabian City"})
            b.write_status({"Flags": journals.NEAR_HAO["Flags"] | self.SC, "Flags2": 0, "Destination": {"Name": self.HAO}})   # out in space
            self.go(page, "nav", "2")
            self.on(page, "nav", 3, what="Traj")
            page.click('#tr-dest button[data-v="hud"]')
            self.until(page, f"() => ED.traj.dest && ED.traj.dest.ok && ED.traj.dest.name === '{self.HAO}'", what="the HUD target")
            self.until(page, "() => !document.getElementById('tr-wait').hidden && /NO STATE VECTOR/i.test(document.getElementById('tr-wait').textContent)",
                       what="the no-position box")
            self.assertIn("OUTSIDE ORBITAL CRUISE RANGE", page.inner_text("#tr-wait").upper())
            time.sleep(0.6)
            for cv in ("tr-plan", "tr-prof"):   # still drawn, behind it
                self.assertGreater(page.evaluate(CANVAS_INK_JS, cv), 5, f"#{cv} is empty")
            # at another body: says where the destination is
            b.write_status(dict(journals.NEAR_HAO, BodyName="HIP 20277 3 a", Latitude=58.0, Longitude=51.0, Altitude=9000,
                                Destination={"Name": self.HAO}))
            self.until(page, "() => /REFERENCE BODY MISMATCH/i.test(document.getElementById('tr-wait').textContent)", what="the other-body box")
            self.assertIn("DEST ON HIP 20277 3 B", page.inner_text("#tr-wait").upper())
            self.assertNotIn("3 A", page.inner_text("#tr-wait").upper())
            self.until(page, "() => /AUTO/.test(document.getElementById('tr-crsv').textContent)", what="the course AUTO")
            # the glide: its bearing becomes the course (taken, not yours)
            self.descend(b, 3, Flags2=self.GLIDE)
            self.until(page, "() => ED.trajGuide().ok && ED.trajGuide().phase === 'glide'", what="the glide")
            self.assertTrue(page.evaluate("() => document.getElementById('tr-wait').hidden"))
            # a reading without a position, then one with: a short miss - no box
            b.write_status({"Flags": journals.NEAR_HAO["Flags"], "Flags2": self.GLIDE, "Destination": {"Name": self.HAO}})
            self.until(page, "() => ED.traj.me === null", what="the reading without a position")
            for _ in range(5):
                self.assertTrue(page.evaluate("() => document.getElementById('tr-wait').hidden && ED.trajGuide().ok"), "a short miss shows no box")
                time.sleep(0.15)
            self.reading(b, 3, Flags2=self.GLIDE)
            taken = self.course(page)
            self.assertIsNotNone(taken, "the bearing at the glide becomes the course")
            self.assertTrue(page.evaluate("() => ED.traj.took[ED.traj.dest.key] === true"))
            g = page.evaluate("() => { const g = ED.trajGuide(); return {auto: g.auto, crs: g.crs, scale: g.scale, entry: g.entry}; }")
            self.assertEqual(g, {"auto": False, "crs": taken, "scale": 30000, "entry": True})
            page.hover("#tr-plan-svg")
            page.mouse.wheel(0, -300)   # your own scale ...
            self.until(page, "() => ED.traj.zoom && ED.trajGuide().scale < 25000", what="zoomed in")
            # back in orbital cruise: the taken course goes; ENTRY 1 waits for the glide; the 100 km scale
            self.reading(b, 3, Flags=journals.NEAR_HAO["Flags"] | self.SC)
            self.until(page, "() => ED.trajGuide().phase === 'cruise'", what="orbital cruise")
            self.until(page, "() => ED.traj.crs[ED.traj.dest.key] == null", what="the taken course dropped")
            self.until(page, "() => ED.traj.zoom === null", what="... gone going back into orbital cruise")
            page.hover("#tr-plan-svg")
            page.mouse.wheel(0, 300)   # (zoomed again in orbital cruise, it stays)
            self.until(page, "() => ED.traj.zoom > 100000", what="zoomed out in orbital cruise")
            self.reading(b, 3, Flags=journals.NEAR_HAO["Flags"] | self.SC, Altitude=3300)
            time.sleep(1.5)
            self.assertGreater(page.evaluate("() => ED.traj.zoom || 0"), 100000, "a zoom set in orbital cruise stays there")
            page.click("#tr-reset")
            g = page.evaluate("() => { const g = ED.trajGuide(); return {auto: g.auto, scale: g.scale, entry: g.entry}; }")
            self.assertEqual(g, {"auto": True, "scale": 100000, "entry": False})
            self.assertIn("ORBITAL CRUISE", page.inner_text("#pg-traj").upper())
            # set it yourself: it stays through the next glide
            bearing = page.evaluate("() => ED.trajGuide().crs")
            page.click("#tr-crsp")
            page.click("#tr-crsp")
            mine = (bearing + 2) % 360
            self.until(page, f"() => ED.traj.crs[ED.traj.dest.key] === {mine}", what="> twice from the bearing")
            for i in range(4, 7):
                self.reading(b, i, Flags2=self.GLIDE)
                time.sleep(1.0)
            self.until(page, "() => ED.trajGuide().phase === 'glide'", what="the glide again")
            self.assertEqual(self.course(page), mine)
            self.assertFalse(page.evaluate("() => !!ED.traj.took[ED.traj.dest.key]"))
            # no more readings: stopped (no speed) - but not "no reading" yet
            self.until(page, "() => ED.trajGuide().gs > 1", what="moving")
            self.until(page, "() => ED.trajGuide().still && ED.trajGuide().gs === 0 && ED.trajGuide().vv === 0", timeout=12, what="stopped")
            self.assertNotIn("NO READING", page.inner_text("#pg-traj").upper())
            # inside 3 km: the final approach, at 3 km
            d = page.evaluate("() => ({lat: ED.traj.dest.lat, lon: ED.traj.dest.lon})")
            for k in range(3):
                b.write_status(dict(journals.NEAR_HAO, Latitude=round(d["lat"] - 0.06 + 0.01 * k, 6), Longitude=round(d["lon"], 6),
                                    Altitude=900 - 100 * k, Destination={"Name": self.HAO}))
                time.sleep(1.0)
            self.until(page, "() => ED.trajGuide().phase === 'final' && ED.trajGuide().scale === 3000", what="the final approach")
            self.assertIn("FINAL APPROACH", page.inner_text("#pg-traj").upper())
            self.no_errors()

    def test_final_to_the_pad(self):
        """Docking granted at a settlement whose layout is confirmed and heading known: inside 3 km the guidance is
        to the pad, not the settlement's position."""
        name, key = "Dhaenens's Lodgings", "m:3814631936"
        with Board("p_traj_pad", **journals.syst()) as b:
            self.assertEqual(b.post("/api/settlement-layout", {"key": key, "layout": "tourist-4", "name": name})[0], 200)
            self.assertEqual(b.post("/api/settlement-heading", {"key": key, "layout": "tourist-4", "heading": 45, "name": name})[0], 200)
            page = self.open(b)
            b.add({"event": "Undocked", "StationName": "Fabian City"})
            here = {"Flags": journals.NEAR_HAO["Flags"], "Flags2": 0, "BodyName": "HIP 20277 3 a", "Heading": 0, "PlanetRadius": 2400000.0,
                    "Destination": {"Name": name}}
            b.write_status(dict(here, Latitude=58.7, Longitude=51.43, Altitude=2000))
            self.go(page, "nav", "2")
            self.on(page, "nav", 3, what="Traj")
            page.click('#tr-dest button[data-v="hud"]')
            self.until(page, f"() => ED.traj.dest && ED.traj.dest.ok && ED.traj.dest.name === {json.dumps(name)}", what="the HUD target")
            d = page.evaluate("() => ({lat: ED.traj.dest.lat, lon: ED.traj.dest.lon})")
            b.add({"event": "DockingGranted", "MarketID": 3814631936, "LandingPad": 2, "StationName": name, "StationType": "OnFootSettlement"})
            for k in range(3):   # 2 km south, coming in
                b.write_status(dict(here, Latitude=round(d["lat"] - 0.048 + 0.002 * k, 6), Longitude=round(d["lon"], 6), Altitude=800 - 50 * k))
                time.sleep(1.0)
            self.until(page, "() => ED.trajGuide().ok && ED.trajGuide().phase === 'final' && ED.trajGuide().onPad", what="guidance to the pad")
            g = page.evaluate("() => { const g = ED.trajGuide(); return {num: g.padNum, dist: g.dist, toSite: g.toSite}; }")
            self.assertEqual(g["num"], 2)
            self.assertGreater(abs(g["dist"] - g["toSite"]), 20, g)   # the pad isn't at the settlement's position
            self.assertIn("PAD 2", page.inner_text("#pg-traj").upper())
            self.no_errors()

    def test_ufc(self):
        with Board("p_traj_ufc", **journals.syst()) as b:
            page = self.open(b)
            b.add({"event": "Undocked", "StationName": "Fabian City"})
            self.descend(b, 2)
            b.ufc_cmd("press ILS", "press Opt2", "press 2")   # the page menu, NAV, the keypad's 2
            self.on(page, "nav", 3, what="Traj from the keypad")
            self.until(page, "() => ED.trajGuide().ok", what="guidance")
            self.until(page, "() => document.getElementById('tr-crs').classList.contains('focus')", what="COMM1 on the course box")
            crs0 = page.evaluate("() => ED.trajGuide().crs")   # AUTO: the bearing
            # the COMM1 VOLUME dial zooms (held in the middle); COMM2 steps between ENTRY 1 and Reset scale
            self.assertTrue(page.evaluate("() => document.getElementById('tr-entry1').classList.contains('focus')"), "COMM2 on ENTRY 1")
            b.ufc_cmd("dial 9 2000", "dial 9 3800")
            self.until(page, "() => ED.traj.zoom && ED.trajGuide().scale < 15000", what="COMM1 VOLUME to zoom in")
            b.ufc_cmd("dial 9 2000")
            time.sleep(0.4)
            z = page.evaluate("() => ED.traj.zoom")
            time.sleep(0.5)
            self.assertEqual(page.evaluate("() => ED.traj.zoom"), z, "the middle holds")
            b.ufc_cmd("press COMM2_PULL")   # on ENTRY 1 (already the profile): the scale stays
            time.sleep(0.6)
            self.assertEqual(page.evaluate("() => ED.traj.zoom"), z)
            b.ufc_cmd("pulse COMM2_CW")
            self.until(page, "() => document.getElementById('tr-reset').classList.contains('focus') && !document.getElementById('tr-entry1').classList.contains('focus')",
                       what="COMM2 on Reset scale")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => ED.traj.zoom === null && ED.trajGuide().scale === 30000", what="a COMM2 pull to reset the scale")
            self.assertEqual(page.evaluate("() => [ED.traj.focus, ED.traj.grab, ED.traj.crs[ED.traj.dest.key] == null]"), ["crs", False, True])
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, "() => ED.traj.grab && document.getElementById('tr-crs').classList.contains('grab')", what="a pull grabs it")
            b.ufc_cmd("pulse COMM1_CW", "pulse COMM1_CW", "pulse COMM1_CW", pause=0.5)   # turned slowly: 1 deg a click
            self.until(page, f"() => ED.traj.crs[ED.traj.dest.key] === {(crs0 + 3) % 360}", what="three slow clicks: 3 deg")
            b.ufc_cmd(*["pulse COMM1_CCW"] * 8, pause=0)   # spun: more a click
            time.sleep(1.2)
            turned = (crs0 + 3 - self.course(page)) % 360
            self.assertGreater(turned, 8, "eight quick clicks turn it more than 8 deg")
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, "() => !ED.traj.grab", what="a pull lets go")
            b.ufc_cmd("pulse COMM1_CW")
            self.until(page, "() => document.getElementById('tr-view').classList.contains('focus')", what="COMM1 on the view switch")
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, "() => ED.traj.view === 'C'", what="a pull flips it to course up")
            b.ufc_cmd("pulse COMM1_CW")
            self.until(page, "() => document.getElementById('tr-dest').classList.contains('focus')", what="COMM1 on the destination switch")
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, "() => ED.traj.mode === 'hud'", what="a pull flips it to DEST")
            self.no_errors()


class Tgt(PageTest):
    """2 Nav > Wpt: making your own waypoints (MANUAL with the keyboard or the UFC's keypad; OVERFLY's MARK and HUD DESIG make
    marks), naming and editing them, seeing them in 1 Syst and guiding to one with Traj, and deleting them."""
    BODY = "HIP 20277 3"     # (b8 in the synthetic system)
    HERE = "HIP 20277 3 b"   # where journals.NEAR_HAO has you

    def select_in_syst(self, page, name):
        key = page.evaluate(f"() => ED.S.data.syst.entries.find(e => e.name === {json.dumps(name)}).key")
        page.evaluate(f"() => {{ ED.S.syMode = 'manual'; ED.S.sySel = {json.dumps(key)}; ED.render(ED.S.data); }}")
        return key

    def save_twice(self, page):   # SAVE: CONFIRM, then saved
        page.click("#tg-save")
        self.until(page, "() => /CONFIRM/i.test(document.getElementById('tg-save').textContent)", what="SAVE turning to CONFIRM")
        page.click("#tg-save")

    def test_page_and_mouse(self):
        with Board("p_tgt", **journals.syst()) as b:
            page = self.open(b)
            b.add({"event": "Undocked", "StationName": "Fabian City"})
            b.write_status(dict(journals.NEAR_HAO, Destination={"Name": "Hao Extraction Prospect"}))
            self.go(page, "nav", 3)
            self.on(page, "nav", 4, what="Wpt")
            self.assertEqual(page.inner_text("#subtabs .stab.on").upper(), "3 WPT")
            self.assertTrue(page.evaluate("() => !!document.querySelector('#pg-tgt .rail') && !!document.querySelector('#pg-tgt .panel')"), "two panels, as 1 Syst")
            self.assertEqual(page.evaluate("() => Array.from(document.querySelectorAll('#tg-meth button')).map(b => [b.textContent.toUpperCase(), b.disabled])"),
                             [["MANUAL", False], ["OVERFLY", False], ["HUD VV", False], ["HUD X-B", False]])
            self.assertTrue(page.evaluate("() => document.getElementById('tg-railx').offsetParent !== null"), "no targets yet")
            # MANUAL with the keyboard, on what 1 Syst has selected (a star is refused); no name: the usual one
            star = page.evaluate("() => ED.S.data.syst.entries.find(e => e.kind === 'star').name")
            self.select_in_syst(page, star)
            self.until(page, "() => /STAR/i.test(document.getElementById('tg-body').textContent)", what="a star refused")
            self.select_in_syst(page, self.BODY)
            self.until(page, "() => document.getElementById('tg-body').textContent.toUpperCase() === '3'", what="the body: 3")
            page.fill("#tg-lat", "26.9707")
            page.fill("#tg-lon", "59.742 W")
            page.press("#tg-lon", "Tab")
            self.until(page, "() => !document.getElementById('tg-save').disabled", what="SAVE ready")
            self.save_twice(page)
            self.until(page, "() => /WPT 1 - 3/i.test(document.getElementById('tg-list').textContent)", what="WPT 1 in the list")
            self.assertIn("WP1 WPT 1 - 3", page.inner_text("#tg-list").upper())   # (by its number and name: its position's on the right)
            self.assertNotIn("26.9707", page.inner_text("#tg-list"))
            self.assertIn("SAVED WPT 1 - 3", page.inner_text("#tg-note").upper())
            # ... and with a name
            page.fill("#tg-nm", "  Crash   site ")
            page.fill("#tg-lat", "-5.5")
            page.fill("#tg-lon", "120.25")
            page.press("#tg-lon", "Tab")
            self.save_twice(page)
            self.until(page, "() => ED.S.data.syst.tgts.some(t => t.name === 'Crash site' && t.num === 2)", what="a named target")
            # EDIT: its name (blank: the usual one) and coordinates
            k1 = page.evaluate("() => ED.S.data.syst.tgts.find(t => t.num === 1).key")
            page.click(f'#tg-list .srow[data-key="{k1}"]')
            page.click("#tg-edit")
            self.until(page, "() => !document.getElementById('tg-form').hidden && document.getElementById('tg-nm').value === 'WPT 1 - 3'", what="the edit form")
            self.assertTrue(page.evaluate("() => document.getElementById('tg-srcrow').hidden"), "the body stays as it is")
            page.fill("#tg-nm", "Wreck")
            page.fill("#tg-lat", "N26.98")
            page.press("#tg-lat", "Tab")
            self.save_twice(page)
            self.until(page, "() => ED.S.data.syst.tgts.some(t => t.num === 1 && t.name === 'Wreck' && t.lat === 26.98 && t.lon === -59.742)", what="WPT 1 changed")
            self.until(page, "() => !document.getElementById('tg-one').hidden && /WRECK/i.test(document.getElementById('tg-name').textContent)", what="back to its details")
            # DEST: the body your target in the game is on (a crash site's, say)
            page.click('#tg-meth button[data-m="manual"]')
            y = page.evaluate("() => ({id64: ED.S.data.syst.id64, bid: ED.S.data.syst.entries.find(e => e.name === 'HIP 20277 3 b').bodyId})")
            b.write_status(dict(journals.NEAR_HAO, Destination={"System": y["id64"], "Body": y["bid"], "Name": "$POIScenario_Watson_Wrecks_Sidewinder_01_Salvage_Easy;",
                                                                "Name_Localised": "Crash Site [Threat&NBSP;1]"}))
            page.click('#tg-src button[data-v="hud"]')
            self.until(page, "() => document.getElementById('tg-body').textContent.toUpperCase() === '3 B'", what="the HUD target's body: 3 b")
            # OVERFLY: the point beneath you, live; MARK makes it a mark (MK1) at once - STORE AS WP keeps it as a waypoint
            page.click('#tg-meth button[data-m="overfly"]')
            self.until(page, "() => !document.getElementById('tg-over').hidden && document.getElementById('tg-olat').textContent === '-13.1000'", what="OVERFLY live")
            self.assertEqual((page.inner_text("#tg-obody").upper(), page.inner_text("#tg-olon")), ("3 B", "34.9000"))
            page.click("#tg-mark")
            self.until(page, "() => ED.S.data.syst.nav.marks.length === 1 && /MK1 · 3 B/i.test(document.getElementById('tg-list').textContent)", what="MK1 marked")
            self.assertIn("MARKED MK1", page.inner_text("#tg-note").upper())
            self.assertEqual(page.evaluate("() => ED.S.data.syst.tgts.length"), 2, "a mark isn't a waypoint")
            page.click('#tg-list .srow[data-key="mk1"]')
            self.until(page, "() => !document.getElementById('tg-mk').hidden && /MK1/.test(document.getElementById('tg-name').textContent)", what="MK1's details")
            page.click("#tg-mstor")
            self.until(page, "() => /WPT 3 - 3 B/i.test(document.getElementById('tg-list').textContent)", what="MK1 stored as WPT 3")
            # in 1 Syst: under their bodies, with their own icon; Traj guides to the one here
            self.until(page, "() => ED.S.data.syst.entries.filter(e => e.kind === 'tgt').length === 3", what="the targets in Syst's list")
            self.go(page, "nav", 1)
            self.until(page, "() => document.querySelectorAll('#sy-list .srow[data-key^=\"t\"]').length === 3", what="three target rows")
            k3 = page.evaluate("() => ED.S.data.syst.tgts.find(t => t.num === 3).key")
            page.click(f'#sy-list .srow[data-key="{k3}"]')
            self.until(page, "() => document.getElementById('sy-name').textContent === 'WPT 3 - 3 b'", what="WPT 3 in Syst")
            self.go(page, "nav", 2)
            page.click('#tr-dest button[data-v="pick"]')
            self.until(page, "() => ED.trajGuide().ok && ED.trajGuide().d.name === 'WPT 3 - 3 b'", what="Traj guiding to WPT 3")
            self.assertLess(page.evaluate("() => ED.trajGuide().dist"), 50)   # (you marked it beneath you)
            # deleting: DELETE, then CONFIRM DELETE
            self.go(page, "nav", 3)
            page.click(f'#tg-list .srow[data-key="{k3}"]')
            self.until(page, "() => !document.getElementById('tg-one').hidden && /WPT 3 - 3 B/i.test(document.getElementById('tg-name').textContent)", what="WPT 3's details")
            self.assertIn("OVERFLY", page.inner_text("#tg-grid").upper())
            page.click("#tg-del")
            self.until(page, "() => !document.getElementById('tg-confirm').hidden", what="CONFIRM DELETE")
            page.click("#tg-confirm")
            self.until(page, "() => !/WPT 3/i.test(document.getElementById('tg-list').textContent) && ED.S.data.syst.tgts.length === 2", what="WPT 3 deleted")
            self.no_errors()

    def test_hud_desig(self):
        """HUD VV (once HUD DESIG): where your flight path - your heading left and right, your flight-path angle up and
        down - meets the ground; nothing while you're not descending. Held steady: the average of the last few seconds'
        points, with how far they wander (+-); low down (the game's altitude from the ground beneath you), a warning."""
        with Board("p_tgt_desig", **journals.syst()) as b:
            page = self.open(b)
            b.add({"event": "Undocked", "StationName": "Fabian City"})
            self.go(page, "nav", 3)
            self.on(page, "nav", 4, what="Wpt")
            page.click('#tg-meth button[data-m="desig"]')
            for i in range(3):   # level, heading east
                b.write_status(dict(journals.NEAR_HAO, Latitude=-13.1, Longitude=round(34.9 + 0.002 * i, 6), Altitude=3000))
                time.sleep(1.0)
            self.until(page, "() => /PATH NOT DESCENDING/i.test(document.getElementById('tg-dbody').textContent)", what="level: not descending")
            self.assertTrue(page.evaluate("() => document.getElementById('tg-dbtn').disabled"))
            for i in range(3, 7):   # a 45 degree dive, east: about 50 m/s across and down
                b.write_status(dict(journals.NEAR_HAO, Latitude=-13.1, Longitude=round(34.9 + 0.002 * 2 + 0.00196 * (i - 2), 6), Altitude=3000 - 50 * (i - 2)))
                time.sleep(1.0)
            self.until(page, "() => ED.tgtDesig().ok", what="a designated point")
            d = page.evaluate("() => { const d = ED.tgtDesig(), m = ED.S.data.syst.me; return {d: d, me: m}; }")
            self.assertLess(abs(d["d"]["fpa"] + 45), 6, d)   # (the filter's speeds)
            self.assertLess(abs(d["d"]["range"] - d["me"]["alt"]), d["me"]["alt"] * 0.15, d)   # 45 degrees: as far ahead as you are up
            self.assertLess(abs(d["d"]["lat"] - d["me"]["lat"]), 0.002, d)   # heading east: due east of you
            self.assertGreater(d["d"]["lon"], d["me"]["lon"])
            self.assertEqual(page.evaluate("() => [document.getElementById('tg-name').textContent, document.getElementById('tg-case').textContent.toUpperCase()]"),
                             ["HUD VV", "CREATE · HUD VV · A MARK, DESIGNATED"])
            for i in range(7, 10):   # held steady: averaged, with how far its points wander
                b.write_status(dict(journals.NEAR_HAO, Latitude=-13.1, Longitude=round(34.9 + 0.002 * 2 + 0.00196 * (i - 2), 6), Altitude=3000 - 50 * (i - 2)))
                time.sleep(1.0)
            self.until(page, "() => { const v = ED.tgtVV(); return v.ok && !v.settling && v.err != null && v.n >= 4; }", what="the average")
            v = page.evaluate("() => ED.tgtVV()")
            self.assertLess(v["err"], 60, v)
            self.assertFalse(v["unsteady"], v)
            self.assertRegex(page.inner_text("#tg-drng"), r"(?i)^\d+(\.\d)? (k?m) ± \d+ m$")
            self.assertTrue(v["low"], "NEAR_HAO: the altitude's from the ground beneath you")
            self.assertIn("LOW", page.inner_text("#tg-dwarn").upper())
            page.click("#tg-dbtn")   # a mark, designated
            self.until(page, "() => ED.S.data.syst.nav.marks.length === 1 && ED.S.data.syst.nav.marks[0].method === 'desig' && (ED.S.data.syst.nav.tgt || {}).key === 'mk1'",
                       what="DESIG: MK1, the target")
            self.assertIn("DESIGNATED MK1 · TGT", page.inner_text("#tg-note").upper())
            self.assertEqual(page.evaluate("() => ED.S.data.syst.tgts.length"), 0)
            self.no_errors()

    def test_hud_xb(self):
        """HUD X-B: TAKE BEARING (the dot on the target) from places round it - the UFC's COMM2 pull, or a click; where the
        lines cross (2), their best fit (3+), how far out it may be and the widest angle between them; a bad sighting
        flagged, and deleted (COMM2 on it, a pull); DESIG makes the point a mark, designated; CLEAR ALL (twice)."""
        R, T = 1500000.0, (-13.4086, 34.7333)   # (Hao Extraction Prospect)
        def brg(a, t):
            p1, l1, p2, l2 = map(math.radians, (a[0], a[1], t[0], t[1]))
            return math.degrees(math.atan2(math.sin(l2 - l1) * math.cos(p2), math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(l2 - l1))) % 360
        def off(f):   # how far the page's point is from the target (m)
            return math.hypot((f["lat"] - T[0]) * math.pi / 180 * R, (f["lon"] - T[1]) * math.pi / 180 * R * math.cos(math.radians(T[0])))
        with Board("p_tgt_xb", **journals.syst()) as b:
            page = self.open(b)
            b.add({"event": "Undocked", "StationName": "Fabian City"})

            def hover(o, h):   # over o, nose at h (the game's heading: whole degrees), until the page has you there
                for k in range(15):
                    b.write_status(dict(journals.NEAR_HAO, Latitude=o[0], Longitude=round(o[1] + k * 1e-7, 7), Altitude=1500, Heading=h))
                    time.sleep(0.6)
                    if page.evaluate(f"() => {{ const p = ED.tgtOver(); return p.ok && Math.abs(p.lat - ({o[0]})) < 2e-6 && Math.abs(p.lon - ({o[1]})) < 2e-5 && ED.S.data.syst.me.hdg === {h}; }}"):
                        return
                self.fail(f"the page never had you at {o}")
            hover((-13.30, 34.70), round(brg((-13.30, 34.70), T)))
            b.ufc_cmd("press ILS", "press Opt2", "press 3")
            self.on(page, "nav", 4, what="Wpt")
            b.ufc_cmd(*["pulse COMM1_CW"] * 3, "press COMM1_PULL")   # MANUAL > OVERFLY > HUD VV > HUD X-B
            self.until(page, "() => ED.tgt.view === 'xb' && !document.getElementById('tg-xb').hidden && document.getElementById('tg-xtake').classList.contains('focus')",
                       what="HUD X-B, COMM2 on TAKE BEARING")
            self.assertTrue(page.evaluate("() => document.querySelector('#tg-meth button[data-m=\"xb\"]').classList.contains('on')"))
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => ED.S.data.syst.nav.xb.list.length === 1", what="the first bearing")
            self.assertIn("ONE BEARING", page.inner_text("#tg-xfix").upper())
            for o in ((-13.40, 34.83), (-13.46, 34.68)):
                n = page.evaluate("() => ED.S.data.syst.nav.xb.list.length")
                hover(o, round(brg(o, T)))
                b.ufc_cmd("press COMM2_PULL")
                self.until(page, f"() => ED.S.data.syst.nav.xb.list.length === {n + 1}", what="another bearing")
            f = page.evaluate("() => ED.tgtXb()")
            self.assertTrue(f["ok"], f)
            self.assertLess(off(f), 60, f)   # (whole-degree headings, 8-12 km off)
            self.assertTrue(f["err"] < 120 and f["cross"] > 60 and not f["far"] and not f["behind"], f)
            self.assertRegex(page.inner_text("#tg-xfix"), r"(?i)^± \d+ m · crossing \d+° · ")
            self.assertEqual(page.evaluate("() => document.querySelectorAll('#tg-xlist .srow').length"), 3)
            # a bad sighting (8 degrees off), by a click: flagged; COMM2 on it and a pull deletes it
            o = (-13.32, 34.62)
            hover(o, round(brg(o, T)) + 8)
            page.click("#tg-xtake")
            self.until(page, "() => ED.S.data.syst.nav.xb.list.length === 4 && ED.tgtXb().far.length === 1", what="the bad bearing flagged")
            bad = page.evaluate("() => ED.S.data.syst.nav.xb.list[3].id")
            self.assertEqual(page.evaluate("() => ED.tgtXb().far"), [bad])
            self.assertIn("BEARING 4 LOOKS WELL OFF THE REST", page.inner_text("#tg-xwarn").upper())
            self.assertTrue(page.evaluate(f"() => document.querySelector('#tg-xlist .srow[data-f2=\"x:{bad}\"] .rt').classList.contains('far')"))
            b.ufc_cmd(*["pulse COMM2_CW"] * 3)   # TAKE BEARING > DESIG > CLEAR ALL > the newest bearing (the bad one)
            self.until(page, f"() => ED.tgt.focus2 === 'x:{bad}'", what="COMM2 on the bad bearing")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => ED.S.data.syst.nav.xb.list.length === 3 && ED.tgtXb().far.length === 0", what="deleted")
            # DESIG: a mark (HUD X-B), designated
            page.click("#tg-xdsg")
            self.until(page, "() => ED.S.data.syst.nav.marks.length === 1 && ED.S.data.syst.nav.marks[0].method === 'xb' && (ED.S.data.syst.nav.tgt || {}).key === 'mk1'",
                       what="DESIG: MK1, the target")
            mk = page.evaluate("() => ED.S.data.syst.nav.marks[0]")
            self.assertLess(off(mk), 60, mk)
            # CLEAR ALL: twice
            page.click("#tg-xclr")
            self.assertEqual(page.inner_text("#tg-xclr").upper(), "CONFIRM CLEAR")
            self.assertEqual(page.evaluate("() => ED.S.data.syst.nav.xb.list.length"), 3)
            page.click("#tg-xclr")
            self.until(page, "() => ED.S.data.syst.nav.xb.list.length === 0 && /NO BEARINGS YET/i.test(document.getElementById('tg-xfix').textContent)", what="cleared")
            self.no_errors()

    def test_ufc(self):
        with Board("p_tgt_ufc", **journals.syst()) as b:
            page = self.open(b)
            b.ufc_cmd("press ILS", "press Opt2", "press 3")   # the page menu, NAV, the keypad's 3
            self.on(page, "nav", 4, what="Wpt from the keypad")
            self.select_in_syst(page, self.BODY)
            self.until(page, "() => document.querySelector('#tg-meth [data-m=\"manual\"]').classList.contains('focus')", what="COMM1 on MANUAL")
            self.until(page, "() => document.getElementById('tg-src').classList.contains('focus')", what="COMM2 on the body switch")
            # the name: 2 / 8 step the letter, 4 / 6 move the cursor; ENT on to the latitude
            b.ufc_cmd("pulse COMM2_CW", "press COMM2_PULL")
            self.until(page, "() => document.getElementById('tg-nm').classList.contains('typing')", what="typing the name")
            b.ufc_cmd(*[f"press {k}" for k in "226248"], pause=0.2)   # A, B; on; A; back; B down to A: "AA"
            self.until(page, "() => ED.tgt.entry && ED.tgt.entry.chars.join('') === 'AA' && ED.tgt.entry.pos === 0", what="AA, the cursor on the first")
            b.wait(lambda: (lambda d: d if (d["s1"], d["scratch"]) == ("NM", "AA") else None)(b.display()), what="the scratchpad showing the name")
            b.ufc_cmd("press Clr", pause=0.2)   # CLR: the whole of it
            self.until(page, "() => ED.tgt.entry.chars.length === 0", what="the name cleared")
            b.ufc_cmd(*[f"press {k}" for k in "222"], "press Ent", pause=0.2)   # A, B, C: "C"; ENT
            self.until(page, "() => ED.tgt.mform.name === 'C' && document.getElementById('tg-lat').classList.contains('typing')", what="on to the latitude")
            # the coordinates: the hemisphere key, then the digits
            b.wait(lambda: b.display()["s1"] == "LA" or None, what="the scratchpad asking for the latitude")
            b.ufc_cmd("press 5", pause=0.2)   # not a hemisphere key: nothing
            b.ufc_cmd(*[f"press {k}" for k in "2269707"], pause=0.2)   # N, then 26.9707
            self.until(page, "() => document.getElementById('tg-lat').value === 'N 26.9707'", what="N 26.9707 typed")
            b.wait(lambda: (lambda d: d if (d["s1"], d["scratch"]) == ("N", "26.9707") else None)(b.display()), what="the scratchpad showing it")
            self.assertEqual(page.evaluate("() => ED.view.sub"), 4, "typing doesn't change the sub-tab")
            b.ufc_cmd("press Ent")
            self.until(page, "() => ED.tgt.mform.lat === 26.9707 && document.getElementById('tg-lon').classList.contains('typing')", what="on to the longitude")
            b.ufc_cmd(*[f"press {k}" for k in "41"], "press Clr", pause=0.2)   # W 1... cleared
            self.until(page, "() => document.getElementById('tg-lon').value === ''", what="CLR")
            b.ufc_cmd(*[f"press {k}" for k in "40597420"], "press Ent", pause=0.2)   # W 059.7420
            self.until(page, "() => ED.tgt.mform.lon === -59.742 && !ED.tgt.entry && document.getElementById('tg-save').classList.contains('focus')", what="SAVE next")
            # SAVE: ENT turns it to CONFIRM, ENT again saves (the keypad stays with the page while SAVE is highlighted)
            b.wait(lambda: b.display()["scratch"] == "SAVE" or None, what="SAVE on the scratchpad")
            b.ufc_cmd("press Ent")
            self.until(page, "() => /CONFIRM/i.test(document.getElementById('tg-save').textContent)", what="CONFIRM")
            b.wait(lambda: b.display()["scratch"] == "CONFIRM" or None, what="CONFIRM on the scratchpad")
            b.ufc_cmd("press 1")   # (the keypad's still the page's: no sub-tab)
            time.sleep(0.5)
            self.assertEqual(page.evaluate("() => ED.view.sub"), 4)
            b.ufc_cmd("press Ent")
            self.until(page, "() => ED.S.data.syst.tgts.length === 1 && ED.S.data.syst.tgts[0].lat === 26.9707 && ED.S.data.syst.tgts[0].lon === -59.742 "
                             "&& ED.S.data.syst.tgts[0].name === 'C'", what="saved, named C")
            # COMM1 to the target, a pull shows it; EDIT its name (the cursor starts at the end)
            b.ufc_cmd("pulse COMM2_CCW")   # off SAVE: the keypad's the sub-tabs' again
            b.ufc_cmd(*["pulse COMM1_CW"] * 4, "press COMM1_PULL")   # (past MANUAL, OVERFLY, HUD VV and HUD X-B)
            self.until(page, "() => !document.getElementById('tg-one').hidden", what="the target's details")
            self.until(page, "() => document.getElementById('tg-edit').classList.contains('focus')", what="COMM2 on EDIT")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => !document.getElementById('tg-form').hidden && document.getElementById('tg-nm').classList.contains('focus')", what="the edit form, on its name")
            b.ufc_cmd("press COMM2_PULL")
            b.ufc_cmd(*[f"press {k}" for k in "22"], "press Ent", "press Ent", "press Ent", pause=0.2)   # "CB"; the coordinates as they are
            self.until(page, "() => ED.tgt.eform.name === 'CB' && document.getElementById('tg-save').classList.contains('focus')", what="SAVE next")
            b.ufc_cmd("press COMM2_PULL", "press COMM2_PULL", pause=0.5)   # COMM2 too: CONFIRM, then saved
            self.until(page, "() => ED.S.data.syst.tgts[0].name === 'CB' && ED.S.data.syst.tgts[0].lat === 26.9707", what="renamed CB")
            # DELETE (past DESIGNATE and O/S), CONFIRM DELETE
            self.until(page, "() => !document.getElementById('tg-one').hidden && document.getElementById('tg-edit').classList.contains('focus')", what="back on EDIT")
            b.ufc_cmd("pulse COMM2_CW", "pulse COMM2_CW", "pulse COMM2_CW")
            self.until(page, "() => document.getElementById('tg-del').classList.contains('focus')", what="COMM2 on DELETE")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => !document.getElementById('tg-confirm').hidden && document.getElementById('tg-cancel').classList.contains('focus')", what="CANCEL first")
            b.ufc_cmd("pulse COMM2_CW", "press COMM2_PULL")
            self.until(page, "() => ED.S.data.syst.tgts.length === 0", what="deleted")
            self.no_errors()


FILTER_JS = r"""
(args) => {   // a synthetic flight through Traj's filter (ED.trajFilter.Nav), with its own clock: what it predicted at each
              // reading, and what the pages would have shown frame by frame (30 a second) up to each reading's arrival
  const F = ED.trajFilter, R = args.R, rd = args.readings, me = r => ({ body: "Synth 1", lat: r[1], lon: r[2], alt: r[3], r: R, avg: false, sc: false, glide: false });
  const nav = new F.Nav(me(rd[0])), out = { pred: [], frames: [], q: [], cont: [] };
  let clk = null, prev = null;
  for (let i = 0; i < rd.length; i++) {
    const t = rd[i][0], tin = t + 0.06;   // taken in 60 ms after it was written
    if (i >= 6) {
      const p = nav.at(t, true), a = nav.xy(p.lat, p.lon), b = nav.xy(rd[i][1], rd[i][2]);
      out.pred.push([t, Math.round(t - nav.t), Math.hypot(b[0] - a[0], b[1] - a[1])]);
      if (clk === null) clk = Math.ceil(tin * 30) / 30;
      for (; clk < tin; clk += 1 / 30) {
        const s = nav.at(clk), xy = nav.xy(s.lat, s.lon);
        if (prev) out.frames.push([clk, Math.hypot(xy[0] - prev[0], xy[1] - prev[1])]);
        prev = xy;
      }
      const before = nav.at(tin);
      nav.add(t, me(rd[i]), tin);
      const after = nav.at(tin), x0 = nav.xy(before.lat, before.lon), x1 = nav.xy(after.lat, after.lon);
      out.cont.push(Math.hypot(x1[0] - x0[0], x1[1] - x0[1]));   // what the pages show, either side of taking it in
    } else nav.add(t, me(rd[i]), tin);
    out.q.push(nav.q);
  }
  const last = rd[rd.length - 1][0], p0 = nav.at(last, true), quiet = args.quiet || 9.5;
  const a45 = nav.at(last + 4.5, true), s6 = nav.at(last + quiet, true), x0 = nav.xy(p0.lat, p0.lon), x45 = nav.xy(a45.lat, a45.lon);
  out.on45 = Math.hypot(x45[0] - x0[0], x45[1] - x0[1]); out.still45 = a45.still; out.still6 = s6.still; out.v6 = Math.hypot(...s6.v);
  out.gs = Math.hypot(nav.kx.x[1], nav.ky.x[1]);
  return out;
}
"""


HOVER_JS = r"""
(args) => {   // slowing from 60 m/s to a hover, a reading a second, then silence; then 30 s later off again at 200 m/s
  const F = ED.trajFilter, R = args.R, cl = Math.cos(1 * Math.PI / 180);
  const me = (x, y) => ({ body: "Synth 1", lat: 1 + y / R * 180 / Math.PI, lon: 38 + x / (R * cl) * 180 / Math.PI, alt: 100, r: R, avg: false, sc: false, glide: false });
  let x = 0, v = 60, t = 0;
  const nav = new F.Nav(me(0, 0));
  for (; t < 12; t += 1) { nav.add(t, me(x, 0), t + 0.06); x += v; v = Math.max(8, v - 6); }
  const lastX = x - v - 6 >= 0 ? null : null, last = nav.last, p = nav.at(t + 5, true), a = nav.xy(p.lat, p.lon), bxy = nav.xy(last.lat, last.lon);
  const out = { drift: Math.hypot(a[0] - bxy[0], a[1] - bxy[1]), slow: Math.hypot(p.v[0], p.v[1]) < F.SLOW };
  t += 30; nav.add(t, me(x, 0), t + 0.06); out.v1 = Math.hypot(nav.kx.x[1], nav.ky.x[1]);
  t += 2; x += 400; nav.add(t, me(x, 0), t + 0.06); out.v2 = Math.hypot(nav.kx.x[1], nav.ky.x[1]);
  return out;
}
"""


class Filter(PageTest):
    """Traj's filter (Wpt and Atk use it too): in level flight the game writes only when your latitude or longitude has
    moved about 0.02 degrees - every 1 to 4 s fast, 8 s or more slower - so the filter carries you on through each gap
    for as long as the game should take at your speed, holds a steady speed, follows a turn, and what the pages show
    moves smoothly through each reading rather than freezing and jumping; slowing to a hover, it doesn't carry a drift
    on. Synthetic flights, with the game's file times a few ms out."""
    R = 2_000_000.0

    def flight(self, seed=7, secs=150, turn=(60, 90), rate=3.0, speed=200, rule=False):
        """Readings at random 1-4 s gaps - or (rule) as the game writes them: on its once-a-second look, when the
        latitude or longitude has moved 0.02 degrees since the last."""
        import random
        rnd = random.Random(seed)
        lat0, lon0, cl = 1.0, 38.0, math.cos(math.radians(1.0))
        times, s = [], 0.0
        while s < secs:
            s += (1.007 if rule else rnd.choice([1, 1, 2, 2, 3, 4])) + rnd.uniform(-0.01, 0.02)
            times.append(s)
        out, x, y, h, tk, j, dt, wrote = [], 0.0, 0.0, math.radians(110), 0.0, 0, 0.005, None
        while j < len(times):
            if tk >= times[j]:
                lat, lon = lat0 + math.degrees(y / self.R), lon0 + math.degrees(x / (self.R * cl))
                if not rule or wrote is None or max(abs(lat - wrote[0]), abs(lon - wrote[1])) >= 0.02:
                    out.append([round(times[j] + rnd.uniform(-0.015, 0.015), 3), round(lat, 7), round(lon, 7), 1000])
                    wrote = (lat, lon)
                j += 1
                continue
            if turn and turn[0] <= tk < turn[1]:
                h += math.radians(rate) * dt
            x += speed * math.sin(h) * dt
            y += speed * math.cos(h) * dt
            tk += dt
        return out

    def test_gaps_turns_and_smoothness(self):
        with Board("p_filter", **journals.syst()) as b:
            page = self.open(b)
            # straight and level at 200 m/s: predictions through 1-4 s gaps, the shown position never freezing or jumping
            got = page.evaluate(FILTER_JS, {"R": self.R, "readings": self.flight(turn=None)})
            settled = [p for p in got["pred"] if p[0] > 20]
            self.assertLess(max(p[2] for p in settled), 25, settled)   # (the old filter froze at 1.2 s: up to 560 m behind)
            moves = [f[1] for f in got["frames"] if f[0] > 20]
            self.assertTrue(min(moves) > 200 / 30 * 0.8 and max(moves) < 200 / 30 * 1.2, (min(moves), max(moves)))
            self.assertLess(max(got["cont"][4:]), 0.5, got["cont"])   # taking a reading in doesn't move what's shown
            self.assertEqual(got["q"][-1], page.evaluate("ED.trajFilter.Q_LO"))   # steady flight: the calm setting
            self.assertTrue(abs(got["on45"] - 200 * 4.5) < 30 and not got["still45"], got)   # carried on 4.5 s past the last
            self.assertTrue(got["still6"] and got["v6"] == 0, got)   # ... and stopped after 9.5 s of silence (game's due in 3.7 s)
            # a 90 degree turn at 3 degrees a second: it notices, and is back on track within a few readings of the end
            got = page.evaluate(FILTER_JS, {"R": self.R, "readings": self.flight(turn=(60, 90))})
            qhi = page.evaluate("ED.trajFilter.Q_HI")
            self.assertIn(qhi / 2, got["q"][10:], "it should have switched to agile in the turn")
            after = [p for p in got["pred"] if p[0] > 100]
            self.assertLess(max(p[2] for p in after), 30, after)
            moves = [f[1] for f in got["frames"] if f[0] > 20]
            self.assertLess(max(moves), 200 / 30 * 2.5, "a correction in the turn should be eased in, not jumped")
            self.no_errors()

    def test_slow_and_hover(self):
        with Board("p_filter_slow", **journals.syst()) as b:
            page = self.open(b)
            # 100 m/s, the game writing by its 0.02 degree rule: every 8 s here - carried on through each gap at the right
            # speed (the old filter decided you'd stopped and then guessed the speed 60% high), never frozen
            rd = self.flight(turn=None, speed=100, rule=True, secs=200)
            gaps = [round(b2[0] - a[0]) for a, b2 in zip(rd, rd[1:])]
            self.assertEqual(max(gaps), 8, gaps)
            got = page.evaluate(FILTER_JS, {"R": self.R, "readings": rd, "quiet": 20})
            settled = [p for p in got["pred"] if p[0] > 40]
            self.assertLess(max(p[2] for p in settled), 20, settled)
            moves = [f[1] for f in got["frames"] if f[0] > 40]
            self.assertTrue(min(moves) > 100 / 30 * 0.8 and max(moves) < 100 / 30 * 1.2, (min(moves), max(moves)))
            self.assertLess(abs(got["gs"] - 100), 3, got["gs"])
            self.assertTrue(got["still6"], "stopped once the game's well overdue")
            # slowing to a hover: no drift carried on past the last reading, and Overfly marks the game's own position
            got = page.evaluate(HOVER_JS, {"R": self.R})
            self.assertLess(got["drift"], 10, got)
            self.assertTrue(got["slow"], got)
            # stopped a while, then off again: the speed starts afresh from the readings, not a guess
            self.assertTrue(got["v1"] == 0 and abs(got["v2"] - 200) < 20, got)
            self.no_errors()


class Atk(PageTest):
    """2 Nav > Atk: the mine-release computer - a level run at a settlement: the countdown, RELEASE, PAST, the cue,
    the arming-time warning, the scratchpad, the zoom."""

    def test_level_run(self):
        with Board("p_atk", **journals.syst()) as b:
            page = self.open(b)
            y = b.state()["syst"]
            hao = next(e for e in y["entries"] if e["name"] == "Hao Extraction Prospect")
            lat0, lon0, R = hao["pic"]["lat"], hao["pic"]["lon"], journals.NEAR_HAO["PlanetRadius"]
            east = lambda m: round(lon0 + m / (R * math.cos(math.radians(lat0))) * 180 / math.pi, 6)
            self.assertEqual(b.post("/api/nav", {"op": "dsg", "key": hao["key"]})[0], 200)   # the target: Hao, designated
            self.go(page, "nav", 5)
            self.on(page, "nav", 6, what="Atk")
            self.assertEqual(page.inner_text("#subtabs .stab.on").upper(), "5 ATK")
            page.click('#ak-mode button[data-v="atk"]')   # ATTACK
            self.until(page, "() => /NO STATE VECTOR/i.test(document.getElementById('ak-wait').textContent)", what="no position yet")
            self.assertIn("HAO EXTRACTION PROSPECT", page.inner_text("#pg-atk .trtop").upper())
            b.add({"event": "Undocked", "StationName": "Fabian City"})
            b.ufc_cmd("press ILS")   # (the page menu: the countdown on the scratchpad)
            # level, east at 150 m/s, 1,000 m up, 209 m north of its line, from 1.2 km short of the release point: the
            # throw is your speed for 10 s (the fall from 1,000 m on a 0.09 g world takes far longer): 1.5 km
            grav = next(e for e in y["entries"] if e["name"] == "HIP 20277 3 b")["gravity"]
            throw = 150 * min(10, math.sqrt(2 * 1000 / (grav * 9.80665)))
            seen, i = set(), 0
            def reading(i, alt=1000):
                b.write_status(dict(journals.NEAR_HAO, Latitude=round(lat0 + 0.008, 6), Longitude=east(-throw - 1200 + 150 * i), Altitude=alt, Heading=90))
            for i in range(4):
                reading(i)
                time.sleep(1.0)
            self.until(page, "() => ED.atkSolve().ok && ED.atkSolve().track", what="a track")
            g = page.evaluate("() => { const g = ED.atkSolve(); return {state: g.state, tau: g.tau, tf: g.tf, thr: g.thr, gs: g.gs, cross: g.cross, gG: g.gG}; }")
            self.assertEqual(g["state"], "Run in", g)
            self.assertLess(abs(g["gs"] - 150), 15, g)
            self.assertLess(abs(g["tf"] - math.sqrt(2 * 1000 / (g["gG"] * 9.80665))), 1, g)   # the fall, level, from the body's gravity
            self.assertLess(abs(g["thr"] - g["gs"] * min(10, g["tf"])), 1, g)   # your speed for 10 s (the fall's longer)
            self.assertTrue(1.5 < g["tau"] < 6.5, g)   # (600 m short of the release point at 150 m/s: about 4 s)
            self.assertTrue(150 < g["cross"] < 270, g)   # it's 209 m right of your line, 8 km on: steer right 1.5 degrees
            self.until(page, "() => /^REL /i.test(document.getElementById('ak-count').textContent)", what="the countdown")
            b.wait(lambda: b.display()["s1"] == "RL" or None, what="the countdown on the scratchpad")
            for cv in ("ak-plan", "ak-cue"):
                self.assertGreater(page.evaluate(CANVAS_INK_JS, cv), 5, f"#{cv} is empty")
            text = page.inner_text("#pg-atk").upper()
            for want in ("GRAVITY", "0.09 G", "FALL", "MIN REL ALT", "THROW", "CARRY 10 S", "ARM 5 S", "STEER R"):
                self.assertIn(want, text)
            # the fall: white over the 10 s carry (from 1,000 m at 0.09 g: 48 s)
            fall = "() => { const c = Array.from(document.querySelectorAll('#ak-rgrid .cell')).find(c => /FALL/i.test(c.textContent)); return getComputedStyle(c.querySelector('.v')).color; }"
            amber_c, red_c = page.evaluate("() => ['var(--accent)', 'var(--bad)'].map(v => { const e = document.createElement('span'); e.style.color = v; document.body.appendChild(e); const c = getComputedStyle(e).color; e.remove(); return c; })")
            self.assertEqual(page.evaluate(fall), "rgb(255, 255, 255)", "a fall over the 10 s carry: white")
            # range, ground speed and heights in two halves: metres, and a pilot's units
            halves = page.evaluate("() => Array.from(document.querySelectorAll('#pg-atk .cell.split')).map(c => Array.from(c.children).map(e => e.textContent))")
            self.assertEqual([h[0] for h in halves], ["Rng", "GS", "Alt", "Min rel alt"])
            rng, gs, alt, hmin = halves
            self.assertTrue(rng[1].endswith((" m", " km")) and rng[2].endswith(" NM"), rng)
            self.assertTrue(gs[2].endswith(" kts") and abs(int(gs[2].split()[0]) - float(gs[1].split()[0]) * 3600 / 1852) < 2, gs)   # (each rounded)
            self.assertTrue(alt[2].endswith(" ft") and abs(int(alt[2].split()[0].replace(",", "")) - 1000 / 0.3048) < 200, alt)
            self.assertTrue(hmin[2].endswith(" ft") and abs(int(hmin[2].split()[0]) - int(hmin[1].split()[0]) / 0.3048) < 3, hmin)
            # the second timer: in step with the countdown - at 12 o'clock on each whole second, amber until the release
            bt = page.evaluate("() => { const t = ED.atkSolve().tau, b = ED.atkBeat(); return {tau: t, b: b}; }")
            self.assertTrue(bt["b"]["on"] and not bt["b"]["red"], bt)
            da = abs(((-bt["tau"]) % 1) * 360 - bt["b"]["angle"])
            self.assertLess(min(da, 360 - da), 20, bt)   # (the two read a moment apart)
            # on to the release point and past it: red from the release beat on, for 3 s
            beats = []
            for i in range(4, 10):
                reading(i)
                for _ in range(4):
                    seen.add(page.evaluate("() => ED.atkSolve().state"))
                    beats.append(page.evaluate("() => { const t = ED.atkSolve().tau, b = ED.atkBeat(); return [t, b.on, !!b.red]; }"))
                    time.sleep(0.25)
            self.assertIn("Release", seen)
            for tau, on, red in beats:
                if tau is not None and tau < -0.2 and tau > -2.8:
                    self.assertTrue(on and red, (tau, on, red))
                if tau is not None and 0.2 < tau < 19.8:
                    self.assertTrue(on and not red, (tau, on, red))
                if tau is not None and tau < -3.2:
                    self.assertFalse(on, (tau, on, red))
            self.until(page, "() => ED.atkSolve().state === 'Past' && /PAST/i.test(document.getElementById('ak-count').textContent)", what="PAST")
            # low over a light world: the fall's shorter than the arming time
            # diving at 30 m/s from 900 m: the fall's still far longer than 10 s, so the throw's the same - no warning; low
            # down, where the fall's nearer 10 s, a dive shortens it (and a climb lengthens it)
            for k, alt in enumerate((970, 940, 910)):
                reading(10 + k, alt=alt)
                time.sleep(1.0)
            time.sleep(1.5)
            self.assertNotIn("DIVING", page.inner_text("#ak-warn").upper())
            m = page.evaluate(f"() => {{ const M = ED.atkModel, gm = {grav} * 9.80665; return [M.CARRY, M.throwOf(150, 60, 0, gm), M.throwOf(150, 60, -10, gm), M.throwOf(150, 60, 10, gm), M.throwOf(150, 900, -30, gm)]; }}")
            self.assertEqual(m[0], 10)
            self.assertTrue(m[2] < m[1] - 300 and m[3] > m[1] - 1 and m[4] == 1500, m)
            reading(13, alt=30)   # 30 m: a fall of 8.2 s - inside the 10 s carry: amber (the height's averaged over 3 s: it comes down a while)
            self.until(page, f"() => ED.atkSolve().tf <= 10 && ED.atkSolve().tf >= 5 && ({fall})() === {json.dumps(amber_c)}", timeout=30, what="the fall amber")
            reading(14, alt=10)
            self.until(page, "() => /UNDER THE 5 S ARMING TIME/i.test(document.getElementById('ak-warn').textContent)", timeout=30, what="the arming warning")
            self.until(page, f"() => ({fall})() === {json.dumps(red_c)}", what="the fall red")
            # the zoom: the wheel, then RESET SCALE
            page.hover("#ak-plan-svg")
            page.mouse.wheel(0, -300)
            self.until(page, "() => ED.atk.zoom && /MANUAL/i.test(document.getElementById('ak-zoom').textContent)", what="zoomed")
            page.click("#ak-reset")
            self.until(page, "() => ED.atk.zoom === null", what="RESET SCALE")
            # undesignated: no target
            self.assertEqual(b.post("/api/nav", {"op": "dsg", "off": True})[0], 200)
            self.until(page, "() => /NO TARGET/i.test(document.getElementById('ak-wait').textContent)", what="no target")
            self.no_errors()

    def test_timing_log(self):
        """--timing-log: the page notes its side - each fetch and refresh, each reading the filter takes in, and every
        frame on Atk (drawn or not), with what it drew from - beside the board's records."""
        with Board("p_atk_timing", extra_args=["--timing-log"], **journals.syst()) as b:
            page = self.open(b)
            y = b.state()["syst"]
            hao = next(e for e in y["entries"] if e["name"] == "Hao Extraction Prospect")
            lat0, lon0, R = hao["pic"]["lat"], hao["pic"]["lon"], journals.NEAR_HAO["PlanetRadius"]
            east = lambda m: round(lon0 + m / (R * math.cos(math.radians(lat0))) * 180 / math.pi, 6)
            self.assertEqual(b.post("/api/nav", {"op": "dsg", "key": hao["key"]})[0], 200)
            self.go(page, "nav", 5)
            self.on(page, "nav", 6, what="Atk")
            page.click('#ak-mode button[data-v="atk"]')
            for i in range(4):
                b.write_status(dict(journals.NEAR_HAO, Latitude=round(lat0 + 0.0008, 6), Longitude=east(-2400 + 150 * i), Altitude=1000, Heading=90))
                time.sleep(1.0)
            self.until(page, "() => ED.timing.on() && ED.atkSolve().ok && ED.atkSolve().track", what="a track, timed")
            self.assertIn("TIMING LOG ON", page.inner_text("#ak-model").upper())
            path = b.dir / "timing_log.jsonl"
            def recs():
                if not path.exists():
                    return None
                r = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
                return r if any(x["k"] == "p.fr" and x.get("tau") is not None for x in r) and any(x["k"] == "p.in" and "jx" in x for x in r) else None
            got = b.wait(recs, timeout=10, what="the page's records")
            kinds = {r["k"] for r in got}
            for k in ("p.info", "p.ref", "p.ev", "p.in", "p.fr", "api", "st"):
                self.assertIn(k, kinds)
            info = next(r for r in got if r["k"] == "p.info")
            self.assertTrue(info["ua"] and info["dpr"] > 0, info)
            ref = [r for r in got if r["k"] == "p.ref" and r.get("mt")][-1]
            self.assertTrue(ref["f"] >= 0 and ref["kb"] > 0 and ref["why"] in ("sse", "poll", "start", "jump") or ref["why"].startswith("again"), ref)
            inn = [r for r in got if r["k"] == "p.in" and "jx" in r][-1]
            self.assertTrue(0 <= inn["e2e"] < 5 and 0.5 < inn["gap"] < 2 and abs(inn["vx"] - 150) < 40, inn)
            fr = [r for r in got if r["k"] == "p.fr"]
            drawn = [r for r in fr if r["d"] == 1 and r.get("tau") is not None]
            self.assertTrue(drawn and any(r["d"] == 0 for r in fr) or len(fr) > 20, fr[:5])   # (offered faster than it draws, at 60 Hz)
            d = drawn[-1]
            self.assertTrue(len(d["p"]) == 4 and d["ms"] >= 0 and 0 <= d["age"] < 3 and abs(d["gs"] - 150) < 40, d)
            self.assertTrue(all(abs(r["w"] - 1e12) > 0 and r["w"] > 1.6e12 for r in fr[:10]), fr[:3])   # wall clock, in ms
            self.no_errors()


class NavPages(PageTest):
    """2 Nav's waypoint system on the page and the UFC: Wpt's UFC sub-levels (a waypoint's POSN, NAME, O/S and DEL; a flight
    plan's INS, AFT, DEL and ACT), DSG cycling a waypoint and its offset aimpoint; the HSI flying a plan (AUTO sequencing,
    COMM1 turning the steer-to point, DSG, MK from the page's filter, the scratchpad and COM windows); Atk's PLAN (its
    sub-level, BUILD, the role, the plan code)."""
    PLANET = "HIP 20277 3 b"
    R = journals.NEAR_HAO["PlanetRadius"]

    def east(self, m, lat0=-13.1, lon0=34.9):   # a longitude m metres east
        return round(lon0 + m / (self.R * math.cos(math.radians(lat0))) * 180 / math.pi, 6)

    def wpts(self, b, *pts):
        return [b.post("/api/tgt", {"op": "add", "body": self.PLANET, "lat": la, "lon": lo, "method": "manual"})[1]["tgt"] for la, lo in pts]

    def nav(self, page, js):
        return page.evaluate(f"() => {{ const n = ED.S.data.syst.nav; return {js}; }}")

    def test_wpt_sub_levels(self):
        with Board("p_nav_wpt", **journals.syst()) as b:
            page = self.open(b)
            w1, w2, w3 = self.wpts(b, (-13.1, 34.9), (-13.0, 35.0), (-12.9, 35.1))
            b.ufc_cmd("press ILS", "press Opt2", "press 3")
            self.on(page, "nav", 4, what="Wpt from the keypad")
            self.until(page, "() => ED.S.data.syst.tgts.length === 3", what="the waypoints")
            b.ufc_cmd(*["pulse COMM1_CW"] * 4)   # past the four methods: WP1
            self.until(page, f"() => ED.tgt.focus1 === '{w1['key']}'", what="COMM1 on WP1")
            # ENT: WP1 on the UFC - POSN NAME O/S DEL
            b.ufc_cmd("press Ent")
            self.until(page, "() => ED.tgt.lv && ED.tgt.lv.kind === 'wpt' && !document.getElementById('tg-lv').hidden", what="WP1's sub-level")
            b.wait(lambda: b.display()["options"] == ["POSN", "NAME", "O/S", "DEL", ""] or None, what="its fields in the option windows")
            # POSN: S 13.2, the longitude as it is
            b.ufc_cmd("press Opt1", *[f"press {k}" for k in "8132"], pause=0.25)
            b.wait(lambda: (lambda d: d if (d["cue"], d["s1"], d["scratch"]) == (1, "S", "13.2") else None)(b.display()), what="POSN typed, ':' beside it")
            b.ufc_cmd("press Ent", "press Ent")
            self.until(page, f"() => ED.S.data.syst.tgts.find(t => t.key === '{w1['key']}').lat === -13.2", what="WP1 moved")
            # NAME: cleared, then B
            b.ufc_cmd("press Opt2", "press Clr", "press 2", "press 2", "press Ent", pause=0.25)
            self.until(page, f"() => ED.S.data.syst.tgts.find(t => t.key === '{w1['key']}').name === 'B'", what="WP1 renamed B")
            # O/S: 500 m at 090
            b.ufc_cmd("press Opt3", *[f"press {k}" for k in "500"], "press Ent", *[f"press {k}" for k in "90"], "press Ent", pause=0.25)
            self.until(page, f"() => (ED.S.data.syst.nav.oaps['{w1['key']}o'] || {{}}).rng === 500", what="its offset aimpoint")
            self.assertEqual(self.nav(page, f"n.oaps['{w1['key']}o'].brg"), 90)
            # DEL: armed (CONFIRM on the scratchpad), CLR disarms; CLR again closes the sub-level
            b.ufc_cmd("press Opt4")
            b.wait(lambda: b.display()["scratch"] == "CONFIRM" or None, what="DEL armed")
            b.ufc_cmd("press Clr", "press Clr")
            b.wait(lambda: b.display()["options"] == ["HOME", "NAV", "CTRS", "DSG", "MK"] or None, what="the page menu back")
            self.until(page, "() => !ED.tgt.lv", what="the sub-level closed")
            self.assertEqual(page.evaluate("() => ED.S.data.syst.tgts.length"), 3)
            # DSG: WP1; again its offset aimpoint; again nothing
            for want in (w1["key"], w1["key"] + "o", None):
                b.ufc_cmd("press Opt4")
                self.until(page, f"() => ((ED.S.data.syst.nav.tgt || {{}}).key || null) === {json.dumps(want)}", what=f"DSG: {want}")
            # SEQ 1 on the UFC: INS 1, 3, 2 (each after the last); AFT 1; DEL 3; ACT
            b.ufc_cmd(*["pulse COMM1_CW"] * 3)
            self.until(page, "() => ED.tgt.focus1 === 'seq:1'", what="COMM1 on SEQ 1")
            b.ufc_cmd("press Ent")
            b.wait(lambda: b.display()["options"] == ["INS", "AFT", "DEL", "CLR", "ACT"] or None, what="the flight plan's fields")
            b.ufc_cmd("press Opt1", "press 1", "press Ent", "press 3", "press Ent", "press 2", "press Ent", pause=0.4)
            keys = [w1["key"], w3["key"], w2["key"]]
            self.until(page, f"() => JSON.stringify(ED.S.data.syst.nav.seqs['1']) === {json.dumps(json.dumps(keys, separators=(",", ":")))}", what="SEQ 1: WP1 WP3 WP2")
            b.ufc_cmd("press Opt3", "press 3", "press Ent", pause=0.3)
            self.until(page, f"() => JSON.stringify(ED.S.data.syst.nav.seqs['1']) === {json.dumps(json.dumps([w1['key'], w2['key']], separators=(",", ":")))}", what="WP3 out")
            b.ufc_cmd("press Opt5")
            self.until(page, f"() => ED.S.data.syst.nav.seq === '1' && ED.S.data.syst.nav.steer === '{w1['key']}'", what="ACT: the HSI's plan")
            self.until(page, "() => /SEQ 1 >WP1 - WP2/i.test(document.getElementById('tg-strip').textContent)", what="the strip")
            self.assertEqual(page.inner_text("#tg-sact").upper(), "SEQ ACTIVATED")
            # the list: each waypoint by its number and name (its position's on the right, not here); no CREATE button lit
            # with a flight plan showing - MANUAL lit only with its panel
            rows = page.evaluate("() => Array.from(document.querySelectorAll('#tg-list .srow.tgr[data-key^=\"t\"]')).map(r => [r.querySelector('.tgnum').textContent, r.querySelector('.rt').textContent])")
            self.assertEqual(rows, [["WP1", ""], ["WP2", ""], ["WP3", ""]])
            self.assertEqual(page.evaluate("() => document.querySelectorAll('#tg-meth button.on').length"), 0)
            page.click('#tg-meth button[data-m="manual"]')
            self.until(page, "() => document.querySelector('#tg-meth button[data-m=\"manual\"]').classList.contains('on')", what="MANUAL lit with its panel")
            page.click('#tg-list .srow[data-key="seq:1"]')
            self.until(page, "() => document.querySelectorAll('#tg-meth button.on').length === 0", what="none lit again")
            # ADD WP # on COMM2: the keypad types the number (on the scratchpad), ENT inserts it - after the picked one
            n = 0
            while page.evaluate("() => ED.tgt.focus2") != "sadd" and n < 8:
                b.ufc_cmd("pulse COMM2_CW")
                time.sleep(0.3)
                n += 1
            self.assertTrue(page.evaluate("() => document.getElementById('tg-sadd').classList.contains('focus')"), "ADD WP # outlined")
            b.ufc_cmd("press 3", pause=0.3)
            b.wait(lambda: (lambda d: d if (d["s1"], d["scratch"]) == ("WP", "3") else None)(b.display()), what="WP 3 on the scratchpad")
            self.assertEqual(page.evaluate("() => [document.getElementById('tg-sadd').value, ED.S.ufc.view]"), ["3", {"tab": "nav", "sub": 4}], "typed, not a sub-tab")
            b.ufc_cmd("press Ent")
            three = json.dumps(json.dumps([w1["key"], w2["key"], w3["key"]], separators=(",", ":")))
            self.until(page, f"() => JSON.stringify(ED.S.data.syst.nav.seqs['1']) === {three}", what="WP3 in at the end")
            # moving up and down: the arrows (the picked one), then COMM2 - a pull grabs it, turns move it, a pull lets go
            page.click(f'#tg-chain .srow[data-c="{w3["key"]}"]')
            page.click("#tg-sup")
            order = lambda *ws: json.dumps(json.dumps([w["key"] for w in ws], separators=(",", ":")))
            self.until(page, f"() => JSON.stringify(ED.S.data.syst.nav.seqs['1']) === {order(w1, w3, w2)}", what="WP3 up one")
            self.assertTrue(page.evaluate("() => document.getElementById('tg-sdn').disabled === false && document.getElementById('tg-sup').disabled === false"))
            page.click("#tg-sup")
            self.until(page, f"() => JSON.stringify(ED.S.data.syst.nav.seqs['1']) === {order(w3, w1, w2)}", what="WP3 first")
            self.until(page, "() => document.getElementById('tg-sup').disabled", what="up off for the first")
            b.ufc_cmd("pulse COMM2_CCW", "pulse COMM2_CCW", "pulse COMM2_CCW", "pulse COMM2_CCW", "pulse COMM2_CCW", pause=0.2)
            self.until(page, f"() => ED.tgt.focus2 === 'c:{w3['key']}'", what="COMM2 on WP3 in the plan")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, f"() => ED.tgt.grab && ED.tgt.grab.key === '{w3['key']}' && document.querySelector('#tg-chain .srow.grab')", what="WP3 grabbed")
            b.ufc_cmd("pulse COMM2_CW", "pulse COMM2_CW", "pulse COMM2_CW", pause=0.2)   # (two places down: the third held at the end)
            self.until(page, f"() => JSON.stringify(ED.S.data.syst.nav.seqs['1']) === {order(w1, w2, w3)}", what="WP3 last")
            b.ufc_cmd("pulse COMM2_CCW", pause=0.3)
            self.until(page, f"() => JSON.stringify(ED.S.data.syst.nav.seqs['1']) === {order(w1, w3, w2)}", what="back up one at once")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => !ED.tgt.grab", what="let go")
            b.ufc_cmd("pulse COMM2_CW", pause=0.3)
            self.until(page, f"() => ED.tgt.focus2 === 'c:{w2['key']}'", what="COMM2 steps on again")
            self.assertEqual(page.evaluate("() => JSON.stringify(ED.S.data.syst.nav.seqs['1'])"), json.loads(order(w1, w3, w2)))
            # the mouse: insert by number after the picked one, remove it
            page.click('#tg-list .srow[data-key="seq:2"]')
            page.fill("#tg-sadd", "3")
            page.click("#tg-sins")
            self.until(page, f"() => JSON.stringify(ED.S.data.syst.nav.seqs['2']) === {json.dumps(json.dumps([w3['key']], separators=(",", ":")))}", what="SEQ 2: WP3")
            page.click(f'#tg-chain .srow[data-c="{w3["key"]}"]')
            page.click("#tg-sdel")
            self.until(page, "() => ED.S.data.syst.nav.seqs['2'].length === 0", what="removed")
            self.no_errors()

    def test_hsi_timer(self):
        """The HSI's timer, bottom left of its map - the T-6A's clock: ET / CD its SEL (the stopwatch or the countdown; not
        while it runs), the time its CTL (start, again reset). A countdown with no time set: CTL asks for it - on the keypad
        (the scratchpad shows it; ENT sets it) or, clicked, the keyboard. At zero it flashes and counts up; SEL stops the
        flashing. With COMM1 on it the scratchpad shows it; on the other pages a copy shows in the sub-tab row. Two pages
        open: each press done once."""
        with Board("p_nav_timer", **journals.syst()) as b:
            page = self.open(b)
            other = self.browser.new_page(viewport={"width": 1280, "height": 800})   # a second screen: each press acted on once
            other.goto(b.url + "/")
            other.wait_for_function("() => document.querySelector('.tab.on') !== null", timeout=10000)
            self.skip_intro(other)
            b.ufc_cmd("press ILS", "press Opt2", "press 4")
            for pg in (page, other):
                self.on(pg, "nav", 5, what="both pages on the HSI")
            # bottom left of the map, under the rose
            geo = page.evaluate("""() => { const w = document.querySelector('#pg-hsi .trwin').getBoundingClientRect(),
                t = document.getElementById('hs-tmr').getBoundingClientRect(); return [w.left, w.bottom, t.left, t.bottom, t.top, t.right, w.left + w.width / 2]; }""")
            self.assertTrue(abs(geo[2] - geo[0]) < 2 and abs(geo[3] - geo[1]) < 2 and geo[5] < geo[6], geo)
            self.assertEqual(page.evaluate("() => [document.getElementById('hs-tmode').textContent, document.getElementById('hs-tdig').textContent]"), ["ET", "00:00:00"])
            # COMM1 on to ET / CD (after KM / NM): the scratchpad shows the timer
            b.ufc_cmd(*["pulse COMM1_CW"] * 5)
            self.until(page, "() => ED.hsi.focus1 === 'tmode' && document.getElementById('hs-tmode').classList.contains('focus')", what="COMM1 on ET / CD")
            b.wait(lambda: (lambda d: d if (d["s1"], d["scratch"]) == ("ET", "00:00:00") else None)(b.display()), what="the timer on the scratchpad")
            # the time (CTL): start - once, with two pages answering - then reset
            b.ufc_cmd("pulse COMM1_CW", "press COMM1_PULL")
            self.until(page, "() => ED.S.ufc.timer.run && /run/.test(document.getElementById('hs-tdig').className)", what="ET running")
            time.sleep(2.2)
            self.assertTrue(b.bus()["timer"]["run"], "started once, not started and reset")
            self.until(page, "() => document.getElementById('hs-tdig').textContent >= '00:00:02'", what="counting")
            b.wait(lambda: (lambda d: d if d["s1"] == "ET" and d["scratch"] >= "00:00:02" else None)(b.display()), what="counting on the scratchpad")
            # SEL doesn't change it while it runs
            b.ufc_cmd("pulse COMM1_CCW", "press COMM1_PULL")
            self.until(page, "() => /resets it first/.test(document.getElementById('hs-note').textContent)", what="SEL refused while running")
            self.assertEqual(b.bus()["timer"]["mode"], "et")
            b.ufc_cmd("pulse COMM1_CW", "press COMM1_PULL")
            self.until(page, "() => !ED.S.ufc.timer.run && document.getElementById('hs-tdig').textContent === '00:00:00'", what="reset to zero")
            # SEL: the countdown - no time set; CTL asks for one on the keypad (digits to the page, not the sub-tabs)
            b.ufc_cmd("pulse COMM1_CCW", "press COMM1_PULL")
            self.until(page, "() => ED.S.ufc.timer.mode === 'cd' && document.getElementById('hs-tmode').textContent === 'CD' && document.getElementById('hs-tdig').textContent === '--:--:--'", what="CD")
            b.ufc_cmd("pulse COMM1_CW", "press COMM1_PULL")
            self.until(page, "() => ED.hsi.tin && ED.hsi.tin.d === '' && /typing/.test(document.getElementById('hs-tdig').className)", what="typing the countdown's time")
            b.ufc_cmd("press 0", "press 0", "press 0", "press 0", "press 0", "press 3")
            self.until(page, "() => document.getElementById('hs-tdig').textContent === '00:00:03'", what="as typed")
            b.wait(lambda: (lambda d: d if (d["s1"], d["scratch"]) == ("CD", "00:00:03") else None)(b.display()), what="the typing on the scratchpad")
            self.assertEqual(b.bus()["view"], {"tab": "nav", "sub": 5}, "the digits typed - no sub-tab")
            b.ufc_cmd("press Ent")
            self.until(page, "() => ED.S.ufc.timer.cd === 3 && !ED.hsi.tin && /set/.test(document.getElementById('hs-tdig').className)", what="ENT: set")
            # CTL starts it; at zero it flashes and counts up (+); the copy in the sub-tab row elsewhere - not on the HSI
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, "() => ED.S.ufc.timer.run", what="the countdown running")
            self.assertTrue(page.evaluate("() => document.getElementById('tmr-mini').hidden"), "no copy on the HSI")
            self.until(page, "() => /alarm/.test(document.getElementById('hs-tdig').className) && document.getElementById('hs-tdig').textContent.startsWith('+')", timeout=8, what="zero: flashing, counting up")
            b.wait(lambda: (lambda d: d if (d["s1"], d["s2"]) == ("CD", "UP") else None)(b.display()), what="UP on the scratchpad")
            b.ufc_cmd("press 3")
            self.on(page, "nav", 4, what="Wpt (the keypad on the sub-tabs again)")
            self.until(page, r"() => { const e = document.getElementById('tmr-mini'); return !e.hidden && /^CD \+00:00:\d\d$/.test(e.textContent) && /alarm/.test(e.className); }", what="the copy in the sub-tab row")
            b.ufc_cmd("press 4")
            self.on(page, "nav", 5, what="the HSI again")
            b.ufc_cmd(*["pulse COMM1_CW"] * 5, "press COMM1_PULL")   # SEL: the alarm seen - still counting up
            self.until(page, "() => ED.S.ufc.timer.ack && ED.S.ufc.timer.run && document.getElementById('hs-tdig').classList.contains('up')", what="SEL: no more flashing")
            b.ufc_cmd("pulse COMM1_CW", "press COMM1_PULL")   # CTL: reset - cleared, to set again
            self.until(page, "() => !ED.S.ufc.timer.run && ED.S.ufc.timer.cd === null && document.getElementById('hs-tdig').textContent === '--:--:--'", what="reset: cleared")
            self.assertTrue(page.evaluate("() => document.getElementById('tmr-mini') === null || document.getElementById('tmr-mini').hidden"))
            # ENT on the timer types a time; CLR clears what's typed, then stops typing
            b.ufc_cmd("press Ent", "press 1")
            self.until(page, "() => ED.hsi.tin && ED.hsi.tin.d === '1'", what="ENT: typing")
            b.ufc_cmd("press Clr")
            self.until(page, "() => ED.hsi.tin && ED.hsi.tin.d === ''", what="CLR: what's typed")
            b.ufc_cmd("press Clr")
            self.until(page, "() => !ED.hsi.tin && document.getElementById('hs-tdig').textContent === '--:--:--'", what="CLR again: not typing")
            # clicked: the keyboard types it (as HH:MM:SS); a click on the time is CTL
            page.click("#hs-tdig")
            self.until(page, "() => !document.getElementById('hs-tin').hidden && document.activeElement.id === 'hs-tin'", what="the keyboard's box")
            page.keyboard.type("013000")
            self.assertEqual(page.evaluate("() => document.getElementById('hs-tin').value"), "01:30:00")
            page.keyboard.press("Enter")
            self.until(page, "() => ED.S.ufc.timer.cd === 5400 && document.getElementById('hs-tdig').textContent === '01:30:00'", what="set by the keyboard")
            page.click("#hs-tdig")
            self.until(page, "() => ED.S.ufc.timer.run && document.getElementById('hs-tdig').textContent < '01:30:00'", what="a click: started")
            self.until(other, "() => ED.S.ufc.timer.run && document.getElementById('hs-tdig').textContent < '01:30:00'", what="the other page too")
            page.click("#hs-tdig")
            self.until(page, "() => !ED.S.ufc.timer.run && ED.S.ufc.timer.cd === null", what="a click: reset")
            page.click("#hs-tmode")
            self.until(page, "() => ED.S.ufc.timer.mode === 'et' && document.getElementById('hs-tmode').textContent === 'ET'", what="a click: SEL")
            self.no_errors()

    def test_hsi(self):
        with Board("p_nav_hsi", **journals.syst()) as b:
            page = self.open(b)
            b.add({"event": "Undocked", "StationName": "Fabian City"})
            ws = self.wpts(b, (-13.1, self.east(1500)), (-13.1, self.east(5000)), (-13.1, self.east(9000)))
            for w in ws:
                b.post("/api/nav", {"op": "seq", "seq": 1, "act": "ins", "id": w["id"]})
            b.post("/api/nav", {"op": "setseq", "seq": "1"})
            b.ufc_cmd("press ILS", "press Opt2", "press 4")
            self.on(page, "nav", 5, what="HSI from the keypad")
            self.until(page, "() => /NO STATE VECTOR/i.test(document.getElementById('hs-fix').textContent + document.getElementById('hs-wait').textContent)",
                       what="no fix: the plan view")
            lons = []
            def reading(i):   # east at 150 m/s, 800 m up
                lons.append(self.east(150 * i))
                b.write_status(dict(journals.NEAR_HAO, Latitude=-13.1, Longitude=lons[-1], Altitude=800, Heading=90))
            for i in range(4):
                reading(i)
                time.sleep(1.0)
            self.until(page, "() => ED.hsiSolve().fix && ED.hsiSolve().dist != null", what="a fix")
            g = page.evaluate("() => { const g = ED.hsiSolve(); return {brg: g.brg, dist: g.dist, gs: g.fix.gs, label: g.st.label}; }")
            self.assertEqual(g["label"], "WP1")
            self.assertTrue(85 < g["brg"] < 95 and 800 < g["dist"] < 1200 and abs(g["gs"] - 150) < 20, g)
            b.wait(lambda: (lambda d: d if (d["s1"], d["s2"], d["com1"], d["com2"]) == ("WP", "1", "1", "1") else None)(b.display()),
                   what="the scratchpad and COM windows")
            self.assertGreater(page.evaluate(CANVAS_INK_JS, "hs-map"), 5)
            # MK: the page marks where its filter has you now (between readings, so not a reading's own position)
            b.ufc_cmd("press Opt5", pause=0.1)
            self.until(page, "() => ED.S.data.syst.nav.marks.length === 1", timeout=5, what="MK")
            mk = page.evaluate("() => ED.S.data.syst.nav.marks[0]")
            self.assertNotIn(mk["lon"], lons, "marked from the filter, not the last reading")
            self.assertTrue(lons[-1] < mk["lon"] < self.east(150 * 5), (mk, lons))
            # AUTO: on past WP1, the steer-to point steps on to WP2
            for i in range(4, 12):
                reading(i)
                time.sleep(1.0)
                if page.evaluate(f"() => ED.S.data.syst.nav.steer === '{ws[1]['key']}'"):
                    break
            self.until(page, f"() => ED.S.data.syst.nav.steer === '{ws[1]['key']}'", what="AUTO: on to WP2")
            b.wait(lambda: b.display()["com1"] == "2" or None, what="COM1: the plan's 2nd point")
            # COMM2 turns the steer-to point (its name over BRG and TTG); a pull designates it, again its offset aimpoint -
            # none: nothing; DSG designates it too
            b.ufc_cmd("pulse COMM2_CW")
            self.until(page, f"() => ED.S.data.syst.nav.steer === '{ws[2]['key']}'", what="COMM2: WP3")
            self.until(page, f"() => document.getElementById('hs-stn').textContent === {json.dumps(ws[2]['name'])}", what="its name")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, f"() => (ED.S.data.syst.nav.tgt || {{}}).key === '{ws[2]['key']}'", what="COMM2 pull: WP3 the target")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => !ED.S.data.syst.nav.tgt", what="again: nothing")
            b.ufc_cmd("press Opt4")
            self.until(page, f"() => (ED.S.data.syst.nav.tgt || {{}}).key === '{ws[2]['key']}'", what="DSG: WP3 the target")
            self.assertFalse(page.evaluate("() => !!document.getElementById('hs-prev') || !!document.getElementById('hs-next')"), "no arrows")
            # COMM1: SEQ, AUTO / MAN (beside the plans), the view, RESET SCALE
            self.assertTrue(page.evaluate("() => document.getElementById('hs-auto').parentNode === document.getElementById('hs-seq').parentNode"))
            b.ufc_cmd("pulse COMM1_CW", "press COMM1_PULL")
            self.until(page, "() => ED.S.data.syst.nav.auto === false", what="MAN")
            b.ufc_cmd("pulse COMM1_CW", "press COMM1_PULL")
            self.until(page, "() => ED.hsi.view === 'N'", what="north up")
            # the body's planetary facilities: a TACAN symbol each and a light dashed ring 10 km round it (Hao Extraction
            # Prospect, 8-9 km south-west; the body's others are hundreds of km off)
            page.evaluate("() => { ED.hsi.zoom = 20000; }")
            self.until(page, "() => ED.hsi.drawn && ED.hsi.drawn.span === 20000 && ED.hsi.drawn.sites === 1 && ED.hsi.drawn.rings === 1", what="Hao: its symbol and ring")
            shapes = page.evaluate("""() => { const s = document.getElementById('hs-map-svg');
                return [Array.from(s.querySelectorAll('polygon')).filter(p => p.getAttribute('points').trim().split(/\\s+/).length === 12).length,
                        Array.from(s.querySelectorAll('path')).filter(p => p.getAttribute('stroke-dasharray') === '2 3').length]; }""")
            self.assertEqual(shapes, [1, 1], "the TACAN symbol (12 corners) and the dashed ring")
            page.evaluate("() => { ED.hsi.zoom = 2000; }")   # (well inside the ring: only its far side, through the rose - no symbol)
            self.until(page, "() => ED.hsi.drawn.span === 2000 && ED.hsi.drawn.sites === 0", what="Hao off the map")
            # COMM1 on: RESET SCALE, then KM / NM - a pull swaps the scale's units (its round steps in NM; kept)
            b.ufc_cmd("pulse COMM1_CW", "press COMM1_PULL")
            self.until(page, "() => ED.hsi.zoom === null && document.getElementById('hs-zoom').textContent.toUpperCase() === 'AUTO'", what="RESET SCALE")
            self.assertEqual(page.evaluate("() => [ED.hsi.units, Array.from(document.querySelectorAll('#hs-units button')).map(b => [b.textContent.toUpperCase(), b.classList.contains('on')])]"),
                             ["km", [["KM", True], ["NM", False]]])
            self.assertEqual(page.evaluate("() => document.getElementById('hs-units').previousElementSibling.id"), "hs-reset", "beside RESET SCALE")
            b.ufc_cmd("pulse COMM1_CW", "press COMM1_PULL")
            self.until(page, "() => ED.hsi.units === 'nm' && document.getElementById('hs-units').classList.contains('focus') && / NM$/.test(document.getElementById('hs-scale').textContent)", what="NM")
            nm_scale = page.evaluate("() => [ED.hsi.drawn.span, document.getElementById('hs-scale').textContent, JSON.parse(localStorage.getItem('ft3000-hsi')).units]")
            self.assertAlmostEqual(nm_scale[0] / 1852, float(nm_scale[1].split()[0]), places=6)
            self.assertIn(float(nm_scale[1].split()[0]), (0.5, 1, 2, 5, 10, 20), nm_scale)
            self.assertEqual(nm_scale[2], "nm", "kept")
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, "() => ED.hsi.units === 'km' && / k?m$/.test(document.getElementById('hs-scale').textContent)", what="back to km")
            page.click('#hs-units button[data-v="nm"]')
            self.until(page, "() => ED.hsi.units === 'nm' && document.querySelector('#hs-units button[data-v=\"nm\"]').classList.contains('on')", what="NM by a click")
            page.click('#hs-units button[data-v="km"]')
            self.until(page, "() => ED.hsi.units === 'km'", what="km by a click")
            # SEQ: NONE, SEQ 1-3, ATK. NONE: no plan - COMM2 steps through all the waypoints, then the marks (listed); a plan
            # activated: its points only
            self.assertEqual(page.evaluate("() => [document.querySelector('#pg-hsi .trtl .lab').textContent.toUpperCase(), "
                                           "Array.from(document.querySelectorAll('#hs-seq button')).map(b => b.textContent.toUpperCase())]"),
                             ["SEQ", ["NONE", "SEQ 1", "SEQ 2", "SEQ 3", "ATK"]])
            page.click('#hs-seq button[data-v="none"]')
            self.until(page, "() => ED.S.data.syst.nav.seq === 'none' && document.getElementById('hs-chainlab').textContent.toUpperCase() === 'ALL WAYPOINTS AND MARKS'", what="SEQ NONE")
            self.until(page, "() => document.querySelectorAll('#hs-chain .srow').length === 4", what="the three waypoints and the mark listed")
            red = page.evaluate("() => { const e = document.createElement('span'); e.style.color = 'var(--bad)'; document.body.appendChild(e); const c = getComputedStyle(e).color; e.remove(); return c; }")
            self.assertEqual(page.evaluate("() => getComputedStyle(document.querySelector('#pg-hsi .hstgtlab')).color"), red, "the Target heading red")
            b.ufc_cmd("pulse COMM2_CW")
            self.until(page, f"() => ED.S.data.syst.nav.steer === '{mk['key']}'", what="NONE: on from WP3 to MK1")
            page.click('#hs-seq button[data-v="1"]')
            self.until(page, f"() => ED.S.data.syst.nav.seq === '1' && ED.S.data.syst.nav.steer === '{ws[0]['key']}'", what="SEQ 1: steer to its first")
            self.until(page, "() => document.querySelectorAll('#hs-chain .srow').length === 3", what="its points listed")
            b.ufc_cmd("pulse COMM2_CCW")
            self.until(page, f"() => ED.S.data.syst.nav.steer === '{ws[2]['key']}'", what="SEQ 1: only its points - back round to WP3")
            self.no_errors()

    def test_two_pages_and_syst_dsg(self):
        """Two pages open both answer every UFC press, and what it does is done once: each turn of COMM2 steps the HSI's
        steer-to point one point (back and forth), and a COMM2 pull's waypoint is stored once. 1 Syst's DSG: what COMM1
        highlights if it can be designated (a waypoint, a surface site with a position), else what's picked."""
        with Board("p_nav_two", **journals.syst()) as b:
            page = self.open(b)
            other = self.browser.new_page(viewport={"width": 1280, "height": 800})   # a second screen
            other.goto(b.url + "/")
            other.wait_for_function("() => document.querySelector('.tab.on') !== null", timeout=10000)
            self.skip_intro(other)
            ws = self.wpts(b, (-13.1, 34.9), (-13.0, 35.0), (-12.9, 35.1), (-12.8, 35.2))
            for w in ws[:3]:
                b.post("/api/nav", {"op": "seq", "seq": 1, "act": "ins", "id": w["id"]})
            b.post("/api/nav", {"op": "setseq", "seq": "1"})
            b.ufc_cmd("press ILS", "press Opt2", "press 4")
            for pg in (page, other):
                self.on(pg, "nav", 5, what="both pages on the HSI")
            steer = f"() => ED.S.data.syst.nav.steer"
            self.until(page, f"() => ED.S.data.syst.nav.steer === '{ws[0]['key']}'", what="WP1")
            b.ufc_cmd("pulse COMM2_CW")
            self.until(page, f"() => ED.S.data.syst.nav.steer === '{ws[1]['key']}'", what="one turn: on one point")
            time.sleep(1.0)
            self.assertEqual(page.evaluate(steer), ws[1]["key"], "one point, not one for each page")
            b.ufc_cmd("pulse COMM2_CW", "pulse COMM2_CW", "pulse COMM2_CCW", pause=0.05)   # quickly: +2 -1
            self.until(page, f"() => ED.S.data.syst.nav.steer === '{ws[2]['key']}'", what="+2 -1: WP3")
            time.sleep(1.0)
            self.assertEqual((page.evaluate(steer), other.evaluate(steer)), (ws[2]["key"], ws[2]["key"]))
            # Wpt, MK1 made: COMM2's STORE on it stores it as a waypoint once, with both pages answering the pull
            b.post("/api/nav", {"op": "mark", "body": self.PLANET, "lat": -12.7, "lon": 35.3, "method": "overfly"})
            b.ufc_cmd("press 3")
            for pg in (page, other):
                self.on(pg, "nav", 4, what="both pages on Wpt")
                self.until(pg, "() => ED.S.data.syst.nav.marks.length === 1", what="MK1")
            self.until(page, "() => !!document.querySelector('#tg-list .srow[data-key=\"mk1\"]')", what="MK1 in the list")
            n = 0
            while page.evaluate("() => ED.tgt.focus1") != "mk1" and n < 12:
                b.ufc_cmd("pulse COMM1_CW")
                time.sleep(0.3)
                n += 1
            self.assertEqual(page.evaluate("() => ED.tgt.focus1"), "mk1")
            self.until(other, "() => ED.tgt.focus1 === 'mk1'", what="the other page on MK1 too")
            b.ufc_cmd("press COMM1_PULL")   # (MK1 in the right panel)
            for pg in (page, other):
                self.until(pg, "() => ED.tgt.view === 'mk1'", what="MK1 shown")
            n = 0
            while page.evaluate("() => ED.tgt.focus2") != "mstor" and n < 8:
                b.ufc_cmd("pulse COMM2_CW")
                time.sleep(0.3)
                n += 1
            self.assertEqual(page.evaluate("() => ED.tgt.focus2"), "mstor")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => ED.S.data.syst.tgts.length === 5", what="MK1 stored")
            time.sleep(1.5)
            self.assertEqual(len(b.state()["syst"]["tgts"]), 5, "stored once")
            # 1 Syst: COMM1 on the star (can't be designated), a site picked: DSG designates the site
            y = b.state()["syst"]
            star = next(e["key"] for e in y["entries"] if e["kind"] == "star")
            hao = next(e["key"] for e in y["entries"] if e["name"] == "Hao Extraction Prospect")
            self.assertEqual(page.evaluate(f"() => [ED.nav.dsgable('{star}'), ED.nav.dsgable('{hao}'), ED.nav.dsgable('{ws[0]['key']}'), ED.nav.dsgable('atk:1:IP')]"),
                             [False, True, True, False])
            b.ufc_cmd("press 1")
            for pg in (page, other):
                self.on(pg, "nav", 1, what="both pages on the System list")
                pg.click(f'#sy-list .srow[data-key="{hao}"]')
            n = 0
            while b.bus()["cursors"].get("syst") != star and n < 40:
                b.ufc_cmd("pulse COMM1_CCW")
                time.sleep(0.2)
                n += 1
            self.assertEqual(b.bus()["cursors"].get("syst"), star)
            b.ufc_cmd("press Opt4")
            self.until(page, f"() => (ED.S.data.syst.nav.tgt || {{}}).key === '{hao}'", what="DSG: the site picked, not the star")
            self.no_errors()
            other.close()

    def comm2_to(self, b, page, stop, n=14):   # COMM2 round the Wpt right panel to a stop
        for _ in range(n):
            if page.evaluate("() => ED.tgt.focus2") == stop:
                return
            b.ufc_cmd("pulse COMM2_CW")
            time.sleep(0.3)
        self.assertEqual(page.evaluate("() => ED.tgt.focus2"), stop)

    def test_time_on_target(self):
        """Time on target, as the Hornet's: on Wpt, a flight plan's TGT (the picked waypoint, boxed), TOT (Zulu, typed
        HHMMSS on the keypad) and GSPD (the IP > TGT leg); on the HSI, the ground speed you need now - to the IP, to fly the
        last leg at GSPD and be over the TGT on the TOT - and how early or late you'd be."""
        import datetime
        with Board("p_nav_tot", **journals.syst()) as b:
            page = self.open(b)
            b.add({"event": "Undocked", "StationName": "Fabian City"})
            ws = self.wpts(b, (-13.1, self.east(1500)), (-13.1, self.east(5000)), (-13.1, self.east(9000)))
            for w in ws:
                b.post("/api/nav", {"op": "seq", "seq": 1, "act": "ins", "id": w["id"]})
            b.post("/api/nav", {"op": "setseq", "seq": "1"})
            b.ufc_cmd("press ILS", "press Opt2", "press 3")
            self.on(page, "nav", 4, what="Wpt")
            page.click('#tg-list .srow[data-key="seq:1"]')
            self.until(page, "() => !document.getElementById('tg-seq').hidden", what="SEQ 1")
            self.assertTrue(page.evaluate("() => document.getElementById('tg-stot').disabled && document.getElementById('tg-sgspd').disabled"), "no TGT: no TOT")
            # SET TGT: the picked waypoint (WP3), boxed; DSG elsewhere doesn't change it
            page.click(f'#tg-chain .srow[data-c="{ws[2]["key"]}"]')
            self.comm2_to(b, page, "stgt")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, f"() => ED.S.data.syst.nav.tots['1'].tgt === '{ws[2]['key']}'", what="SEQ 1's TGT: WP3")
            self.until(page, f"() => !!document.querySelector('#tg-chain .srow[data-c=\"{ws[2]['key']}\"] .tgbox')", what="WP3 boxed")
            # TOT: the keypad's digits fill HH:MM:SS (on the scratchpad), ENT sets it; GSPD the same
            z = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
            digits = z.strftime("%H%M%S")
            self.comm2_to(b, page, "stot")
            b.ufc_cmd(*[f"press {k}" for k in digits], pause=0.15)
            b.wait(lambda: (lambda d: d if (d["s1"], d["scratch"]) == ("TO", z.strftime("%H:%M:%S")) else None)(b.display()), what="the TOT on the scratchpad")
            b.ufc_cmd("press Ent")
            want = z.hour * 3600 + z.minute * 60 + z.second
            self.until(page, f"() => ED.S.data.syst.nav.tots['1'].tot === {want}", what="the TOT set")
            self.comm2_to(b, page, "sgspd")
            b.ufc_cmd("press 3", "press 0", "press 0", "press Ent", pause=0.15)
            self.until(page, "() => ED.S.data.syst.nav.tots['1'].gspd === 300", what="GSPD 300")
            self.assertIn("WP2 (IP) > WP3 AT 300 KTS", page.inner_text("#tg-totl").upper())
            # the HSI (NAV: the next sub-tab - the keypad's GSPD's while it's highlighted): flying east at 150 m/s towards WP1
            b.ufc_cmd("press Opt2")
            self.on(page, "nav", 5, what="HSI")
            for i in range(4):
                b.write_status(dict(journals.NEAR_HAO, Latitude=-13.1, Longitude=self.east(150 * i), Altitude=800, Heading=90))
                time.sleep(1.0)
            self.until(page, "() => !document.getElementById('hs-totgrid').hidden && ED.hsiTot() && ED.hsiTot().req != null", what="the timing")
            got = page.evaluate("() => { const g = ED.hsiSolve(), t = ED.hsiTot(); return {t: t, lat: g.fix.lat, lon: g.fix.lon, R: g.R, gs: g.gs}; }")
            t, R = got["t"], got["R"]
            def arc(la1, lo1, la2, lo2):
                p1, p2, dl = math.radians(la1), math.radians(la2), math.radians(lo2 - lo1)
                return 2 * R * math.asin(math.sqrt(math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))
            to_ip = arc(got["lat"], got["lon"], -13.1, ws[0]["lon"]) + arc(-13.1, ws[0]["lon"], -13.1, ws[1]["lon"])
            leg = arc(-13.1, ws[1]["lon"], -13.1, ws[2]["lon"]) / (300 * 1852 / 3600)
            left = t["tot"] - t["now"] - leg
            self.assertEqual(t["to"], "IP")
            self.assertAlmostEqual(t["req"], to_ip / left, delta=to_ip / left * 0.02)
            self.assertAlmostEqual(t["late"], t["now"] + to_ip / got["gs"] + leg - t["tot"], delta=3)
            self.assertLess(t["late"], 0, "10 minutes out at 150 m/s over a few km: early")
            txt = page.inner_text("#hs-totgrid").upper()
            self.assertIn("REQ GS · TO IP", txt)
            self.assertIn("EARLY", txt)
            self.assertIn(z.strftime("%H:%M:%S") + " Z", txt)
            self.no_errors()

    def test_atk_plan(self):
        with Board("p_nav_atk", **journals.syst()) as b:
            page = self.open(b)
            w, = self.wpts(b, (-13.1, 34.9))
            b.ufc_cmd("press ILS", "press Opt2", "press 5")
            self.on(page, "nav", 6, what="Atk from the keypad")
            self.until(page, "() => !document.getElementById('ak-pv').hidden && /NO TARGET/i.test(document.getElementById('ak-pwait').textContent)",
                       what="PLAN, no target")
            b.post("/api/nav", {"op": "dsg", "key": w["key"]})
            self.until(page, "() => /WP1/.test(document.getElementById('ak-dname').textContent) && /NOT BUILT/i.test(document.getElementById('ak-pchip').textContent)",
                       what="the target, not built")
            self.assertGreater(page.evaluate(CANVAS_INK_JS, "ak-geo"), 5)
            # the UFC's sub-level: HDG 045, SPD 240, BLD twice
            b.ufc_cmd("press Ent")
            b.wait(lambda: b.display()["options"] == ["HDG", "SPD", "BASE", "ROLE", "BLD"] or None, what="the plan on the UFC")
            b.ufc_cmd("press Opt1", "press 0", "press 4", "press 5", "press Ent", pause=0.3)
            self.until(page, "() => ED.S.data.syst.nav.plan.hdg === 45", what="ATK HDG 045")
            b.ufc_cmd("press Opt2", "press 2", "press 4", "press 0", "press Ent", pause=0.3)
            self.until(page, "() => ED.S.data.syst.nav.plan.kts === 240", what="240 kts")
            b.ufc_cmd("press Opt5")
            b.wait(lambda: b.display()["scratch"] == "CONFIRM" or None, what="BLD armed")
            b.ufc_cmd("press Opt5")
            self.until(page, "() => ED.S.data.syst.nav.built && ED.S.data.syst.nav.built.hdg === 45 && ED.S.data.syst.nav.seq === 'atk'", what="built")
            self.until(page, "() => document.getElementById('ak-pchip').hidden && /FT1\\//.test(document.getElementById('ak-code').textContent)", what="the code")
            self.assertIn("WK51, IN SOUTH", page.inner_text("#ak-pts").upper())   # (from 045, the run in's from the south-west)
            b.ufc_cmd("press Clr")
            b.wait(lambda: b.display()["options"] == ["HOME", "NAV", "CTRS", "DSG", "MK"] or None, what="the page menu back")
            # COMM1: PLAN / ATTACK, ATK HDG, ROLE: a pull on ROLE flies #2 (the steer-to point follows)
            b.ufc_cmd("pulse COMM1_CW", "pulse COMM1_CW")
            self.until(page, "() => ED.atk.focus1 === 'role' && document.getElementById('ak-role').classList.contains('focus')", what="COMM1 on ROLE")
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, "() => ED.S.data.syst.nav.plan.role === 2 && ED.S.data.syst.nav.steer === 'atk:2:START'", what="#2")
            self.until(page, "() => /WK52/.test(document.getElementById('ak-pts').textContent)", what="#2's points")
            # the code: COPY puts it on the clipboard; LOAD (the box empty: the clipboard) builds it with you as #1
            code = page.evaluate("() => ED.S.data.syst.nav.built.code")
            self.assertIn("/WK52/", code)
            page.click("#ak-copy")
            b.wait(lambda: f"Copy button: {code} - copied" in b.log() or None, what="the code copied")
            page.click("#ak-load")
            self.until(page, "() => ED.S.data.syst.nav.plan.role === 1 && /LOADED/i.test(document.getElementById('ak-bnote').textContent)", what="loaded as #1")
            # ATTACK: the release cue against the target
            page.click('#ak-mode button[data-v="atk"]')
            self.until(page, "() => !document.getElementById('ak-atk').hidden && document.getElementById('ak-pv').hidden", what="ATTACK")
            self.no_errors()


class Remote(PageTest):
    """1 Syst's CURRENT SYSTEM / REMOTE from the UFC: COMM1's first stop is the switch, its pull the list; COMM1 through
    the list, a pull picks (the route's destination); MANUAL's name on the keypad (as a waypoint's NAME), its matches
    under it, COMM1 and a pull to pick one; the remote system's name amber here and in the strip; the Nav pages with
    it (Wpt: OVERFLY marks where you are - not there); CURRENT SYSTEM back."""

    def test_remote_from_the_ufc(self):
        j = journals.jump()
        j.pop("fuel")
        with Board("p_remote", **j) as b:
            page = self.open(b)
            b.ufc_cmd("press ILS", "press Opt2")
            self.on(page, "nav", 1, what="Syst")
            self.until(page, "() => document.querySelector('#sy-list .srow') !== null", what="the list")
            b.ufc_cmd(*["pulse COMM1_CCW"] * 40, pause=0.02)
            self.until(page, "() => document.getElementById('sy-rem').classList.contains('cur')", what="COMM1 on the switch")
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, "() => !document.getElementById('sy-rpop').hidden && ED.remote.state.items.length > 0", what="the list open")
            self.assertEqual(page.evaluate("() => Array.from(document.querySelectorAll('#sy-rpop .rpg')).map(e => e.textContent.toUpperCase())"),
                             ["ROUTE DESTINATION", "BEEN LATELY"])
            b.wait(lambda: (lambda d: d if (d["s1"], d["scratch"]) == ("RM", "MANUAL") else None)(b.display()), what="MANUAL on the scratchpad")
            # COMM1 down one: the route's destination; a pull picks it
            b.ufc_cmd("pulse COMM1_CW")
            self.until(page, "() => ED.remote.state.sel === 1", what="COMM1 on Carthage")
            b.wait(lambda: (lambda d: d if d["scratch"] == "CARTHAGE" else None)(b.display()), what="CARTHAGE on the scratchpad")
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, "() => ED.S.data.syst.system === 'Carthage' && ED.S.data.syst.status === 'ok' && document.getElementById('sy-rpop').hidden",
                       what="Carthage in 1 Syst")
            self.assertTrue(page.evaluate("() => /^REMOTE · CARTHAGE/.test(document.getElementById('sy-lab').textContent.toUpperCase()) && !!document.querySelector('#sy-lab .rmt')"))
            self.assertEqual(page.inner_text("#rmt").upper(), "REMOTE CARTHAGE")
            self.assertTrue(page.evaluate("() => document.querySelector('#sy-rem button[data-v=\"rem\"]').classList.contains('on')"))
            self.assertRegex(page.inner_text("#sy-rly").upper(), r"^\d+(\.\d)? LY AWAY$")
            # the Nav pages with it: Wpt's waypoints are Carthage's; OVERFLY marks where you are - not there
            b.ufc_cmd("press 3")
            self.on(page, "nav", 4, what="Wpt")
            self.until(page, "() => /REMOTE · CARTHAGE/i.test(document.getElementById('tg-sys').textContent)", what="Wpt on Carthage")
            page.click('#tg-meth button[data-m="overfly"]')
            self.until(page, "() => /REMOTE SYSTEM/i.test(document.getElementById('pg-tgt').textContent)", what="OVERFLY: not there")
            # MANUAL: the keypad spells CAL (2 steps the letter, 6 the cursor); the matches under it; COMM1 to one, a pull
            b.ufc_cmd("press 1")
            self.on(page, "nav", 1, what="Syst")
            page.click('#sy-rem button[data-v="rem"]')
            self.until(page, "() => !document.getElementById('sy-rpop').hidden && ED.remote.state.sel === 0", what="the list again")
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, "() => !!ED.remote.state.typing", what="typing the name")
            b.ufc_cmd(*[f"press {k}" for k in "222" + "6" + "2" + "6" + "2" * 12], pause=0.08)
            self.until(page, "() => ED.remote.state.typing.chars.join('') === 'CAL'", what="CAL")
            b.wait(lambda: (lambda d: d if (d["s1"], d["scratch"]) == ("SY", "CAL") else None)(b.display()), what="CAL on the scratchpad")
            self.until(page, "() => ED.remote.state.matches.length && ED.remote.state.matches[0].name === 'Calennero'", what="Calennero, matched")
            b.ufc_cmd("pulse COMM1_CW")
            self.until(page, "() => ED.remote.state.msel === 0", what="COMM1 on it")
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, "() => ED.S.data.remote.system === 'Calennero' && ED.S.data.syst.system === 'Calennero'", what="Calennero")
            # opened again: a new name, not the last
            page.click('#sy-rem button[data-v="rem"]')
            self.until(page, "() => !document.getElementById('sy-rpop').hidden && document.getElementById('sy-rq').value === '' && !ED.remote.state.typing",
                       what="the list, afresh")
            # the page reloaded with the list open: the keypad's the sub-tabs' again
            b.wait(lambda: b.display()["s1"] == "RM" or None, what="the list's claim")
            page.reload()
            page.wait_for_function("() => document.querySelector('.tab.on') !== null", timeout=10000)
            if page.evaluate("() => !document.getElementById('boot').hidden"):
                self.skip_intro(page)
            self.go(page, "nav", 1)
            self.on(page, "nav", 1, what="Syst after the reload")
            b.ufc_cmd("press 2")
            self.on(page, "nav", 3, what="the keypad's 2: Traj")
            b.ufc_cmd("press 1")
            self.on(page, "nav", 1, what="Syst")
            # CURRENT SYSTEM: where you are again
            page.click('#sy-rem button[data-v="cur"]')
            self.until(page, "() => !ED.S.data.remote.on && ED.S.data.syst.system === 'HIP 20277' && document.getElementById('rmt').hidden", what="the current system")
            self.no_errors()


class Boot(PageTest):
    def test_loading_in(self):
        with Board("p_boot", journal=journals.syst()["journal"], status={"Flags": 0}, edsm=(), no_edsm=True, ufc=False) as b:
            page = self.open(b)
            time.sleep(1.5)
            # the game starting again (a new journal) loses the signal; the load waits for Status.json
            b.add({"event": "Fileheader", "part": 1}, {"event": "LoadGame", "Commander": "Deckard", "Ship": "Krait_MkII", "GameMode": "Solo"})
            self.until(page, "() => document.getElementById('boot').classList.contains('wait')", timeout=8, what="the waiting screen")
            time.sleep(2)
            self.assertFalse(page.evaluate("() => document.getElementById('bt-text').classList.contains('bt-ship')"),
                             "the start-up must wait for the game")
            b.write_status({"Flags": DOCKED_FLAGS})
            self.until(page, "() => document.getElementById('bt-text').classList.contains('bt-ship')", timeout=6, what="the start-up")
            self.until(page, "() => document.getElementById('boot').hidden", timeout=20, what="the start-up to finish")
            self.no_errors()

    def test_preview_and_exit(self):
        with Board("p_boot2", journal=journals.syst()["journal"], edsm=(), no_edsm=True, ufc=False) as b:
            page = self.open(b, "/#boot-srv")
            self.until(page, "() => !document.getElementById('boot').hidden", timeout=6, what="the preview")
            self.until(page, "() => document.getElementById('bt-text').classList.contains('bt-srv')", timeout=8, what="the SRV boot screen")
            page.click("#boot")   # tap to skip
            self.until(page, "() => document.getElementById('boot').hidden", timeout=5, what="the skip")
            page.click("#quit")
            page.click("#quit")
            self.until(page, "() => !document.getElementById('halt').hidden", timeout=5, what="the stopped screen")
            self.assertEqual(page.evaluate("() => getComputedStyle(document.querySelector('.sweep')).display"), "none")
            b.wait(lambda: b.proc.poll() is not None, timeout=8, what="the board to stop")
            self.no_errors()


class UfcAndPage(PageTest):
    """The page and the UFC keeping track of each other."""

    def test_follow_and_cursors(self):
        j = journals.contracts()
        with Board("p_ufc", journal=j["journal"], status=j["status"], ocor=True,
                   coords=journals.ocor()["coords"]) as b:
            page = self.open(b)
            other = self.browser.new_page(viewport={"width": 1280, "height": 800})   # a second screen (a phone, say)
            other.goto(b.url + "/")
            other.wait_for_function("() => document.querySelector('.tab.on') !== null", timeout=10000)
            self.skip_intro(other)
            b.ufc_cmd("press ILS")
            # tabs picked on the page move the UFC's ':' marker
            for tab, key, cue in (("home", None, 1), ("contracts", 3, 3), ("nav", 1, 2), ("contracts", 1, 3)):
                self.go(page, tab, key)
                b.wait(lambda: b.display()["cue"] == cue or None, what=f"the UFC marker for {tab}")
            # tabs picked on the UFC move every page
            b.ufc_cmd("press Opt3", "press 3")
            for pg in (page, other):
                self.on(pg, "contracts", 3, what="both pages on OCOR")
            # OCOR: the knob skips struck-out objectives; a pull selects
            self.until(page, "() => document.querySelector('#ob-list .item.cur') !== null", what="the OCOR highlight")
            first = page.eval_on_selector("#ob-list .item.cur", "e => e.dataset.oid")
            b.ufc_cmd("pulse COMM1_CW")
            self.until(page, f"() => document.querySelector('#ob-list .item.cur').dataset.oid !== {json.dumps(first)}", what="the highlight to move")
            nxt = page.eval_on_selector("#ob-list .item.cur", "e => e.dataset.oid")
            self.assertFalse(page.eval_on_selector(f'#ob-list .item[data-oid="{nxt}"]', "e => e.classList.contains('done')"))
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, f"() => document.querySelector('#ob-list .item.sel').dataset.oid === {json.dumps(nxt)}", what="the pull")
            # System list: the highlight, a pull picks (Manual), COMM2 pull flips AUTO / MANUAL back
            b.ufc_cmd("press Opt2")
            self.until(page, "() => document.querySelector('#sy-list .srow.cur') !== null", what="the System highlight")
            b.ufc_cmd("pulse COMM1_CW", "pulse COMM1_CW")
            cur = page.eval_on_selector("#sy-list .srow.cur", "e => e.dataset.key")
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, f"() => document.querySelector('#sy-list .srow.sel').dataset.key === {json.dumps(cur)}", what="the System pick")
            self.until(page, "() => document.getElementById('sy-man').classList.contains('on')", what="Manual")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => document.getElementById('sy-auto').classList.contains('on')", what="the COMM2 pull back to Auto")
            # the map's highlight follows the map's own order
            b.ufc_cmd("press 1")
            self.until(page, "() => document.getElementById('app').classList.contains('symap')", what="the map")
            b.wait(lambda: b.bus()["cursors"]["syst"] in b.state()["syst"]["map"]["order"] or None, what="the cursor on the map's order")
            # the Contracts panel scrolls with COMM2 (small screen, so there's something to scroll)
            b.ufc_cmd("press Opt3", "press 1")
            self.on(other, "contracts", 1, what="Contracts on the second screen")
            other.click('#list .item[data-key="black sun crew"]')
            time.sleep(0.5)
            top = other.evaluate("() => document.getElementById('pc').scrollTop")
            b.ufc_cmd("pulse COMM2_CW", "pulse COMM2_CW", "pulse COMM2_CW")
            time.sleep(0.6)
            room = other.evaluate("() => { const p = document.getElementById('pc'); return p.scrollHeight - p.clientHeight; }")
            if room > 4:
                self.assertGreater(other.evaluate("() => document.getElementById('pc').scrollTop"), top)
            self.no_errors()

    def test_script_restarted(self):
        """Close the script and run it again with the page left open: the page carries on with the new run."""
        j = journals.contracts()
        with Board("p_restart", journal=j["journal"], status=j["status"], ocor=True, coords=journals.ocor()["coords"]) as b:
            page = self.open(b)
            b.ufc_cmd("press ILS", "press Opt3", "press Opt2", "press Opt2", "press Opt1", "pulse COMM2_CW", "pulse COMM2_CW")   # run the counts up
            self.until(page, "() => document.querySelector('.tab.on').dataset.tab === 'home'", what="Home")
            self.go(page, "contracts", 1)
            b.wait(lambda: b.display()["cue"] == 3 or None, what="the UFC marker on Contracts")
            run = page.evaluate("() => ED.S.ufc.run")
            b.restart()
            self.until(page, f"() => ED.S.ufc && ED.S.ufc.run !== {json.dumps(run)}", timeout=15, what="the page to reach the new run")
            b.ufc_cmd("press ILS")
            b.wait(lambda: b.display()["cue"] == 3 or None, what="the new run to know the page is on Contracts")
            b.ufc_cmd("press Opt3")   # the very first press after the restart counts (Contracts again: its next sub-tab)
            self.until(page, "() => ED.view.tab === 'contracts' && ED.view.sub === 2", timeout=6, what="the first press after the restart")
            self.errors = [e for e in self.errors if "net::ERR_" not in e]   # the page couldn't reach the script while it was stopped
            self.no_errors()

    def test_lock_and_log(self):
        j = journals.contracts()
        with Board("p_lock", journal=j["journal"], status=j["status"]) as b:
            page = self.open(b)
            page.click('.tab[data-tab="home"]')
            time.sleep(1.0)
            n = page.evaluate("() => document.querySelectorAll('#lg-lines .ll').length")
            b.add({"event": "Bounty", "Target": "python", "Target_Localised": "Python", "TotalReward": 123456,
                   "VictimFaction": "Black Sun Crew", "PilotName_Localised": "Bo Rix"})
            self.until(page, f"() => document.querySelectorAll('#lg-lines .ll').length === {n + 1}", what="the new log line")
            self.until(page, "() => /123,456/.test(document.getElementById('lg-lines').lastElementChild.innerText)", what="its text")
            # a fresh lock on a target's ship jumps to Contracts and selects it
            b.add({"event": "ShipTargeted", "TargetLocked": True, "Ship": "python", "ScanStage": 3,
                   "PilotName": "$npc_name_decorate:#name=Kirsten Vance;", "PilotName_Localised": "Kirsten Vance", "PilotRank": "Deadly",
                   "ShieldHealth": 30.0, "HullHealth": 70.0, "LegalStatus": "Wanted", "Bounty": 950000})
            self.until(page, "() => ED.view.tab === 'contracts' && ED.view.sub === 1", what="the jump to Contracts")
            self.until(page, "() => document.querySelector('#list .item.sel').dataset.key === 'kirsten vance'", what="the target selected")
            self.until(page, "() => document.getElementById('panel').classList.contains('lock')", what="the lock frame")
            self.until(page, "() => /30%/.test(document.getElementById('p-sh').textContent)", what="the new shield reading")
            self.no_errors()


WATCH_JS = r"""() => {   // every class #boot and #bt-text have had, from now on
  window.__seen = new Set();
  const note = () => { ['boot', 'bt-text'].forEach(id => document.getElementById(id).classList.forEach(c => window.__seen.add(id + '.' + c))); };
  note();
  new MutationObserver(note).observe(document.getElementById('boot'), { attributes: true, subtree: true, attributeFilter: ['class'] });
}"""


class Terminal(PageTest):
    """The UCEC FT3000's own screens: powering on, its boot screen, waiting for the game, losing it."""

    def seen(self, page):
        return set(page.evaluate("() => Array.from(window.__seen)"))

    def sweeping(self, page):   # the band down the screen: only with the board connected
        return page.evaluate("() => getComputedStyle(document.querySelector('.sweep')).display !== 'none'")

    def test_waits_for_the_game_then_the_ship(self):
        j = journals.syst()
        journal = j["journal"] + [{"timestamp": ago(30), "event": "Music", "MusicTrack": "MainMenu"}]
        with Board("p_term_wait", journal=journal, status={"Flags": 0}, edsm=(), no_edsm=True, ufc=False) as b:
            self.assertFalse(b.state()["game"]["in"])
            page = self.open(b, intro=True)
            time.sleep(1.0)
            self.assertEqual(page.evaluate("() => document.getElementById('boot').className"), "power")   # black for 2 s
            self.assertFalse(self.sweeping(page))
            self.until(page, "() => /UCEC FT3000 FIELD TERMINAL/i.test(document.getElementById('bt-text').innerText)", timeout=9,
                       what="the UCEC boot screen")
            self.assertTrue(page.evaluate("() => !!document.querySelector('.ucec-logo canvas')"))
            self.until(page, "() => document.getElementById('boot').classList.contains('wait')", timeout=16, what="the waiting screen")
            self.assertEqual(page.inner_text("#bt-osd").upper().replace("_", "").split(), "UCEC FT3000 WAITING FOR INPUT SIGNAL".split())
            time.sleep(2.5)   # it stays while you're at the main menu
            self.assertTrue(page.evaluate("() => document.getElementById('boot').classList.contains('wait')"))
            self.assertFalse(self.sweeping(page))
            b.add({"event": "LoadGame", "Commander": "Deckard", "Ship": "Krait_MkII", "ShipName": "Night Owl", "ShipIdent": "BR-49K", "GameMode": "Solo"})
            time.sleep(2.5)
            self.assertTrue(page.evaluate("() => document.getElementById('boot').classList.contains('wait')"), "still loading: no signal yet")
            b.write_status({"Flags": DOCKED_FLAGS})
            self.until(page, "() => document.getElementById('bt-text').classList.contains('bt-ship')", timeout=6, what="the ship's start-up")
            self.assertFalse(self.sweeping(page))
            self.until(page, "() => document.getElementById('boot').hidden", timeout=10, what="the board")
            self.assertTrue(self.sweeping(page), "connected: the sweep runs")
            self.no_errors()

    def test_in_game_goes_straight_to_the_ship(self):
        j = journals.syst()
        with Board("p_term_in", journal=j["journal"], status=j["status"], edsm=(), no_edsm=True, ufc=False) as b:
            page = self.open(b, intro=True, viewport=(390, 844))   # an upright phone, for the layout
            page.evaluate(WATCH_JS)
            self.until(page, "() => document.getElementById('bt-text').classList.contains('bt-ucec')", timeout=9, what="the UCEC boot screen")
            self.until(page, "() => document.getElementById('bt-text').classList.contains('bt-ship')", timeout=16, what="the ship's start-up")
            self.until(page, "() => document.getElementById('boot').hidden", timeout=10, what="the board")
            self.assertNotIn("boot.wait", self.seen(page), "in the game already: no waiting screen")
            self.no_errors()

    def test_losing_the_game_then_skipping(self):
        j = journals.syst()
        with Board("p_term_lost", journal=j["journal"], status=j["status"], edsm=(), no_edsm=True, ufc=False) as b:
            page = self.open(b)
            b.add({"event": "Music", "MusicTrack": "MainMenu"})
            self.until(page, "() => !document.getElementById('boot').hidden", timeout=6, what="the picture breaking up")
            self.until(page, "() => document.getElementById('boot').classList.contains('wait')", timeout=8, what="the waiting screen")
            self.assertFalse(self.sweeping(page))
            self.skip_intro(page)   # a tap: straight to the board
            self.assertEqual(self.fp(page)["tab"], "home")
            b.add({"event": "LoadGame", "Commander": "Deckard", "Ship": "Krait_MkII", "GameMode": "Solo"})
            time.sleep(1.2)
            b.write_status({"Flags": DOCKED_FLAGS})   # skipped, so loading in plays the usual start-up
            self.until(page, "() => !document.getElementById('boot').hidden", timeout=6, what="the start-up")
            self.until(page, "() => document.getElementById('bt-text').classList.contains('bt-ship')", timeout=8, what="the ship's boot screen")
            self.no_errors()

    def test_nosignal_preview(self):
        j = journals.syst()
        with Board("p_term_prev", journal=j["journal"], status=j["status"], edsm=(), no_edsm=True, ufc=False) as b:
            page = self.open(b, "/#nosignal")
            self.until(page, "() => document.getElementById('boot').classList.contains('wait')", timeout=8, what="the waiting screen")
            time.sleep(2.5)   # a preview: it stays though you're in the game
            self.assertTrue(page.evaluate("() => document.getElementById('boot').classList.contains('wait')"))
            self.skip_intro(page)
            self.no_errors()

    def test_ufc_follows_the_page(self):
        """The UFC acts as if the page drives it: blank with no page or while the terminal is off; every digit
        8 through its BIOS and waiting screen; the version and test patterns through a vehicle's start-up; then
        the menu; 8s again back at the game's main menu; blank once the page closes."""
        j = journals.syst()
        journal = j["journal"] + [{"timestamp": ago(30), "event": "Music", "MusicTrack": "MainMenu"}]
        blank = {"options": [""] * 5, "com1": "", "com2": "", "cue": None, "scratch": "", "s1": "", "s2": ""}
        with Board("p_term_ufc", journal=journal, status={"Flags": 0}, edsm=(), no_edsm=True, stub_page=False) as b:
            version = b.state()["version"]
            self.assertRegex(version, r"^\d+\.\d\d\.\d\d$")
            b.wait(lambda: b.display() == blank or None, timeout=5, what="no page: the displays blank")
            page = self.open(b, intro=True)
            time.sleep(1.0)
            self.assertEqual(page.evaluate("() => document.getElementById('boot').className"), "power")
            self.assertEqual(b.display(), blank, "the terminal still off")
            self.until(page, "() => document.getElementById('bt-text').classList.contains('bt-ucec')", timeout=9, what="the UCEC boot screen")
            self.assertIn(version, page.inner_text("#bt-text"))   # on the BIOS screen
            d = b.wait(lambda: b.display() if b.display()["scratch"] == "88888888" else None, timeout=3, what="every digit lit")
            self.assertEqual((d["options"], d["com1"], d["com2"], d["s1"], d["s2"]), (["8888"] * 5, "88", "88", "88", "88"))
            self.until(page, "() => document.getElementById('boot').classList.contains('wait')", timeout=16, what="the waiting screen")
            time.sleep(1.0)
            self.assertEqual(b.display()["scratch"], "88888888", "8s through the waiting screen")
            b.add({"event": "LoadGame", "Commander": "Deckard", "Ship": "Krait_MkII", "ShipName": "Night Owl", "ShipIdent": "BR-49K", "GameMode": "Solo"})
            time.sleep(1.2)
            b.write_status({"Flags": DOCKED_FLAGS})
            self.until(page, "() => document.getElementById('bt-text').classList.contains('bt-ship')", timeout=8, what="the ship's start-up")
            b.wait(lambda: b.display()["scratch"] == version or None, timeout=3, what="the version in the scratchpad")
            seen = set()
            for _ in range(6):   # the other displays run test patterns
                seen.add(tuple(b.display()["options"]))
                time.sleep(0.15)
            self.assertGreater(len(seen), 2)
            self.until(page, "() => document.getElementById('boot').hidden", timeout=10, what="the board")
            menu = b.wait(lambda: b.display() if b.display()["options"][0] not in ("", "8888") and b.display()["scratch"] != version else None,
                          timeout=3, what="the menu")
            b.add({"event": "Music", "MusicTrack": "MainMenu"})   # back at the game's main menu
            self.until(page, "() => document.getElementById('boot').classList.contains('wait')", timeout=10, what="the waiting screen")
            b.wait(lambda: b.display()["scratch"] == "88888888" or None, timeout=3, what="8s at the main menu")
            page.close()
            t0 = time.time()
            b.wait(lambda: b.display() == blank or None, timeout=6, what="the page closed: blank")
            self.assertLess(time.time() - t0, 4.5)

    def test_ufc_on_foot_and_two_pages(self):
        """On foot: the menu stays (no self-test). A second page doesn't take the displays over until the
        first one closes. Unknown screens are refused."""
        j = journals.syst()
        with Board("p_term_ufc2", journal=j["journal"], status=j["status"], edsm=(), no_edsm=True, stub_page=False) as b:
            first = self.open(b)
            menu = b.wait(lambda: b.display() if b.display()["options"][0] else None, timeout=5, what="the menu")
            b.add({"event": "Disembark", "SRV": False, "Taxi": False, "Multicrew": False, "OnStation": True})   # on foot
            self.until(first, "() => !document.getElementById('boot').hidden", timeout=6, what="the disconnect")
            while first.evaluate("() => !document.getElementById('boot').hidden"):
                self.assertEqual(b.display()["options"], menu["options"], "on foot: the menu throughout")
                time.sleep(0.2)
            b.add({"event": "Embark", "SRV": False, "Taxi": False, "Multicrew": False, "OnStation": True})   # back in the ship
            b.wait(lambda: b.display()["scratch"] == b.state()["version"] or None, timeout=8, what="the ship's self-test")
            b.wait(lambda: b.display()["options"] == menu["options"] or None, timeout=10, what="the menu back")
            second = self.browser.new_page(viewport={"width": 1280, "height": 800})   # a second screen, starting up
            second.goto(b.url + "/")
            for _ in range(15):   # its BIOS doesn't take the displays from the first page
                self.assertEqual(b.display()["options"], menu["options"])
                time.sleep(0.2)
            first.close()   # now they follow the second page (on its BIOS, or the board by now)
            b.wait(lambda: b.display()["options"] != menu["options"] or None, timeout=5, what="the second page's screens")
            second.click("#boot")   # skip to the board
            b.wait(lambda: b.display()["options"] == menu["options"] or None, timeout=5, what="the menu, from the second page")
            self.assertEqual(b.post("/api/bootfx", {"fx": "suit", "page": "x"})[0], 400)   # on foot (or anything else): refused
            second.close()

    def test_tube_switches_off_only_leaving_the_game(self):
        """Changing vehicle loses the signal (static); only leaving the game switches the tube off (down to a dot)."""
        j = journals.syst()
        with Board("p_term_tube", journal=j["journal"], status=j["status"], edsm=(), no_edsm=True, ufc=False) as b:
            page = self.open(b)
            watch = """(h) => { window.__tr = []; const cv = document.getElementById('bt-noise'), t0 = performance.now();
                (function f() { window.__tr.push(cv.style.transform); if (performance.now() - t0 < 2800) requestAnimationFrame(f); })();
                location.hash = h; }"""
            page.evaluate(watch, "exit-ship")   # leaving the ship
            time.sleep(3.2)
            self.assertFalse(any("scale" in t for t in page.evaluate("window.__tr")), "changing vehicle shouldn't switch the tube off")
            self.skip_intro(page)
            page.evaluate(watch, "nosignal")    # back to the main menu
            time.sleep(3.2)
            self.assertTrue(any("scale" in t for t in page.evaluate("window.__tr")), "leaving the game switches the tube off")
            self.no_errors()

class Schematics(PageTest):
    """4 Syst: Maximise / Minimise, and an Odyssey settlement's schematic: zoom in, pick a layout, confirm it."""

    def pick(self, page, name):
        key = page.evaluate(f"() => ED.S.data.syst.entries.find(e => e.name === {json.dumps(name)}).key")
        page.click(f'#sy-list .srow[data-key="{key}"]')
        self.until(page, f"() => document.getElementById('sy-name').textContent === {json.dumps(name)}", what=name)

    def js(self, page, expr):
        return page.evaluate("() => " + expr)

    def test_schematic_view(self):
        j = journals.syst()
        with Board("p_schem", journal=j["journal"], status=j["status"]) as b:
            page = self.open(b)
            self.go(page, "nav", 1)
            # only Odyssey settlements (and planetary construction sites); an orbital station doesn't maximise or zoom
            self.pick(page, "Fabian City")
            self.assertTrue(self.js(page, "document.getElementById('sy-sch').disabled"))
            self.assertTrue(self.js(page, "document.getElementById('sy-max').hidden"))
            # an economy with no layouts yet starts on a type that has some (the Type toggle changes it)
            self.pick(page, "Hao Extraction Prospect")
            self.assertFalse(self.js(page, "document.getElementById('sy-sch').disabled"))
            self.assertEqual(page.inner_text("#sy-snote").upper(), "TYPE: TOURISM (NO EXTRACTION LAYOUTS YET)")
            self.pick(page, "Dhaenens's Lodgings")
            self.assertFalse(self.js(page, "document.getElementById('sy-sch').disabled"))
            # Maximise: the picture takes the details' place
            page.click("#sy-max")
            self.assertTrue(self.js(page, "document.getElementById('sy-pc').classList.contains('max')"))
            self.assertEqual(self.js(page, "getComputedStyle(document.getElementById('sy-grid')).display"), "none")
            self.assertEqual(page.inner_text("#sy-max").upper(), "MINIMISE")
            # Schematic view: a zoom onto the settlement, then the first layout to pick from
            page.click("#sy-sch")
            self.until(page, "() => !!document.querySelector('#sy-svg g[transform]')", timeout=2, what="the zoom")
            self.until(page, "() => !document.getElementById('sy-pick').hidden", timeout=4, what="the layout picker")
            self.assertEqual(page.inner_text("#sy-sch").upper(), "PLANETARY VIEW")
            self.assertIsNone(self.js(page, "document.getElementById('sy-cap')"), "no layout description")
            # nothing in the panel is smaller than the MARKET chip (the buttons, caption and heading line included)
            sizes = page.evaluate("""() => { const chip = parseFloat(getComputedStyle(document.querySelector('#sy-chips .chip')).fontSize);
                let min = 1e9, what = '';
                document.querySelectorAll('#sy-pc *').forEach(el => {
                  if (!el.offsetParent || ![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) return;
                  const f = parseFloat(getComputedStyle(el).fontSize); if (f < min) { min = f; what = el.id || el.className; } });
                return [chip, min, what]; }""")
            self.assertGreaterEqual(sizes[1], sizes[0], f"{sizes[2]} is smaller than the MARKET chip")
            self.assertEqual(page.inner_text("#sy-pname").upper(), "FUFLUNS")
            self.assertEqual(page.inner_text("#sy-pnum").upper(), "1 OF 4")
            page.click("#sy-prev")
            self.assertEqual(page.inner_text("#sy-pnum").upper(), "4 OF 4")
            page.click("#sy-next"); page.click("#sy-next")
            self.assertEqual(page.inner_text("#sy-pname").upper(), "AERGIA")
            self.assertTrue(self.js(page, "!!document.querySelector('#sy-svg path[opacity]')"),
                            "Aergia's HABs are cut off by the map's legend: those edges are drawn faint")
            # icons: off to start with, then on by type
            labels = self.js(page, "document.querySelectorAll('#sy-svg text').length")   # the buildings' names
            page.click('#sy-icons button[data-ic="term"]')
            self.assertGreater(self.js(page, "document.querySelectorAll('#sy-svg text').length"), labels)
            # the mouse wheel zooms where the pointer is, a double-click shows the whole settlement again
            box = page.locator("#sy-svg").bounding_box()
            page.mouse.move(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.5)
            page.mouse.wheel(0, -400)
            self.until(page, "() => ED.S.sc.zoom > 1.5 && ED.S.sc.pan[0] !== 0", what="the wheel to zoom where the pointer is")
            page.dblclick("#sy-svg")
            self.until(page, "() => ED.S.sc.zoom === 1", what="a double-click for the whole settlement")
            # the dials: BRT tilts it, COMM2 VOLUME turns it
            b.ufc_cmd("press ILS", "dial 5 2500", "dial 7 2500")
            self.until(page, "() => !/Tilt 0\u00b0/.test(document.getElementById('sy-rotlab').textContent)", what="the BRT dial to tilt it")
            self.until(page, "() => !/Heading 000/.test(document.getElementById('sy-rotlab').textContent)", what="the VOLUME dial to turn it")
            # confirm it: kept by the board, and the picker steps aside
            page.click("#sy-ok")
            b.wait(lambda: b.state()["syst"]["layouts"] == {"m:3814631936": "tourist-2"} or None, what="the layout to be saved")
            self.until(page, "() => document.getElementById('sy-pnum').textContent === 'Set'", what="Set")
            self.assertEqual(page.inner_text("#sy-ok").upper(), "SET LAYOUT")
            # maximised: MINIMISE, PLANETARY VIEW, AERGIA SET, SET LAYOUT and ALIGN LAYOUT along one line (even the longest name)
            for nm in ("Aergia", "Picumnus"):
                page.evaluate(f"() => {{ document.getElementById('sy-pname').textContent = '{nm}'; }}")
                mids = self.js(page, "['sy-max', 'sy-sch', 'sy-pname', 'sy-ok', 'sy-align'].map(i => { const r = document.getElementById(i).getBoundingClientRect(); return r.top + r.height / 2; })")
                self.assertLess(max(mids) - min(mids), 4, f"one line with {nm}: {mids}")
            page.evaluate("() => { document.getElementById('sy-pname').textContent = 'Aergia'; }")
            # anything else selected: small again, and the planet
            self.pick(page, "Fabian City")
            self.assertFalse(self.js(page, "document.getElementById('sy-pc').classList.contains('max')"))
            self.assertTrue(self.js(page, "document.getElementById('sy-pick').hidden"))
            # back to the settlement: its schematic opens on the confirmed layout
            self.pick(page, "Dhaenens's Lodgings")
            page.click("#sy-sch")
            self.until(page, "() => !document.getElementById('sy-pick').hidden", timeout=4, what="the schematic")
            self.assertEqual((page.inner_text("#sy-pname").upper(), page.inner_text("#sy-pnum").upper()), ("AERGIA", "SET"))
            # Planetary view: the zoom back out
            page.click("#sy-sch")
            self.until(page, "() => document.getElementById('sy-pick').hidden && !document.querySelector('#sy-svg g[transform]')",
                       timeout=4, what="the planet")
            self.assertEqual(page.inner_text("#sy-sch").upper(), "SCHEMATIC VIEW")
            self.no_errors()

    def test_icon_toggles(self):
        """Maximised, a plan fitted to SrvSurvey shows its pads' sizes and numbers, and each icon toggle adds its
        icons: expendables and combat-zone points (in rings) as well as terminals, doors and power/alarm."""
        j = journals.syst()
        with Board("p_icons", journal=j["journal"], status=j["status"], ufc=False) as b:
            page = self.open(b)
            self.go(page, "nav", 1)
            self.pick(page, "Dhaenens's Lodgings")
            page.click("#sy-max")
            page.click("#sy-sch")
            self.until(page, "() => !document.getElementById('sy-pick').hidden", timeout=4, what="the schematic")
            self.assertEqual(page.inner_text("#sy-pname").upper(), "FUFLUNS")
            texts = "[...document.querySelectorAll('#sy-svg text')].map(t => t.textContent)"
            self.assertTrue({"S1", "S2", "L3", "L4"} <= set(self.js(page, texts)), "the pads' sizes and numbers")
            icons = "document.querySelectorAll('#sy-svg text[data-icon]').length"
            n = self.js(page, icons)
            self.assertEqual(n, 0, "no icons until a toggle is on")
            for ic in ("exp", "cz", "term", "door", "power"):
                page.click(f'#sy-icons button[data-ic="{ic}"]')
                self.assertEqual(self.js(page, f"document.querySelector('#sy-icons button[data-ic=\"{ic}\"]').getAttribute('aria-pressed')"), "true")
                m = self.js(page, icons)
                self.assertGreater(m, n, f"the {ic} toggle adds icons")
                n = m
            self.assertIsNone(self.js(page, "document.querySelector('#sy-icons button[data-ic=\"loot\"]')"), "no Loot toggle")
            self.assertGreater(self.js(page, "document.querySelectorAll('#sy-svg text[data-icon=\"ring\"]').length"), 0,
                               "combat-zone points in rings")
            self.assertIn("+", self.js(page, texts), "a medkit")
            self.no_errors()

    def test_align_settlement(self):
        """Align Settlement (a confirmed layout): the picture maximises with Cancel and Confirm heading over it; the
        way you face stays up the picture as you turn (from Status.json), its tilt follows your height and distance,
        you turn it to match; Confirm heading keeps it (the label then gives the compass bearing of the top of the
        picture) and you appear on it; Cancel puts it back. The UFC steps between the picture and the two buttons."""
        j = journals.syst()
        near = {"Flags": 16777216 | (1 << 21) | 8, "Flags2": 0, "BodyName": "HIP 20277 3 a", "Latitude": 58.7750, "Longitude": 51.4311,
                "Altitude": 200, "Heading": 90, "PlanetRadius": 2400000.0}   # ~240 m north of Dhaenens's Lodgings, 200 m up, facing east
        with Board("p_align", journal=j["journal"], status=near) as b:
            key = "m:3814631936"
            self.assertEqual(b.post("/api/settlement-layout", {"key": key, "layout": "tourist-2", "name": "Dhaenens's Lodgings"})[0], 200)
            page = self.open(b)
            self.go(page, "nav", 1)
            self.pick(page, "Dhaenens's Lodgings")
            page.click("#sy-sch")
            self.until(page, "() => !document.getElementById('sy-pick').hidden", timeout=4, what="the schematic")
            self.assertEqual(page.inner_text("#sy-pnum").upper(), "SET")
            self.assertEqual(page.inner_text("#sy-align").upper(), "ALIGN LAYOUT")
            self.assertFalse(self.js(page, "document.getElementById('sy-align').hidden"))
            self.assertIn("HEADING 000", page.inner_text("#sy-rotlab").upper())   # its heading isn't known yet
            self.assertEqual(self.js(page, "document.querySelectorAll('#sy-svg polygon').length"), 0, "nor where you are on it")
            page.click("#sy-align")
            # the mode: maximised, framed, its two buttons over the picture and the others gone
            self.until(page, "() => !document.getElementById('sy-alignbar').hidden", what="the Align Settlement overlay")
            self.assertTrue(self.js(page, "document.getElementById('sy-pc').classList.contains('max')"))
            self.assertTrue(self.js(page, "document.getElementById('sy-win').classList.contains('align')"))
            self.assertEqual(self.js(page, "['sy-pick', 'sy-icons', 'sy-max', 'sy-sch'].map(id => document.getElementById(id).hidden)"), [True] * 4)
            self.assertEqual((page.inner_text("#sy-alcancel").upper(), page.inner_text("#sy-alok").upper()), ("CANCEL", "CONFIRM HEADING"))
            bar, win = page.locator("#sy-alignbar").bounding_box(), page.locator("#sy-win").bounding_box()
            self.assertTrue(win["y"] <= bar["y"] and bar["y"] + bar["height"] <= win["y"] + win["height"], "the buttons sit over the picture")
            self.assertFalse(self.js(page, "document.getElementById('sy-alok').disabled"))
            self.assertAlmostEqual(self.js(page, "ED.S.sc.tilt"), 50.1, delta=1.5)   # atan(240 m / 200 m): as you see it
            self.assertIn("FACES 090", page.inner_text("#sy-alnote").upper())   # (the picture as it was, your heading up)
            # turn it to match: dragging across turns it, and the heading it would keep with it
            box = page.locator("#sy-svg").bounding_box()
            page.mouse.move(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.6)
            page.mouse.down()
            page.mouse.move(box["x"] + box["width"] * 0.3 + 50, box["y"] + box["height"] * 0.6, steps=5)
            page.mouse.up()
            rot, h = self.js(page, "[ED.S.sc.rot, ED.S.sc.align.h]")
            self.assertAlmostEqual(rot, 30, delta=0.5)
            self.assertAlmostEqual(h, 120, delta=0.5)
            self.assertIn("FACES 120", page.inner_text("#sy-alnote").upper())
            # you turn (Status.json): the settlement stays put on the ground, turning the other way in the picture
            b.write_status(dict(near, Heading=180))
            self.until(page, "() => Math.abs(ED.S.sc.rot - 300) < 0.6", what="the picture to turn as you do")
            self.assertAlmostEqual(self.js(page, "ED.S.sc.align.h"), 120, delta=0.5)
            # the UFC: the picture and the two buttons only; a pull on Cancel puts the picture back
            b.ufc_cmd("press ILS", "pulse COMM2_CCW")
            self.until(page, "() => document.getElementById('sy-alcancel').classList.contains('focus')", what="Cancel highlighted")
            b.ufc_cmd("pulse COMM2_CCW", "pulse COMM2_CCW")   # (the picture is the first stop)
            self.until(page, "() => document.getElementById('sy-pic').classList.contains('focus')", what="the picture highlighted")
            b.ufc_cmd("pulse COMM2_CW", "press COMM2_PULL")
            self.until(page, "() => document.getElementById('sy-alignbar').hidden", what="the pull to cancel")
            self.assertEqual(self.js(page, "[ED.S.sc.rot, ED.S.sc.tilt]"), [0, 0])
            self.assertFalse(self.js(page, "document.getElementById('sy-pc').classList.contains('max')"), "small again, as it was")
            self.assertEqual(b.state()["syst"]["headings"], {})
            # again, and Confirm heading: kept by the board (by hand, no docking before it: not locked)
            page.click("#sy-align")
            self.until(page, "() => !document.getElementById('sy-alignbar').hidden", what="the overlay again")
            self.assertAlmostEqual(self.js(page, "ED.S.sc.align.h"), 180, delta=0.5)   # your heading up, nothing kept yet
            page.evaluate("() => { ED.S.sc.rot = 60; }")
            page.mouse.move(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.6)
            page.mouse.down(); page.mouse.move(box["x"] + box["width"] * 0.3 + 10, box["y"] + box["height"] * 0.6, steps=2); page.mouse.up()   # +6°
            page.click("#sy-alok")
            got = b.wait(lambda: b.state()["syst"]["headings"].get(key), what="the heading to be saved")
            self.assertEqual((got["layout"], got["src"], got["locked"]), ("tourist-2", "manual", False))
            self.assertAlmostEqual(got["h"], 246, delta=0.6)   # 60 + 6 + 180
            self.until(page, "() => document.getElementById('sy-alignbar').hidden", what="the overlay to go")
            lab = page.inner_text("#sy-rotlab").upper()
            self.assertIn("UP 180", lab)   # the top of the picture: the way you face
            self.assertIn("ALIGNED", lab)
            self.assertRegex(lab, r"YOU 2\d\d M")
            self.assertGreater(self.js(page, "document.querySelectorAll('#sy-svg polygon').length"), 0, "you, on it")
            # opened again from the planet: the way you face up
            page.click("#sy-sch")
            self.until(page, "() => document.getElementById('sy-pick').hidden && !document.querySelector('#sy-svg g[transform]')", timeout=4, what="the planet")
            page.click("#sy-sch")
            self.until(page, "() => !document.getElementById('sy-pick').hidden", timeout=4, what="the schematic again")
            self.assertAlmostEqual(self.js(page, "ED.S.sc.rot"), 66, delta=0.6)   # 246 - 180
            self.no_errors()

    def test_settlement_of_no_known_type(self):
        """A surface station only your journal knows (approached, not docked: no type): Schematic view looks as it
        does for a starport - greyed, no note, no UFC highlight - but a click or a COMM2 pull still opens its
        schematics; once a layout is confirmed for it, it's an ordinary button."""
        j = journals.syst()
        j["journal"].append({"timestamp": ago(300), "event": "ApproachSettlement", "SystemAddress": 102, "Name": "Quill Rest House",
                             "MarketID": 4308000001, "BodyName": "HIP 20277 3 a", "BodyID": 11, "Latitude": 12.5, "Longitude": 40.25,
                             "StationFaction": {"Name": "HIP 20277 Party"}, "StationEconomy_Localised": "Tourism"})
        with Board("p_unsure", journal=j["journal"], status=j["status"]) as b:
            page = self.open(b)
            self.go(page, "nav", 1)
            look = """(() => { const b = document.getElementById('sy-sch'), c = getComputedStyle(b);
                return [c.color, c.borderColor, c.backgroundColor, c.cursor, b.title, b.textContent,
                        document.getElementById('sy-snote').textContent]; })()"""
            self.pick(page, "Fabian City")
            port = self.js(page, look)
            self.pick(page, "Quill Rest House")
            self.assertEqual(self.js(page, look), port, "Schematic view looks as it does for a starport")
            self.assertFalse(self.js(page, "document.getElementById('sy-sch').disabled"))
            # the UFC stops on it, unhighlighted, and a pull opens the schematic
            b.ufc_cmd("press ILS")
            for _ in range(4):
                if self.js(page, "ED.S.syFocus") == "sch":
                    break
                b.ufc_cmd("pulse COMM2_CW")
            self.until(page, "() => ED.S.syFocus === 'sch'", what="the knob to stop on Schematic view")
            self.assertEqual(self.js(page, "getComputedStyle(document.getElementById('sy-sch')).boxShadow"), "none", "no highlight")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => !document.getElementById('sy-pick').hidden", timeout=4, what="the pull to open the schematic")
            self.assertEqual(page.inner_text("#sy-pname").upper(), "FUFLUNS")   # by its economy (Tourism)
            self.assertFalse(self.js(page, "document.getElementById('sy-sch').classList.contains('off')"), "Planetary view is an ordinary button")
            page.click("#sy-sch")   # back, no layout confirmed: still quiet
            self.until(page, "() => document.getElementById('sy-pick').hidden && !document.querySelector('#sy-svg g[transform]')", timeout=4, what="the planet")
            self.assertEqual(self.js(page, look), port)
            # a click opens it too; confirming a layout makes it an ordinary settlement
            page.click("#sy-sch")
            self.until(page, "() => !document.getElementById('sy-pick').hidden", timeout=4, what="a click to open the schematic")
            page.click("#sy-ok")
            b.wait(lambda: b.state()["syst"]["layouts"].get("m:4308000001") == "tourist-1" or None, what="the layout to be saved")
            page.click("#sy-sch")
            self.until(page, "() => document.getElementById('sy-pick').hidden && !document.querySelector('#sy-svg g[transform]')", timeout=4, what="the planet")
            self.assertNotEqual(self.js(page, look)[0], port[0], "an ordinary button now")
            self.assertEqual(self.js(page, "document.getElementById('sy-sch').title"), "")
            self.until(page, "() => ED.S.syFocus === 'sch' && getComputedStyle(document.getElementById('sy-sch')).boxShadow !== 'none'",
                       what="the UFC highlight on it")
            self.no_errors()

    def test_picture_in_coarse_pixels(self):
        """The picture shows on a canvas, in pixels the size of the text's (whole screen pixels: 2 here), small
        or maximised - maximised it has more of them, not finer ones - in the picture's colours."""
        j = journals.syst()
        with Board("p_pixels", journal=j["journal"], status=j["status"], ufc=False) as b:
            page = self.open(b)
            self.go(page, "nav", 1)
            self.pick(page, "Dhaenens's Lodgings")
            look = """(() => { const cv = document.getElementById('sy-px'), svg = document.getElementById('sy-svg');
                const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data; let lit = 0, amber = 0;
                for (let i = 0; i < d.length; i += 4) { if (d[i + 3]) lit++; if (d[i] === 0xe3 && d[i + 1] === 0xa2) amber++; }
                return { w: cv.width, h: cv.height, cssw: cv.offsetWidth, svgw: svg.clientWidth,
                         svgh: svg.clientHeight, lit: lit, amber: amber, seen: getComputedStyle(svg.firstElementChild).visibility }; })()"""
            self.until(page, "() => document.getElementById('sy-px').width > 1", what="the picture's canvas")
            small = self.js(page, look)
            self.assertEqual((small["w"], small["h"]), (small["svgw"] // 2, small["svgh"] // 2))
            self.assertAlmostEqual(small["cssw"], small["w"] * 2, delta=0.01)
            self.assertGreater(small["lit"], 200)
            self.assertGreater(small["amber"], 0, "the settlement's marker, in amber")
            self.assertEqual(small["seen"], "hidden", "the SVG under it doesn't show")
            page.click("#sy-max")
            page.click("#sy-sch")
            self.until(page, "() => !document.getElementById('sy-pick').hidden", timeout=4, what="the schematic")
            big = self.js(page, look)
            self.assertEqual((big["w"], big["h"]), (big["svgw"] // 2, big["svgh"] // 2))
            self.assertGreater(big["w"], small["w"] * 2)
            self.assertGreater(big["amber"], 100, "the landing pads, dashed amber")
            # the icons' boxes and the names are drawn in pixels too: switching them on lights more
            page.click('#sy-icons button[data-ic="door"]')
            self.assertGreater(self.js(page, look)["lit"], big["lit"])
            self.no_errors()

    def test_ufc_reaches_the_buttons(self):
        j = journals.syst()
        with Board("p_schem_ufc", journal=j["journal"], status=j["status"]) as b:
            page = self.open(b)
            self.go(page, "nav", 1)
            self.pick(page, "Dhaenens's Lodgings")
            b.ufc_cmd("press ILS", "pulse COMM2_CW", "pulse COMM2_CW")   # switch -> picture -> Maximise
            self.until(page, "() => document.getElementById('sy-max').classList.contains('focus')", what="Maximise highlighted")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => document.getElementById('sy-pc').classList.contains('max')", what="the pull to maximise")
            b.ufc_cmd("pulse COMM2_CW")   # -> Schematic view
            self.until(page, "() => document.getElementById('sy-sch').classList.contains('focus')", what="Schematic view highlighted")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => !document.getElementById('sy-pick').hidden", timeout=4, what="the pull to open the schematic")
            b.ufc_cmd("pulse COMM2_CW", "pulse COMM2_CW")   # -> the next-layout arrow
            self.until(page, "() => document.getElementById('sy-next').classList.contains('focus')", what="the arrow highlighted")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => document.getElementById('sy-pnum').textContent === '2 of 4'", what="the pull to step on")
            # grab the schematic: the knob zooms, the dials pan, a long pull shows the whole of it again
            b.ufc_cmd(*["pulse COMM2_CCW"] * 4)   # back up to the picture
            self.until(page, "() => document.getElementById('sy-pic').classList.contains('focus')", what="the picture highlighted")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => document.getElementById('sy-pic').classList.contains('grab')", what="the pull to grab it")
            b.ufc_cmd("pulse COMM2_CW", "pulse COMM2_CW")   # grabbed, the COMM2 knob does nothing (zoom is on COMM1 VOLUME)
            time.sleep(0.4)
            self.assertEqual(self.js(page, "ED.S.sc.zoom"), 1)
            b.ufc_cmd("dial 9 3800")   # COMM1 VOLUME turned clockwise: zooms in while it's turned
            self.until(page, "() => ED.S.sc.zoom > 1.6", what="COMM1 VOLUME to zoom in")
            b.ufc_cmd("dial 9 2000")   # the middle: it holds
            time.sleep(0.4)
            z = self.js(page, "ED.S.sc.zoom")
            time.sleep(0.5)
            self.assertEqual(self.js(page, "ED.S.sc.zoom"), z)
            self.assertIn("ZOOM", page.evaluate("() => document.getElementById('sy-rotlab').textContent").upper())
            self.assertTrue(self.js(page, "document.getElementById('sy-pic').classList.contains('focus')"), "zooming doesn't move the highlight")
            b.ufc_cmd("dial 7 3500")   # VOLUME: across, not turning it
            self.until(page, "() => ED.S.sc.pan[0] !== 0 || ED.S.sc.pan[1] !== 0", what="the dial to pan")
            b.ufc_cmd("dial 7 2000")
            self.assertIn("HEADING 000", page.inner_text("#sy-rotlab").upper())
            b.ufc_cmd("hold COMM2_PULL 2.3", pause=2.8)
            self.until(page, "() => ED.S.sc.zoom === 1 && ED.S.sc.pan[0] === 0", what="a long pull for the whole settlement")
            b.ufc_cmd("press COMM2_PULL")   # let go: the dials turn it again
            self.until(page, "() => !document.getElementById('sy-pic').classList.contains('grab')", what="the pull to let go")
            self.assertEqual(self.js(page, "[...document.querySelectorAll('#sy-icons button')].map(b => b.dataset.f).join()"),
                             "ic-term,ic-door,ic-power,ic-exp,ic-cz,ic-type")   # the icon toggles and the Type toggle (no tips, no Loot)
            self.no_errors()


class ZoomTypesCopy(PageTest):
    """COMM1 VOLUME (and the wheel) zoom planets too; the Type toggle shows another type's layouts and is
    remembered; the copy / paste button beside a system's name, pressed on the page or by a COMM2 pull."""

    pick = Schematics.pick
    js = Schematics.js

    def test_planet_zoom(self):
        j = journals.syst()
        with Board("p_zoom", journal=j["journal"], status=j["status"]) as b:
            page = self.open(b)
            self.go(page, "nav", 1)
            self.pick(page, "HIP 20277 3 b")
            self.assertFalse(self.js(page, "document.getElementById('sy-max').hidden"))
            b.ufc_cmd("press ILS", "dial 9 3800")   # the page menu; COMM1 VOLUME turned in
            self.until(page, "() => ED.S.syZoom > 1.6", what="COMM1 VOLUME to zoom the planet")
            b.wait(lambda: b.display()["s1"] == "Z+" or None, what="Z+ on the scratchpad while it zooms")
            b.ufc_cmd("dial 9 2000")
            b.wait(lambda: b.display()["s1"] == "B" or None, what="the menu letters back")
            self.assertIn("ZOOM", page.evaluate("() => document.getElementById('sy-rotlab').textContent").upper())
            page.dispatch_event("#sy-svg", "dblclick")
            self.until(page, "() => ED.S.syZoom === 1", what="a double-click for the whole planet")
            box = page.locator("#sy-svg").bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.wheel(0, -300)
            self.until(page, "() => ED.S.syZoom > 1.2", what="the wheel to zoom the planet")
            self.pick(page, "Fabian City")   # in orbit: no zoom, no maximise
            self.assertEqual(self.js(page, "ED.S.syZoom"), 1)
            b.ufc_cmd("dial 9 3800")
            time.sleep(0.6)
            self.assertEqual(self.js(page, "ED.S.syZoom"), 1)
            self.assertTrue(self.js(page, "document.getElementById('sy-max').hidden"))
            # a dial left turned: a new selection doesn't start zooming until it's been back in the middle
            self.pick(page, "HIP 20277 3 b")
            time.sleep(0.8)
            self.assertEqual(self.js(page, "ED.S.syZoom"), 1)
            b.ufc_cmd("dial 9 2000", "dial 9 3800")
            self.until(page, "() => ED.S.syZoom > 1.3", what="zooming once it's been in the middle")
            b.ufc_cmd("dial 9 2000")
            self.no_errors()

    def test_spin_holds(self):
        """Turned or tilted with the dials, a planet stays where you leave it; selecting it again, a double-click
        or a 2-second COMM2 pull with nothing under the cursor sets it spinning on its own again."""
        j = journals.syst()
        with Board("p_spin", journal=j["journal"], status=j["status"]) as b:
            page = self.open(b)
            self.go(page, "nav", 1)

            def spinning(what):
                rot = page.evaluate("() => ED.S.syRot")
                self.until(page, f"() => ((ED.S.syRot - {rot} + 360) % 360) > 2 && ((ED.S.syRot - {rot} + 360) % 360) < 90",
                           what=what)

            def still(what):
                time.sleep(0.3)
                rot, tilt = page.evaluate("() => [ED.S.syRot, ED.S.syTilt]")
                time.sleep(0.8)
                now = page.evaluate("() => [ED.S.syRot, ED.S.syTilt]")
                self.assertAlmostEqual(now[0], rot, places=3, msg=what)
                self.assertAlmostEqual(now[1], tilt, places=3, msg=what)

            self.pick(page, "HIP 20277 3 b")
            spinning("the planet's own spin")
            b.ufc_cmd("press ILS", "dial 5 3600")   # BRT: tilting it stops the spin too
            tilt = page.evaluate("() => ED.S.syTilt")
            self.until(page, f"() => ED.S.syTilt > {tilt} + 5", what="BRT to tilt it")
            b.ufc_cmd("dial 5 2000")
            still("tilted: it holds")
            b.ufc_cmd("dial 7 3600")
            rot = page.evaluate("() => ED.S.syRot")
            self.until(page, f"() => Math.abs(((ED.S.syRot - {rot} + 540) % 360) - 180) > 10", what="COMM2 VOLUME to spin it")
            b.ufc_cmd("dial 7 2000")
            still("turned: it holds")
            # select something else and come back: spinning on its own again
            self.pick(page, "Fabian City")
            self.pick(page, "HIP 20277 3 b")
            spinning("its own spin after selecting it again")
            # a double-click: the whole planet, spinning on its own
            b.ufc_cmd("dial 7 3600")
            time.sleep(0.5)
            b.ufc_cmd("dial 7 2000")
            still("turned again: it holds")
            page.dispatch_event("#sy-svg", "dblclick")
            spinning("its own spin after a double-click")
            # a 2-second pull with nothing under the cursor: the same (out of a zoom too)
            b.ufc_cmd("dial 9 3800", "dial 7 3600")
            self.until(page, "() => ED.S.syZoom > 1.5", what="COMM1 VOLUME to zoom it")
            b.ufc_cmd("dial 9 2000", "dial 7 2000")
            still("zoomed and turned: it holds")
            self.assertFalse(page.evaluate("() => ED.S.syGrab"))
            b.ufc_cmd("hold COMM2_PULL 2.3", pause=2.8)
            self.until(page, "() => ED.S.syZoom === 1 && !ED.S.syHeld", what="a long pull for the whole planet")
            spinning("its own spin after a long pull")
            # with a settlement under the (+) cursor, a long pull still selects it
            page.evaluate("""() => { const e = ED.S.data.syst.entries.find(x => x.name === 'Hao Extraction Prospect');
                                     ED.S.syHeld = true; ED.S.syRot = e.pic.lon; ED.S.syTilt = e.pic.lat; }""")
            b.ufc_cmd("pulse COMM2_CW")
            self.until(page, "() => document.getElementById('sy-pic').classList.contains('focus')", what="the picture focus")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => /HAO EXTRACTION/i.test(document.getElementById('sy-rotlab').textContent)", what="the settlement under the cursor")
            b.ufc_cmd("hold COMM2_PULL 2.3", pause=2.8)
            self.until(page, "() => document.getElementById('sy-name').textContent === 'Hao Extraction Prospect'", what="a long pull to select it")
            self.no_errors()

    def test_descent_to_the_schematic(self):
        """Maximised, a planet zooms on past its own size, centred on a settlement, the grid getting finer, to its
        schematic at the same scale; zooming out goes back up to the planet."""
        j = journals.syst()
        with Board("p_descent", journal=j["journal"], status=j["status"]) as b:
            page = self.open(b)
            self.go(page, "nav", 1)
            self.pick(page, "HIP 20277 3 b")
            page.click("#sy-max")
            b.ufc_cmd("press ILS", "dial 9 4000")   # full speed in
            self.until(page, "() => !!ED.S.desc.lock", timeout=6, what="a settlement to go down to")
            target = page.evaluate("() => ED.S.desc.lock.name")
            self.until(page, "() => /GRID 0\\.\\d+°/i.test(document.getElementById('sy-rotlab').textContent)", timeout=8, what="the grid getting finer")
            self.assertRegex(page.evaluate("() => document.getElementById('sy-rotlab').textContent"), r"Grid 0\.\d+° \(≈ [\d.,]+ k?m\)")
            self.until(page, "() => ED.S.sc.view === 'schematic'", timeout=12, what="the schematic taking over")
            self.assertEqual(page.inner_text("#sy-name").upper(), target.upper())   # the settlement's details now
            self.assertTrue(self.js(page, "document.getElementById('sy-pc').classList.contains('max')"))
            b.ufc_cmd("dial 9 0")   # full speed out: back up through the schematic to the planet
            self.until(page, "() => ED.S.sc.view === 'planet' && ED.S.syZoom < 100", timeout=12, what="back to the planet")
            self.until(page, "() => ED.S.syZoom === 1 && !ED.S.desc.lock", timeout=12, what="the whole planet again")
            b.ufc_cmd("dial 9 2000")
            self.no_errors()

    def test_range_bar_and_schematics_on_the_planet(self):
        """Maximised, a range bar gives the scale in the game's units (m, km, Mm, ls); on the way down a planet, a
        settlement with a confirmed layout shows as its schematic from a few pixels across - with its yellow box
        while small, the box alone when smaller still - and the small picture goes down as far as the big one."""
        j = journals.syst()
        with Board("p_range", journal=j["journal"], status=j["status"], ufc=False) as b:
            key = "m:3814631936"
            self.assertEqual(b.post("/api/settlement-layout", {"key": key, "layout": "tourist-2", "name": "Dhaenens's Lodgings"})[0], 200)
            page = self.open(b)
            self.go(page, "nav", 1)
            bar = "(document.querySelector('#sy-svg text[data-range]') || {}).textContent || ''"
            for name, unit in (("HIP 20277 3 a", "km"), ("HIP 20277 1", "Mm"), ("HIP 20277 2", "ls"), ("HIP 20277", "ls")):
                self.pick(page, name)
                self.assertEqual(self.js(page, bar), "", "no range bar on the small picture")
                page.click("#sy-max")
                self.until(page, f"() => / {unit}$/.test({bar})", what=f"the range bar in {unit} for {name}")
                self.assertRegex(self.js(page, bar), r"^(1|2|5|10|20|50|100|200|500|0\.1|0\.2|0\.5) " + unit + "$")
            # going down to Dhaenens's Lodgings (its layout confirmed): the yellow box, then the schematic with it, then the schematic
            self.pick(page, "Dhaenens's Lodgings")
            page.click("#sy-max")
            lat, lon = self.js(page, "[ED.S.syEntry.pic.lat, ED.S.syEntry.pic.lon]")
            sid = self.js(page, "ED.S.syEntry.key")

            def at(z):
                page.evaluate(f"() => {{ ED.S.syHeld = true; ED.S.syRot = {lon}; ED.S.syTilt = {lat}; ED.S.syZoom = {z}; window.dispatchEvent(new Event('resize')); }}")
                self.until(page, f"() => !!(ED.S.syShown || {{}})['{sid}']", what="the settlement drawn on the planet")
                return self.js(page, f"ED.S.syShown['{sid}']")
            far = at(20)
            self.assertEqual(far["how"], "box")
            per = far["wpx"] / 20   # (its size grows with the zoom)
            self.assertEqual(at(15 / per)["how"], "plan+box")
            near = at(80 / per)
            self.assertEqual(near["how"], "plan")
            self.assertAlmostEqual(near["wpx"], 80, delta=1)
            self.assertGreater(self.js(page, "document.querySelectorAll('#sy-svg path[stroke-dasharray]').length"), 0)
            self.assertRegex(self.js(page, bar), r" (m|km)$")
            # its schematic, maximised: the range bar in metres
            page.click("#sy-sch")
            self.until(page, "() => !document.getElementById('sy-pick').hidden", timeout=4, what="the schematic")
            self.until(page, f"() => / m$/.test({bar})", what="the range bar in metres")
            page.click("#sy-sch")
            self.until(page, "() => document.getElementById('sy-pick').hidden && !document.querySelector('#sy-svg g[transform]')", timeout=4, what="the planet")
            # small, the wheel goes down past 8 times, into the schematic
            page.click("#sy-max")
            self.assertFalse(self.js(page, "document.getElementById('sy-pc').classList.contains('max')"))
            page.evaluate("() => { ED.S.syZoom = 1; window.dispatchEvent(new Event('resize')); }")
            box = page.locator("#sy-svg").bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            for _ in range(120):
                page.mouse.wheel(0, -400)
                if self.js(page, "ED.S.sc.view") == "schematic":
                    break
                time.sleep(0.03)
            self.until(page, "() => ED.S.sc.view === 'schematic'", what="the small picture going down into the schematic")
            self.assertFalse(self.js(page, "document.getElementById('sy-pc').classList.contains('max')"))
            self.no_errors()

    def test_type_toggle(self):
        j = journals.syst()
        with Board("p_type", journal=j["journal"], status=j["status"], ufc=False) as b:
            plan = json.loads((b.dir / "schematics" / "tourist-1.json").read_text(encoding="utf-8"))   # an Industrial layout too
            plan.update(id="industrial-1", category="industrial", name="Made-up Industrial Layout")
            (b.dir / "schematics" / "industrial-1.json").write_text(json.dumps(plan), encoding="utf-8")
            b.wait(lambda: (b.state().get("schematics") or {}).get("industrial") or None, what="the new layout")
            page = self.open(b)
            self.go(page, "nav", 1)
            self.pick(page, "Dhaenens's Lodgings")
            page.click("#sy-max")
            page.click("#sy-sch")
            self.until(page, "() => !document.getElementById('sy-pick').hidden", timeout=4, what="the layout picker")
            self.assertEqual(page.inner_text("#sy-type").upper(), "TYPE: TOURISM")
            page.click("#sy-type")
            self.until(page, "() => document.getElementById('sy-pname').textContent === 'Made-up Industrial Layout'", what="the Industrial layouts")
            self.assertEqual(page.inner_text("#sy-type").upper(), "TYPE: INDUSTRIAL")
            key = page.evaluate("() => ED.S.syEntry.settlement.key")
            b.wait(lambda: b.state()["syst"]["types"] == {key: "industrial"} or None, what="the type remembered")
            page.click("#sy-type")   # round again: back to the data's type, nothing kept
            self.until(page, "() => /TOURISM/i.test(document.getElementById('sy-type').textContent)", what="Tourism again")
            b.wait(lambda: b.state()["syst"]["types"] == {} or None, what="the type forgotten")
            self.no_errors()

    def test_copy_buttons(self):
        with Board("p_clip", **journals.ocor()) as b:
            page = self.open(b)
            self.go(page, "contracts", 3)
            page.click('#ob-list .item[data-oid="o4"]')
            self.until(page, "() => !document.getElementById('ob-clip').hidden", what="the copy button")
            system = page.evaluate("() => document.getElementById('ob-clip').dataset.clip")
            self.assertEqual(system, "Maia")
            page.click("#ob-clip")
            self.until(page, "() => /PASTE/i.test(document.getElementById('ob-clip').textContent)", what="copied: Paste next")
            b.ufc_cmd("press ILS", "press COMM2_PULL")   # in VR: a short COMM2 pull presses it - pasted (Ctrl+V into Elite)
            self.until(page, "() => /PASTED/i.test(document.getElementById('ob-clip').textContent)", what="pasted")
            b.wait(lambda: "UFC: Paste Maia" in b.log() or None, what="Ctrl+V sent")
            self.go(page, "contracts", 1)   # Contracts: beside Location
            self.until(page, "() => !document.getElementById('f-clip').hidden || !document.querySelector('#rail .item')", what="the Contracts copy button")
            self.no_errors()


class HistoryPages(PageTest):
    """Nav › Hist and Contracts › History: the rows (a line for each day), the toggles and their totals, a row's
    details; the UFC's COMM1 picks a row, COMM2 steps to a toggle (a pull flips it) or the copy button."""

    def test_nav_hist(self):
        j = journals.history()
        with Board("p_hist", journal=j["journal"], status=j["status"], edsm=("hip 20277",)) as b:
            b.wait(lambda: (b.state().get("hist") or {}).get("ready") or None, timeout=20, what="the old journals read")
            page = self.open(b)
            self.assertTrue(page.evaluate("() => document.getElementById('subtabs').hidden"), "Home has no sub-tabs")
            self.go(page, "nav", 6)
            self.assertEqual(page.inner_text("#subtabs .stab.on").upper(), "6 HIST")
            self.assertEqual(page.evaluate("() => Array.from(document.querySelectorAll('#subtabs .stab')).map(b => b.textContent.toUpperCase())"),
                             ["1 SYST", "2 TRAJ", "3 WPT", "4 HSI", "5 ATK", "6 HIST"])
            self.until(page, "() => document.querySelectorAll('#hi-list .hrow').length === 11", what="the rows")
            days = page.evaluate("() => Array.from(document.querySelectorAll('#hi-list .hday')).map(d => d.textContent.toUpperCase())")
            self.assertEqual(len(days), 2)
            self.assertTrue(days[0].startswith("TODAY · "), days)
            self.assertEqual(page.inner_text("#hi-tot").upper(), "4 SYSTEMS · 3 STATIONS · 2 PLANETARY")
            self.until(page, "() => document.getElementById('hi-name').textContent === 'HIP 20277'", what="the newest row's details")
            words = page.evaluate("""() => Array.from(document.querySelectorAll('#hi-list .hrow')).map(r =>
                                       [r.querySelector('.hw').textContent.trim(), !!r.querySelector('.hw svg.ico')])""")
            self.assertEqual([[w.upper(), i] for w, i in words[:8]], [["JUMP", False], ["DOCK", True], ["JUMP", False], ["DOCK", True],
                                                                        ["", False], ["ORBIT", True], ["NEAR", False], ["LAND", True]])
            page.click('#hi-list [data-key*="|near|"]')
            self.until(page, "() => document.getElementById('hi-name').textContent === 'Hao Extraction Prospect'", what="the settlement")
            self.assertIn("LANDED", page.inner_text("#hi-chips").upper())
            self.assertIn("CAME WITHIN RANGE", page.inner_text("#hi-vis").upper())
            time.sleep(0.5)
            self.assertGreater(page.evaluate(CANVAS_INK_JS, "hi-px"), 10, "the picture is empty")   # (a dashed globe: sparse)
            # Systems off: the places alone, each with its system
            page.click('#pg-hist .htg[data-tg="systems"]')
            self.until(page, "() => document.querySelectorAll('#hi-list .hrow').length === 6", what="the places alone")
            self.assertEqual(page.inner_text("#hi-tot").upper(), "3 STATIONS · 2 PLANETARY")
            self.assertIn("FABIAN CITY · HIP 20277", page.inner_text("#hi-list .hrow").upper())
            # the UFC: COMM2 to the first toggle, a pull flips it back on
            b.ufc_cmd("press ILS", "pulse COMM2_CW")
            self.until(page, "() => document.querySelector('#pg-hist .htg.focus') !== null", what="the toggle focus")
            b.ufc_cmd("press COMM2_PULL")
            self.until(page, "() => document.querySelectorAll('#hi-list .hrow').length === 11", what="Systems back on")
            # COMM1 steps through the rows, a pull picks one
            b.ufc_cmd("pulse COMM1_CW", "pulse COMM1_CW")
            self.until(page, "() => document.querySelector('#hi-list .hrow.cur') !== null", what="the UFC highlight")
            cur = page.eval_on_selector("#hi-list .hrow.cur", "e => e.dataset.key")
            b.ufc_cmd("press COMM1_PULL")
            self.until(page, f"() => document.querySelector('#hi-list .hrow.sel').dataset.key === {json.dumps(cur)}", what="the pull")
            row = next(r for r in json.loads(b.get("/api/hist?page=nav")[1])["rows"] if r["k"] == cur)
            self.until(page, f"() => ED.S.hiSel === {json.dumps(cur)} && document.getElementById('hi-clip').dataset.clip === {json.dumps(row.get('s') or (row['n'] if row['d'] == 0 else 'HIP 20277'))}",
                       what="its details")
            sysname = page.evaluate("() => document.getElementById('hi-clip').dataset.clip")
            # COMM2 on past the toggles to the copy button: a pull copies the system's name
            b.ufc_cmd("pulse COMM2_CW", "pulse COMM2_CW", "pulse COMM2_CW")
            self.until(page, "() => ED.hist.nav.focus === 'copy' && document.getElementById('hi-clip').classList.contains('focus')",
                       what="the copy button's focus")
            b.ufc_cmd("press COMM2_PULL")
            b.wait(lambda: f"Copy button: {sysname} - copied" in b.log() or None, what="the system copied")
            self.no_errors()

    def test_contract_history(self):
        j = journals.history()
        with Board("p_chist", journal=j["journal"], status=j["status"], edsm=("hip 20277",), ufc=False) as b:
            b.wait(lambda: (b.state().get("hist") or {}).get("ready") or None, timeout=20, what="the old journals read")
            page = self.open(b)
            self.go(page, "contracts", 2)
            self.until(page, "() => document.querySelectorAll('#ch-list .item').length === 1", what="the completed mission")
            self.assertEqual(page.inner_text("#ch-tot").upper(), "1 COMPLETED")
            self.until(page, "() => document.getElementById('ch-name').textContent === '12 × Gold'", what="its details")
            self.assertEqual((page.inner_text("#ch-out").upper(), page.inner_text("#ch-paid")), ("COMPLETED", "310,000 CR"))
            self.assertIn("2 × Grid Resistors", page.inner_text("#ch-brief"))
            self.assertFalse(page.evaluate("() => document.getElementById('ch-clip').hidden"))
            page.click('#pg-chist .htg[data-tg="failed"]')
            self.until(page, "() => document.querySelectorAll('#ch-list .item').length === 2", what="the failed one too")
            self.assertEqual(page.inner_text("#ch-tot").upper(), "1 COMPLETED · 1 FAILED")
            page.click('#ch-list .item[data-key="h:2900"]')
            self.until(page, "() => /FAILED/i.test(document.getElementById('ch-out').textContent)", what="the failed mission")
            self.assertIn("ACCEPTED BEFORE YOUR JOURNALS", page.inner_text("#ch-chips").upper())
            page.click('#pg-chist .htg[data-tg="completed"]')
            self.until(page, "() => document.querySelectorAll('#ch-list .item').length === 1", what="the failed one alone")
            self.assertEqual(page.inner_text("#ch-tot").upper(), "1 FAILED")
            self.no_errors()


class Setup(PageTest):
    def test_controls(self):
        """4 Setup > Controls: the UFC's jobs, in groups, each on its button (the UFC's own by default); ASSIGN, then a
        press on any controller; what Elite also does with it; a row lit while its button's held; RESTORE DEFAULTS
        (twice)."""
        j = journals.syst()
        with Board("p_controls", journal=j["journal"], status=j["status"]) as b:
            page = self.open(b)
            page.click('.tab[data-tab="setup"]')
            self.on(page, "setup", 1, what="4 Setup > Controls")
            self.assertEqual(page.evaluate("() => Array.from(document.querySelectorAll('#subtabs .stab')).map(b => b.textContent.toUpperCase())"), ["1 CONTROLS", "2 SETTINGS"])
            self.until(page, "() => document.querySelectorAll('#ct-jobs .ctrow').length === 34", what="the jobs")
            self.assertEqual(page.evaluate("() => Array.from(document.querySelectorAll('#ct-jobs .ctgrp')).map(g => g.firstChild.textContent.trim().toUpperCase())"),
                             ["COMM1 AND COMM2", "OPTION BUTTONS", "MENU BUTTONS", "KEYPAD", "DIALS"])
            self.assertIn("UFC I/L/S", page.inner_text('.ctrow[data-job="ILS"] .ctbind').upper())
            self.assertIn("DEFAULT", page.inner_text('.ctrow[data-job="ILS"] .ctbind').upper())
            self.until(page, "() => document.querySelectorAll('#ct-devs .ctdev').length === 2", what="the controllers")
            self.assertTrue(page.evaluate("() => document.getElementById('ct-restore').disabled"), "nothing to restore")
            # ASSIGN: then a press on the box
            page.click('.ctrow[data-job="COMM1_PULL"] button[data-a="assign"]')
            self.until(page, "() => !document.getElementById('ct-learn').hidden && /COMM1 PULL/i.test(document.getElementById('ct-learn-t').textContent)", what="waiting")
            self.until(page, "() => /PRESS THE BUTTON/i.test(document.getElementById('ct-learn-t').textContent)", what="ready")
            self.assertIn("PRESS IT", page.inner_text('.ctrow[data-job="COMM1_PULL"] .ctbind').upper())
            b.ufc_cmd("box press 3")
            self.until(page, "() => /COMM1 PULL: SIM BUTTON BOX · BUTTON 3/i.test(document.getElementById('ct-note').textContent) && document.getElementById('ct-learn').hidden", what="learned")
            bind = page.inner_text('.ctrow[data-job="COMM1_PULL"] .ctbind')
            self.assertIn("BUTTON 3", bind.upper())
            self.assertIn("Elite also: Cycle Next Target", bind)
            self.assertNotIn("DEFAULT", bind.upper())
            self.until(page, "() => Array.from(document.querySelectorAll('#ct-devs .ctdev')).some(r => /SIM BUTTON BOX/i.test(r.textContent) && /IN USE/i.test(r.textContent))", what="the box in use")
            b.ufc_cmd("box hold 3 2", pause=0.1)
            self.until(page, "() => document.querySelector('.ctrow[data-job=\"COMM1_PULL\"]').classList.contains('lit')", what="lit while held")
            # CLEAR
            page.click('.ctrow[data-job="Ent"] button[data-a="clear"]')
            self.until(page, "() => /NONE/i.test(document.querySelector('.ctrow[data-job=\"Ent\"] .ctbind').textContent)", what="ENT cleared")
            # RESTORE DEFAULTS: twice
            page.click("#ct-restore")
            self.assertEqual(page.inner_text("#ct-restore").upper(), "CONFIRM RESTORE")
            page.click("#ct-restore")
            self.until(page, "() => Array.from(document.querySelectorAll('#ct-jobs .ctdf')).length === 34 && /BACK TO THE UFC/i.test(document.getElementById('ct-note').textContent)", what="restored")
            self.assertIn("UFC COMM1 PULL", page.inner_text('.ctrow[data-job="COMM1_PULL"] .ctbind').upper())
            self.no_errors()


    def test_settings(self):
        """4 Setup > Settings: each setting's switch (kept as it's pressed), what it's using now, RESTART TO APPLY until a
        restart, the command line's options saying they won; a folder that isn't there refused; RESTART NOW - the page
        stays open and finds the new start, with the new settings in use."""
        import os, signal
        from pathlib import Path
        j = journals.syst()
        with Board("p_settings", journal=j["journal"], status=j["status"]) as b:
            page = self.open(b)
            self.go(page, "setup", 2)
            self.on(page, "setup", 2, what="4 Setup > Settings")
            self.until(page, "() => /VERSION\\s*3\\.\\d\\d\\.\\d\\d/i.test(document.getElementById('st-about').innerText)", what="the About block")
            self.assertEqual(page.evaluate("() => document.querySelector('#st-engine .on').dataset.v"), "auto")
            self.assertIn("SET BY --ENGINE AT START", page.inner_text("#st-f-engine").upper())
            self.assertIn("NOW: NONE (NO BACKSTORIES)", page.inner_text("#st-einfo").upper())
            self.assertIn("THE DEFAULT FOLDER", page.inner_text("#st-jinfo").upper())
            self.assertIn(f"NOW READING {str(b.jdir).upper()}", page.inner_text("#st-jinfo").upper(), "--journal-dir's folder")
            self.assertTrue(page.evaluate("() => document.getElementById('st-lwarn').hidden"))
            self.assertFalse(page.evaluate("() => document.getElementById('st-restart').classList.contains('arm')"))
            # a switch: kept, and waiting for a restart
            page.click('#st-lan button[data-v="true"]')
            self.until(page, "() => /RESTART TO APPLY/i.test(document.getElementById('st-f-lan').textContent) && document.getElementById('st-restart').classList.contains('arm')", what="RESTART TO APPLY")
            self.assertFalse(page.evaluate("() => document.getElementById('st-lwarn').hidden"), "the warning, with it on")
            self.assertIn("NOW: OFF, THIS PC ONLY", page.inner_text("#st-linfo").upper())
            self.assertTrue(json.loads((b.dir / "settings.json").read_text(encoding="utf-8"))["lan"])
            # a folder that isn't there: refused (Enter saves)
            page.fill("#st-jdir", str(b.dir / "nowhere"))
            page.press("#st-jdir", "Enter")
            self.until(page, "() => /NO SUCH FOLDER/i.test(document.getElementById('st-note').textContent)", what="refused")
            page.fill("#st-jdir", str(b.jdir))
            page.click("#st-jsave")
            self.until(page, "() => /JOURNAL FOLDER KEPT/i.test(document.getElementById('st-note').textContent)", what="kept")
            self.until(page, "() => /^1 JOURNAL THERE/i.test(document.getElementById('st-jinfo').textContent)", what="its journal counted")
            page.click("#st-jdef")
            self.until(page, "() => document.getElementById('st-jdir').value === '' && /THE DEFAULT/i.test(document.getElementById('st-note').textContent)", what="the default again")
            # RESTART NOW: the page finds the new start
            first = b.proc
            page.click("#st-restart")
            self.until(page, "() => /RESTARTING/i.test(document.getElementById('st-note').textContent)", what="restarting")
            first.wait(10)
            child = None
            try:
                self.until(page, "() => /STARTED AGAIN/i.test(document.getElementById('st-note').textContent)", timeout=25, what="started again")
                child = json.loads((b.dir / "ft3000.pid").read_text())["pid"]
                self.assertNotEqual(child, first.pid)
                self.until(page, "() => /^NOW: ON - OPEN HTTP:/i.test(document.getElementById('st-linfo').textContent) && !document.getElementById('st-restart').classList.contains('arm')", what="in use now")
                self.assertEqual(page.inner_text("#st-f-lan"), "")
                self.assertEqual(page.inner_text("#st-restart").upper(), "RESTART NOW")
                self.until(page, "() => document.getElementById('link').className !== 'bad'", timeout=10, what="the page's link back")
                self.errors = [e for e in self.errors if "net::ERR_" not in e]   # the page couldn't reach the board while it restarted
                self.no_errors()
            finally:
                if child is None:
                    try:
                        child = json.loads((b.dir / "ft3000.pid").read_text())["pid"]
                    except (OSError, ValueError):
                        child = None
                if child and child != first.pid:
                    os.kill(child, signal.SIGTERM)
                    end = time.time() + 5
                    while time.time() < end and Path(f"/proc/{child}").exists():
                        time.sleep(0.1)


class Pages(PageTest):
    """Each tab is made of pages: the page and the board must agree on them (the UFC's option
    buttons step through a tab's pages), and every page's section must be on the screen."""

    def test_registry_matches_board(self):
        import ast
        from harness import SCRIPT
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        board, subtabs = (next(ast.literal_eval(n.value) for n in tree.body
                               if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == name for t in n.targets))
                          for name in ("PAGE_TABS", "PAGE_SUBTABS"))
        j = journals.contracts()
        with Board("p_pages", journal=j["journal"], status=j["status"]) as b:
            page = self.open(b)
            reg = page.evaluate("""() => Object.keys(ED.tabs).map(t => [t, ED.tabs[t].map(p => ({
                sub: p.sub, key: p.key, el: p.el, there: !!document.getElementById(p.el),
                section: (document.getElementById(p.el) || {}).dataset || {} }))])""")
            self.assertEqual(sorted(t for t, _ in reg), sorted(board))
            for tab, pages in reg:
                self.assertEqual(len(pages), len(board[tab]), f"pages on the {tab} tab")
                for i, p in enumerate(pages, 1):
                    self.assertEqual(p["sub"], i)
                    self.assertEqual(p["key"], subtabs[tab][i - 1], f"{tab} page {i}'s sub-tab (the keypad digit)")
                    self.assertTrue(p["there"], f"section #{p['el']}")
                    self.assertEqual((p["section"].get("tab"), p["section"].get("sub")), (tab, str(i)), f"#{p['el']}'s data-tab / data-sub")
            buttons = page.evaluate("() => Array.from(document.querySelectorAll('.tab[data-tab]')).map(b => b.dataset.tab)")
            self.assertEqual(sorted(buttons), sorted(board))
            self.no_errors()

    def test_page_change_pull(self):
        """Changing page, the screen settles on the new one: the full lens pull for another tab, a lighter pull on the
        page alone for another page of the same tab (Syst's list and map too)."""
        j = journals.contracts()
        with Board("p_pull", journal=j["journal"], status=j["status"], ocor=True, coords=journals.ocor()["coords"]) as b:
            page = self.open(b)
            page.evaluate("""() => { window._fx = []; new MutationObserver(ms => ms.forEach(m => {
                ['pull', 'pullbig'].forEach(c => { if (m.target.classList.contains(c) && !(m.oldValue || '').split(' ').includes(c))
                  window._fx.push(c + ' ' + (m.target.id || '')); }); }))
                .observe(document.body, {subtree: true, attributes: true, attributeFilter: ['class'], attributeOldValue: true}); }""")
            def fx(do):
                page.evaluate("() => { window._fx = []; document.querySelectorAll('.pull, .pullbig').forEach(e => e.classList.remove('pull', 'pullbig')); }")
                do()
                time.sleep(0.8)
                return set(page.evaluate("() => window._fx"))
            sub = lambda k: (lambda: page.click(f'#subtabs .stab[data-key="{k}"]'))
            self.assertIn("pullbig app", fx(lambda: page.click('.tab[data-tab="nav"]')))
            for key, el in ((2, "pg-traj"), (3, "pg-tgt"), (4, "pg-hsi"), (5, "pg-atk"), (6, "pg-hist"), (1, "pg-syst-list")):
                got = fx(sub(key))
                self.assertIn(f"pull {el}", got, f"Nav {key}")
                self.assertNotIn("pullbig app", got)
            self.assertIn("pull pg-syst-map", fx(lambda: page.click('#syst-rail .syview button[data-view="map"]')))
            self.assertIn("pullbig app", fx(lambda: page.click('.tab[data-tab="contracts"]')))
            for key, el in ((2, "pg-chist"), (3, "pg-ocor"), (1, "pg-contracts")):
                self.assertIn(f"pull {el}", fx(sub(key)), f"Contracts {key}")
            self.no_errors()


if __name__ == "__main__":
    unittest.main()
