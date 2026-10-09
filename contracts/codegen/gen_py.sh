#!/usr/bin/env bash
# Generates pipeline/strata_pipeline/contracts.py from contracts/schemas/strata.schema.json.
# Do not hand-edit the output — see CLAUDE.md §2. Regenerate with `make contracts`.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

OUT=pipeline/strata_pipeline/contracts.py

uv run --project pipeline datamodel-codegen \
  --input contracts/schemas/strata.schema.json \
  --input-file-type jsonschema \
  --output "$OUT" \
  --output-model-type pydantic_v2.BaseModel \
  --target-python-version 3.11 \
  --use-schema-description \
  --use-field-description \
  --enum-field-as-literal all \
  --use-standard-collections \
  --use-union-operator \
  --field-constraints \
  --disable-timestamp

{
  echo '"""'
  echo "GENERATED FILE — do not hand-edit. Source: contracts/schemas/strata.schema.json"
  echo "Regenerate with \`make contracts\` (contracts/codegen/gen_py.sh)."
  echo '"""'
  echo
  cat "$OUT"
} > "$OUT.tmp"
mv "$OUT.tmp" "$OUT"

echo "wrote $OUT"
