# Nexus AGENTS

**Package:** SwiftPM executable `Nexus`
**Version:** 3.0.0
**GitHub:** `RazorBackRoar/Nexus`

Native macOS Safari bookmark manager and batch URL opener. Swift 6, SwiftUI, macOS 14+. No Python — do not reintroduce Python components, deps, or runtimes.

## Entry

- App: `Sources/Nexus/NexusApp.swift`
- Bookmark files: `bookmarks_v2.json` and `bookmark_groups.json`
- Store code: `Sources/Nexus/Store/`
- Safari scripts: `Sources/Nexus/Safari/SafariScripts.swift`
- Run tests: `swift test`
- Package: `./scripts/build-mac.sh`

## UI

Keep the dark purple space theme with stars (including shooting stars) as the main visual style. Bookmarks, buttons, and other interactive controls must use distinct contrasting colors so they stand out — do not flatten the UI to a single purple look.

## Library

Writes are atomic: move the current file to `.bak`, write an exclusive `.tmp` that does not follow symlinks, fsync, then rename. If the primary file is missing, unreadable, or an empty array, restore `.bak` before creating defaults. Quick Save stays first and cannot be deleted.

Safari control needs Automation permission. Always launch into Private Browsing by default. Private windows need Accessibility and must not fall back to a standard window. When opening multiple items/tabs, use a small controlled delay between actions so launches do not race and fail.

## Verification

```bash
swift test
./scripts/build-mac.sh
```

Do not mount the DMG or copy the app into `/Applications`.
