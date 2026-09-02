from __future__ import annotations

import re
from pathlib import Path


def validate_generated_cpp_inputs(cpp_path: Path) -> None:
    """Fail when generated C++ references an undeclared i_data_* variable."""
    source = cpp_path.read_text(encoding="utf-8")
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    source = re.sub(r"//.*", "", source)
    declared = set(
        re.findall(
            r"\bfxp::QU_[A-Za-z0-9_]+\s+(i_data_[A-Za-z0-9_]+)\s*;",
            source,
        )
    )
    referenced = set(re.findall(r"\bi_data_[A-Za-z0-9_]+\b", source))
    missing = sorted(referenced - declared)
    if missing:
        raise ValueError(
            f"{cpp_path}: generated C++ references undeclared fixed-point input(s): "
            + ", ".join(missing)
        )

