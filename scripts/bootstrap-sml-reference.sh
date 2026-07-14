#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
rom_path="${1:-}"
reference_dir="${repo_root}/reference/sml-disassembly"
rgbds_dir="${repo_root}/.cache/rgbds-0.3.5"
rgbds_bin="${repo_root}/.cache/rgbds-0.3.5-bin"
expected_rom_sha1="418203621b887caa090215d97e3f509b79affd3e"
reference_commit="618d00ed6c330928e106719533c6e294ae5d5726"

if [[ -z "${rom_path}" || ! -f "${rom_path}" ]]; then
    echo "Usage: $0 path/to/Super-Mario-Land-Rev-A.gb" >&2
    exit 2
fi

actual_rom_sha1="$(sha1sum "${rom_path}" | cut -d' ' -f1)"
if [[ "${actual_rom_sha1}" != "${expected_rom_sha1}" ]]; then
    echo "ROM SHA-1 does not match Super Mario Land Rev A: ${actual_rom_sha1}" >&2
    exit 1
fi

if [[ ! -d "${reference_dir}/.git" ]]; then
    git clone https://github.com/kaspermeerts/supermarioland.git "${reference_dir}"
fi
git -C "${reference_dir}" checkout --detach "${reference_commit}"

if [[ ! -x "${rgbds_bin}/rgbasm" ]]; then
    if [[ ! -d "${rgbds_dir}/.git" ]]; then
        git clone --depth 1 --branch v0.3.5 https://github.com/gbdev/rgbds.git "${rgbds_dir}"
    fi
    git -C "${rgbds_dir}" checkout --detach v0.3.5
    make -C "${rgbds_dir}" clean
    make -C "${rgbds_dir}" -j"$(nproc)" rgbasm rgbfix rgblink \
        CFLAGS="-O2 -fcommon" WARNFLAGS="-Wall"
    mkdir -p "${rgbds_bin}"
    cp "${rgbds_dir}"/{rgbasm,rgbfix,rgblink} "${rgbds_bin}/"
fi

ln -sfn "$(realpath "${rom_path}")" "${reference_dir}/baserom.gb"
PATH="${rgbds_bin}:${PATH}" make -C "${reference_dir}" clean
PATH="${rgbds_bin}:${PATH}" make -C "${reference_dir}" all

rebuilt_sha1="$(sha1sum "${reference_dir}/mario.gb" | cut -d' ' -f1)"
if [[ "${rebuilt_sha1}" != "${expected_rom_sha1}" ]]; then
    echo "Reference rebuild mismatch: ${rebuilt_sha1}" >&2
    exit 1
fi

echo "Reference disassembly rebuild matches Super Mario Land Rev A (${expected_rom_sha1})"
