#!/usr/bin/env bash
set -euo pipefail

# Install Rust toolchain
if ! command -v cargo &>/dev/null; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
    source "$HOME/.cargo/env"
fi

# Create virtualenv if it doesn't exist
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi

# Install Python dependencies
.venv/bin/pip install maturin torch gymnasium fastapi "uvicorn[standard]" pyyaml jsonschema httpx

# Build the Rust extension
source "$HOME/.cargo/env"
.venv/bin/maturin develop --release

echo "Bootstrap complete. Activate with: source .venv/bin/activate"
