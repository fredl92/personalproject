#!/usr/bin/env bash
# Push to https://github.com/fredl92/personalproject
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

REMOTE="${GITHUB_REMOTE:-https://github.com/fredl92/personalproject.git}"

if ! gh auth status &>/dev/null; then
  echo "Not logged into GitHub. Run:" >&2
  echo "  gh auth login -h github.com -p https -w" >&2
  exit 1
fi

git remote remove origin 2>/dev/null || true
git remote add origin "${REMOTE}"
git branch -M main

echo "Pushing to ${REMOTE} ..."
git push -u origin main --force-with-lease

echo ""
echo "Done: https://github.com/fredl92/personalproject"
