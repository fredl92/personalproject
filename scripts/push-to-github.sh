#!/usr/bin/env bash
# Compatibility helper: never rename branches, rewrite history, or change remotes.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
BRANCH="$(git branch --show-current)"
if [[ -z "$BRANCH" || "$BRANCH" == main ]]; then
  echo "Use a feature branch and a pull request." >&2; exit 1
fi
git push -u origin "$BRANCH"
