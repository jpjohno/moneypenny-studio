#!/bin/zsh
set -eu
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
if [[ ! -f node_modules/three/build/three.module.js ]]; then
  npm ci --ignore-scripts --cache .runtime/npm-cache
fi
.venv/bin/python scripts/setup.py
exec .venv/bin/python scripts/launch.py
