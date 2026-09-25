# Nexus native rebuild plan

Swift 6 + SwiftUI replacement for the current PySide6 app. This file lives in the Nexus repo at `/Users/home/Workspace/Apps/Nexus/Nexus-Swift-Plan.md`. Every code change from this plan happens in this same repo. The paste-ready instruction is `~/Desktop/Nexus-Swift-Prompt.md`, and that prompt follows this file.

Do not start this plan until that prompt is the task. Keep this plan file. The Python removal phase does not delete it.

## Outcome

Nexus stays a Mac-only Safari bookmark manager and batch URL opener. The shipping app becomes a native Swift 6 / SwiftUI application with a normal macOS window, system typography, consistent spacing, rounded surfaces, and light/dark appearance. Existing bookmark files keep working. Python, PySide6, PyObjC, and PyInstaller leave the repo only after the Swift app proves it can read those files and open URLs in Safari.

Version target for the replacement: **3.0.0**. Leave the published 2.0.0 DMG alone until a human UAT pass on the new package.

## Product to keep

- Paste, drop, or import links, then open them in Safari in one action.
- Sidebar of bookmark folders, saved groups, and individual links.
- Quick Save: dated cards (date and time, links, notes), newest first.
- Save the current URL list as a named group inside a folder.
- Import open Safari tabs.
- Export the current list as text or CSV.
- Copy Rich Links as Apple Notes–friendly HTML on the pasteboard.
- Private Safari as an explicit mode. If Accessibility permission is missing, stop and say so. Never quietly open a normal window instead.
- Bookmark Health: duplicate URLs, and a cancellable dead-link check.
- Preferences, keyboard shortcuts, and a Check for Updates action.
- Per-folder accent color, used as a small marker, not as a second theme system.

## Data contract

Live library, confirm the directory on the machine before coding by finding the existing files:

- `bookmarks_v2.json`
- `bookmark_groups.json`
- sibling `.bak` from the last good write
- sibling `.tmp` only as an in-progress write, never as a source of truth

The preferences screen currently shows `~/Library/Application Support/Nexus`. Qt’s app-data location can be one level deeper. Use whichever directory already contains `bookmarks_v2.json`. Do not create a second library.

`bookmarks_v2.json` is a JSON array of nodes. Keep the key `type`.

Folder:

```json
{ "type": "folder", "name": "Tech", "accent": "#5B8DEF", "children": [] }
```

Bookmark:

```json
{ "type": "bookmark", "name": "Example", "url": "https://example.com", "accent": null }
```

Group marker inside a folder (payload lives in the sidecar):

```json
{ "type": "group", "id": "stable-id" }
```

Quick Save entry, stored inside the Quick Save folder, not in the sidecar:

```json
{
  "type": "quick_save",
  "id": "stable-id",
  "created_at": "2026-09-24T18:00:00+00:00",
  "urls": ["https://example.com"],
  "notes": ""
}
```

`bookmark_groups.json` is a JSON array:

```json
{
  "id": "stable-id",
  "name": "Sunday reading",
  "created_at": "2026-09-24T18:00:00+00:00",
  "items": [{ "title": "Example", "url": "https://example.com" }]
}
```

Writes: move the current file to `.bak`, write `name.tmp` with an exclusive create that does not follow symlinks, mode `0600`, flush and fsync, then `rename` over the destination. If the primary file is missing, unreadable, or an empty array, restore from `.bak` before inventing defaults. Skip a bad node and keep the rest of the library.

Default folders, only when no library and no backup exist:

Quick Save, Fun, Misc, Tech, Work, Extra, Hidden, Special, Favorites.

Quick Save stays first and cannot be deleted. Its accent is `#2EC4A0`. Other default accents: Fun `#E5738A`, Misc `#D4A05A`, Tech `#5B8DEF`, Work `#E85A5A`, Extra `#8A95A8`, Hidden `#2A2A35`, Special `#F0F4FA`, Favorites `#5BA86A`.

