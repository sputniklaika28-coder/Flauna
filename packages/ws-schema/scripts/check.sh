#!/usr/bin/env bash
# Idempotency check: re-generate and diff
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENERATED_DIR="$SCRIPT_DIR/../src/generated"
SCHEMAS_DIR="$SCRIPT_DIR/../schemas"

# Create temp copies
TMP=$(mktemp -d)
cp -r "$GENERATED_DIR" "$TMP/generated_before"
cp -r "$SCHEMAS_DIR" "$TMP/schemas_before"

# Re-run generation
bash "$SCRIPT_DIR/generate.sh"

# Diff
if ! diff -r --brief "$TMP/generated_before" "$GENERATED_DIR" > /dev/null 2>&1; then
  echo "[ws-schema] ERROR: Generated TypeScript is out of date. Run 'pnpm --filter @tacex/ws-schema generate'." >&2
  rm -rf "$TMP"
  exit 1
fi

if ! diff -r --brief "$TMP/schemas_before" "$SCHEMAS_DIR" > /dev/null 2>&1; then
  echo "[ws-schema] ERROR: JSON Schemas are out of date. Run 'pnpm --filter @tacex/ws-schema generate'." >&2
  rm -rf "$TMP"
  exit 1
fi

rm -rf "$TMP"
echo "[ws-schema] OK: generated files are up to date."
