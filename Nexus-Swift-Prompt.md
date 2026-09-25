# Nexus Swift rebuild prompt

Paste this whole document as the task. Follow the plan at `/Users/home/Workspace/Apps/Nexus/Nexus-Swift-Plan.md` as the phase order. Build the app in that same repo. Do not stop at a sketch.

---

Rebuild Nexus, the RazorBackRoar Safari bookmark manager and batch URL opener, as a native macOS application in Swift 6 and SwiftUI. Remove the Python / PySide6 implementation only after the Swift app covers the behavior below and its tests pass. The result must feel like a finished Mac app: system typography, even spacing, rounded surfaces, quiet depth, room for every label, and smooth state changes. Recreate the job the current app does. Do not recreate its custom-painted Qt shell.

## Where to work

- Repo: `/Users/home/Workspace/Apps/Nexus`. All source, tests, packaging, and Python removal happen here. Do not create a second app folder.
- Plan: `/Users/home/Workspace/Apps/Nexus/Nexus-Swift-Plan.md`. Follow its phase order. Do not delete that file when removing Python.
- Stay on `main`. Do not create a branch, commit, or push unless I explicitly ask.
- Do not edit any other app.
- Do not write `~/AGENTS.md` or `/Users/home/AGENTS.md`.
- After the Swift app builds, package it with the repo’s `scripts/build-mac.sh`, which must call the shared `Apps/.razorcore` branding and DMG scripts. Leave `build/Release/Nexus.dmg` and `~/Desktop/Nexus.dmg`. Do not mount the DMG, do not zip a backup, and do not install into `/Applications`.
- Stack: Swift tools 6.3, Swift language mode v6, macOS 14 or newer, Apple Silicon. Tests: `swift test`. Look at Swifter (`Apps/Swifter`) for `Package.swift`, `scripts/build-mac.sh`, and CI shape. Nexus does not import the Python `razorcore` package. Packaging scripts are shared; runtime code is not.
- Bundle identifier: `com.razorbackroar.nexus.app`
- Display name: Nexus
- Version: 3.0.0 when Python is removed
- Icon: keep `assets/icons/Nexus.icns` and load it from the bundle
- Info.plist must include a plain-language reason for controlling Safari, and a plain-language reason for Accessibility because Private windows need it

## What “polished” means

Use a standard macOS window. Standard traffic lights, standard minimize and zoom, a draggable title bar, and a resize handle from the system. Minimum size about 1100 by 720 points. Default size about 1200 by 760. Remember the window frame across launches.

Use `NavigationSplitView`.

Sidebar, fixed and comfortable, about 260 points:

- Section title “Bookmarks”
- A trailing “+” button with the help “New Folder”
- A search field whose placeholder is “Filter Bookmarks”
- Folder rows: a 3-point accent bar, the folder name, and a count of children when the count is greater than zero
- The selected folder is clearly selected in both appearances
- Groups inside a folder show a small accent dot, the group name, and a count
- Links show the bookmark name, and the accent dot of the bookmark or its folder
- Rows are at least 36 points tall for links and groups, and about 44 points for folders
- Drag folders to reorder them
- Nothing in the sidebar uses a boxed table grid

Detail column:

- A short line at the top: “Paste URLs. Open in Safari.”
- A “Load File” button aligned to the trailing edge of that line
- The main surface is a rounded rectangle, inset from the window edge, with padding inside
- When the list is empty, center this copy, each block on its own line, with space between them:
  - Title: “Paste URLs to get started”
  - Body: “Copied links show up here. Paste, import your open Safari tabs, or drop a text file.”
  - Buttons: “Paste from Clipboard” and “Import Safari Tabs”
- When the list has URLs, show borderless rows. Each row is the URL and a status. No header row, no grid lines, no boxed cells.
- When Quick Save is selected, replace that surface with Quick Save cards. Do not show the empty-state copy at the same time.

Bottom of the detail column, one centered row of six buttons, each wide enough for its label, about 46 points tall, with at least 12 points between them:

Home, Open All, Save, Import, Export, Clear

