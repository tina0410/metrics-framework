"""Shared import paths for the aggregated basic-module verification suites."""

from __future__ import annotations

import sys
from pathlib import Path


# PyTV's legacy module loader parses argv at import time. Pytest has already
# consumed its own CLI here, so keep only the executable name for that loader.
sys.argv = sys.argv[:1]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTV_ROOT = PROJECT_ROOT / "Generator" / "LSCE" / "BehaviorialVerification"

for path in (PROJECT_ROOT, PYTV_ROOT):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)
