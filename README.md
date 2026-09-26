# Nexus

Save Safari links in colored folders, then open a bunch of them at once. Private browsing gets a black hole. Regular Safari gets an eclipse.

<p align="center">
  <img src="https://github.com/RazorBackRoar/Nexus/raw/main/docs/screenshots/app.png" alt="Nexus window with bookmark folders and a paste area" width="860">
</p>

<p align="center">

[![Download](https://img.shields.io/github/v/release/RazorBackRoar/Nexus?style=for-the-badge&label=Download%20DMG)](https://github.com/RazorBackRoar/Nexus/releases/latest)
[![macOS](https://img.shields.io/badge/macOS-Apple%20Silicon-2ea44f?style=for-the-badge&logo=apple&logoColor=white)](https://support.apple.com/en-us/HT211814)
[![Swift](https://img.shields.io/badge/Swift-F05138?style=for-the-badge&logo=swift&logoColor=white)](https://swift.org/)

</p>

## Run it

1. Download [Nexus.dmg](https://github.com/RazorBackRoar/Nexus/releases/latest/download/Nexus.dmg)
2. Drag **Nexus.app** into Applications
3. First launch: right-click the app and choose **Open**
4. In **System Settings → Privacy & Security → Automation**, allow Nexus to control Safari

macOS 14 or later on Apple Silicon.

Paste URLs, drop a text file, or press ⌘⇧S to save the current links. Select a folder and open them in Safari.

Bookmarks live in `~/Library/Application Support/Nexus/`.

## What it does

- Open a selection in Safari, including Private Browsing
- Keep folders with their own colors
- Copy links as HTML that Apple Notes can paste
- Import from the clipboard or a `.txt`, `.csv`, or `.md` file

## Build it yourself

```bash
git clone https://github.com/RazorBackRoar/Nexus.git
cd Nexus
swift test
swift run
./scripts/build-mac.sh
```

The DMG lands at `build/Release/Nexus.dmg`.

## License

MIT. See [LICENSE](LICENSE).

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
