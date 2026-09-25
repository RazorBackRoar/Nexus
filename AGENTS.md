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

Approved look (Sep 2026) — refine within it, do not redesign or return to pink/washed-out purple glassmorphism:

- Dark cosmic environment. Private Safari: near-black deep space with a massive spinning black hole. Standard Safari: a bright white-gold dwarf star in the same spot. Switching modes animates between them.
- The glass reflects the active light source: warm gold in Standard, cool violet in Private. Colors change with the mode.
- Crystal-clear dark spacecraft glass with crisp, high-contrast text.
- Stars fly across in parallax depth layers, with slow shooting stars.
- Bookmark categories keep distinct accent colors; pink is a rare accent only. Action buttons stay punchy.
- Hover makes cards and buttons glow, lift, or highlight. No star/sparkle particles near the cursor.

Closing the window quits the app (`applicationShouldTerminateAfterLastWindowClosed` returns true). It must not keep running invisibly.

README screenshots are offscreen renders of the real components with the default folders. Never capture the live window or library (bookmarks, clipboard URLs), and never take a full-screen capture.

## Library

Writes are atomic: move the current file to `.bak`, write an exclusive `.tmp` that does not follow symlinks, fsync, then rename. If the primary file is missing, unreadable, or an empty array, restore `.bak` before creating defaults. Quick Save stays first and cannot be deleted.

Safari control needs Automation permission. Always launch into Private Browsing by default. Private windows need Accessibility and must not fall back to a standard window. When opening multiple items/tabs, use a small controlled delay between actions so launches do not race and fail.

## Verification

```bash
swift test
./scripts/build-mac.sh
```

Do not mount the DMG or copy the app into `/Applications`.
