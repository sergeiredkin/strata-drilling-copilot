#!/usr/bin/env bash
# Copy lint — docs/05_DESIGN_SYSTEM.md §9 ("Copy lint"), T10.3.
#
# Forbidden phrases list is exactly what §9 enumerates. "any vendor product name" is NOT checked
# here: §9 gives no list of names to check against, and inventing one would mean blocklisting
# real company names on no authority — that needs a list from Sergei (or a manual review pass),
# not a guess baked into CI.
set -euo pipefail

cd "$(dirname "$0")/.."

FORBIDDEN=(
  "autopilot"
  "optimal setpoint"
  "recommended WOB"
  "recommended RPM"
  "guaranteed"
  "% NPT reduction"
  "fleet-wide"
  "AI-powered"
)

fail=0

for phrase in "${FORBIDDEN[@]}"; do
  if matches=$(grep -rniE --include="*.ts" --include="*.tsx" -- "$phrase" src); then
    echo "copy-lint: forbidden phrase \"$phrase\" found:"
    echo "$matches" | sed 's/^/  /'
    fail=1
  fi
done

# "Best parameter window" must always be accompanied by the word "advisory" on the same line.
if matches=$(grep -rniE --include="*.ts" --include="*.tsx" -- "best parameter window" src); then
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    if ! echo "$line" | grep -qiE "advisory"; then
      echo "copy-lint: \"best parameter window\" without \"advisory\" on the same line:"
      echo "  $line"
      fail=1
    fi
  done <<< "$matches"
fi

if [ "$fail" -eq 0 ]; then
  echo "copy-lint: clean"
fi
exit $fail
