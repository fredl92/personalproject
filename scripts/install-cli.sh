#!/usr/bin/env bash
# Install CLI tools: yt-dlp, Ollama, faster-whisper (Whisper)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${ROOT}/.venv"

echo "==> Installing CLI tools for Personal Toolkit"
echo "    Root: ${ROOT}"

# ── System deps ──────────────────────────────────────────────────────────────
if command -v apt-get &>/dev/null; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq ffmpeg curl ca-certificates python3-venv python3-pip zstd >/dev/null
fi

# ── Python venv (Whisper + yt-dlp) ────────────────────────────────────────────
if [[ ! -d "${VENV}" ]]; then
  python3 -m venv "${VENV}"
fi
# shellcheck disable=SC1091
source "${VENV}/bin/activate"
pip install -q --upgrade pip
pip install -q yt-dlp faster-whisper

echo "    ✓ yt-dlp $(yt-dlp --version)"
echo "    ✓ faster-whisper installed"

# ── Ollama ───────────────────────────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
  echo "==> Installing Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
else
  echo "    ✓ Ollama already installed"
fi

# ── Pull a default model (small, fast) ───────────────────────────────────────
if command -v ollama &>/dev/null; then
  if ! ollama list 2>/dev/null | grep -q "llama3.2"; then
    echo "==> Pulling default Ollama model (llama3.2:3b)..."
    ollama pull llama3.2:3b || echo "    (skipped — start Ollama service first: ollama serve)"
  fi
fi

# ── Directories ──────────────────────────────────────────────────────────────
mkdir -p "${ROOT}/downloads" "${ROOT}/transcripts" "${ROOT}/generated"

echo ""
echo "Done! Activate the venv with:  source ${VENV}/bin/activate"
echo "Or use the unified CLI:         ./bin/pt --help"
