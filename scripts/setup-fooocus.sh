#!/usr/bin/env bash
# Set up Fooocus — local Midjourney-style image generation (requires NVIDIA GPU)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FOOOCUS_DIR="${ROOT}/services/fooocus"

echo "==> Setting up Fooocus (GPU image generation)"

if ! command -v nvidia-smi &>/dev/null; then
  echo "WARNING: No NVIDIA GPU detected. Fooocus requires a CUDA-capable GPU."
  echo "         You can still clone the repo, but generation will not work on CPU-only."
  read -r -p "Continue anyway? [y/N] " ans
  [[ "${ans,,}" == "y" ]] || exit 1
fi

if [[ ! -d "${FOOOCUS_DIR}/.git" ]]; then
  git clone https://github.com/lllyasviel/Fooocus.git "${FOOOCUS_DIR}"
fi

cd "${FOOOCUS_DIR}"

if [[ -f "environment.yaml" ]] && command -v conda &>/dev/null; then
  echo "==> Creating conda environment..."
  conda env create -f environment.yaml -n fooocus || conda env update -f environment.yaml -n fooocus
  echo ""
  echo "Activate with:  conda activate fooocus"
  echo "Launch with:    python launch.py"
elif [[ -f "requirements_versions.txt" ]]; then
  VENV="${FOOOCUS_DIR}/.venv"
  python3 -m venv "${VENV}"
  # shellcheck disable=SC1091
  source "${VENV}/bin/activate"
  pip install -q --upgrade pip
  pip install -q -r requirements_versions.txt
  echo ""
  echo "Activate with:  source ${VENV}/bin/activate"
  echo "Launch with:    cd ${FOOOCUS_DIR} && python launch.py"
else
  echo "Clone complete. See ${FOOOCUS_DIR}/README.md for install instructions."
fi

echo ""
echo "Fooocus UI will be at http://localhost:7865 after launch"
