# Architecture

Nexus is a Swift 6 / SwiftUI app. Entry point: `Sources/Nexus/NexusApp.swift`.

## Layout

| Path | Role |
|------|------|
| `Sources/Nexus/NexusApp.swift` | App entry, window lifecycle |
| `Sources/Nexus/App/` | `AppModel`, `MainView`, sheets, starfield |
| `Sources/Nexus/Store/` | `BookmarkStore`, `LibraryCodec`, models, atomic JSON writes |
| `Sources/Nexus/Safari/` | `SafariRunner` and AppleScript in `SafariScripts` |
| `Sources/Nexus/Sidebar/` | Folder sidebar |
| `Sources/Nexus/URLWorkspace/` | Paste, drop, and URL extraction |
| `Sources/Nexus/Health/` | Library health scan |
| `Sources/Nexus/Settings/` | Settings |
| `Tests/NexusTests/` | `swift test` |

## Library

Bookmark files stay `bookmarks_v2.json` and `bookmark_groups.json` under `~/Library/Application Support/Nexus/`.

`AtomicJSON.replace` writes an exclusive `.tmp` (`O_NOFOLLOW`), fsyncs, then renames over the destination. A missing or unreadable primary file restores `.bak` before defaults are created. Quick Save stays first and cannot be deleted.

## Safari

`SafariRunner` opens one tab at a time through `osascript`. Private Browsing is the default. Private windows need Accessibility and do not fall back to a standard window. Batches pause between tabs so Safari does not drop launches.

## Build

`swift test`, then `./scripts/build-mac.sh`. Version is `Sources/Nexus/Resources/version.json`.
