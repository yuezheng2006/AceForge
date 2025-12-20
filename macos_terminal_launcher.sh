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

# Escape the directory path for safe use in AppleScript
# Replace single quotes with '\'' to properly escape them
ESCAPED_DIR="${SCRIPT_DIR//\'/\'\\\'\'}"

# Open Terminal.app and run the launch script
# The script will stay open because launch_in_terminal.sh has a read at the end
osascript -e "tell application \"Terminal\"
    do script \"cd '$ESCAPED_DIR' && exec './launch_in_terminal.sh'\"
    activate
end tell"
