"""Process-isolated MIMO area predictor/reference reader."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AREA_ROOT = PROJECT_ROOT / "Area_TP_Estimator" / "Est_INSA_MMSE"
sys.path.insert(0, str(AREA_ROOT))


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in {"predict", "validate"}:
        print("usage: mimo_area_worker.py predict|validate CONFIG", file=sys.stderr)
        return 1
    import mimo_area_interface

    config_path = Path(sys.argv[2]).resolve()
    if sys.argv[1] == "predict":
        result = mimo_area_interface.predict_area(config_path)
    else:
        with config_path.open("r", encoding="utf-8-sig") as stream:
            config = json.load(stream)
        result = mimo_area_interface.read_reference_area(config)
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
