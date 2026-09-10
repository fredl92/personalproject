#!/usr/bin/env bash
# Append the toolkit bin directory to the user's shell PATH once.
# If the marker already exists but points at another install, update that line.
set -euo pipefail
ROOT="${1:?Usage: register-path.sh <toolkit-root>}"
if [[ -z "${HOME:-}" ]]; then
  echo "HOME is unset; add ${ROOT}/bin to PATH yourself." >&2
  exit 0
fi
case "${SHELL:-/bin/bash}" in
  */zsh) SHELL_RC="${HOME}/.zshrc" ;;
  */bash)
    if [[ "$(uname -s)" == Darwin ]]; then SHELL_RC="${HOME}/.bash_profile"
    else SHELL_RC="${HOME}/.bashrc"
    fi
    ;;
  *) SHELL_RC="${HOME}/.profile" ;;
esac
MARKER='# Personal Toolkit PATH'
BIN_PATH="${ROOT}/bin"
EXPORT_LINE="export PATH=$(printf '%q' "$BIN_PATH"):\"\$PATH\""
touch "$SHELL_RC"
if grep -Fq "$MARKER" "$SHELL_RC"; then
  if grep -Fq "$EXPORT_LINE" "$SHELL_RC"; then
    exit 0
  fi
  tmp="$(mktemp "${SHELL_RC}.toolkitpath.XXXXXX")"
  TOOLKIT_PATH_MARKER="$MARKER" TOOLKIT_PATH_EXPORT="$EXPORT_LINE" awk '
    $0 == ENVIRON["TOOLKIT_PATH_MARKER"] {
      print
      if ((getline nextline) > 0) {
        if (nextline ~ /^export PATH=/) { print ENVIRON["TOOLKIT_PATH_EXPORT"]; next }
        print ENVIRON["TOOLKIT_PATH_EXPORT"]
        print nextline
        next
      }
      print ENVIRON["TOOLKIT_PATH_EXPORT"]
      next
    }
    { print }
  ' "$SHELL_RC" > "$tmp"
  mv "$tmp" "$SHELL_RC"
  echo "Updated ${BIN_PATH} in PATH in ${SHELL_RC}. Open a new terminal to use pt."
  exit 0
fi
{ printf '\n%s\n' "$MARKER"; printf '%s\n' "$EXPORT_LINE"; } >> "$SHELL_RC"
echo "Added ${BIN_PATH} to PATH in ${SHELL_RC}. Open a new terminal to use pt."
