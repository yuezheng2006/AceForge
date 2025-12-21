#!/bin/bash
# ---------------------------------------------------------------------------
#  AceForge - Terminal Launcher Wrapper
#  This script opens Terminal.app and runs the launch_in_terminal.sh script
#  This is the actual executable that gets placed as "AceForge" in MacOS/
# ---------------------------------------------------------------------------

# Get the directory where this script lives (Contents/MacOS/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCH_SCRIPT="${SCRIPT_DIR}/launch_in_terminal.sh"

# Check if launch script exists
if [ ! -f "$LAUNCH_SCRIPT" ]; then
    echo "Error: launch_in_terminal.sh not found at $LAUNCH_SCRIPT"
    exit 1
fi

# Use heredoc to safely pass the directory path to AppleScript
# This avoids issues with special characters in paths
osascript <<EOF
tell application "Terminal"
    do script "cd $(printf %q "$SCRIPT_DIR") && exec './launch_in_terminal.sh'"
    activate
end tell
EOF

exit 0
