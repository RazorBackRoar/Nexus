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
- razorcore: editable dep at `../.razorcore`
- **⚠️ macOS Full Disk Access required** — without it, `Bookmarks.plist` raises `PermissionError`. Grant in System Settings → Privacy & Security → Full Disk Access.
- **Always open plist in binary mode**: `open(path, "rb")` — macOS uses binary plist format, not XML
