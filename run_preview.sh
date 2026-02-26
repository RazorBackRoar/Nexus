#!/usr/bin/env zsh
emulate -L zsh
set -euo pipefail

if [[ ! -d ".venv" ]]; then
  print -u2 "Missing .venv in $(pwd). Run: uv sync"
  exit 1
fi

exec env PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}" uv run -- python -m nexus.main "$@"