Footer, full width:

- Leading: a status line. Idle copy is “Ready”.
- Trailing: a switch or segmented control labeled so the current mode is obvious: “Standard Safari” or “Private Safari”.

Menus, even with a simple window, must exist:

- File: New Folder, Import URLs from File, Import Safari Tabs, Save URLs as Group, Quick Save, Export URLs, Close
- Edit: Undo, Cut, Copy, Paste, Select All, Copy Rich Links, Clear URL List
- View: URL Workspace, Quick Save, Find in Bookmarks, Appearance (System, Light, Dark)
- Safari: Open All URLs in Safari, Import Safari Tabs, Private Browsing (checkmark)
- Tools: Bookmark Health, Settings
- Help: Keyboard Shortcuts, Check for Updates, About Nexus

Settings is a separate window, not a crowded popover. Tabs:

- Appearance: System, Light, or Dark
- Safari: batch size (1–100, default 20), minimum delay, maximum delay, “Pause longer between links on the same site” (on by default), “Open in Private Safari by default” (off by default)
- Privacy: “Add copied links automatically” (on by default), “Keep URLs out of logs” (on, and not a switch that reveals raw URLs)
- Rich Links: “Skip duplicate URLs” (on), “Sort links alphabetically” (off), “Keep blank lines” (on)
- Storage: read-only path of the library, “Show in Finder”, and how many backup generations to keep (default 7)

Keyboard shortcuts sheet lists the shortcuts below in four groups: General, Navigation, URLs and Safari, Bookmarks. Shortcut text uses the Mac symbols.

Typography and spacing:

- System font only. Window title and the empty-state title are semibold. Body is regular. URLs use a monospaced face slightly smaller than body.
- Page margins 20 points. Space between sidebar and detail 20 points. Space between stacked sections 12 to 16 points. Card and button corner radius 10 to 12 points.
- If a label does not fit, change the words or widen the control. Do not let text clip, collide, or sit on a one-pixel margin.
- Support Light and Dark, and follow the system when Appearance is System. Check both appearances before calling the UI done.
- Accent is a deep navy blue for selection, links, and the main action. Folder colors are only the small bar or dot beside that folder. No particle background, no hand-drawn traffic lights, no gel-button painting, no outer glow, no neon.

Motion stays short. Selection, the empty-state swap, and button press use the system animation. No looping animation on the window background.

## Library

Find the existing library before choosing a path. Look for `bookmarks_v2.json`. The settings screen in the Python app displays `~/Library/Application Support/Nexus`, and Qt may have stored the file one directory deeper. Read and write that existing directory. Do not create a second library. Do not open the live library from tests. Tests use a temporary directory and fixtures.

`bookmarks_v2.json` is a JSON array. Preserve the `type` field exactly.

Folder node:

```json
{ "type": "folder", "name": "Tech", "accent": "#5B8DEF", "children": [] }
```

Bookmark node:

```json
{ "type": "bookmark", "name": "Example", "url": "https://example.com", "accent": null }
```

`accent` may be a hex string or null. Null means “use the folder color.”

Group marker, stored in a folder’s `children`. The URLs live in the sidecar:

```json
{ "type": "group", "id": "stable-id" }
```

Quick Save entry, stored as a child of the folder named “Quick Save”, not in the sidecar:

```json
{
  "type": "quick_save",
  "id": "stable-id",
  "created_at": "2026-09-24T18:00:00+00:00",
  "urls": ["https://example.com"],
  "notes": ""
}
```

`bookmark_groups.json` is a JSON array of:

```json
{
  "id": "stable-id",
  "name": "Sunday reading",
  "created_at": "2026-09-24T18:00:00+00:00",
  "items": [{ "title": "Example", "url": "https://example.com" }]
}
```

Unknown `type` values are kept as raw JSON so a future marker is not destroyed. A single bad node is skipped. A file that is not an array, or that cannot be parsed, is a failed read.

Load order for each file: the primary file, then the `.bak` beside it. If the primary file is missing, unreadable, or an empty array, and the backup has data, restore the backup into the primary file. If both are missing, create the default folders and save them.

