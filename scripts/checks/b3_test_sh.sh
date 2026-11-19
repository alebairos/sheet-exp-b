#!/bin/sh
set -e
cd "$(dirname "$0")/../.."
out=$(./test.sh 2>&1) || { echo "$out" >&2; echo "./test.sh failed" >&2; exit 1; }
echo "$out" | grep -q "no tests yet" && { echo "./test.sh still the seed stub" >&2; exit 1; }
# Must have exercised a real suite: scripts/test exists and is executable (test.sh delegates to it)
test -x ./scripts/test || { echo "missing ./scripts/test (./test.sh must run a real suite)" >&2; exit 1; }
