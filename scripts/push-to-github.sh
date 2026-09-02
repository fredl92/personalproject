#!/usr/bin/env bash
# Create GitHub repo and push all branches
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

REPO_NAME="${1:-personalproject}"
VISIBILITY="${2:-private}"

if ! gh auth status &>/dev/null; then
  echo "Not logged into GitHub. Run:" >&2
  echo "  gh auth login -h github.com -p https -w" >&2
  exit 1
fi

USER="$(gh api user -q .login)"
REMOTE="https://github.com/${USER}/${REPO_NAME}.git"

# Ensure main branch
git branch -M main

if gh repo view "${USER}/${REPO_NAME}" &>/dev/null; then
  echo "Repo already exists: https://github.com/${USER}/${REPO_NAME}"
  git remote remove origin 2>/dev/null || true
  git remote add origin "${REMOTE}"
else
  echo "Creating ${VISIBILITY} repo: ${USER}/${REPO_NAME}"
  gh repo create "${REPO_NAME}" \
    --"${VISIBILITY}" \
    --description "Personal open-source toolkit: yt-dlp, Ollama, Whisper, n8n, Penpot, Plausible, Fooocus" \
    --source=. \
    --remote=origin \
    --push
  echo ""
  echo "Pushed to: https://github.com/${USER}/${REPO_NAME}"
  exit 0
fi

git push -u origin main

echo ""
echo "Pushed to: https://github.com/${USER}/${REPO_NAME}"
