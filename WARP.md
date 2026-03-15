# WARP.md — Nexus

> **⭐ CODEGRAPHCONTEXT:** [/Users/home/Workspace/Apps/.code-analysis/monorepo-analysis.md](file:///Users/home/Workspace/Apps/.code-analysis/monorepo-analysis.md)
> **⭐ QUERIES:** [/Users/home/Workspace/Apps/.code-analysis/essential-queries.md](file:///Users/home/Workspace/Apps/.code-analysis/essential-queries.md)
> **Agent Context:** [/Users/home/Workspace/Apps/Nexus/AGENTS.md](file:///Users/home/Workspace/Apps/Nexus/AGENTS.md)

## ⚡ Quick Commands

| Action | Command | Notes |
| --- | --- | --- |
| **Push** | `razorpush Nexus` | Commit and save Nexus only |
| **Build (Release)** | `nexusbuild` | Full .app + DMG (~2m) |
| **Verify** | `uv run pytest tests/ -q` | Repo-level check |
| **Run** | `uv run python -m nexus.main` | Dev run |

## 🏗️ Architecture

| Component | Location | Purpose |
| --- | --- | --- |
| **MainWindow** | `src/nexus/gui/main_window.py` | Theme state, bookmark tree, Safari actions, persistence wiring |
| **URLProcessor** | `src/nexus/utils/url_processor.py` | URL extraction, validation, normalization |
| **SafariController** | `src/nexus/core/safari.py` | AppleScript automation with stealth mode |
| **BookmarkManager** | `src/nexus/core/bookmarks.py` | JSON hierarchical storage with `.tmp` and `.bak` safety writes |

## 🔑 Key Features

- Local bookmark persistence in `bookmarks_v2.json`
- URL extraction from pasted or dropped content
- AppleScript Safari control with batch and domain grouping

## 💾 Data & Permissions

- **Storage**: Qt `AppDataLocation`, using `bookmarks_v2.json`
- **Requires**: macOS **Automation** permission for Safari control

## 🚨 Rules

1.  **Python Lock**: **STRICTLY 3.13.x**.
2.  **Imports**: Absolute ONLY (`from nexus.core import X`).
3.  **Threading**: Use `BaseWorker` (from `razorcore.threading`).
4.  **Persistence**: Bookmark state is local JSON, not Safari `Bookmarks.plist`.
5.  **Version**: Read from `pyproject.toml` (SSOT).