Default folders, in this order, Quick Save first:

| Folder | Accent |
| --- | --- |
| Quick Save | `#2EC4A0` |
| Fun | `#E5738A` |
| Misc | `#D4A05A` |
| Tech | `#5B8DEF` |
| Work | `#E85A5A` |
| Extra | `#8A95A8` |
| Hidden | `#2A2A35` |
| Special | `#F0F4FA` |
| Favorites | `#5BA86A` |

Quick Save always exists, stays at the top, and cannot be renamed or deleted. Other folders can be renamed, recolored, reordered, and deleted. Deleting a folder asks for confirmation when it contains anything.

Save procedure, both files:

1. If the destination exists, replace it onto `filename.bak` first.
2. Write `filename.tmp` with an exclusive create, no-follow, mode `0600`. If a leftover `.tmp` is a symlink, unlink the symlink itself before creating the file.
3. Write pretty JSON, UTF-8, indent 2, `ensure_ascii` off. Flush and fsync.
4. Rename the temp file onto the destination.
5. On failure, if the destination is gone and the backup exists, move the backup back.

Timestamps are ISO-8601 with seconds precision. New ids are UUIDs.

Sidebar behavior:

- Click a normal folder to show its contents in the sidebar and keep the URL workspace available.
- Click Quick Save to show the Quick Save card list in the detail column.
- Double-click a link to open that one URL in Safari.
- Double-click a group, or choose Open from its menu, to open every URL in that group.
- Context menu on a folder: Rename, Set Color, Delete. Quick Save omits Rename and Delete.
- Context menu on a group: Open in Safari, Rename, Move to Folder, Delete.
- Context menu on a link: Open, Copy URL, Set Color, Delete.
- “+” opens New Folder: a name field (40 characters) and the accent swatches above, plus a custom color picker. OK stays disabled while the name is blank.
- Delete and Backspace delete the selected sidebar item, with the Quick Save exception.
- The filter field matches folder, group, and link names, case-insensitive, without destroying the saved order. Clearing the field restores the full tree. Pasting URLs into the filter field loads those URLs into the workspace instead of searching.

## URL workspace

The working list is in memory until the user saves, quick-saves, or exports it. Edits push an undo snapshot. Undo (Command-Z) restores the previous list. Clear asks before wiping a non-empty list, then leaves one undo step.

Intake sources, all of them:

- Automatic clipboard monitoring, when the privacy setting is on. Ignore the same clipboard text twice in a row.
- Paste (Command-V) from anywhere in the window when a text field is not focused.
- “Paste from Clipboard” on the empty state. A click on the empty surface also pastes.
- Drag and drop onto the empty surface or the list.
- Load File and Import, which share one file panel.
- Import Safari Tabs.

Accepted pasteboard forms, in order: file URLs, link URLs, HTML `href` values, then plain text. HTML wins over plain text when both exist and the HTML contains an href.

Extraction rules:

- Allow `http` and `https` only at open time.
- Also recognize `www.` hosts and bare domains, and store them as `https://…`.
- Recognize common short links (`bit.ly`, `tinyurl.com`, `t.co`, `goo.gl`, `short.link`, `is.gd`, `v.gd`, `ow.ly`, `buff.ly`, `rebrand.ly`, `tiny.cc`, `shorturl.at`) and store them as `https://…`.
- Split URLs that were concatenated without a space.
- Stop extraction at 10,000 characters of input.
- Reject `file`, `javascript`, `data`, and any other scheme.
- Reject strings whose path looks like a local file with an extension such as png, jpg, pdf, zip, dmg, mp4, and the other non-page extensions the current extractor ignores.
- Deduplicate, then sort case-insensitively.
- Files: `.txt`, `.csv`, and `.md` only. Read UTF-8, replacing bad bytes. CSV contributes every non-empty cell. Text and Markdown are split into lines.

