#!/usr/bin/env bash
# Clone and configure Plausible Community Edition (privacy-first analytics)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAUSIBLE_DIR="${ROOT}/services/plausible"
VERSION="v3.2.1"

if [[ -f "${ROOT}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
fi

echo "==> Setting up Plausible Community Edition"

if [[ ! -d "${PLAUSIBLE_DIR}/.git" ]]; then
  git clone -b "${VERSION}" --single-branch \
    https://github.com/plausible/community-edition "${PLAUSIBLE_DIR}"
else
  echo "    Plausible CE already cloned at ${PLAUSIBLE_DIR}"
fi

ENV_FILE="${PLAUSIBLE_DIR}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  BASE_URL="${PLAUSIBLE_BASE_URL:-http://localhost:8000}"
  SECRET="${PLAUSIBLE_SECRET_KEY_BASE:-$(openssl rand -base64 48)}"

  cat > "${ENV_FILE}" <<EOF
BASE_URL=${BASE_URL}
SECRET_KEY_BASE=${SECRET}
HTTP_PORT=8000
DISABLE_REGISTRATION=false
EOF
  echo "    Created ${ENV_FILE}"
else
  echo "    Using existing ${ENV_FILE}"
fi

cat > "${PLAUSIBLE_DIR}/compose.override.yml" <<'EOF'
services:
  plausible:
    ports:
      - "8000:80"
EOF

echo ""
echo "Plausible is ready. Start with:"
echo "  cd ${PLAUSIBLE_DIR} && docker compose up -d"
echo "  Open http://localhost:8000 and create your account"
