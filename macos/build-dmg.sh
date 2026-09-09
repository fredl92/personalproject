#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$(uname -s)" != Darwin ]] || ! command -v hdiutil >/dev/null; then
  echo "Building a native DMG requires macOS and hdiutil." >&2; exit 1
fi
VERSION="$(cat "${ROOT}/VERSION")"
DIST="${ROOT}/dist"
mkdir -p "$DIST"
STAGING="$(mktemp -d "${DIST}/dmg-staging.XXXXXX")"
trap 'rm -rf "$STAGING"' EXIT
APP="${STAGING}/PersonalToolkit-Installer.app"
mkdir -p "${APP}/Contents/MacOS" "${APP}/Contents/Resources/toolkit"
cp "${ROOT}/macos/PersonalToolkit-Installer.app/Contents/Info.plist" "${APP}/Contents/"
cp "${ROOT}/macos/PersonalToolkit-Installer.app/Contents/MacOS/install" "${APP}/Contents/MacOS/"
bash "${ROOT}/scripts/copy-toolkit.sh" "$ROOT" "${APP}/Contents/Resources/toolkit"
chmod +x "${APP}/Contents/MacOS/install"
cp "${ROOT}/macos/INSTALL.txt" "${STAGING}/README.txt"
# hdiutil sizes and populates the image directly: no parsing space-delimited mount output.
DMG="${DIST}/Personal-Toolkit-${VERSION}.dmg"
hdiutil create -srcfolder "$STAGING" -volname "Personal Toolkit" -fs HFS+ -format UDZO -ov "$DMG"
shasum -a 256 "$DMG" > "${DMG}.sha256"
echo "Built: $DMG"
