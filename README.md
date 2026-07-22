# Nexus

[![Download](https://img.shields.io/github/v/release/RazorBackRoar/Nexus?style=for-the-badge&label=Download%20DMG&color=d32f2f)](https://github.com/RazorBackRoar/Nexus/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/RazorBackRoar/Nexus/ci.yml?branch=main&style=for-the-badge&label=CI)](https://github.com/RazorBackRoar/Nexus/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blueviolet?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.14-2ea44f?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-Qt6-41cd52?style=for-the-badge&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![macOS](https://img.shields.io/badge/mac%20os-Apple%20Silicon-d32f2f?style=for-the-badge&logo=apple&logoColor=white)](https://support.apple.com/en-us/HT211814)

**Native macOS Safari bookmark manager and batch URL opener.**

Organize bookmarks, batch open URLs, and manage your browsing workflow with a dark native interface.

<p align="center">
  <a href="https://github.com/RazorBackRoar/Nexus/releases/latest/download/Nexus.dmg"><strong>↓ Download Nexus.dmg</strong></a>
  ·
  <a href="https://github.com/RazorBackRoar/Nexus/releases">All releases</a>
</p>

![Nexus](docs/screenshots/app.png)

## Features

- **Safari Integration** — batch open URLs in Safari via AppleScript
- **Hierarchical Bookmarks** — drag-and-drop folder organization
- **Smart URL Extraction** — find valid links in any pasted text
- **Private Browsing** — one-click stealth/private mode support
- **Export / Import** — back up your collections as JSON
- **Apple Silicon Native** — arm64 build optimized for M-series Macs

---

## Install

1. Download [`Nexus.dmg`](https://github.com/RazorBackRoar/Nexus/releases/latest/download/Nexus.dmg)
2. Open the DMG and drag `Nexus.app` to `/Applications`
3. First launch — right-click the app → **Open** to bypass Gatekeeper on the ad-hoc signed build
4. Go to **System Settings → Privacy & Security → Automation** and enable **Safari** for Nexus

---

## Usage

1. **Add Bookmarks** — click `+` or paste URLs directly
2. **Organize** — create folders and drag to rearrange
3. **Batch Open** — select multiple bookmarks → **Open in Safari**
4. **Extract URLs** — paste any block of text and Nexus finds all valid links automatically

---

## Development

### Requirements

- Python 3.14
- macOS 12.0+
- [uv](https://github.com/astral-sh/uv)

### Setup

```bash
git clone https://github.com/RazorBackRoar/Nexus.git
cd Nexus
# Workspace layout: sibling Apps/.razorcore provides editable razorcore
uv sync
uv run python -m nexus.main
```

### Build

```bash
razorbuild Nexus
# Output: dist/Nexus.dmg
```

### Lint & Test

```bash
uv run ruff check .
uv run ty check src --python-version 3.14
uv run pytest tests/ -q
```

---

## Community & docs

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
- Download the macOS `.dmg` or `.app` release. Python does not need to be installed.

For developers:
- Primary development/build target: Python 3.14 with `uv`.
- Source/build target: Python 3.14 only.
- Setup: `uv sync`
- Run: `uv run python -m nexus.main`
<!-- razorcore:runtime:end -->