## Behavior to reimplement

URL intake accepts `http` and `https` only. Also accept `www.` and bare domains, then normalize them to `https`. Pull URLs from plain text, HTML `href`s, and pasteboard URL items. Cap extraction input around 10,000 characters. Ignore file, javascript, and data URLs. Dropped or imported files are `.txt`, `.csv`, and `.md` only. CSV is flattened cell by cell. Sort the working list case-insensitively and drop duplicates.

Clipboard watch is on by default and can be turned off. Ignore a clipboard snapshot that was already ingested.

Open All paces requests. Defaults: batch size 20, delay about 0.35–0.6 seconds between batches, extra delay when the next URL shares a domain, same-domain batch cap 10. Settings can change batch size and the delay range. Domain staggering is on by default. Status per row: Ready, Opening, Opened, Failed.

Single open: double-click a row, or click a Quick Save link.

Import Safari Tabs reads every window. Each line is title, tab, URL. Skip empty URLs.

Private mode uses Safari’s Shift-Command-N through System Events, then sets the front document URL. Requires Accessibility. Failure copy stays specific: enable Accessibility for Nexus, and do not open the URLs in a standard window.

Rich Links writes HTML plus plain text to `NSPasteboard` so Notes can paste real links. Options: skip duplicate URLs, sort alphabetically, preserve blank separator lines.

Health scanner walks folders and groups, normalizes URLs (lowercase host, strip trailing slash, keep query), and lists duplicates. Dead-link checks run off the main actor, with progress, and can be cancelled.

Undo restores the previous URL-list snapshot. Search filters the sidebar. Folders can be reordered. Context menus cover new folder, rename, accent, open group, copy URL, add link, and delete. Delete and Backspace delete the sidebar selection. Quick Save itself cannot be deleted.

## Visual direction

Build a Mac app people recognize as Mac. Use a real window: standard traffic lights, standard zoom and minimize, a title of Nexus, and a resizable frame. Minimum size about 1100×720, default about 1200×760.

Layout:

- `NavigationSplitView`.
- Sidebar: “Bookmarks”, a filter field, folder rows with a short accent bar, name, and count. Groups and links indent under the open folder.
- Detail: one of three states. Empty (short title, one sentence, Paste and Import Safari Tabs). URL list. Quick Save cards.
- Bottom bar: Home, Open All, Save, Import, Export, Clear. Equal width, one row, labels fully visible.
- Footer: status on the left, Standard / Private on the right.

Typography is the system font. Titles are semibold, body is regular, URLs can be monospaced at a slightly smaller size. Leave real padding: 16–20 points around columns, 12 points between rows, 10–12 point corner radius on cards and buttons. Use system materials and separators for depth. Support System, Light, and Dark. Text and controls must meet contrast in both appearances. Every label must fit without clipping, wrapping into the control, or colliding with a neighbor. If a label is long, shorten the words (“Open All”, “Import Tabs”) instead of shrinking the control until it looks cramped.

Identity color is a deep navy accent used sparingly (sidebar selection, links, the primary action). Folder accents stay on the folder marker only. No shooting-star canvas, no fake glass gel buttons, no frameless shell, no neon glow.

## Swift shape

Match the other RazorBackRoar Swift apps: Swift tools 6.3, language mode Swift 6, macOS 14+, Apple Silicon, `swift test`, package with `scripts/build-mac.sh` so branding and the locked DMG path stay shared.

Suggested layout:

```text
Nexus/
  Package.swift
  Sources/Nexus/NexusApp.swift
  Sources/Nexus/App/MainView.swift
  Sources/Nexus/Sidebar/
  Sources/Nexus/URLWorkspace/
  Sources/Nexus/QuickSave/
  Sources/Nexus/Library/          models, JSON, atomic save
  Sources/Nexus/Safari/           script builders + runner
  Sources/Nexus/Pasteboard/
  Sources/Nexus/Health/
  Sources/Nexus/Settings/
  Sources/Nexus/Resources/
  Tests/NexusTests/
  scripts/build-mac.sh
```

