#!/bin/sh
# b1: each value kind round-trips through the CLI.
# Contract (plan i2-values): src.values.from_json(json_value) -> Value; src.values.to_json(Value) -> json_value.
# Kinds: number, text, boolean, blank (null / missing) and the six errors {"error": "#..."}.
set -eu
cd "$(dirname "$0")/../../.."
export PYTHONDONTWRITEBYTECODE=1
python3 - <<'PY'
import json, subprocess, sys
from src.values import from_json, to_json
kinds = [1, -2.5, 0, 1e-7, 123456789012, "text", "", "12", "TRUE", True, False, None,
         {"error": "#DIV/0!"}, {"error": "#VALUE!"}, {"error": "#REF!"},
         {"error": "#NAME?"}, {"error": "#N/A"}, {"error": "#NUM!"}]
def same(got, want):
    if isinstance(want, bool) or want is None or isinstance(want, (str, dict)):
        return type(got) is type(want) and got == want
    return type(got) in (int, float) and not isinstance(got, bool) and got == want
bad = 0
for v in kinds:
    got = to_json(from_json(v))
    if not same(got, v):
        bad += 1
        print("FAIL to_json(from_json(%r)) = %r" % (v, got))
# An integral number is written as a JSON integer (2.0 -> 2), as Calc shows it.
got = to_json(from_json(2.0))
if not (type(got) is int and got == 2):
    bad += 1
    print("FAIL to_json(from_json(2.0)) = %r, want 2" % (got,))
# Through the CLI: a workbook holding every kind comes back unchanged; a missing cell is null.
cells = {"A%d" % (i + 1): v for i, v in enumerate(kinds) if v is not None}
book = {"sheets": {"Sheet1": cells}}
out = subprocess.run(["./engine", "-"], input=json.dumps(book), capture_output=True, text=True)
if out.returncode != 0:
    bad += 1
    print("FAIL ./engine - exited %d: %s" % (out.returncode, out.stderr))
else:
    got = json.loads(out.stdout)["sheets"]["Sheet1"]
    for k, v in cells.items():
        if not same(got.get(k, "<missing>"), v):
            bad += 1
            print("FAIL CLI %s: got %r, want %r" % (k, got.get(k), v))
blank = subprocess.run(["./engine", "-", "--cell", "Sheet1!Z99"], input=json.dumps(book), capture_output=True, text=True)
if blank.returncode != 0 or json.loads(blank.stdout) is not None:
    bad += 1
    print("FAIL CLI blank cell: %r" % (blank.stdout,))
if bad:
    sys.exit(1)
print("ok b1")
PY
