# Nexus AGENTS

**Package:** `nexus`  
**Version:** 2.0.0  
**GitHub:** `RazorBackRoar/Nexus`

Use with `../AGENTS.md`. Keep this file Nexus-specific.

## Purpose and entry points

Native macOS Safari bookmark manager and batch URL opener (PySide6).

- Main: `src/nexus/main.py`
- Core: `src/nexus/core/bookmarks.py`, `src/nexus/core/safari.py`
- UI: `src/nexus/gui/main_window.py`, `src/nexus/gui/widgets.py`
- Run: `uv run python -m nexus.main`
- Build: `nexusbuild` or `razorbuild Nexus`

Dev clones expect sibling `../.razorcore` (editable `razorcore>=1.211.0`).

## razorcore integration (v1.1)

| Surface | Usage |
|---------|--------|
| `logging` | Setup; file logging is **opt-in** (`NEXUS_LOG_DIR` / `NEXUS_ENABLE_FILE_LOGGING`) because pasted URLs can be sensitive |
| `config.get_version` | Version resolution |
| `threading.AsyncTaskWorker` | Async worker base (`AsyncWorker` keeps `result_ready` for MainWindow) |
| `appinfo` / `updates` | Startup banner, About, update check |

Bookmark persistence and Safari automation remain Nexus-local.

## Non-obvious rules

- Bookmarks persist as `bookmarks_v2.json`, not Safari’s `Bookmarks.plist`.
- `BookmarkManager.save_bookmarks` uses atomic `.tmp` + `.bak` — keep that path intact.
- Safari control goes through AppleScript / `osascript`; runtime checks need local Safari and Automation permission.
- If a bundled app fails to launch or control Safari, inspect `Nexus.spec` (assets, AppleEvents usage text) before changing app logic.
- Do not overwrite or delete bookmark sources without explicit approval; prefer export/backup first.

## Verification

```bash
uv run ruff check .
uv run ty check src --python-version 3.14
uv run pytest tests/ -q
```

Focused: `tests/test_bookmarks.py`, `tests/core/test_safari_controller.py`. GUI smoke: `uv run python -m nexus.main`.

If Safari/Automation blocks a check, say so — do not imply the path was exercised.

## CI limitations

CI covers lint, types, and unit tests. It does **not** prove Safari permissions, AppleScript, or Automation entitlements.

## Release checklist

- [ ] ruff / ty / pytest clean
- [ ] App launches after clean `uv sync`
- [ ] One end-to-end bookmark/open flow exercised (with Automation granted)
- [ ] Packaging artifact smoke-tested when shipping a DMG
- [ ] `pyproject.toml` version matches README badge

## Safety and scope

- Read `../../docs/Agent Pre-Safety Rules.md` before changes.
- Keep changes scoped to this app unless asked otherwise.
- Do not create branches, commit, or push unless explicitly requested.
- Behavioral guidelines inherit from `../AGENTS.md`.

## Learned User Preferences

- Canonical app icon is `assets/icons/Nexus.icns`; load it via `get_resource_path()` in dev and packaged builds.
- Prefer `./run_preview.sh` for the latest dev build over an `/Applications/Nexus.app` copy unless the user asks for the installed or DMG build.
- Nexus UI should echo the icon: near-black navy shell, metallic silver typography, and vivid accent colors — avoid muted or washed-out palettes.
- Past-URLs rows stay borderless; no boxed cells or divider lines in the URL table.
- Hero "Nexus" title uses metallic silver gradient lettering with wider tracking, positioned slightly higher in the header.
- Eject mounted `Nexus` DMG volumes when done (`hdiutil detach /Volumes/Nexus`).
- When publishing Nexus, rebuild the DMG, install to `/Applications`, and replace the sole GitHub release asset (do not keep older DMG releases).

## Learned Workspace Facts

- `assets/icons/Nexus.icns` is gitignored; shipping icon changes requires `git add -f assets/icons/Nexus.icns`.
- Packaged smoke path: `razorbuild Nexus` → `dist/Nexus.dmg` → mount and launch `Nexus.app` from `/Volumes/Nexus`.
- GitHub release surface is a single `v2.0.0` DMG; older releases were removed Jul 2026.
- Quick Save is a top-level bookmark column with no subfolders; each save is a rectangular card (Date & Time | Bookmarks | Notes), newest first; right-click to copy or delete a block.
- Drag-and-drop of `.txt` onto the URL table loads URLs; Rich Links copies Apple Notes–friendly rich links to the clipboard.
