#!/bin/sh
# Fails on base: no ./engine. Passes when constants echo in SPEC.md shape.
set -e
cd "$(dirname "$0")/../.."
test -x ./engine || { echo "missing executable ./engine" >&2; exit 1; }
input='{"sheets":{"Sheet1":{"A1":1,"A2":"text","A3":true},"Sheet2":{}}}'
got=$(printf '%s' "$input" | ./engine -)
# Compare as JSON values (key order independent)
python3 - "$got" "$input" <<'PY'
import json, sys
got, expect = json.loads(sys.argv[1]), json.loads(sys.argv[2])
if got != expect:
    print("expected", expect, file=sys.stderr)
    print("got", got, file=sys.stderr)
    sys.exit(1)
PY