Each row shows the URL and a status: Ready, Opening, Opened, or Failed. Ready is green, Opening is amber, Opened is blue, Failed is red, tuned so they stay readable on light and dark. Double-click a row to open that URL. The status line under the list counts URLs, for example “12 URLs”, and shows “Waiting for pasted URLs” when the list is empty.

Buttons:

- Home (Command-H and Command-1) leaves Quick Save and shows the URL list.
- Open All (Command-Shift-O) opens every URL in the list.
- Save (Command-S) opens Save Group: a name (60 characters) and a folder menu. The current folder is preselected when it is not Quick Save. Saving into Quick Save creates a Quick Save card instead of a group. OK stays disabled while the name is blank.
- Import (Command-O) opens the file panel.
- Export (Command-E) writes `.txt` or `.csv` of the current URLs.
- Clear (Command-Delete) empties the list after confirm.

Quick Save (Command-Shift-S) always creates a card in the Quick Save folder: id, `created_at`, the current URLs, empty notes. Cards render newest first. Each card is one rounded row with three columns: date and time (for example “Sep 24 26” and “6:30 PM”), the links, and a notes field. Click a link to open it. Edit notes and save them back into that entry. Right-click a card: Copy URLs, Load into URL List, Delete. Command-2 selects Quick Save.

A bookmark name generated from a URL uses the host, without a leading `www.`.

## Safari

Construct AppleScript as plain strings in a type that has no AppKit dependency, so tests can run without Safari.

Escape user strings for AppleScript: backslash, quote, newline, carriage return, tab, vertical tab, form feed. Strip null bytes.

Allow a URL only when the scheme is `http` or `https` and a host is present.

Scripts to support:

- Probe: `tell application "Safari" to count of windows`
- Is Safari running, without launching it: System Events process list contains Safari
- Activate Safari
- Read every tab in every window as lines of title, tab character, URL. Skip missing or empty URLs.
- New document with a URL
- New tab in the front window with a URL
- Open a list in the front window, creating a window when none exists
- Private: activate Safari, System Events keystroke `n` using shift and command, delay half a second, set the front document URL. Safari’s dictionary cannot create a private window. Do not fall back to a normal window if System Events fails.

Open All:

- Drop URLs that fail the scheme check.
- Make sure Safari is running.
- When “pause longer between links on the same site” is on, group by host. Open at most 10 URLs from one host before moving on, then add about 0.3 seconds on top of the normal delay when the next URL repeats a host. The extra delay grows slightly as batches continue.
- Otherwise open in batches of the configured size (default 20).
- Sleep a random interval between the configured minimum and maximum (defaults 0.35 and 0.6 seconds) between batches.
- Mark each row Opening, then Opened or Failed.
- Private mode uses the private script for the first URL and then tabs in that private window. If the private keystroke fails, stop, set the status to a clear error, and leave the URLs unopened in a normal window. The error tells the user to turn on Accessibility for Nexus in System Settings, Privacy & Security.

Import Safari Tabs parses the tab-separated lines into title plus URL, runs them through the same extractor, and loads the URL list. Shortcut Command-Shift-I.

Do not log raw URLs. If a log line needs an identity, use a 12-character SHA-256 prefix. File logging stays off unless a setting or environment flag turns it on.

## Rich Links, health, updates

Copy Rich Links (Command-Shift-C) places HTML and a plain-text fallback on `NSPasteboard` so Apple Notes pastes clickable links. Honor the three Rich Links settings. A right-click on Export can offer the same action.

Bookmark Health (Command-Shift-H) has two panes:

- Duplicates: walk every bookmark and every group item. Normalize by lowercasing the scheme and host, stripping one trailing slash on the path, and keeping the query. Show groups of two or more.
- Dead links: check those URLs off the main actor, a handful at a time, with a progress count. The user can cancel. Show the name, the container, the status code or the error, and the URL.

Check for Updates reads the latest GitHub release of `RazorBackRoar/Nexus` and shows it in a small alert. About shows the name, version 3.0.0, and one sentence: Safari bookmark manager and batch URL opener.

Storage’s Show in Finder reveals the real library directory.

## Shortcuts

