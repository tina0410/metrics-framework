"""Regenerate default basic-module configurations from unique DC report rows."""

import json
import re

from metrics_framework.adapters.basic_area import (
    AREA_ROOT,
    MODULE_DIRECTORIES,
    PROJECT_ROOT,
    _normalized,
    _xlsx_rows,
    read_area_reference,
)


def quantization(row, prefix):
    return {
        "bitwidth": int(row[f"{prefix}_DWT"]),
        "fractional_width": int(row[f"{prefix}_FRAC"]),
        "signed": bool(_normalized(row[f"{prefix}_IF_SIGNED"])),
    }


def configure(name, original, row):
    config = {key: value for key, value in original.items() if key in {"clock", "n_frames"}}
    config["test_case"] = str(row["RTLx"])
    if name in {"counter"}:
        for key in ("DWT", "STEP", "IF_RST_N", "HAS_CLEAR", "HAS_WRAP"):
            config[key] = _normalized(row[key])
        return config
    if name in {"delay", "mux"}:
        config["data_width"] = int(row["DWT"])
        if name == "mux":
            config["n_inputs"] = int(row["N_INPUTS"])
            return config
    elif name in {"addertree", "comptree"}:
        match = re.fullmatch(r"QuType\((\d+),(\d+),([TF])\)", str(row["QU_IN"]))
        if not match:
            raise ValueError(f"Unsupported tree input quantization: {row['QU_IN']!r}")
        config["input"] = {
            "bitwidth": int(match[1]), "fractional_width": int(match[2]),
            "signed": match[3] == "T",
        }
        config["output"] = quantization(row, "QU_OUT")
        config["n_inputs"] = int(row["N_INPUTS"])
        config["config_mode"] = str(row["CONFIG_MODE"])
    elif name in {"cadd", "cmul", "csub", "comp", "sub"}:
        for key, prefix in (("input_1", "QU_IN_1"), ("input_2", "QU_IN_2"), ("output", "QU_OUT")):
            config[key] = quantization(row, prefix)
    else:
        config["input"] = quantization(row, "QU_IN")
        config["output"] = quantization(row, "QU_OUT")
    config["n_pipeline"] = int(row["N_PIPELINES" if name in {"addertree", "comptree", "comp"} else "N_CLK"])
    reset = _normalized(row["IF_RST_N"])
    config["if_rst_n"] = list(reset) if isinstance(reset, tuple) else reset
    if name != "delay":
        config["quantization_mode"] = str(row["QU_MODE"])
        config["overflow_mode"] = str(row["OF_MODE"])
    if name in {"comp", "comptree"}:
        fields = {"IF_GIDX": "greater_index", "IF_LIDX": "less_index", "IF_GVAL": "greater_value", "IF_LVAL": "less_value"}
        if name == "comp":
            fields["IF_EIDX"] = "equal_index"
        config["outputs"] = {key: bool(_normalized(row[column])) for column, key in fields.items()}
    if name == "cmul":
        config["method"] = str(row["METHOD"])
    if name == "sxmatch":
        config["shift"] = int(row["SHIFT"])
    return config


def main():
    for name, directory in MODULE_DIRECTORIES.items():
        report = AREA_ROOT / directory / "report"
        workbook = report / ("test.xlsx" if (report / "test.xlsx").is_file() else "basic.xlsx")
        rows = [row for row in _xlsx_rows(workbook, directory) if row.get("area") is not None]
        if name in {"addertree", "comptree"}:
            rows = [row for row in rows if row.get("CONFIG_MODE") == "A"]
        if name == "comptree":
            # The existing RTL testbench exposes only IF_GIDX. Keep the DC
            # parameters identical to what that testbench can instantiate.
            rows = [row for row in rows if all(
                bool(_normalized(row[key])) == expected
                for key, expected in {
                    "IF_LIDX": False, "IF_EIDX": False,
                    "IF_GVAL": True, "IF_LVAL": False,
                }.items()
            )]
            rows = [row for row in rows if bool(_normalized(row["IF_GIDX"]))]
        if name == "comp":
            # The original C++/RTL comparison checks every output stream.
            rows = [row for row in rows if all(
                bool(_normalized(row[key]))
                for key in ("IF_GIDX", "IF_LIDX", "IF_EIDX", "IF_GVAL", "IF_LVAL")
            )]
        selected = []
        seen = set()
        for row in rows:
            identity = tuple((key, repr(_normalized(value))) for key, value in row.items() if key not in {"RTLx", "area", f"Est_{directory}", "MAPE"} and not str(key).endswith("(s)"))
            if identity not in seen:
                seen.add(identity)
                selected.append(row)
            if len(selected) == 5:
                break
        if len(selected) != 5:
            raise LookupError(f"{directory} has fewer than five unique report rows")
        for index, row in enumerate(selected, 1):
            path = PROJECT_ROOT / "Generator" / "BasicModules" / directory / "configs" / f"config_case{index}.json"
            original = json.loads(path.read_text(encoding="utf-8"))
            config = configure(name, original, row)
            read_area_reference(name, config)
            path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{directory}: {', '.join(str(row['RTLx']) for row in selected)}")


if __name__ == "__main__":
    main()
