#!/usr/bin/env bash
# macOS installer — Homebrew + Python venv + Docker Desktop
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${ROOT}/.venv"
INSTALL_DIR="${PERSONAL_TOOLKIT_HOME:-${HOME}/PersonalToolkit}"

echo "==> Personal Toolkit — macOS setup"
echo "    Install dir: ${INSTALL_DIR}"

# ── Homebrew ─────────────────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
  echo "==> Installing Homebrew..."
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # shellcheck disable=SC1091
  if [[ -f /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -f /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
fi

echo "==> Installing dependencies via Homebrew..."
brew install yt-dlp ffmpeg python@3.12 ollama 2>/dev/null || brew install yt-dlp ffmpeg python@3.12 ollama

if ! command -v docker &>/dev/null; then
  echo "==> Installing Docker Desktop (required for n8n + Penpot)..."
  brew install --cask docker 2>/dev/null || true
  echo "    Open Docker Desktop from Applications and finish setup, then re-run setup."
fi

# ── Python venv ───────────────────────────────────────────────────────────────
if [[ ! -d "${VENV}" ]]; then
  python3 -m venv "${VENV}"
fi
# shellcheck disable=SC1091
source "${VENV}/bin/activate"
pip install -q --upgrade pip
pip install -q yt-dlp faster-whisper

echo "    ✓ yt-dlp $(yt-dlp --version)"
echo "    ✓ faster-whisper installed"

# ── Ollama service ───────────────────────────────────────────────────────────
if command -v brew &>/dev/null; then
  brew services start ollama 2>/dev/null || true
fi
sleep 2
if command -v ollama &>/dev/null; then
  if ! ollama list 2>/dev/null | grep -q "llama3.2"; then
    echo "==> Pulling default model (llama3.2:3b)..."
    OLLAMA_HOST="127.0.0.1:11434" ollama pull llama3.2:3b || true
  fi
fi

# ── Environment ──────────────────────────────────────────────────────────────
mkdir -p "${ROOT}/downloads" "${ROOT}/transcripts" "${ROOT}/generated"
if [[ ! -f "${ROOT}/.env" ]]; then
  cp "${ROOT}/.env.example" "${ROOT}/.env"
  python3 - <<'PY'
import secrets, re
from pathlib import Path
p = Path(".env")
text = p.read_text()
text = text.replace("change-me-generate-with-openssl-rand-hex-32", secrets.token_hex(32))
text = text.replace("change-me-generate-64-char-random-string", secrets.token_hex(32))
text = text.replace("change-me-generate-with-openssl-rand-base64-48", secrets.token_urlsafe(48))
text = re.sub(r"N8N_BASIC_AUTH_PASSWORD=change-me", "N8N_BASIC_AUTH_PASSWORD=changeme-local-dev", text)
p.write_text(text)
PY
fi

# ── Shell PATH ───────────────────────────────────────────────────────────────
MARKER="# Personal Toolkit"
SHELL_RC="${HOME}/.zshrc"
[[ -f "${HOME}/.bash_profile" ]] && SHELL_RC="${HOME}/.bash_profile"

if ! grep -q "${MARKER}" "${SHELL_RC}" 2>/dev/null; then
  cat >> "${SHELL_RC}" <<EOF

${MARKER}
export PERSONAL_TOOLKIT_HOME="${ROOT}"
export PATH="\${PERSONAL_TOOLKIT_HOME}/bin:\${PATH}"
alias pt="\${PERSONAL_TOOLKIT_HOME}/bin/pt"
EOF
  echo "    ✓ Added pt to ${SHELL_RC}"
fi

# ── Docker services ──────────────────────────────────────────────────────────
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
  cd "${ROOT}"
  docker compose pull -q 2>/dev/null || true
  docker compose up -d
  echo "    ✓ Docker services started (n8n + Penpot)"
else
  echo "    ⚠ Start Docker Desktop, then run: cd ${ROOT} && docker compose up -d"
fi

echo ""
echo "Setup complete!"
"${ROOT}/bin/pt" urls 2>/dev/null || true
echo ""
echo "Run:  pt ask 'Hello!'"
