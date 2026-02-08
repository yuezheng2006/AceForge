#!/bin/bash
# ---------------------------------------------------------------------------
#  AceForge - Run locally for testing (no .app bundle)
#  Builds the React UI if needed, then starts the Flask server at http://127.0.0.1:5056
#
#  Prerequisites:
#    - Python 3.11 and dependencies. Easiest: run ./build_local.sh once to create
#      venv_build and install deps; then use this script. Or create a venv and:
#      pip install -r requirements_ace_macos.txt (plus TTS/ACE-Step as in build_local.sh).
#    - Bun (only if ui/dist is missing): https://bun.sh
#
#  Optional:
#    ACEFORGE_SKIP_UI_BUILD=1  - Skip UI build; use existing ui/dist/
# ---------------------------------------------------------------------------

set -e
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

# Build UI if needed
UI_DIR="${APP_DIR}/ui"
if [ -f "$UI_DIR/package.json" ] && [ -z "${ACEFORGE_SKIP_UI_BUILD}" ]; then
    if [ ! -f "$UI_DIR/dist/index.html" ]; then
        if ! command -v bun &> /dev/null; then
            echo "ERROR: ui/dist missing and Bun not found. Install Bun (https://bun.sh) or run: ./scripts/build_ui.sh"
            exit 1
        fi
        echo "[Run] Building UI..."
        "${APP_DIR}/scripts/build_ui.sh"
    fi
fi

# Prefer venv from full build
VENV_PY="${APP_DIR}/venv_build/bin/python"
if [ -x "$VENV_PY" ]; then
    PY="$VENV_PY"
    echo "[Run] Using venv_build"
else
    PY="python3"
    echo "[Run] Using system python3 (install deps in a venv if you see ModuleNotFoundError)"
fi

echo "[Run] Starting AceForge at http://127.0.0.1:5056"
echo ""
exec "$PY" music_forge_ui.py
