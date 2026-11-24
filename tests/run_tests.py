#!/usr/bin/env python3
"""Runs the ED Target Board tests.

    python tests/run_tests.py               # everything (the page tests need Playwright)
    python tests/run_tests.py server        # just the API / UFC tests (standard library only)
    python tests/run_tests.py release       # just the release script (release.py) - standard library only
    python tests/run_tests.py page          # just the page tests
    python tests/run_tests.py --update      # accept the current behaviour as the new golden files
    python tests/run_tests.py --keep        # keep each test's temporary folder (journal, log) to look at

Each test starts its own copy of the board in a temporary folder, with made-up journals,
a simulated UFC and no internet, so it never touches your real files, caches or UFC.
The page tests need:  pip install playwright  then  playwright install chromium
"""
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    args = sys.argv[1:]
    if "--update" in args:
        os.environ["EDTB_UPDATE_GOLDEN"] = "1"
    if "--keep" in args:
        os.environ["EDTB_KEEP"] = "1"
    which = [a for a in args if not a.startswith("--")] or ["server", "release", "page"]
    sys.path.insert(0, str(HERE))
    loader = unittest.TestLoader()
    suite = unittest.TestSuite(loader.loadTestsFromName(f"test_{w}") for w in which)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