Keep script construction pure and testable: allowed schemes, AppleScript string escaping, batch text. Run AppleScript on a background task. Keep library I/O off the view layer. Views observe a single store.

Bundle identifier stays `com.razorbackroar.nexus.app`. Display name stays Nexus. Reuse `assets/icons/Nexus.icns`. Info.plist usage strings must explain Safari automation and, for Private mode, Accessibility.

GitHub update check is a small native check against `RazorBackRoar/Nexus` releases. Do not import the Python `razorcore` package.

File logging stays off unless the user opts in. Logs never contain raw URLs; use a short SHA-256 prefix if a log line must identify a link.

## Phases

Each phase ends with `swift test` for the code it added. Do not delete Python in an early phase.

1. **Package skeleton.** Swift 6 executable, app entry, empty split view, icon, `swift test` that compiles. Python tree still present.
2. **Library.** Codable models, atomic writer, backup restore, default folders, round-trip tests using fixtures copied from the JSON shapes above. Run the tests against a temp directory, never against the live library.
3. **URL engine.** Extract, normalize, dedupe, sort, file parse. Tests cover plain text, HTML hrefs, `www.`, rejected schemes, csv cells, and the length cap.
4. **Shell UI.** Sidebar, empty state, URL list, Quick Save cards, bottom actions, settings window, shortcuts sheet. Sample data only. Check light and dark, and that every string fits.
5. **Wire the library.** Load and save the real files. Filter, reorder, rename, accent, delete, undo. Quick Save cards edit notes and delete one card.
6. **Safari.** Open one, Open All with pacing, import tabs, private-window failure path. Script-builder tests run without Safari. A live open test is manual.
7. **Rich Links, export, health, updates.** Pasteboard HTML, text/CSV export, duplicate report, dead-link scan, update check.
8. **Remove Python.** After phases 2–7 pass: remove `src/`, `tests/` (pytest), `pyproject.toml`, `uv.lock`, `Nexus.spec`, `run_preview.sh`, and Python CI. Add Swift CI modeled on Swifter. Rewrite `AGENTS.md` for the Swift app. Keep the icon asset and keep `Nexus-Swift-Plan.md`.
9. **Package.** `scripts/build-mac.sh` through the shared branding and DMG scripts. Leave `build/Release/Nexus.dmg` and `~/Desktop/Nexus.dmg`. Do not mount the DMG or copy the app into `/Applications`.

## Leave behind

Do not port these. They are Qt implementation details or unused code:

- `CosmicFrame`, shooting stars, glints, nebula gradients
- Fake traffic-light title bar and the sun/moon capsule drawn by hand
- `GlassButton` gel painting, `NeonButton`, `GlassPanel`, `OutlinedLabel`
- `BookmarkTreeDelegate` and `GroupRowDelegate` as paint code
- The old named theme dictionaries (Midnight Blue, Rose, Forest, Violet, Ember) and the preferences palette list that does not match them
- PySide6, PyObjC, PyInstaller, `razorcore` imports

## Guardrails

- Work in `/Users/home/Workspace/Apps/Nexus`.
- Stay on `main`. Do not create a branch, commit, or push unless the user asks.
- Do not edit other apps.
- Do not write `~/AGENTS.md`.
- Do not log or print the user’s real bookmark URLs in test output.
- Do not point tests at the live Application Support library.
- Human UAT before any GitHub Release: launch, open a small batch, private-mode permission message, light and dark, wording that fits.

## Done when

- `swift test` passes.
- A fixture library round-trips to the same JSON shapes.
- The app opens an existing `bookmarks_v2.json` and shows Quick Save cards and groups.
- Open All and Import Safari Tabs work on this Mac with Automation permission.
- Private mode fails closed without Accessibility.
- Light and dark layouts show every control label in full.
- The repo no longer contains the Python app.
- A local DMG exists in the repo and on the Desktop.
