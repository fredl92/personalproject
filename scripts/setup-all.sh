#!/usr/bin/env bash
# Kept for compatibility: setup now installs the core; modules are opt-in.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "${ROOT}/scripts/install-cli.sh"
