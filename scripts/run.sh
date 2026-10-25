#!/usr/bin/env bash
# Build whatever is missing or stale, then run the project.
#
# Usage:
#   bash scripts/run.sh             # start the web UI on http://127.0.0.1:8000
#   bash scripts/run.sh test        # run Rust + Python test suites
#   bash scripts/run.sh --rebuild   # force a rebuild of the Rust extension first
#
# Env: PORT (default 8000), HOST (default 127.0.0.1)
set -euo pipefail

cd "$(dirname "$0")/.."

MODE=web
FORCE_BUILD=0
for arg in "$@"; do
    case "$arg" in
        web|test)  MODE="$arg" ;;
        --rebuild) FORCE_BUILD=1 ;;
        -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
        *) echo "unknown option: $arg" >&2; exit 1 ;;
    esac
done

# Fresh checkout (or after clean.sh --venv): full setup incl. dependencies + build.
[ -f "$HOME/.cargo/env" ] && source "$HOME/.cargo/env"
if [ ! -x .venv/bin/maturin ] || ! command -v cargo &>/dev/null; then
    echo "[run] environment incomplete — running bootstrap.sh"
    bash scripts/bootstrap.sh
    source "$HOME/.cargo/env"
fi

# Rebuild the extension if it is missing or older than any Rust source.
so=$(ls python/cod_sim/*.so 2>/dev/null | head -n1 || true)
if [ "$FORCE_BUILD" -eq 1 ] || [ -z "$so" ] || \
   [ -n "$(find cod_sim Cargo.toml Cargo.lock pyproject.toml -newer "$so" -type f -print -quit)" ]; then
    echo "[run] building Rust extension"
    .venv/bin/maturin develop --release
fi

case "$MODE" in
    web)
        if ! ls checkpoints/checkpoint_*.pt &>/dev/null; then
            echo "[run] note: no trained policy in checkpoints/ — AI will be unavailable" \
                 "(train with: .venv/bin/python scripts/train.py)"
        fi
        exec .venv/bin/python -m uvicorn cod_sim.api.main:app \
            --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
        ;;
    test)
        cargo test -p cod_sim
        .venv/bin/python -m pytest tests/python/ -q
        ;;
esac
