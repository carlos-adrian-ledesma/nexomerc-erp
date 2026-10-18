"""Execute stdlib-compatible backend tests when PySide6 is unavailable.

Qt-specific test modules remain in the project for the Windows full test run.
"""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
QT_MODULES = {"test_f03.py", "test_retail_ui.py"}


def main() -> int:
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for file in sorted((ROOT / "tests").glob("test_*.py")):
        if file.name in QT_MODULES:
            continue
        suite.addTests(loader.discover(str(ROOT / "tests"), pattern=file.name))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
