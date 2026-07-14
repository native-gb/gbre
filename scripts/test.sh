#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
python3 -m unittest discover -s "${repo_root}/tests" -v
python3 -m py_compile "${repo_root}"/tools/*.py
node --check "${repo_root}/editor/vscode-gbre/extension.js"
