#!/usr/bin/env python3
"""Run the repository's local structure, safety, and contract checks."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    validator = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_repo.py")], cwd=ROOT)
    if validator.returncode:
        return validator.returncode
    secret_scan = subprocess.run([sys.executable, str(ROOT / "scripts" / "secret_scan.py")], cwd=ROOT)
    if secret_scan.returncode:
        return secret_scan.returncode
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
