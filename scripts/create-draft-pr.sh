#!/usr/bin/env bash
# Push branch and open draft PR to fredl92/personalproject
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

BRANCH="${1:-cursor/personal-toolkit-8ae4}"
REMOTE="https://github.com/fredl92/personalproject.git"
BODY_FILE="${ROOT}/.github/PULL_REQUEST_TEMPLATE.md"

if ! gh auth status &>/dev/null; then
  echo "Not logged into GitHub. Run:" >&2
  echo "  gh auth login -h github.com -p https -w" >&2
  exit 1
fi

git remote remove origin 2>/dev/null || true
git remote add origin "${REMOTE}"
git checkout "${BRANCH}" 2>/dev/null || git checkout -b "${BRANCH}"

echo "Pushing ${BRANCH} ..."
git push -u origin "${BRANCH}"

echo "Creating draft pull request ..."
gh pr create \
  --repo fredl92/personalproject \
  --base main \
  --head "${BRANCH}" \
  --title "Add personal open-source toolkit (yt-dlp, Ollama, Whisper, n8n, Penpot)" \
  --body-file "${BODY_FILE}" \
  --draft

echo ""
gh pr view --repo fredl92/personalproject --web 2>/dev/null || gh pr view --repo fredl92/personalproject
