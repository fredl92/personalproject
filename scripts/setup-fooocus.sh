#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${ROOT}/services/fooocus"
if [[ "$(uname -s)" != Darwin ]] && ! command -v nvidia-smi >/dev/null; then
  echo "This optional installer supports Apple Silicon (MPS) or Linux with NVIDIA. CPU-only installation is not automatic." >&2
  exit 1
fi
if [[ "$(uname -s)" == Darwin && "$(uname -m)" != arm64 ]]; then
  echo "This Mac installer targets Apple Silicon. Intel Macs require a separate setup." >&2; exit 1
fi
if [[ ! -d "${DEST}/.git" ]]; then
  git clone --depth 1 --branch v2.5.5 https://github.com/lllyasviel/Fooocus.git "$DEST"
fi
# Preserve existing installs/models; never reset or update someone else's checkout.
if [[ ! -f "${DEST}/entry_with_update.py" ]]; then echo "Existing Fooocus checkout is incomplete." >&2; exit 1; fi
if [[ ! -d "${DEST}/.venv" ]]; then python3 -m venv "${DEST}/.venv"; fi
"${DEST}/.venv/bin/python" -m pip install -r "${DEST}/requirements_versions.txt"
if [[ "$(uname -s)" == Darwin ]]; then
  "${DEST}/.venv/bin/python" -c 'import torch; assert torch.backends.mps.is_available(), "MPS unavailable; check the Python/PyTorch installation"'
fi
printf '\nLaunch on demand:\n  cd %q && .venv/bin/python entry_with_update.py\n' "$DEST"
echo "Fooocus has limited maintenance; Mac speed/quality must be tested on your own hardware."
