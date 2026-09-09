#!/usr/bin/env bash
# Copy application code without deleting or bundling any user state.
set -euo pipefail
SOURCE="${1:?Usage: copy-toolkit.sh <source> <destination>}"
DEST="${2:?Usage: copy-toolkit.sh <source> <destination>}"
if ! command -v rsync >/dev/null; then
  echo "rsync is required to copy toolkit files. macOS includes it; on Linux install rsync and rerun." >&2
  exit 1
fi
mkdir -p "$DEST"
# Allowlist source files. services/, data/, .env, models and user files are untouched.
for item in bin src scripts macos config workflows docker docs tests dashboard .github \
            README.md LICENSE VERSION Makefile pyproject.toml requirements.txt \
            docker-compose.yml .env.example .gitignore .dockerignore; do
  if [[ -e "${SOURCE}/${item}" ]]; then
    if [[ -d "${SOURCE}/${item}" ]]; then
      mkdir -p "${DEST}/${item}"
      exclusions=(--exclude '__pycache__' --exclude '*.pyc')
      if [[ "$item" == dashboard ]]; then exclusions+=(--exclude 'config.js' --exclude 'status-proxy.conf'); fi
      rsync -a "${exclusions[@]}" "${SOURCE}/${item}/" "${DEST}/${item}/"
    else
      cp "${SOURCE}/${item}" "${DEST}/${item}"
    fi
  fi
done
