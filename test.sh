#!/bin/sh
# The whole test suite. Replace the body once the engine has tests.
set -e
[ -x ./scripts/test ] && exec ./scripts/test
echo "no tests yet"
