#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$(uname -s)" == "Darwin" ]]; then
  exec bash "${ROOT}/scripts/install-macos.sh"
fi
if ! command -v python3 >/dev/null || ! command -v ffmpeg >/dev/null; then
  echo "Install Python 3.10+, python3-venv and ffmpeg, then rerun make setup." >&2
  exit 1
fi
if [[ ! -d "${ROOT}/.venv" ]]; then python3 -m venv "${ROOT}/.venv"; fi
"${ROOT}/.venv/bin/python" -m pip install -r "${ROOT}/requirements.txt"
bash "${ROOT}/bin/pt" init
if command -v ollama >/dev/null; then
  OLLAMA_HOST=127.0.0.1:11434 ollama pull "$(bash "${ROOT}/bin/pt" model)"
else
  echo "Install/start Ollama from https://ollama.com, then rerun make setup." >&2
  exit 1
fi
export PATH="${ROOT}/bin:${PATH}"
bash "${ROOT}/scripts/register-path.sh" "$ROOT"
echo "This Terminal can already use pt. New windows pick PATH up from your shell config."
echo "If a new window still says pt: command not found, run:"
printf '  export PATH=%q:"$PATH"\n' "${ROOT}/bin"
bash "${ROOT}/bin/pt" doctor
