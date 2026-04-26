#!/usr/bin/env bash
# Pydantic → JSON Schema → TypeScript generation pipeline
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
GM_DIR="$REPO_ROOT/apps/gm"
SCHEMA_DIR="$REPO_ROOT/packages/ws-schema/schemas"
GENERATED_DIR="$REPO_ROOT/packages/ws-schema/src/generated"

mkdir -p "$SCHEMA_DIR" "$GENERATED_DIR"

echo "[ws-schema] Exporting JSON Schemas from Pydantic models..."
cd "$GM_DIR"
uv run python tools/export_schemas.py --out "$SCHEMA_DIR"

echo "[ws-schema] Generating TypeScript types from JSON Schemas..."
cd "$REPO_ROOT/packages/ws-schema"
for schema_file in "$SCHEMA_DIR"/*.json; do
  name=$(basename "$schema_file" .json)
  npx json-schema-to-typescript "$schema_file" \
    --no-additionalProperties \
    --unreachableDefinitions \
    --out "$GENERATED_DIR/${name}.ts"
  echo "  Generated: $GENERATED_DIR/${name}.ts"
done

# Generate ErrorCode and CloseCode enums from Python source
echo "[ws-schema] Generating ErrorCode / CloseCode enums..."
uv --directory "$GM_DIR" run python - <<'PYEOF'
import sys, json
sys.path.insert(0, "src")
from tacex_gm.errors import ErrorCode, CloseCode

lines = ["// AUTO-GENERATED – do not edit by hand", ""]

lines.append("export const ErrorCode = {")
for member in ErrorCode:
    lines.append(f'  {member.name}: "{member.value}",')
lines.append("} as const;")
lines.append("export type ErrorCode = typeof ErrorCode[keyof typeof ErrorCode];")
lines.append("")

lines.append("export const CloseCode = {")
for member in CloseCode:
    lines.append(f'  {member.name}: {member.value},')
lines.append("} as const;")
lines.append("export type CloseCode = typeof CloseCode[keyof typeof CloseCode];")

out = sys.argv[1] if len(sys.argv) > 1 else "src/generated/codes.ts"
import pathlib
pathlib.Path(out).write_text("\n".join(lines) + "\n")
print(f"  Generated: {out}")
PYEOF

echo "[ws-schema] Done."
