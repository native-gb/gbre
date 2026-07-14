#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
source_dir="${repo_root}/.cache/mgba"
build_dir="${source_dir}/build-headless"
mgba_commit="5157ce208a5965e8a47bf5b48b5aae5198c22a5e"

if [[ ! -d "${source_dir}/.git" ]]; then
    git clone https://github.com/mgba-emu/mgba.git "${source_dir}"
fi

if ! git -C "${source_dir}" cat-file -e "${mgba_commit}^{commit}" 2>/dev/null; then
    git -C "${source_dir}" fetch origin "${mgba_commit}"
fi
git -C "${source_dir}" checkout --detach "${mgba_commit}"
video_patch="${repo_root}/oracle/mgba-headless-video-buffer.patch"
raw_framebuffer_patch="${repo_root}/oracle/mgba-raw-framebuffer.patch"
for patch in "${video_patch}" "${raw_framebuffer_patch}"; do
    if ! git -C "${source_dir}" apply --reverse --check "${patch}" 2>/dev/null; then
        git -C "${source_dir}" apply --check "${patch}"
        git -C "${source_dir}" apply "${patch}"
    fi
done

cmake -S "${source_dir}" -B "${build_dir}" -G Ninja \
    -DBUILD_HEADLESS=ON \
    -DBUILD_QT=OFF \
    -DBUILD_SDL=OFF \
    -DBUILD_GL=OFF \
    -DBUILD_GLES2=OFF \
    -DBUILD_GLES3=OFF \
    -DBUILD_TEST=OFF \
    -DBUILD_EXAMPLE=OFF \
    -DUSE_FFMPEG=OFF \
    -DUSE_LIBZIP=OFF \
    -DUSE_DISCORD_RPC=OFF \
    -DUSE_EDITLINE=OFF \
    -DCMAKE_BUILD_TYPE=Release
cmake --build "${build_dir}" --target mgba-headless -j "$(nproc)"

echo "mGBA oracle ready at ${build_dir}/mgba-headless (${mgba_commit})"
