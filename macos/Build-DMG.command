#!/bin/bash
# Double-click on macOS to build Personal-Toolkit.dmg
cd "$(dirname "$0")/.."
osascript -e 'display notification "Building DMG — check Terminal" with title "Personal Toolkit"'
open -a Terminal "$(pwd)/macos/build-dmg.sh"
