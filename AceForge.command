#!/bin/bash
# AceForge Launcher
# 
# NOTE: This .command file is deprecated and no longer needed.
# 
# To launch AceForge:
# 1. Copy AceForge.app to your Applications folder (or anywhere on your Mac)
# 2. Double-click AceForge.app to launch it in Terminal
#
# The app will now automatically open in a Terminal window where you can
# see logs and control the application.
#
# If you still want to use this .command file for some reason:

# Get the directory where this script lives
cd "$(dirname "$0")" || exit 1

# Check if AceForge.app exists
if [ ! -d "AceForge.app" ]; then
    echo "Error: AceForge.app not found in this directory"
    echo "Please place AceForge.app in the same folder as this script"
    read -n 1 -s -r -p "Press any key to close..."
    exit 1
fi

echo "Launching AceForge..."
echo ""
echo "NOTE: You can also just double-click AceForge.app directly!"
echo ""

# Open the app bundle directly
open -a "$(pwd)/AceForge.app"

