#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
rom_path="${1:-}"
if [[ -z "${rom_path}" || ! -f "${rom_path}" ]]; then
    echo "Usage: $0 path/to/Tetris-v1.1.gb" >&2
    exit 2
fi
python3 "${repo_root}/tools/gbre_scenario.py" run-all --tag music --rom "${rom_path}"
