# Nexus

<p align="center">

[![Download](https://img.shields.io/github/v/release/RazorBackRoar/Nexus?style=for-the-badge&label=Download%20DMG&color=d32f2f)](https://github.com/RazorBackRoar/Nexus/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/RazorBackRoar/Nexus/ci.yml?branch=main&style=for-the-badge&label=CI)](https://github.com/RazorBackRoar/Nexus/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blueviolet?style=for-the-badge)](LICENSE)
[![Swift](https://img.shields.io/badge/Swift-F05138?style=for-the-badge&logo=swift&logoColor=white)](https://swift.org/)
[![SwiftUI](https://img.shields.io/badge/SwiftUI-007AFF?style=for-the-badge)](https://developer.apple.com/swiftui/)
[![macOS](https://img.shields.io/badge/mac%20os-Apple%20Silicon-d32f2f?style=for-the-badge&logo=apple&logoColor=white)](https://support.apple.com/en-us/HT211814)

</p>

**Native macOS Safari bookmark manager and batch URL opener.**

Swift 6 and SwiftUI. Save links, group them, and open a selection in Safari. Private Safari uses a black-hole theme. Standard Safari uses a solar eclipse.

<p align="center">
  <a href="https://github.com/RazorBackRoar/Nexus/releases/latest/download/Nexus.dmg"><strong>Download Nexus.dmg</strong></a>
  ·
  <a href="https://github.com/RazorBackRoar/Nexus/releases">All releases</a>
</p>

![Nexus](docs/screenshots/app.png)

## Features

- Opens selected bookmarks in Safari, including Private Browsing with a pause between tabs
- Quick Save (⌘⇧S) stores a dated card of the current links plus a note
- Colored folders you can filter and reorder
- Copy rich links as HTML that Apple Notes can paste
- Paste URLs, or drop `.txt`, `.csv`, and `.md` files onto the table
- Apple Silicon only

## Install

macOS 14 or later on Apple Silicon.

1. Download [`Nexus.dmg`](https://github.com/RazorBackRoar/Nexus/releases/latest/download/Nexus.dmg)
2. Open the DMG and drag `Nexus.app` to `/Applications`
3. First launch: right-click the app and choose **Open** (ad-hoc signed build)
4. In **System Settings → Privacy & Security → Automation**, allow Nexus to control Safari

## Usage

1. Add bookmarks with `+`, a paste, or a dropped text file
2. Press ⌘⇧S to capture the current links with a timestamp
3. Create folders, save groups, and drag to rearrange
4. Select bookmarks and choose **Open in Safari**
5. Copy formatted links when you want them in Apple Notes

Data lives in `~/Library/Application Support/Nexus/` as `bookmarks_v2.json` and `bookmark_groups.json`.

## Development

```bash
git clone https://github.com/RazorBackRoar/Nexus.git
cd Nexus
swift test
swift run
./scripts/build-mac.sh
```

The package lands at `build/Release/Nexus.dmg`.

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Build and release](BUILD_AND_RELEASE.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [Code of conduct](CODE_OF_CONDUCT.md)

## License

MIT License. See [LICENSE](LICENSE).

Copyright © 2026 RazorBackRoar

If you need me, give me a holler.

<!-- razorcore:runtime:start -->
## Runtime Requirements

For users:
- Download the macOS `.dmg` or `.app` release. Xcode/Swift do not need to be installed.

For developers:
- Toolchain: Swift 6 on Apple Silicon.
- Test: `swift test`
- Run: `swift run`
- Package: `./scripts/build-mac.sh`
<!-- razorcore:runtime:end -->
