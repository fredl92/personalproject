#!/usr/bin/env bash
# Append the toolkit bin directory to the user's shell PATH once.
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
if grep -Fq "$MARKER" "$SHELL_RC" 2>/dev/null; then
  exit 0
fi
touch "$SHELL_RC"
{ printf '\n%s\n' "$MARKER"; printf 'export PATH=%q:"$PATH"\n' "${ROOT}/bin"; } >> "$SHELL_RC"
echo "Added ${ROOT}/bin to PATH in ${SHELL_RC}. Open a new terminal to use pt."
