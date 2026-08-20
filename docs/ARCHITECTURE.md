# Architecture — Nexus

Developer map for the Safari bookmark manager and batch URL opener (PySide6).

## Package layout

| Path | Role |
|------|------|
| `src/nexus/main.py` | Entry point |
| `src/nexus/core/bookmarks.py` | Tree model, `bookmarks_v2.json` persistence |
| `src/nexus/core/group_store.py` | Bookmark groups sidecar (`bookmark_groups.json`) |
| `src/nexus/core/link_converter.py` | Rich Links clipboard (AppKit HTML) |
| `src/nexus/core/safari.py` | AppleScript Safari control |
| `src/nexus/core/models.py` | `BookmarkGroup`, `QuickSaveEntry`, accents |
| `src/nexus/gui/main_window.py` | Shell, migration, palettes |
| `src/nexus/gui/widgets/` | URL table, Quick Save panel, group rows |
| `src/nexus/gui/dialogs/` | New folder, Save Group dialogs |
| `src/nexus/applescript/` | Script builder + poller |

## Sidebar columns

**Quick Save** (top-level, no subfolders) plus eight default bookmark tabs:
`Fun`, `Misc`, `Tech`, `Work`, `Extra`, `Hidden`, `Special`, `Favorites`
(`DEFAULT_BOOKMARK_FOLDER_NAMES` in `bookmarks.py`).

## Persistence

| File | Location | Contents |
|------|----------|----------|
| `bookmarks_v2.json` | Qt `AppDataLocation` (~`~/Library/Application Support/Nexus/`) | Bookmark tree + Quick Save markers |
| `bookmark_groups.json` | Same directory | Named groups (sidecar to tree) |

`BookmarkManager.save_bookmarks` uses atomic `.tmp` + `.bak`. On load failure,
`.bak` is attempted before falling back to defaults.

## Key workflows

- **Batch open** — selected bookmarks → Safari via AppleScript (Automation permission required).
- **Quick Save** — `Ctrl+Shift+S` saves URL blocks as dated cards (Date & Time | Bookmarks | Notes).
- **Copy Rich Links** — Apple Notes–friendly HTML to clipboard.
- **Drag-drop** — `.txt`/`.csv`/`.md` onto URL table extracts links.
- **Save Group** — persists a named group under the active tab.

## Async workers

`AsyncWorker` extends `razorcore.threading.AsyncTaskWorker` for Safari open
tasks. Bookmark I/O stays on the main thread with atomic file writes.

## Testing

```bash
uv run pytest tests/ -q
```

Focused modules:

| Area | Tests |
|------|-------|
| Bookmarks | `tests/test_bookmarks.py` |
| Groups | `tests/core/test_group_store.py` |
| Quick Save | `tests/gui/test_quick_save*.py` |
| Safari | `tests/core/test_safari_controller.py` |

GUI tests set `QT_QPA_PLATFORM=offscreen`.

CI does **not** prove Safari Automation permissions or live AppleScript.

## Related docs

- [BUILD_AND_RELEASE.md](../BUILD_AND_RELEASE.md)
- [docs/DMG_BUILD_README.md](DMG_BUILD_README.md)
- [CONTRIBUTING.md](../CONTRIBUTING.md)
