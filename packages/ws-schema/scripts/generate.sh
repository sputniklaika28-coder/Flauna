#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
GM_DIR="$REPO_ROOT/apps/gm"
SCHEMA_DIR="$REPO_ROOT/packages/ws-schema/schemas"
TS_DIR="$REPO_ROOT/packages/ws-schema/ts"

echo "==> Exporting JSON Schemas from Pydantic..."
cd "$GM_DIR"
uv run python tools/export_schemas.py
cd "$REPO_ROOT"

echo "==> Generating TypeScript types from JSON Schema..."
pnpm exec json-schema-to-typescript \
  "$SCHEMA_DIR/client_message.json" \
  "$SCHEMA_DIR/server_message.json" \
  --no-additionalProperties \
  --out "$TS_DIR/generated.ts" 2>/dev/null || \
  node -e "
    const { compileFromFile } = require('json-schema-to-typescript');
    const fs = require('fs');
    Promise.all([
      compileFromFile('$SCHEMA_DIR/client_message.json'),
      compileFromFile('$SCHEMA_DIR/server_message.json'),
    ]).then(([c, s]) => fs.writeFileSync('$TS_DIR/generated.ts', c + '\n' + s));
  "

echo "==> Generating error_codes.ts..."
node --input-type=module <<'EOF'
import { readFileSync, writeFileSync } from 'fs';
const data = JSON.parse(readFileSync('packages/ws-schema/schemas/error_codes.json', 'utf8'));
const codes = data.error_codes;
const enumLines = codes.map(c => `  ${c} = "${c}",`).join('\n');
const ts = `// AUTO-GENERATED — do not edit manually. Run: bash packages/ws-schema/scripts/generate.sh
export enum ErrorCode {\n${enumLines}\n}\n
export const CLOSE_CODES = {
  NORMAL: 1000,
  CLIENT_LEAVING: 1001,
  AUTH_FAILED: 4000,
  SESSION_LOST_TIMEOUT: 4001,
  SESSION_LOST_RESTART: 4002,
  BACK_PRESSURE: 4003,
  RATE_LIMITED: 4004,
  DUPLICATE_CONNECTION: 4005,
} as const;\n`;
writeFileSync('packages/ws-schema/ts/error_codes.ts', ts);
EOF

echo "==> Done. Schema artifacts updated in packages/ws-schema/"
