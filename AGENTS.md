# Nexus AGENTS

**Package:** `nexus`
**Version:** 2.0.0
**GitHub:** `RazorBackRoar/Nexus`

Use with `../AGENTS.md`. Keep this file Nexus-specific.

## Purpose and entry points

Native macOS Safari bookmark manager and batch URL opener (PySide6).

- Main: `src/nexus/main.py`
- Core: `src/nexus/core/bookmarks.py`, `src/nexus/core/group_store.py`, `src/nexus/core/link_converter.py`, `src/nexus/core/safari.py`
- UI: `src/nexus/gui/main_window.py`, `src/nexus/gui/widgets/` (`_base.py`, `quick_save_panel.py`, `group_row_delegate.py`), `src/nexus/gui/dialogs/`
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
- When publishing Nexus, rebuild the DMG, run a short human UAT pass on the packaged DMG (visual interaction, notification, launch-at-login, sleep/wake), then replace the sole GitHub release asset. A local Desktop DMG does not replace that UAT. Do not keep older DMG releases.

## Learned Workspace Facts

- `assets/icons/Nexus.icns` is gitignored; shipping icon changes requires `git add -f assets/icons/Nexus.icns`.
- Packaged try path: `razorbuild Nexus` → `dist/Nexus.dmg`. Open that DMG yourself to install. Human UAT (notification, launch-at-login, sleep/wake) still happens before a GitHub Release. See `../AGENTS.md` Post-Build Install & UAT Policy.
- GitHub release surface is a single `v2.0.0` DMG; older releases were removed Jul 2026.
- Quick Save is a top-level bookmark column with no subfolders; each save is a rectangular card (Date & Time | Bookmarks | Notes), newest first; right-click to copy or delete a block.
- Drag-and-drop of `.txt` onto the URL table loads URLs; Rich Links copies Apple Notes–friendly rich links to the clipboard.


## Jules Repository Contract

Jules reads this repository-root `AGENTS.md` when it clones the repository. Parent workspace policy files are not available in that clone.

- Jules runs tasks in an Ubuntu VM; macOS runtime behavior, GUI behavior, Safari automation, AppleScript, and packaged-app behavior are not proven there.
- The repository's GitHub macOS `quality` workflow is authoritative for merge readiness.
- Daily audits must inspect existing open and recently closed PRs before proposing work, avoid duplicates, and open at most one focused PR per task.
- `sentinel-*` security, `bolt-*` performance, and `palette-*` design branches always require human review.
- Jules PRs are merged by the owner. There is no auto-merge workflow.
- PR descriptions must list changed files, risk, verification commands and results, benchmark evidence when relevant, and unverified paths.
- Never auto-merge runtime, dependency, lockfile, workflow, packaging, release, privacy, file-operation, or user-data changes.

## Automated Agent & Jules Integration Guidelines
- **Jules PR Review**: all Jules PRs require the owner to merge; there is no auto-merge workflow.
- **No Duplicate Issue/PR Reopening**: Jules subagents must verify existing closed and open PRs before proposing repetitive fixes or contact info updates.
- **Branch Cleanup**: Head branches are deleted automatically upon squash-merge.


### Jules Autonomous Execution Rules
- **Auto-Approve Plans**: Automatically approve execution plans for background suggestions (testing, code health, performance). Do not pause or wait for human plan approval on routine refactoring.
- **Batching**: Group related unit tests or code health fixes into a single PR rather than creating endless single-function PRs.
