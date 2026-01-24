#!/bin/bash
# Test script to capture voice cloning crash logs

set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

LOGFILE="/tmp/aceforge_voice_clone_crash_$(date +%s).log"
APP_BINARY="dist/AceForge.app/Contents/MacOS/AceForge_bin"

echo "=========================================="
echo "AceForge Voice Cloning Crash Test"
echo "=========================================="
echo ""
echo "Log file: $LOGFILE"
echo ""
echo "Instructions:"
echo "1. The app will launch now"
echo "2. Navigate to the 'Voice Cloning' tab"
echo "3. Click 'Choose File' or select a file in the 'Reference Audio File' input"
echo "4. The app should crash - check the log file for errors"
echo ""
echo "To monitor logs in real-time:"
echo "  tail -f $LOGFILE"
echo ""
echo "Press Ctrl+C to stop monitoring after the crash"
echo ""
echo "=========================================="
echo ""

# Remove quarantine attributes
xattr -cr "dist/AceForge.app" 2>/dev/null || true

# Launch app with full logging
"$APP_BINARY" 2>&1 | tee "$LOGFILE" &
APP_PID=$!

echo "App started (PID: $APP_PID)"
echo "Logging to: $LOGFILE"
echo ""

# Monitor the app
while ps -p $APP_PID > /dev/null 2>&1; do
    sleep 1
done

echo ""
echo "=========================================="
echo "App has exited/crashed"
echo "=========================================="
echo ""
echo "Last 50 lines of log:"
echo "----------------------------------------"
tail -50 "$LOGFILE"
echo ""
echo "Full log available at: $LOGFILE"
