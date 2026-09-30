"""Authoritative location for generated RTL, lint, simulation, and synthesis artifacts."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Optional


GENERATED_ROOT_ENV = "PHY_PUSCH_GENERATED_ROOT"
DEFAULT_GENERATED_ROOT = Path("/mnt/g/PHY_PUSCH_verilog")

_WRITE_PROBED_ROOTS: set[Path] = set()


def resolve_generated_root(configured_root: Optional[Path] = None) -> Path:
    """Resolve explicit path, environment setting, or the external-drive default."""

    configured = configured_root
    if configured is None:
        configured = Path(
            os.environ.get(GENERATED_ROOT_ENV, str(DEFAULT_GENERATED_ROOT))
        )
    return configured.expanduser().resolve()


def require_writable_generated_root(root: Optional[Path] = None) -> Path:
    """Prove the selected root writable, without a repository or ``/tmp`` fallback."""

    resolved = resolve_generated_root(root)
    if resolved in _WRITE_PROBED_ROOTS:
        return resolved

    probe_path: Optional[Path] = None
    try:
        resolved.mkdir(parents=True, exist_ok=True)
        descriptor, raw_path = tempfile.mkstemp(
            prefix=".phy_pusch_write_probe.", dir=resolved
        )
        os.close(descriptor)
        probe_path = Path(raw_path)
        probe_path.unlink()
    except OSError as error:
        if probe_path is not None:
            try:
                probe_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise RuntimeError(
            f"generated/build root is not writable: {resolved}. "
            "RTL generation was not started; no repository or /tmp fallback "
            f"is permitted. Filesystem error: {error}"
        ) from error

    _WRITE_PROBED_ROOTS.add(resolved)
    return resolved


__all__ = [
    "DEFAULT_GENERATED_ROOT",
    "GENERATED_ROOT_ENV",
    "require_writable_generated_root",
    "resolve_generated_root",
]
