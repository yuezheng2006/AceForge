#!/usr/bin/env bash
# Build the new UI (React/Vite) for AceForge. Output: ui/dist/
# Run from repo root. Requires Bun (https://bun.sh).

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
UI_DIR="$REPO_ROOT/ui"

if [ ! -f "$UI_DIR/package.json" ]; then
  echo "ERROR: ui/package.json not found. Run from repo root after copying UI source into ui/." >&2
  exit 1
fi

if ! command -v bun &> /dev/null; then
  echo "ERROR: Bun not found. Install from https://bun.sh" >&2
  exit 1
fi

cd "$UI_DIR"
bun install --frozen-lockfile 2>/dev/null || bun install
bun run build

if [ ! -f "$UI_DIR/dist/index.html" ]; then
  echo "ERROR: UI build did not produce ui/dist/index.html" >&2
  exit 1
fi
echo "UI build OK: $UI_DIR/dist/"
