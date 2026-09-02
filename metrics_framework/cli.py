"""Command-line interface with machine-stable stdout semantics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .core import AdapterFailure, EvaluationUnavailable, evaluate, predict


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="metrics")
    parser.add_argument("module", help="Registered module name")
    parser.add_argument("mode", choices=("predict", "evaluate"))
    parser.add_argument("config", nargs="?", help="Config path or numeric case ID")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = _parser().parse_args(argv)
    try:
        result = (
            predict(args.module, args.config)
            if args.mode == "predict"
            else evaluate(args.module, args.config)
        )
    except EvaluationUnavailable as error:
        print(error, file=sys.stderr)
        return 2
    except (AdapterFailure, OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return 0
