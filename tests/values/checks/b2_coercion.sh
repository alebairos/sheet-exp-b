#!/bin/sh
# b2: coercion between kinds matches Calc (LibreOffice defaults) for arithmetic and comparison.
# Contract (plan i2-values), on values built with from_json:
#   to_number(v) -> a number Value or an error Value   (arithmetic operands)
#   to_text(v)   -> a text Value or an error Value     (& operands)
#   compare(a, b) -> -1, 0 or 1, or an error Value      (= <> < > <= >=)
set -eu
cd "$(dirname "$0")/../../.."
export PYTHONDONTWRITEBYTECODE=1
python3 - <<'PY'
import sys
from src.values import from_json as v, to_json, to_number, to_text, compare
E = lambda c: {"error": c}
bad = 0
def eq(got, want):
    if isinstance(want, (int, float)) and not isinstance(want, bool):
        return type(got) in (int, float) and not isinstance(got, bool) and abs(got - want) < 1e-12
    return type(got) is type(want) and got == want
def expect(label, got, want):
    global bad
    if not eq(got, want):
        bad += 1
        print("FAIL %s: got %r, want %r" % (label, got, want))
# Arithmetic: text to number, booleans as 1 and 0, the blank cell as 0, errors pass through.
for x, want in [(3, 3), (True, 1), (False, 0), (None, 0), ("12", 12), ("-2.5", -2.5), ("1E3", 1000),
                ("abc", E("#VALUE!")), ("", E("#VALUE!")), ("TRUE", E("#VALUE!")),
                (E("#DIV/0!"), E("#DIV/0!")), (E("#N/A"), E("#N/A"))]:
    expect("to_number(%r)" % (x,), to_json(to_number(v(x))), want)
# Concatenation: numbers in Calc's general format, booleans as TRUE/FALSE, the blank cell as "".
for x, want in [("ab", "ab"), (1, "1"), (2.5, "2.5"), (-3, "-3"), (0.1 + 0.2, "0.3"),
                (True, "TRUE"), (False, "FALSE"), (None, ""), (E("#REF!"), E("#REF!"))]:
    expect("to_text(%r)" % (x,), to_json(to_text(v(x))), want)
# Comparison: numbers (booleans count as numbers in Calc) < text; text compares case-insensitively;
# the blank cell equals both 0 and ""; an error operand gives that error.
def cmp(a, b):
    r = compare(v(a), v(b))
    return r if isinstance(r, int) and not isinstance(r, bool) else to_json(r)
for a, b, want in [(1, 2, -1), (2, 2, 0), (3, 2, 1), ("a", "b", -1), ("a", "A", 0), ("B", "a", 1),
                   (1, "1", -1), ("1", 1, 1), (100, "a", -1), (True, 1, 0), (False, 0, 0),
                   (None, 0, 0), (None, "", 0), (None, 1, -1), (None, "a", -1),
                   (E("#DIV/0!"), 1, E("#DIV/0!")), (1, E("#N/A"), E("#N/A"))]:
    expect("compare(%r, %r)" % (a, b), cmp(a, b), want)
if bad:
    sys.exit(1)
print("ok b2")
PY
