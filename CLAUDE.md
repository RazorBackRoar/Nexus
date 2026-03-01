# Claude Code — Nexus

See workspace policy: `/Users/home/Workspace/CLAUDE.md`

## Context load order
1. `/Users/home/Workspace/CLAUDE.md`
2. `/Users/home/Workspace/Apps/AGENTS.md`
3. `/Users/home/Workspace/Apps/Nexus/AGENTS.md` ← nearest, wins on conflicts
4. Relevant `~/.skills/` guides

## Quick reference
- Package: `nexus` | Entry: `python -m nexus.main`
- Launch: `./run_preview.sh`
- Toolchain: `uv sync` → `uv run ruff check .` → `uv run ty check src --python-version 3.13`
- razorcore: editable dep at `../.razorcore`
