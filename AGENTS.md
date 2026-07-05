# Nexus AGENTS

**Package:** `nexus`
**Version:** 2.0.0

Use this file with `../AGENTS.md`. It only records Nexus-specific context.

## Purpose And Entry Points

- Main app: `src/nexus/main.py`
- Key areas: `src/nexus/core/bookmarks.py`, `src/nexus/core/safari.py`, `src/nexus/gui/main_window.py`
- Run locally: `uv run python -m nexus.main`
- Build through workspace wrappers: `nexusbuild` or `razorbuild Nexus`

## Non-Obvious Rules

- Nexus persists its own bookmarks as `bookmarks_v2.json`, not Safari's `Bookmarks.plist`. Bookmark save/load issues now point at local JSON persistence, not Safari file access.
- `BookmarkManager.save_bookmarks` uses an atomic `.tmp` plus `.bak` write flow. Keep that safety path intact when changing bookmark persistence.
- Safari automation goes through AppleScript and `osascript`; runtime verification depends on local Safari state and macOS Automation permission.
- If a bundled app builds but fails on launch or cannot control Safari, inspect `Nexus.spec` for packaging metadata such as bundled assets and AppleEvents usage text before changing app logic.

## Verification

Baseline:

```bash
uv run ruff check .
uv run ty check src --python-version 3.14
uv run pytest tests/ -q
```

Add focused checks when relevant:

- Bookmark parsing or plist writes: `uv run pytest tests/test_bookmarks.py -q`
- Safari automation or GUI flows that invoke Safari: `uv run pytest tests/core/test_safari_controller.py -q`
- Safari, bookmark, or main-window behavior: run `uv run python -m nexus.main`

If runtime verification is blocked by Safari state or macOS Automation permission, say that explicitly instead of implying the code path was exercised.

## CI Limitations

CI proves lint, type safety, and unit test correctness. It does NOT prove Safari permissions
are granted, AppleScript works, or macOS automation entitlements are intact.

## Release Readiness Checklist

Before tagging a release, verify all of the following:
- [ ] `uv run ruff check .` passes with no errors
- [ ] `uv run ty check src --python-version 3.14` passes with no errors
- [ ] `uv run pytest tests/ -q` passes with no failures
- [ ] App launches locally from a clean `uv sync`
- [ ] At least one core user flow exercised manually end-to-end
- [ ] `pyproject.toml` version matches README badge/display text

### What CI Does Not Prove
> Green CI is necessary but not sufficient for a safe release.
> Source site behavior (4Charm) and macOS permissions (Nexus)
> cannot be fully validated by static CI checks.

## Universal Safety Rules

Before making changes, read and follow:

../../docs/Agent Pre-Safety Rules.md

---

## App Repository Rules

This is an individual app repository. Keep all changes scoped to this app
unless explicitly requested.
- Do not modify unrelated apps.
- Do not create branches unless explicitly requested.
- Do not switch branches unless explicitly requested.
- Do not create or switch worktrees unless explicitly requested.
- Do not commit unless explicitly requested.
- Do not push unless explicitly requested.
- Do not delete, rename, move, or overwrite unrelated files.
- Preserve existing project style and conventions.
- Keep changes minimal and targeted.

---

## App Environment

Assume:
- Apple Silicon macOS
- Python 3.14
- uv
- ruff
- ty
- pytest

Prefer:
    uv sync
    uv run ruff check .
    uv run ty check .
    uv run pytest

---

## App Workflow

Before editing:

1. Inspect relevant files.
2. Identify existing project commands.
3. Make the smallest safe change.
4. Avoid broad refactors unless explicitly requested.
5. Avoid dependency/config changes unless required.

---

## App Validation

After code changes, suggest or run relevant checks:
    uv run ruff check .
    uv run ty check .
    uv run pytest

If packaging/build files changed, inspect existing build scripts before
suggesting build commands. Do not claim validation passed unless actual command
output confirms it.

---

## Nexus Notes

Nexus is a Safari bookmark manager app.
Be careful with bookmark data:
- Do not overwrite or delete bookmark sources unless explicitly requested.
- Prefer backups, exports, and dry runs before destructive bookmark operations.
- Preserve existing Safari/macOS-specific behavior.


## Behavioral Guidelines

Shared behavioral guidelines (Think Before Coding, Simplicity First, Surgical
Changes, Goal-Driven Execution) are inherited from `../AGENTS.md` and the
workspace root `../../AGENTS.md`. Do not duplicate them here. Future changes
belong in the root AGENTS.md only, unless Nexus needs a specific local
exception.
