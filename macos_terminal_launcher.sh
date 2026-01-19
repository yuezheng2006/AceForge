#!/bin/bash
# ---------------------------------------------------------------------------
#  AceForge - Terminal Launcher Wrapper
#  This script opens Terminal.app and runs the launch_in_terminal.sh script
#  This is the actual executable that gets placed as "AceForge" in MacOS/
#  
#  The wrapper stays alive to keep the app visible in the dock, and monitors
#  the actual server process to exit gracefully when it's done.
# ---------------------------------------------------------------------------

# Get the directory where this script lives (Contents/MacOS/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCH_SCRIPT="${SCRIPT_DIR}/launch_in_terminal.sh"

# Check if launch script exists
if [ ! -f "$LAUNCH_SCRIPT" ]; then
    echo "Error: launch_in_terminal.sh not found at $LAUNCH_SCRIPT"
    exit 1
fi

# Create a marker file to track if we launched the Terminal
MARKER_FILE="/tmp/aceforge_launcher_$$"
touch "$MARKER_FILE"

# Cleanup function to remove marker file on exit
cleanup() {
    rm -f "$MARKER_FILE"
}
trap cleanup EXIT

# Launch Terminal with our script using AppleScript
osascript <<EOF
tell application "Terminal"
    do script "cd $(printf %q "$SCRIPT_DIR") && exec './launch_in_terminal.sh'"
    activate
end tell
EOF

# Give the process a moment to start
sleep 2

# Keep this process alive to maintain app visibility in the dock
# We monitor the AceForge_bin process and exit when it's done
while [ -f "$MARKER_FILE" ]; do
    # Check if AceForge_bin is running
    if pgrep -f "AceForge_bin" > /dev/null 2>&1; then
        # Process is running, continue waiting
        sleep 3
    else
        # Process not found - check if it's still starting up or has finished
        # Wait a bit longer to distinguish between "not started yet" and "finished"
        sleep 3
        if ! pgrep -f "AceForge_bin" > /dev/null 2>&1; then
            # Still not running after grace period - it likely finished or failed
            # Check if we've been running for at least 10 seconds (enough for startup)
            if [ $SECONDS -gt 10 ]; then
                # We've been running long enough, process has ended
                break
            fi
        fi
    fi
done

exit 0
