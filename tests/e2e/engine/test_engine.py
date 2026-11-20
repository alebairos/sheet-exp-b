"""Product e2e workbooks match LibreOffice Calc pins through ./engine."""

from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BOOKS = Path(__file__).resolve().parent / "books"
ENGINE = ROOT / "engine"


def _same(got, want):
    if isinstance(want, bool) or isinstance(got, bool) or not isinstance(
        want, (int, float)
    ) or not isinstance(got, (int, float)):
        return type(got) is type(want) and got == want
    return abs(got - want) <= 1e-9 * max(1.0, abs(want))


def _run(book):
    proc = subprocess.run(
        [str(ENGINE), "-"],
        input=json.dumps(book),
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(ROOT),
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if proc.returncode:
        raise AssertionError(
            "engine exited %d: %s" % (proc.returncode, proc.stderr.strip()[-300:])
        )
    return json.loads(proc.stdout)


class EngineBooksTest(unittest.TestCase):
    def test_each_product_book_matches_calc(self):
        names = sorted(
            p.stem
            for p in BOOKS.glob("*.json")
            if not p.name.endswith(".calc.json")
        )
        self.assertTrue(names, "tests/e2e/engine/books needs at least one workbook")
        for name in names:
            with self.subTest(book=name):
                book = json.loads((BOOKS / f"{name}.json").read_text(encoding="utf-8"))
                want = json.loads(
                    (BOOKS / f"{name}.calc.json").read_text(encoding="utf-8")
                )
                got = _run(book)
                for sheet, cells in want["sheets"].items():
                    for addr, expected in cells.items():
                        actual = got.get("sheets", {}).get(sheet, {}).get(addr)
                        self.assertTrue(
                            _same(actual, expected),
                            "%s!%s: Calc %s, engine %s"
                            % (sheet, addr, json.dumps(expected), json.dumps(actual)),
                        )


if __name__ == "__main__":
    unittest.main()
