#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
GM_DIR="$REPO_ROOT/apps/gm"
WS_SCHEMA_DIR="$REPO_ROOT/packages/ws-schema"

echo "==> Exporting JSON Schemas from Pydantic..."
cd "$GM_DIR"
uv run python tools/export_schemas.py
cd "$REPO_ROOT"

echo "==> Generating TypeScript types from JSON Schema..."
# Run from ws-schema directory so ESM imports resolve against its node_modules
cd "$WS_SCHEMA_DIR"
node --input-type=module <<'JSEOF'
import { compileFromFile } from 'json-schema-to-typescript';
import { writeFileSync } from 'fs';

const header = '// AUTO-GENERATED — do not edit manually. Run: bash packages/ws-schema/scripts/generate.sh\n\n';
const [client, server] = await Promise.all([
  compileFromFile('./schemas/client_message.json', { additionalProperties: false }),
  compileFromFile('./schemas/server_message.json', { additionalProperties: false }),
]);
writeFileSync('./ts/generated.ts', header + client + '\n' + server);
console.log('Generated ts/generated.ts');
JSEOF
cd "$REPO_ROOT"

echo "==> Generating error_codes.ts..."
cd "$WS_SCHEMA_DIR"
node --input-type=module <<'JSEOF'
import { readFileSync, writeFileSync } from 'fs';
const data = JSON.parse(readFileSync('./schemas/error_codes.json', 'utf8'));
const codes = data.error_codes;
const enumLines = codes.map(c => `  ${c} = "${c}",`).join('\n');
const ts = `// AUTO-GENERATED — do not edit manually. Run: bash packages/ws-schema/scripts/generate.sh
export enum ErrorCode {\n${enumLines}\n}

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
writeFileSync('./ts/error_codes.ts', ts);
console.log('Generated ts/error_codes.ts');
JSEOF
cd "$REPO_ROOT"

echo "==> Done. Schema artifacts updated in packages/ws-schema/"
