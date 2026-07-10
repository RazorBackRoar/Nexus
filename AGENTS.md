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

## CI: vendored razorcore wheel

GitHub Actions installs razorcore from `ci/vendor/` (not the private repo).
After changing `.razorcore`, run `razorvendor` from the Apps workspace root.
See `ci/vendor/README.md`.

## razorcore integration (v1.1)

| Surface | Usage |
|---------|--------|
| `logging` | Setup; file logging is **opt-in** (`NEXUS_LOG_DIR` / `NEXUS_ENABLE_FILE_LOGGING`) because pasted URLs can be sensitive |
| `config.get_version` | Version resolution |
| `threading.AsyncTaskWorker` | Async worker base (`AsyncWorker` keeps `result_ready` for MainWindow) |
| `appinfo` / `updates` | Startup banner, About, update check |

Bookmark persistence and Safari automation remain Nexus-local.

## Theme settings

Five muted dark themes live in `MainWindow._setup_themes`. Saved theme names in
`QSettings` are migrated from legacy neon names on load (`legacy_theme_map` in
`main_window.py`). Default: **Midnight Blue**.

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
