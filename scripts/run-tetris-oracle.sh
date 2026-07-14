#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
mgba="${repo_root}/.cache/mgba/build-headless/mgba-headless"
oracle_script="${repo_root}/oracle/tetris_trace.lua"
expected_sha1="74591cc9501af93873f9a5d3eb12da12c0723bbc"

rom_path="${1:-}"
input_path="${2:-${repo_root}/../native-gb-tetris-re/oracle/inputs/no-input.csv}"
output_path="${3:-${repo_root}/build/oracle/tetris-trace.jsonl}"
frame_count="${4:-600}"
patch_path="${5:-}"
music_id="${6:-}"

if [[ -z "${rom_path}" || ! -f "${rom_path}" ]]; then
    echo "Usage: $0 path/to/Tetris-v1.1.gb [input.csv] [trace.jsonl] [frames]" >&2
    exit 2
fi
if [[ ! -f "${input_path}" ]]; then
    echo "Input script does not exist: ${input_path}" >&2
    exit 2
fi
if [[ ! "${frame_count}" =~ ^[1-9][0-9]*$ ]]; then
    echo "Frame count must be a positive integer: ${frame_count}" >&2
    exit 2
fi
if [[ -n "${patch_path}" && ! -f "${patch_path}" ]]; then
    echo "Patch script does not exist: ${patch_path}" >&2
    exit 2
fi
if [[ -n "${music_id}" && ! "${music_id}" =~ ^([1-9]|1[0-7])$ ]]; then
    echo "Music ID must be in 1..17: ${music_id}" >&2
    exit 2
fi

actual_sha1="$(sha1sum "${rom_path}" | cut -d' ' -f1)"
if [[ "${actual_sha1}" != "${expected_sha1}" ]]; then
    echo "ROM SHA-1 does not match Tetris (JUE) v1.1: ${actual_sha1}" >&2
    exit 1
fi
if [[ ! -x "${mgba}" ]]; then
    echo "Headless mGBA is missing. Run scripts/bootstrap-mgba-oracle.sh first." >&2
    exit 1
fi

mkdir -p "$(dirname "${output_path}")"
export GBRE_ORACLE_INPUT="$(realpath "${input_path}")"
export GBRE_ORACLE_OUTPUT="$(realpath -m "${output_path}")"
export GBRE_ORACLE_FRAMES="${frame_count}"
export GBRE_ORACLE_ROM_SHA1="${actual_sha1}"
if [[ -n "${patch_path}" ]]; then
    export GBRE_ORACLE_PATCHES="$(realpath "${patch_path}")"
else
    unset GBRE_ORACLE_PATCHES || true
fi
if [[ -n "${music_id}" ]]; then
    export GBRE_ORACLE_MUSIC_ID="${music_id}"
    export GBRE_ORACLE_MUSIC_FRAME=700
else
    unset GBRE_ORACLE_MUSIC_ID GBRE_ORACLE_MUSIC_FRAME || true
fi

"${mgba}" \
    -C idleOptimization=none \
    -C logLevel=0 \
    --script "${oracle_script}" \
    "${rom_path}"

echo "Wrote ${frame_count} deterministic frames to ${output_path}"
