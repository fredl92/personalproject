#!/usr/bin/env bash
# Build Personal-Toolkit.dmg — native on macOS, ISO fallback on Linux
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${VERSION:-1.0.0}"
DIST="${ROOT}/dist"
STAGING="${DIST}/dmg-staging"
APP_NAME="PersonalToolkit-Installer.app"
DMG_NAME="Personal-Toolkit-${VERSION}.dmg"
DMG_PATH="${DIST}/${DMG_NAME}"

echo "==> Building ${DMG_NAME}"

rm -rf "${STAGING}"
mkdir -p "${STAGING}" "${DIST}"

# ── Bundle toolkit inside the installer app ───────────────────────────────────
APP_STAGING="${STAGING}/${APP_NAME}"
mkdir -p "${APP_STAGING}/Contents/MacOS" "${APP_STAGING}/Contents/Resources"

cp "${ROOT}/macos/${APP_NAME}/Contents/Info.plist" "${APP_STAGING}/Contents/"
cp "${ROOT}/macos/${APP_NAME}/Contents/MacOS/install" "${APP_STAGING}/Contents/MacOS/"
chmod +x "${APP_STAGING}/Contents/MacOS/install"

TOOLKIT_DEST="${APP_STAGING}/Contents/Resources/toolkit"
mkdir -p "${TOOLKIT_DEST}"

rsync -a \
  --exclude '.git' --exclude '.venv' --exclude 'dist' --exclude 'downloads' \
  --exclude 'transcripts' --exclude 'generated' --exclude '.env' \
  --exclude 'assets' --exclude 'agent-tools' \
  "${ROOT}/" "${TOOLKIT_DEST}/"

# ── DMG window contents ───────────────────────────────────────────────────────
cp "${ROOT}/macos/INSTALL.txt" "${STAGING}/README.txt"
cp "${ROOT}/README.md" "${STAGING}/README.md"
ln -sf /Applications "${STAGING}/Applications"

# ── Create disk image ─────────────────────────────────────────────────────────
rm -f "${DMG_PATH}"

if [[ "$(uname -s)" == "Darwin" ]] && command -v hdiutil &>/dev/null; then
  echo "    Using hdiutil (macOS native DMG)..."

  # Writable scratch image, then compress to UDZO
  SCRATCH="${DIST}/scratch.dmg"
  rm -f "${SCRATCH}"
  hdiutil create -size 200m -fs HFS+ -volname "Personal Toolkit" "${SCRATCH}" -ov -quiet
  MOUNT="$(hdiutil attach -nobrowse -readwrite "${SCRATCH}" | awk 'END {print $3}')"
  trap 'hdiutil detach "$MOUNT" -quiet 2>/dev/null || true' EXIT

  cp -R "${STAGING}/"* "${MOUNT}/"
  sync

  hdiutil detach "${MOUNT}" -quiet
  hdiutil convert "${SCRATCH}" -format UDZO -imagekey zlib-level=9 -o "${DMG_PATH}" -quiet
  rm -f "${SCRATCH}"
  trap - EXIT

elif [[ "${FORCE_LINUX_DMG:-}" == "1" ]] && command -v genisoimage &>/dev/null; then
  echo "    WARNING: Linux DMG is a preview ISO — build on macOS for a working installer."
  genisoimage -V "Personal Toolkit" -D -R -apple -joliet-long -no-pad \
    -o "${DMG_PATH}" "${STAGING}/"

elif [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: Native DMG requires macOS (uses hdiutil)." >&2
  echo "" >&2
  echo "  On your Mac, run:" >&2
  echo "    make dmg" >&2
  echo "  Or double-click: macos/Build-DMG.command" >&2
  echo "" >&2
  echo "  Staged files are at: ${STAGING}" >&2
  exit 1

else
  echo "ERROR: hdiutil not found." >&2
  exit 1
fi

# ── Checksum ──────────────────────────────────────────────────────────────────
if command -v shasum &>/dev/null; then
  shasum -a 256 "${DMG_PATH}" | tee "${DMG_PATH}.sha256"
elif command -v sha256sum &>/dev/null; then
  sha256sum "${DMG_PATH}" | tee "${DMG_PATH}.sha256"
fi

echo ""
echo "✓ Built: ${DMG_PATH}"
echo "  Size:  $(du -h "${DMG_PATH}" | cut -f1)"
echo ""
echo "On Mac: open ${DMG_PATH}"
echo "        Double-click 'PersonalToolkit-Installer'"
