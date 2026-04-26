#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA_DIR="$SCRIPT_DIR/../schemas"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

cd "$REPO_ROOT/apps/gm"
uv run python tools/export_schemas.py --out "$TEMP_DIR"

if diff -r "$SCHEMA_DIR" "$TEMP_DIR" > /dev/null 2>&1; then
  echo "Schema check: OK (idempotent)"
else
  echo "Schema check: schemas are out of sync, run 'pnpm -F @tacex/ws-schema generate'"
  diff -r "$SCHEMA_DIR" "$TEMP_DIR" || true
  exit 1
fi
