# Nexus AGENTS

**Package:** `nexus`
**Version:** 3.12.7

Use this file with `/Users/home/Workspace/Apps/AGENTS.md`. It only records Nexus-specific context.

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
uv run ty check src --python-version 3.13
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
- [ ] `uv run ty check src --python-version 3.13` passes with no errors
- [ ] `uv run pytest tests/ -q` passes with no failures
- [ ] App launches locally from a clean `uv sync`
- [ ] At least one core user flow exercised manually end-to-end
- [ ] `pyproject.toml` version matches README badge/display text

### What CI Does Not Prove
> Green CI is necessary but not sufficient for a safe release.
> Source site behavior (4Charm), macOS permissions (Nexus), and external tools (L!bra/Papyrus)
> cannot be fully validated by static CI checks.
