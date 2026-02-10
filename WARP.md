# WARP.md — Nexus

> **⭐ CODEGRAPHCONTEXT:** [/Users/home/Workspace/Apps/.code-analysis/monorepo-analysis.md](file:///Users/home/Workspace/Apps/.code-analysis/monorepo-analysis.md)
> **⭐ QUERIES:** [/Users/home/Workspace/Apps/.code-analysis/essential-queries.md](file:///Users/home/Workspace/Apps/.code-analysis/essential-queries.md)
> **Agent Context:** [/Users/home/Workspace/Apps/Nexus/AGENTS.md](file:///Users/home/Workspace/Apps/Nexus/AGENTS.md)

## ⚡ Quick Commands

| Action | Command | Notes |
| --- | --- | --- |
| **Push** | `razorpush Nexus` | Commit and save Nexus only |
| **Build (Release)** | `nexusbuild` | Full .app + DMG (~2m) |
| **Build (Test)** | `nexustest` | Fast .app only (~30s) |
| **Run** | `python src/nexus/main.py` | Dev run |

## 🏗️ Architecture

| Component | Location | Purpose |
| --- | --- | --- |
| **MainWindow** | `src/nexus/main.py` | Glass Noir UI, sidebar, URL table (Inherits SpaceBarAboutMixin) |
| **URLProcessor** | `src/nexus/core/processor.py` | URL extraction, validation, normalization |
| **SafariController** | `src/nexus/core/safari.py` | AppleScript automation with stealth mode |
| **BookmarkManager** | `src/nexus/core/bookmarks.py` | JSON hierarchical storage with backups |

## 🔑 Key Features

- **Glass Noir**: Dark theme with neon accents
- **Automation**: AppleScript Safari control (Stealth mode supported)
- **Shortcuts**: `Cmd+V` (Paste URLs), `Space` (About)

## 💾 Data & Permissions

- **Storage**: `~/Library/Application Support/Nexus/`
- **Requires**: **Full Disk Access** (to read `~/Library/Safari/Bookmarks.plist`) & **Automation** permission.

## 🚨 Rules

1.  **Python Lock**: **STRICTLY 3.13.x**.
2.  **Imports**: Absolute ONLY (`from nexus.core import X`).
3.  **Threading**: Use `BaseWorker` (from `razorcore.threading`).
4.  **Version**: Read from `pyproject.toml` (SSOT).
