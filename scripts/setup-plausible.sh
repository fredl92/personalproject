#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${ROOT}/services/plausible"
if [[ ! -d "${DEST}/.git" ]]; then
  git clone --depth 1 --branch v3.2.1 https://github.com/plausible/community-edition.git "$DEST"
fi
export PERSONAL_TOOLKIT_HOME="$ROOT" PYTHONPATH="${ROOT}/src"
python3 "${ROOT}/scripts/configure-plausible.py" "$DEST"
printf 'Start when needed:\n  cd %q && docker compose up -d\n' "$DEST"
echo "Open http://localhost:8000 and create the local account."
