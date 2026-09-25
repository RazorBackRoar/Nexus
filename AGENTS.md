# Nexus AGENTS

**Package:** SwiftPM executable `Nexus`
**Version:** 3.0.0
**GitHub:** `RazorBackRoar/Nexus`

Native macOS Safari bookmark manager and batch URL opener. Swift 6, SwiftUI, macOS 14+.

## Entry

- App: `Sources/Nexus/NexusApp.swift`
- Bookmark files: `bookmarks_v2.json` and `bookmark_groups.json`
- Store code: `Sources/Nexus/Store/`
- Safari scripts: `Sources/Nexus/Safari/SafariScripts.swift`
- Run tests: `swift test`
- Package: `./scripts/build-mac.sh`

## Library

Writes are atomic: move the current file to `.bak`, write an exclusive `.tmp` that does not follow symlinks, fsync, then rename. If the primary file is missing, unreadable, or an empty array, restore `.bak` before creating defaults. Quick Save stays first and cannot be deleted.

Safari control needs Automation permission. Private windows need Accessibility and must not fall back to a standard window.

## Verification

```bash
swift test
./scripts/build-mac.sh
```

Do not mount the DMG or copy the app into `/Applications`.
