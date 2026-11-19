#!/bin/sh
set -e
cd "$(dirname "$0")/../.."
test -x ./engine || { echo "missing executable ./engine" >&2; exit 1; }
input='{"sheets":{"Sheet1":{"A1":1,"A2":"text"}}}'
got=$(printf '%s' "$input" | ./engine - --cell Sheet1!A1)
# one JSON value: the number 1
python3 - "$got" <<'PY'
import json, sys
v = json.loads(sys.argv[1])
if v != 1:
    print("expected 1, got", v, file=sys.stderr)
    sys.exit(1)
PY
