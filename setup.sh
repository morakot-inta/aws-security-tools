#!/bin/bash
# setup.sh — Install dependencies for AWS CloudShell
set -euo pipefail

echo "[setup] Installing checkov..."
pip3 install checkov --user -q

# Add ~/.local/bin to PATH for this session if not already present
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    export PATH="$HOME/.local/bin:$PATH"
    echo "[setup] Added ~/.local/bin to PATH for this session."
    echo "[setup] To make it permanent, add this to ~/.bashrc:"
    echo "         export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo "[setup] Verifying installations..."
aws --version
python3 --version
checkov --version

echo "[setup] Done. You can now run: ./assess.sh"
