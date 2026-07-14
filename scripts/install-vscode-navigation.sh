#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
extension_source="${repo_root}/editor/vscode-gbre"
extension_target="${HOME}/.vscode/extensions/vega.gbre-navigation-0.1.0"

if [[ -e "${extension_target}" && ! -L "${extension_target}" ]]; then
    echo "Refusing to replace non-symlink extension at ${extension_target}" >&2
    exit 1
fi

ln -sfn "${extension_source}" "${extension_target}"
echo "Installed GBRE Navigation from ${extension_source}"
echo "Reload the VS Code window once to activate it."
