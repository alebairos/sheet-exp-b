"""Engine CLI: read SPEC.md workbook JSON, echo constants; optional --cell."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def load_workbook(raw: str) -> dict[str, Any]:
    data = json.loads(raw)
    if not isinstance(data, dict) or "sheets" not in data:
        raise SystemExit("workbook JSON must be an object with a 'sheets' key")
    return data


def compute_constants(workbook: dict[str, Any]) -> dict[str, Any]:
    """Return workbook with constant cells unchanged. Formulas are out of scope here."""
    sheets_out: dict[str, dict[str, Any]] = {}
    for name, cells in workbook.get("sheets", {}).items():
        if not isinstance(cells, dict):
            sheets_out[name] = cells
            continue
        out_cells: dict[str, Any] = {}
        for addr, value in cells.items():
            # Constants only: leave values as-is (including formula strings; not evaluated).
            out_cells[addr] = value
        sheets_out[name] = out_cells
    return {"sheets": sheets_out}


def cell_value(workbook: dict[str, Any], ref: str) -> Any:
    if "!" not in ref:
        raise SystemExit(f"cell ref must look like Sheet1!A1, got {ref!r}")
    sheet, addr = ref.split("!", 1)
    sheets = workbook.get("sheets", {})
    if sheet not in sheets:
        raise SystemExit(f"unknown sheet {sheet!r}")
    cells = sheets[sheet]
    if addr not in cells:
        return None
    return cells[addr]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engine")
    parser.add_argument("source", help="workbook file path, or '-' for stdin")
    parser.add_argument("--cell", default=None, help="print one cell, e.g. Sheet1!A1")
    args = parser.parse_args(argv)

    if args.source == "-":
        raw = sys.stdin.read()
    else:
        with open(args.source, encoding="utf-8") as f:
            raw = f.read()

    workbook = load_workbook(raw)
    computed = compute_constants(workbook)

    if args.cell:
        json.dump(cell_value(computed, args.cell), sys.stdout, separators=(",", ":"))
        sys.stdout.write("\n")
    else:
        json.dump(computed, sys.stdout, separators=(",", ":"))
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
