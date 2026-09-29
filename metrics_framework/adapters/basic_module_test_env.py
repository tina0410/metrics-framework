"""Prepare the flat ``modules`` imports expected by BasicModules' RTL tests."""

from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_SUPPORT = Path(__file__).resolve().parents[1] / "testing" / "basic_support.py"


@contextmanager
def isolated_test_environment(module_root: Path) -> Iterator[dict[str, str]]:
    """Expose this module's sources as ``modules`` without relying on a ZIP asset."""
    with tempfile.TemporaryDirectory(prefix="basic-module-tests-") as directory:
        temp_root = Path(directory)
        package = temp_root / "modules"
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
        for source in module_root.glob("*.py"):
            if source.name.endswith("_metrics.py"):
                continue
            shutil.copy2(source, package / source.name)
        shutil.copy2(TEST_SUPPORT, temp_root / "basic_support.py")
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            [str(temp_root), environment.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        yield environment
