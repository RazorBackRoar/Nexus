# Nexus

[![Download](https://img.shields.io/github/v/release/RazorBackRoar/Nexus?style=for-the-badge&label=Download%20DMG&color=d32f2f)](https://github.com/RazorBackRoar/Nexus/releases/latest)
[![Version](https://img.shields.io/badge/version-3.0.0-blue?style=for-the-badge)](https://github.com/RazorBackRoar/Nexus/releases/tag/v3.0.0)
[![CI](https://img.shields.io/github/actions/workflow/status/RazorBackRoar/Nexus/ci.yml?branch=main&style=for-the-badge&label=CI)](https://github.com/RazorBackRoar/Nexus/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blueviolet?style=for-the-badge)](LICENSE)
[![Swift](https://img.shields.io/badge/swift-6-F05138?style=for-the-badge&logo=swift&logoColor=white)](https://swift.org/)
[![SwiftUI](https://img.shields.io/badge/SwiftUI-macOS-0078D7?style=for-the-badge)](https://developer.apple.com/swiftui/)
[![macOS](https://img.shields.io/badge/mac%20os-Apple%20Silicon-d32f2f?style=for-the-badge&logo=apple&logoColor=white)](https://support.apple.com/en-us/HT211814)

<!-- Workspace Health Layer -->
![Status](https://img.shields.io/badge/status-active-2ea44f?style=for-the-badge)
![Tests](https://img.shields.io/badge/tests-present-2ea44f?style=for-the-badge)
![Build](https://img.shields.io/badge/build-swift-F05138?style=for-the-badge)

**Native macOS Safari bookmark manager and batch URL opener.**

Swift 6 and SwiftUI. Deep purple glass, a star field, and colored controls. Opens links in Private Safari.

<p align="center">
  <a href="https://github.com/RazorBackRoar/Nexus/releases/latest/download/Nexus.dmg"><strong>↓ Download Nexus.dmg</strong></a>
  ·
  <a href="https://github.com/RazorBackRoar/Nexus/releases">All releases</a>
</p>

![Nexus](docs/screenshots/app.png)

## Features

- **Private Safari** — launches in Private Browsing and pauses between tabs
- **Quick Save** — dated URL cards with notes (⌘⇧S)
- **Bookmark folders** — colored glass rows you can filter and reorder
- **Copy Rich Links** — Apple Notes–friendly HTML on the clipboard
- **Paste and drop** — links from the clipboard, or `.txt` / `.csv` / `.md` files
- **Apple Silicon** — Swift 6, arm64 only

---

## Install

1. Download [`Nexus.dmg`](https://github.com/RazorBackRoar/Nexus/releases/latest/download/Nexus.dmg)
2. Open the DMG and drag `Nexus.app` to `/Applications`
3. First launch — right-click the app → **Open** to bypass Gatekeeper on the ad-hoc signed build
4. Go to **System Settings → Privacy & Security → Automation** and enable **Safari** for Nexus

---

## Usage

1. **Add Bookmarks** — click `+`, paste URLs, or drop a text file onto the URL table
2. **Quick Save** — press ⌘⇧S to capture the current links with a timestamp
3. **Organize** — create folders, save groups, and drag to rearrange
4. **Batch Open** — select bookmarks → **Open in Safari**
5. **Rich Links** — copy formatted links for Apple Notes

Data files live under `~/Library/Application Support/Nexus/`:
`bookmarks_v2.json` and `bookmark_groups.json`.

---

## Development

### Requirements

- Swift 6
- macOS 14 or newer
- Apple Silicon

### Setup

```bash
git clone https://github.com/RazorBackRoar/Nexus.git
cd Nexus
swift test
swift run
```

### Build

```bash
./scripts/build-mac.sh
# Output: build/Release/Nexus.dmg
```

### Test

```bash
swift test
```

---

## Community & docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — persistence model, modules, testing
- [BUILD_AND_RELEASE.md](BUILD_AND_RELEASE.md) — prerequisites, build, packaging, release, versioning
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to contribute
- [SECURITY.md](SECURITY.md) — vulnerability reporting
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — community standards

## License

MIT License — see [LICENSE](LICENSE) for details.
Copyright © 2026 RazorBackRoar

<!-- razorcore:runtime:start -->
## Runtime Requirements

For users:
- Download the macOS DMG. Nexus is a native Swift app.

For developers:
- Swift 6, SwiftUI, Apple Silicon.
- Test: `swift test`
- Run: `swift run`
- Package: `./scripts/build-mac.sh`
<!-- razorcore:runtime:end -->
