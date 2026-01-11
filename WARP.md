# WARP.md — Nexus

> Safari bookmark manager & batch URL opener for macOS. Python 3.13+ / PySide6 / Apple Silicon.

## Quick Commands

```bash
# Run
python src/nexus/main.py

# Test
pytest tests/

# Build
razorcore build Nexus
```

## Architecture

| Component | Location | Purpose |
|-----------|----------|---------|
| **MainWindow** | `main.py` | Glass Noir UI, sidebar, URL table |
| **URLProcessor** | `main.py` | URL extraction, validation, normalization |
| **SafariController** | `main.py` | AppleScript automation with stealth mode |
| **BookmarkManager** | `main.py` | JSON hierarchical storage with backups |

## Key Features
- Glass Noir dark theme with neon accents
- AppleScript Safari automation
- Stealth mode: domain grouping, staggered delays
- Private browsing support
- Drag-drop and paste URL handling

## Data Storage
- Bookmarks: `~/Library/Application Support/Nexus/`
- Settings: QSettings (window state, theme)

## Shortcuts
- **Cmd+V**: Paste URLs into table

## Rules
1. Build with `razorcore build Nexus`
2. Version lives in `pyproject.toml`
3. Requires Automation permission for Safari
4. Use AsyncWorker for background tasks
