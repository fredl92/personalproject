#!/usr/bin/env bash
# Create GitHub repo and push all branches
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

REPO_NAME="${1:-personal-toolkit}"
VISIBILITY="${2:-private}"

if ! gh auth status &>/dev/null; then
  echo "Not logged into GitHub. Run:" >&2
  echo "  gh auth login -h github.com -p https -w" >&2
  exit 1
fi

USER="$(gh api user -q .login)"
REMOTE="https://github.com/${USER}/${REPO_NAME}.git"

if gh repo view "${USER}/${REPO_NAME}" &>/dev/null; then
  echo "Repo already exists: https://github.com/${USER}/${REPO_NAME}"
else
  echo "Creating ${VISIBILITY} repo: ${USER}/${REPO_NAME}"
  gh repo create "${REPO_NAME}" --"${VISIBILITY}" --description "Personal open-source toolkit: yt-dlp, Ollama, Whisper, n8n, Penpot, Plausible, Fooocus" --source=. --remote=origin
fi

git remote remove origin 2>/dev/null || true
git remote add origin "${REMOTE}"

# Ensure main branch exists
if ! git show-ref --verify --quiet refs/heads/main; then
  git branch -M main 2>/dev/null || git checkout -b main
fi

git push -u origin main
git push -u origin cursor/personal-toolkit-8ae4 2>/dev/null || true

echo ""
echo "Pushed to: https://github.com/${USER}/${REPO_NAME}"
