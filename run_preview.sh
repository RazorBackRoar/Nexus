#!/bin/bash
set -euo pipefail

if [[ ! -d ".venv" ]]; then
  echo "Missing .venv in $(pwd). Run: uv sync" >&2
  exit 1
fi

if [[ ! -d "../.razorcore" ]]; then
  echo "Missing ../.razorcore. This app requires a sibling .razorcore worktree." >&2
  exit 1
fi

if ! uv run python - <<'PY' >/dev/null 2>&1
import importlib
importlib.import_module("PySide6")
importlib.import_module("razorcore")
PY
then
  echo "Dependencies missing in .venv; running uv sync..." >&2
  uv sync
fi

exec env PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}" uv run -- python -m nexus.main "$@"