| Shortcut | Action |
| --- | --- |
| Command-Comma | Settings |
| Command-Slash | Keyboard Shortcuts |
| Command-Q | Quit |
| Command-H | URL workspace |
| Command-F | Filter field |
| Escape | Clear the filter, or close a dialog |
| Command-1 | URL workspace |
| Command-2 | Quick Save |
| Command-Shift-O | Open All |
| Command-Shift-I | Import Safari Tabs |
| Command-Shift-S | Quick Save |
| Command-Shift-C | Copy Rich Links |
| Command-O | Import file |
| Command-E | Export |
| Command-Delete | Clear list |
| Command-N | New Folder |
| Command-S | Save Group |
| Delete, Backspace | Delete sidebar selection |
| Return | Open the selected link or group |
| Command-Shift-H | Bookmark Health |
| Command-Z | Undo URL list |

## Code layout

```text
Package.swift
Sources/Nexus/NexusApp.swift
Sources/Nexus/App/MainView.swift
Sources/Nexus/Sidebar/
Sources/Nexus/URLWorkspace/
Sources/Nexus/QuickSave/
Sources/Nexus/Library/
Sources/Nexus/Safari/
Sources/Nexus/Pasteboard/
Sources/Nexus/Health/
Sources/Nexus/Settings/
Sources/Nexus/Resources/
Tests/NexusTests/
scripts/build-mac.sh
```

Views do not build AppleScript or write files. `Library` and `Safari` are callable from tests without opening a window. Swift 6 concurrency: UI on the main actor, script runs and dead-link checks off the main actor, no data races papered over with unchecked sends.

## Tests, before deleting Python

`swift test` must cover:

- JSON decode and encode of a folder, a bookmark, a group marker, a Quick Save entry, and a sidecar group, including null accent and unknown `type`
- Backup restore when the primary file is empty or corrupt
- Atomic write leaves no `.tmp` behind on failure
- URL extraction cases: plain text, HTML href, `www.`, bare domain, short link, concatenated URLs, `javascript:` rejected, file extension rejected, duplicate collapse, sort, 10,000 character cap
- CSV cell flatten and Markdown line split
- AppleScript escaping and rejection of non-http(s) URLs
- Private-script text contains the Shift-Command-N keystroke and does not contain a fallback `make new document` used as a substitute
- Duplicate detection normalization
- Quick Save sort, newest first
- Default folder order and the rule that Quick Save cannot be deleted

Use fixtures in the test bundle. Never read or write `~/Library/Application Support`.

## Remove Python only after those tests pass

Delete the Python app from this repo:

- `src/`
- pytest `tests/`
- `pyproject.toml`, `uv.lock`, `Nexus.spec`, `run_preview.sh`
- Python GitHub workflow, replaced by a Swift CI workflow named `CI`, modeled on Swifter

Rewrite `Nexus/AGENTS.md` so it describes the Swift app, the library contract, `swift test`, and `scripts/build-mac.sh`. Keep the note that bookmarks are `bookmarks_v2.json` plus `bookmark_groups.json`, that writes are atomic with `.bak`, and that Safari needs Automation permission. Do not document the Qt widgets.

Keep the icon. Keep the license and the GitHub repo identity `RazorBackRoar/Nexus`. Keep `Nexus-Swift-Plan.md` and `Nexus-Swift-Prompt.md`.

Do not port these, they are the old painting layer:

- Cosmic frame, shooting stars, glints, nebula washes
- Hand-drawn traffic lights and the sun/moon toggle art
- Gel buttons, neon buttons, glass panels, outlined labels
- Qt item delegates
- The unused theme name lists

## Finish

1. `swift test` passes.
2. `swift build` passes.
3. Run `scripts/build-mac.sh` so the shared branding script and `package-dmg.sh` produce the DMG. Confirm both DMG paths exist. Do not mount or install.
4. Tell me what you verified, what still needs a human pass (live Safari, Accessibility, light and dark wording, notification and launch-at-login if those exist), and which files you removed.

Do not publish a GitHub Release. Do not commit unless I ask.
