#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"

echo "==> Running schema generation for drift check..."
bash "$REPO_ROOT/packages/ws-schema/scripts/generate.sh"

echo "==> Checking for uncommitted schema drift..."
if ! git -C "$REPO_ROOT" diff --exit-code packages/ws-schema/ > /dev/null 2>&1; then
  echo "ERROR: Schema drift detected in packages/ws-schema/"
  echo "Run 'bash packages/ws-schema/scripts/generate.sh' and commit the result."
  git -C "$REPO_ROOT" diff --stat packages/ws-schema/
  exit 1
fi

echo "==> OK: packages/ws-schema/ is up to date."
