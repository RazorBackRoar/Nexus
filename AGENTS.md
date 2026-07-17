# Nexus AGENTS

**Package:** `nexus`  
**Version:** 2.0.0  
**GitHub:** `RazorBackRoar/Nexus`

Use with `../AGENTS.md`. Keep this file Nexus-specific.

## Purpose and entry points

Native macOS Safari bookmark manager and batch URL opener (PySide6).

- Main: `src/nexus/main.py`
- Core: `src/nexus/core/bookmarks.py`, `src/nexus/core/group_store.py`, `src/nexus/core/models.py`, `src/nexus/core/safari.py`
- UI: `src/nexus/gui/main_window.py`, `src/nexus/gui/widgets/` (package), `src/nexus/gui/dialogs/`
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

Bookmark persistence, saved groups, and Safari automation remain Nexus-local.

## Bookmark groups (saved URL batches)

Users paste Safari "Copy All Tabs" batches into the URL table, save them as named
**groups** under a sidebar folder, and reopen or move groups later. Design spec:
`docs/superpowers/specs/2026-07-16-bookmark-groups-design.md`.

| Piece | Role |
|-------|------|
| `GroupStore` (`group_store.py`) | Sidecar persistence for `bookmark_groups.json` — atomic `.tmp` + `.bak`, same pattern as bookmarks |
| `BookmarkGroup` / `GroupItem` (`models.py`) | Saved group schema (`id`, `name`, `created_at`, `items[]`) |
| Group markers in bookmark tree | Raw dicts `{"type": "group", "id": "<uuid>"}` embedded under a folder via `BookmarkManager.save_bookmarks_raw` |
| `SaveGroupDialog` | Modal: group name + target folder combo |
| `NewFolderDialog` | Modal: folder name + accent swatch (`DEFAULT_PALETTE` matches design-spec tab colors) |
| `GroupRowDelegate` (`widgets/group_row_delegate.py`) | Paints indented group rows beneath folder pills |

Default sidebar folders ship from `DEFAULT_BOOKMARK_FOLDER_NAMES` in `bookmarks.py`
(currently eight names: Fun, Misc, Tech, Work, Extra, Hidden, Special, Favorites).
Folders and bookmarks may carry an optional `accent` hex field; custom folders pick
colors via `NewFolderDialog`.

## Non-obvious rules

- Bookmarks persist as `bookmarks_v2.json`; saved groups as `bookmark_groups.json` (see `Config` in `core/config.py`). Neither file is Safari’s `Bookmarks.plist`.
- `BookmarkManager.save_bookmarks` uses atomic `.tmp` + `.bak` — keep that path intact. `GroupStore` mirrors the same protocol.
- Group markers in the bookmark tree are raw dicts, not dataclasses — use `load_bookmarks_raw` / `save_bookmarks_raw` when mixing markers with folders.
- `GroupStore` skips malformed entries on load and dedupes by `id` on upsert/delete.
- Safari control goes through AppleScript / `osascript`; runtime checks need local Safari and Automation permission.
- If a bundled app fails to launch or control Safari, inspect `Nexus.spec` (assets, AppleEvents usage text) before changing app logic.
- Do not overwrite or delete bookmark sources without explicit approval; prefer export/backup first.

## Verification

```bash
uv run ruff check .
uv run ty check src --python-version 3.14
uv run pytest tests/ -q
```

Focused: `tests/test_bookmarks.py`, `tests/core/test_group_store.py`, `tests/core/test_safari_controller.py`, `tests/gui/test_group_row_paint.py`, `tests/gui/test_save_group_dialog.py`. GUI smoke: `uv run python -m nexus.main`.

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

## Learned Workspace Facts

- `assets/icons/Nexus.icns` is gitignored; shipping icon changes requires `git add -f assets/icons/Nexus.icns`.
- Packaged smoke path: `razorbuild Nexus` → `dist/Nexus.dmg` → mount and launch `Nexus.app` from `/Volumes/Nexus`.
- GitHub release surface is a single `v2.0.0` DMG; older releases were removed Jul 2026.
