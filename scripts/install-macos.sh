#!/usr/bin/env bash
# Installs the local core only. Docker/Node/design tools are opt-in.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if ! command -v brew >/dev/null; then
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  else
    echo "Install Homebrew from https://brew.sh, then rerun this installer." >&2
    exit 1
  fi
fi
brew install ffmpeg python@3.12 ollama
PYTHON="$(brew --prefix python@3.12)/bin/python3.12"
if [[ ! -d "${ROOT}/.venv" ]]; then "$PYTHON" -m venv "${ROOT}/.venv"; fi
"${ROOT}/.venv/bin/python" -m pip install -r "${ROOT}/requirements.txt"
bash "${ROOT}/bin/pt" init
brew services start ollama
READY=0
for attempt in {1..30}; do
  if OLLAMA_HOST=127.0.0.1:11434 ollama list >/dev/null 2>&1; then READY=1; break; fi
  sleep 1
done
if [[ "$READY" != 1 ]]; then echo "Ollama did not become ready. Check brew services info ollama." >&2; exit 1; fi
OLLAMA_HOST=127.0.0.1:11434 ollama pull "$(bash "${ROOT}/bin/pt" model)"
# Register only the current shell, without overwriting existing configuration.
case "${SHELL:-/bin/zsh}" in
  */bash) SHELL_RC="${HOME}/.bash_profile" ;;
  *) SHELL_RC="${HOME}/.zshrc" ;;
esac
MARKER='# Personal Toolkit PATH'
if ! grep -Fq "$MARKER" "$SHELL_RC" 2>/dev/null; then
  { printf '\n%s\n' "$MARKER"; printf 'export PATH=%q:"$PATH"\n' "${ROOT}/bin"; } >> "$SHELL_RC"
fi
bash "${ROOT}/bin/pt" doctor
echo "Core ready. Open a new Terminal window to use pt."
echo "Optional modules: pt services up automation / pt services up design"
