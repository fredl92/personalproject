#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
BRANCH="$(git branch --show-current)"
if [[ -z "$BRANCH" || "$BRANCH" == main ]]; then echo "Use a feature branch first." >&2; exit 1; fi
git push -u origin "$BRANCH"
gh pr create --draft --base main --head "$BRANCH" --title "Personal Toolkit improvements" --body-file .github/PULL_REQUEST_TEMPLATE.md
