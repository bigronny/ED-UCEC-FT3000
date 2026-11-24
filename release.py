#!/usr/bin/env python3
"""Builds UCEC FT3000's release zip: everything someone needs to run it on Windows, Python included - unzip, then
double-click Start UCEC FT3000. Nothing to install.

    python release.py                 # dist/UCEC-FT3000-<version>.zip, for this version (VERSION in ed_target_board.py)

What goes in (one folder, "UCEC FT3000"):
    ed_target_board.py, web/, schematics/       the program
    README.md, CHANGELOG.md, LICENSE, CREDITS.md, docs/ (the README's pictures)
    Start UCEC FT3000.bat                       starts it with the Python beside it
    Timing log.bat                              the same, with the timing log on
    python/                                     Python's "embeddable package" for 64-bit Windows, with hidapi (for the
                                                UFC and other game controllers) in python/Lib/site-packages
Not the tests, __backup, or anyone's data.

Python and hidapi are downloaded once (from python.org and PyPI) into .release-cache/, and checked against the
SHA-256 sums pinned below - change PYTHON / HIDAPI and their sums together to move to new versions (the script prints
a new download's sum, to pin). --python-zip and --hidapi-wheel use files you already have instead.

Before zipping, it checks nothing private is going out: no one's folders (C:\\Users\\<name>\\..., /home/<name>/...),
e-mail addresses, or any word listed in .release-private (one a line - your name, say; that file stays on your PC:
.gitignore keeps it out of the repository). Anything found stops the build, saying where.

Runs with any Python 3.8 or later, on Windows or anywhere else (it only copies, downloads and zips).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = "UCEC FT3000"                      # the folder inside the zip
PYTHON = "3.13.17"                       # Python's embeddable package for 64-bit Windows
PYTHON_SHA256 = "9e35319bffedab8b36ad44d8f377cb4f1733bcec257a0b6d04d94f01486ddb38"
HIDAPI = "0.15.0"                        # cython-hidapi, its wheel for that Python
HIDAPI_SHA256 = "04e0c1ed6d742bc6e1d00599394bec6b2afb8ee2fc5a0a183d3c4c2d4e315c34"

PROGRAM = ["ed_target_board.py", "web", "schematics", "README.md", "CHANGELOG.md", "LICENSE", "CREDITS.md", "docs",
           "Timing log.bat"]
LEAVE_OUT = {"__pycache__", ".DS_Store", "Thumbs.db", "desktop.ini"}   # (anywhere in the folders copied)

LAUNCHER = r"""@echo off
rem UCEC FT3000: starts the terminal with the Python that comes with it (the python folder) - nothing to install.
rem Leave this window open while you play: it's the FT3000 running. To stop it, press EXIT on the page or close
rem this window. Options for ed_target_board.py can follow the name (most are on the page: 4 Setup > Settings).
cd /d "%~dp0"
"%~dp0python\python.exe" "%~dp0ed_target_board.py" %*
if errorlevel 1 (
  echo.
  echo UCEC FT3000 stopped with an error - the lines above say why.
  pause
)
"""

TEXT = {".py", ".js", ".html", ".css", ".json", ".md", ".txt", ".bat", ".binds", ""}   # (files the privacy check reads)
USER_DIR = re.compile(r"(?i)\b[A-Z]:[\\/]+Users[\\/]+(?!Deckard\b|<|%|Public\b|Default\b)[^\\/\s\"'<>]+|"
                      r"(?<![\w.])/(?:home|Users)/(?!<)[A-Za-z0-9._-]+")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
EMAIL_OK = {"noreply@anthropic.com"}


def say(text):
    print(text, flush=True)


def version(source):
    m = re.search(r'^VERSION = "([^"]+)"', (source / "ed_target_board.py").read_text(encoding="utf-8"), re.M)
    if not m:
        sys.exit("Couldn't find VERSION in ed_target_board.py.")
    return m.group(1)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def checked(path, want, what):
    got = sha256(path)
    if want and got != want:
        sys.exit(f"{what} ({path.name}) isn't the file pinned in release.py: its SHA-256 is {got}, not {want}. "
                 "Delete it from .release-cache to download it again, or pin the new sum if you meant to change it.")
    if not want:
        say(f"  {path.name}: SHA-256 {got} (pin this in release.py)")
    return path


def get_python(cache, given):
    if given:
        return Path(given)
    path = cache / f"python-{PYTHON}-embed-amd64.zip"
    if not path.exists():
        url = f"https://www.python.org/ftp/python/{PYTHON}/{path.name}"
        say(f"Downloading {url}")
        cache.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        tmp.replace(path)
    return checked(path, PYTHON_SHA256, "Python")


def get_hidapi(cache, given):
    if given:
        return Path(given)
    cp = "cp" + "".join(PYTHON.split(".")[:2])
    path = cache / f"hidapi-{HIDAPI}-{cp}-{cp}-win_amd64.whl"
    if not path.exists():
        say(f"Downloading hidapi {HIDAPI} for Python {PYTHON} (64-bit Windows) from PyPI")
        cache.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "pip", "download", f"hidapi=={HIDAPI}", "--only-binary=:all:", "--no-deps",
                        "--platform", "win_amd64", "--python-version", ".".join(PYTHON.split(".")[:2]),
                        "--implementation", "cp", "-d", str(cache), "-q"], check=True)
    return checked(path, HIDAPI_SHA256, "hidapi")


def copy_program(source, app):
    for name in PROGRAM:
        src = source / name
        if not src.exists():
            sys.exit(f"{name} is missing from {source}.")
        if src.is_dir():
            shutil.copytree(src, app / name, ignore=lambda d, names: [n for n in names if n in LEAVE_OUT])
        else:
            shutil.copy2(src, app / name)
    (app / "Start UCEC FT3000.bat").write_bytes(LAUNCHER.replace("\r\n", "\n").replace("\n", "\r\n").encode("ascii"))


def add_python(app, python_zip, hidapi_wheel):
    py = app / "python"
    with zipfile.ZipFile(python_zip) as z:
        z.extractall(py)
    pth = sorted(py.glob("python3*._pth"))
    if not (py / "python.exe").exists() or not pth:
        sys.exit(f"{python_zip.name} isn't Python's embeddable package (no python.exe and ._pth file in it).")
    # The ._pth file is the embedded Python's whole search path: hidapi's folder is added to it (site stays off, so
    # nothing else on the PC - another Python's packages, PYTHONPATH - is picked up)
    lines = pth[0].read_text(encoding="utf-8").splitlines()
    if "Lib\\site-packages" not in lines:
        lines.insert(lines.index(".") + 1 if "." in lines else len(lines), "Lib\\site-packages")
    pth[0].write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    site = py / "Lib" / "site-packages"
    site.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(hidapi_wheel) as z:
        z.extractall(site)
    if not list(site.glob("hid*.pyd")):
        sys.exit(f"{hidapi_wheel.name} has no hid .pyd for Windows in it.")


def private_words(source):
    path = source / ".release-private"
    if not path.exists():
        return []
    return [w.strip() for w in path.read_text(encoding="utf-8").splitlines() if w.strip() and not w.startswith("#")]


def privacy_check(app, words):
    """What would go out that's private: [(file, line, what)] - the program's own files (not Python's)."""
    found = []
    word_rx = re.compile(r"(?i)(?<![A-Za-z0-9])(" + "|".join(re.escape(w) for w in words) + r")(?![A-Za-z0-9])") if words else None
    for f in sorted(app.rglob("*")):
        rel = f.relative_to(app)
        if not f.is_file() or rel.parts[0] == "python" or f.suffix.lower() not in TEXT:
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for rx, what in ((USER_DIR, "someone's folder"), (EMAIL, "an e-mail address"), (word_rx, "a private word")):
                if rx is None:
                    continue
                for m in rx.finditer(line):
                    if what == "an e-mail address" and m.group(0).lower() in EMAIL_OK:
                        continue
                    found.append((str(rel), n, f"{what}: {m.group(0)}"))
    return found


def build(source, out, python_zip, hidapi_wheel, keep=False):
    ver = version(source)
    work = out / "build"
    if work.exists():
        shutil.rmtree(work)
    app = work / APP
    app.mkdir(parents=True)
    say(f"Building {APP} {ver}")
    copy_program(source, app)
    add_python(app, python_zip, hidapi_wheel)
    problems = privacy_check(app, private_words(source))
    if problems:
        for f, n, what in problems:
            say(f"  {f}, line {n}: {what}")
        sys.exit(f"Stopped: {len(problems)} private thing(s) would go out (above). Nothing was zipped.")
    say("Privacy check: nothing private found.")
    zpath = out / f"UCEC-FT3000-{ver}.zip"
    if zpath.exists():
        zpath.unlink()
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(app.rglob("*")):
            arc = f.relative_to(work).as_posix()
            z.write(f, arc + ("/" if f.is_dir() else ""))
    if not keep:
        shutil.rmtree(work)
    say(f"Done: {zpath} ({zpath.stat().st_size / 1e6:.1f} MB), SHA-256 {sha256(zpath)}")
    return zpath


def main(argv=None):
    p = argparse.ArgumentParser(description="Build UCEC FT3000's release zip (Python included) in dist/.")
    p.add_argument("--out", default=str(HERE / "dist"), help="where the zip goes (default: dist/ here)")
    p.add_argument("--cache", default=str(HERE / ".release-cache"), help="where downloads are kept")
    p.add_argument("--python-zip", help="Python's embeddable package (python-X.Y.Z-embed-amd64.zip) to use, not downloaded")
    p.add_argument("--hidapi-wheel", help="hidapi's win_amd64 wheel to use, not downloaded")
    p.add_argument("--source", default=str(HERE), help=argparse.SUPPRESS)   # (the tests build from a copy)
    p.add_argument("--keep", action="store_true", help="keep the unzipped build in <out>/build to look at")
    a = p.parse_args(argv)
    out, cache = Path(a.out).resolve(), Path(a.cache).resolve()
    out.mkdir(parents=True, exist_ok=True)
    python_zip, hidapi_wheel = get_python(cache, a.python_zip), get_hidapi(cache, a.hidapi_wheel)
    build(Path(a.source).resolve(), out, python_zip, hidapi_wheel, keep=a.keep)


if __name__ == "__main__":
    main()
