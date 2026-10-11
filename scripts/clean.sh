#!/usr/bin/env bash
# Remove build artifacts and caches that can be regenerated.
#
# Usage:
#   bash scripts/clean.sh           # caches + Rust build output + built extension
#   bash scripts/clean.sh --venv    # also delete .venv (~5 GB, recreated by bootstrap.sh)
#   bash scripts/clean.sh --dry-run # show what would be removed
#
# Never touches checkpoints/, ratings.json or rulebooks/ (not cheaply regenerable).
# Rebuild afterwards with: bash scripts/run.sh  (or bash scripts/bootstrap.sh)
set -euo pipefail

cd "$(dirname "$0")/.."

DRY_RUN=0
REMOVE_VENV=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --venv)    REMOVE_VENV=1 ;;
        -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
        *) echo "unknown option: $arg" >&2; exit 1 ;;
    esac
done

targets=(target .pytest_cache python/cod_sim/*.so python/cod_sim/*.pyd)
while IFS= read -r d; do targets+=("$d"); done < <(
    find . -path ./.venv -prune -o -type d -name __pycache__ -print
)
[ "$REMOVE_VENV" -eq 1 ] && targets+=(.venv)

for t in "${targets[@]}"; do
    [ -e "$t" ] || continue
    size=$(du -sh "$t" 2>/dev/null | cut -f1)
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "would remove  $size  $t"
    else
        rm -rf "$t"
        echo "removed  $size  $t"
    fi
done
