#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
rom_path="${1:-}"

"${repo_root}/scripts/bootstrap-tetris-reference.sh" "${rom_path}"
python3 "${repo_root}/tools/build_rgbds_source_map.py" \
    --reference "${repo_root}/reference/tetris-disassembly" \
    --rgbds-bin "${repo_root}/.cache/rgbds-0.5.2-bin" \
    --build-dir "${repo_root}/build/tetris-v1.1-source-map" \
    --output "${repo_root}/analysis/tetris-v1.1-source-map.csv" \
    --expected-sha1 "74591cc9501af93873f9a5d3eb12da12c0723bbc" \
    --rom-size 0x8000 \
    --source tetris.asm \
    --source audio.asm \
    --source wram.asm \
    --source hram.asm \
    --source music.asm \
    --source sprites.asm
python3 "${repo_root}/tools/build_rom_map.py" \
    --manifest "${repo_root}/analysis/tetris-v1.1-manifest.json" \
    --rgbds-map "${repo_root}/reference/tetris-disassembly/tetris.map" \
    --rgbds-sym "${repo_root}/reference/tetris-disassembly/tetris.sym" \
    --source-map "${repo_root}/analysis/tetris-v1.1-source-map.csv" \
    --output "${repo_root}/analysis/tetris-v1.1-rom-map.csv"
python3 "${repo_root}/tools/build_report.py" \
    --manifest "${repo_root}/analysis/tetris-v1.1-manifest.json" \
    --rom-map "${repo_root}/analysis/tetris-v1.1-rom-map.csv" \
    --reference-root "${repo_root}/reference/tetris-disassembly" \
    --rom "${rom_path}" \
    --output "${repo_root}/build/tetris-v1.1-report.html"
