#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCHEMA_OUT="$SCRIPT_DIR/../schemas"

mkdir -p "$SCHEMA_OUT"

cd "$REPO_ROOT/apps/gm"
uv run python tools/export_schemas.py --out "$SCHEMA_OUT"

echo "Schema generation complete: $SCHEMA_OUT"
