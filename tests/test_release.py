"""release.py: the release zip - the program, the papers, a launcher and Python (with hidapi) beside it, in one
"UCEC FT3000" folder; not the tests, __backup or anyone's data; and nothing private going out. Built here from stand-ins
for Python's embeddable package and hidapi's wheel (no downloads)."""
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE = ROOT / "release.py"


def fake_zip(path, files):
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return path


class Release(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="edtb_release_"))
        self.src = self.tmp / "src"
        shutil.copytree(ROOT, self.src, ignore=shutil.ignore_patterns("__pycache__", "dist", "build", ".release-cache", ".git"))
        (self.src / "__backup").mkdir(exist_ok=True)
        (self.src / "__backup" / "old.py").write_text("old", encoding="utf-8")
        (self.src / "web" / "__pycache__").mkdir(exist_ok=True)
        (self.src / "edsm_cache.json").write_text("{}", encoding="utf-8")   # (someone's data beside the program)
        import re
        pyver = re.search(r'^PYTHON = "([^"]+)"', RELEASE.read_text(encoding="utf-8"), re.M).group(1)
        self.py = fake_zip(self.tmp / f"python-{pyver}-embed-amd64.zip", {
            "python.exe": b"MZ", "python313.dll": b"MZ", "LICENSE.txt": "PSF", "python313.zip": b"PK",
            "python313._pth": "python313.zip\r\n.\r\n\r\n# Uncomment to run site.main() automatically\r\n#import site\r\n"})
        self.whl = fake_zip(self.tmp / "hidapi-0.15.0-cp313-cp313-win_amd64.whl", {
            "hid.cp313-win_amd64.pyd": b"MZ", "hidapi-0.15.0.dist-info/licenses/LICENSE.txt": "three licences"})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_release(self):
        return subprocess.run([sys.executable, str(self.src / "release.py"), "--source", str(self.src), "--out", str(self.tmp / "dist"),
                               "--python-zip", str(self.py), "--hidapi-wheel", str(self.whl)], capture_output=True, text=True)

    def test_the_zip(self):
        r = self.run_release()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        import re
        ver = re.search(r'^VERSION = "([^"]+)"', (ROOT / "ed_target_board.py").read_text(encoding="utf-8"), re.M).group(1)
        zpath = self.tmp / "dist" / f"UCEC-FT3000-{ver}.zip"
        self.assertIn("Privacy check: nothing private found.", r.stdout)
        with zipfile.ZipFile(zpath) as z:
            names = z.namelist()
            self.assertTrue(all(n.startswith("UCEC FT3000/") for n in names), "one folder")
            top = {n.split("/")[1] for n in names if n.count("/") >= 1 and n.split("/")[1]}
            self.assertEqual(top, {"ed_target_board.py", "web", "schematics", "docs", "python", "README.md", "CHANGELOG.md",
                                   "LICENSE", "CREDITS.md", "Start UCEC FT3000.bat", "Timing log.bat"})
            for n in ("python/python.exe", "python/LICENSE.txt", "python/Lib/site-packages/hid.cp313-win_amd64.pyd",
                      "web/index.html", "web/js/settings.js", "web/vga.woff"):
                self.assertIn("UCEC FT3000/" + n, names)
            self.assertFalse([n for n in names if "__pycache__" in n or "__backup" in n or "/tests/" in n or "edsm_cache" in n],
                             "no tests, backups, caches or data")
            pth = z.read("UCEC FT3000/python/python313._pth").decode().splitlines()
            self.assertEqual(pth[:3], ["python313.zip", ".", "Lib\\site-packages"], "hidapi's folder on the embedded Python's path")
            self.assertIn("#import site", pth, "site stays off: nothing else on the PC picked up")
            bat = z.read("UCEC FT3000/Start UCEC FT3000.bat")
            self.assertIn(b"\r\n", bat)
            self.assertNotIn(b"\r\r", bat)
            self.assertIn(b'"%~dp0python\\python.exe" "%~dp0ed_target_board.py" %*', bat)
            self.assertIn(b"pause", bat, "an error stays on screen")
            self.assertIn(b"\r\n", z.read("UCEC FT3000/Timing log.bat"), "Windows line endings")

    def test_private_things_stop_it(self):
        with open(self.src / "web" / "js" / "core.js", "a", encoding="utf-8") as f:
            f.write("\n// from C:\\Users\\Someone\\Documents\\x and /home/someone/x, mail me@example.com, Deckard is fine: C:\\Users\\Deckard\\x, flown by Rick Blaine\n")
        (self.src / ".release-private").write_text("# private words\nrick blaine\n", encoding="utf-8")
        r = self.run_release()
        self.assertNotEqual(r.returncode, 0)
        out = r.stdout + r.stderr
        for what in ("someone's folder: C:\\Users\\Someone", "someone's folder: /home/someone", "an e-mail address: me@example.com",
                     "a private word: Rick Blaine"):
            self.assertIn(what, out)
        self.assertNotIn("Deckard\\x", out)
        self.assertIn("Nothing was zipped", out)
        self.assertFalse(list((self.tmp / "dist").glob("*.zip")))

    def test_pinned_sums(self):
        """A download that isn't the pinned file stops it (here: the stand-in in the cache, where a download would be)."""
        cache = self.tmp / "cache"
        cache.mkdir()
        shutil.copy2(self.py, cache / self.py.name)
        r = subprocess.run([sys.executable, str(self.src / "release.py"), "--source", str(self.src), "--out", str(self.tmp / "dist"),
                            "--cache", str(cache), "--hidapi-wheel", str(self.whl)], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("isn't the file pinned in release.py", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
