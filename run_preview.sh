#!/usr/bin/env zsh
emulate -L zsh
set -euo pipefail

if [[ ! -d ".venv" ]]; then
  print -u2 "Missing .venv in $(pwd). Run: uv sync"
  exit 1
fi

if [[ ! -d "../.razorcore" ]]; then
  print -u2 "Missing ../.razorcore. This app requires a sibling .razorcore worktree."
  exit 1
fi

if ! uv run python - <<'PY' >/dev/null 2>&1
import importlib
importlib.import_module("PySide6")
importlib.import_module("razorcore")
PY
then
  print -u2 "Dependencies missing in .venv; running uv sync..."
  uv sync
fi

exec env PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}" uv run -- python -m nexus.main "$@"
