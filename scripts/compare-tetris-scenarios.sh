#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
rom_path="${1:-}"
if [[ -z "${rom_path}" || ! -f "${rom_path}" ]]; then
    echo "Usage: $0 path/to/Tetris-v1.1.gb" >&2
    exit 2
fi

for scenario in \
    tetris.start-type-b \
    tetris.menu-traversal \
    tetris.type-a-controls \
    tetris.attract-cycle \
    tetris.rocket-large \
    tetris.buran-height-five
do
    python3 "${repo_root}/tools/gbre_scenario.py" run "${scenario}" --rom "${rom_path}"
done
