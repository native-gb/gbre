#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
rom_path="${1:-}"
reference_dir="${repo_root}/reference/tetris-disassembly"
rgbds_dir="${repo_root}/.cache/rgbds-0.5.2"
rgbds_bin="${repo_root}/.cache/rgbds-0.5.2-bin"
expected_rom_sha1="74591cc9501af93873f9a5d3eb12da12c0723bbc"
reference_commit="b95c66859339f5523e80213de5857eefc1c7703f"

if [[ -z "${rom_path}" || ! -f "${rom_path}" ]]; then
    echo "Usage: $0 path/to/Tetris-v1.1.gb" >&2
    exit 2
fi

actual_rom_sha1="$(sha1sum "${rom_path}" | cut -d' ' -f1)"
if [[ "${actual_rom_sha1}" != "${expected_rom_sha1}" ]]; then
    echo "ROM SHA-1 does not match Tetris v1.1: ${actual_rom_sha1}" >&2
    exit 1
fi

if [[ ! -d "${reference_dir}/.git" ]]; then
    git clone https://github.com/kaspermeerts/tetris.git "${reference_dir}"
fi
git -C "${reference_dir}" checkout --detach "${reference_commit}"

if [[ ! -x "${rgbds_bin}/rgbasm" ]]; then
    git clone --depth 1 --branch v0.5.2 https://github.com/gbdev/rgbds.git "${rgbds_dir}"
    make -C "${rgbds_dir}" -j"$(nproc)"
    mkdir -p "${rgbds_bin}"
    cp "${rgbds_dir}"/{rgbasm,rgbfix,rgbgfx,rgblink} "${rgbds_bin}/"
fi

cd "${reference_dir}"
"${rgbds_bin}/rgbgfx" -d 2 -o gfx/configandgameplay.2bpp gfx/configandgameplay.png
"${rgbds_bin}/rgbgfx" -d 2 -o gfx/copyrightandtitlescreen.2bpp gfx/copyrightandtitlescreen.png
"${rgbds_bin}/rgbgfx" -d 1 -o gfx/font.1bpp gfx/font.png
"${rgbds_bin}/rgbgfx" -d 2 -o gfx/multiplayerandburan.2bpp gfx/multiplayerandburan.png
truncate -s $((197 * 16)) gfx/configandgameplay.2bpp
truncate -s $((119 * 16)) gfx/copyrightandtitlescreen.2bpp
truncate -s $((39 * 8)) gfx/font.1bpp
truncate -s $((207 * 16)) gfx/multiplayerandburan.2bpp

PATH="${rgbds_bin}:${PATH}" make clean
PATH="${rgbds_bin}:${PATH}" make tetris.gb
rebuilt_sha1="$(sha1sum tetris.gb | cut -d' ' -f1)"
if [[ "${rebuilt_sha1}" != "${expected_rom_sha1}" ]]; then
    echo "Reference rebuild mismatch: ${rebuilt_sha1}" >&2
    exit 1
fi

echo "Reference disassembly rebuild matches Tetris v1.1 (${expected_rom_sha1})"
