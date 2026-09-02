#!/usr/bin/env bash
# Full setup: CLI tools + Docker services + optional Plausible
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Personal Open-Source Toolkit — Setup                    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 1. Environment file
if [[ ! -f .env ]]; then
  cp .env.example .env
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
  echo "✓ Created .env (review and set passwords before exposing to network)"
fi

# 2. CLI tools
bash scripts/install-cli.sh

# 3. Docker (if available)
if command -v docker &>/dev/null; then
  mkdir -p downloads transcripts generated
  docker compose pull -q 2>/dev/null || true
  docker compose up -d
  echo "✓ Docker services started (n8n + Penpot)"
else
  echo "⚠ Docker not found — install Docker to run n8n and Penpot"
  echo "  Ubuntu: curl -fsSL https://get.docker.com | sh"
fi

# 4. Optional: Plausible
if [[ "${SETUP_PLAUSIBLE:-}" == "y" ]] || [[ "${SETUP_PLAUSIBLE:-}" == "Y" ]]; then
  bash scripts/setup-plausible.sh
elif [[ -t 0 ]]; then
  read -r -p "Set up Plausible analytics? [y/N] " setup_plausible
  if [[ "${setup_plausible,,}" == "y" ]]; then
    bash scripts/setup-plausible.sh
  fi
fi

chmod +x bin/pt scripts/*.sh

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Setup complete!"
echo ""
./bin/pt urls
echo ""
echo "Quick start:"
echo "  ./bin/pt download <url>"
echo "  ./bin/pt ask 'Hello!'"
echo "  ./bin/pt services up"
