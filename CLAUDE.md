# Claude Code — Nexus

See workspace policy: `/Users/home/Workspace/CLAUDE.md`

## Context load order
1. `/Users/home/Workspace/CLAUDE.md`
2. `/Users/home/Workspace/Apps/AGENTS.md`
3. `/Users/home/Workspace/Apps/Nexus/AGENTS.md` ← nearest, wins on conflicts
4. Relevant `~/.skills/` guides

## Quick reference
- **Purpose:** Native macOS Safari bookmark manager (reads `~/Library/Safari/Bookmarks.plist` via plistlib)
- Package: `nexus` | Entry: `python -m nexus.main`
- Launch: `./run_preview.sh`
- Build: `nexusbuild` or `razorbuild Nexus` | Push: `nexuspush` or `razorpush Nexus`
- Toolchain: `uv sync` → `uv run ruff check .` → `uv run ty check src --python-version 3.13`
- Tests: `uv run pytest tests/ -v`
- razorcore: editable dep at `../.razorcore`
- **⚠️ macOS Full Disk Access required** — without it, `Bookmarks.plist` raises `PermissionError`. Grant in System Settings → Privacy & Security → Full Disk Access.
- **Always open plist in binary mode**: `open(path, "rb")` — macOS uses binary plist format, not XML

## Module structure (post-refactor)
- `applescript/builder.py` — pure AppleScript string construction (no asyncio, no subprocess); fully testable on any platform
- `applescript/poller.py` — async Safari state queries; `run_applescript()`, `wait_for_safari_ready()`, `check_safari_status()`
- `core/safari.py` — coordinator only; no raw AppleScript strings
