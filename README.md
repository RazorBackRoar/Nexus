# Nexus

[![CI](https://github.com/RazorBackRoar/Nexus/actions/workflows/ci.yml/badge.svg)](https://github.com/RazorBackRoar/Nexus/actions/workflows/ci.yml)
[![Ruff](https://github.com/RazorBackRoar/Nexus/actions/workflows/ruff.yml/badge.svg)](https://github.com/RazorBackRoar/Nexus/actions/workflows/ruff.yml)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Apple
Silicon](https://img.shields.io/badge/Apple%20Silicon-Native-brightgreen.svg)](https://support.apple.com/en-us/HT211814)
[![PySide6](https://img.shields.io/badge/PySide6-Qt6-orange.svg)](https://doc.qt.io/qtforpython/)

```text
███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
```

> **Native macOS Safari bookmark manager and batch URL opener**
> Organize bookmarks, batch open URLs, and manage your browsing workflow with a
modern, neon-themed interface.

---

## ✨ Features

- 🌐 **Safari Integration** – Batch open URLs in Safari with AppleScript
- 📑 **Hierarchical Bookmarks** – Drag-and-drop folder organization
- 🎨 **Neon-Themed UI** – Customizable dark interface with vibrant accents
- 🔒 **Private Browsing** – One-click stealth/private mode support
- ✨ **Smart URL Extraction** – Find valid links in any pasted text
- 📦 **Export/Import** – Backup collections as JSON
- 🖥️ **Apple Silicon Native** – Optimized for M1/M2/M3 chips

---

## 🚀 Quick Start

### Installation

1. Download the latest `Nexus.dmg` from

   [Releases](https://github.com/RazorBackRoar/Nexus/releases)

2. Drag `Nexus.app` to `/Applications`
3. **First Launch**:

```bash
   # If prompted with "App is damaged":
   sudo xattr -cr /Applications/Nexus.app
```

1. **Grant Permissions**:
   - Go to **System Settings → Privacy & Security → Automation**
   - Enable **Safari** for Nexus (required for opening tabs)

### Usage

1. **Add Bookmarks**: Click "+" or paste URLs directly
2. **Organize**: Create folders, drag and drop to rearrange
3. **Batch Open**: Select multiple bookmarks → Click "Open in Safari"
4. **Extract URLs**: Paste any text containing URLs → Nexus finds them all

---

## 🛠️ Development

This project uses `.razorcore` for build tooling.

### Prerequisites

- Python 3.10+
- macOS 11.0+

### Setup

```bash
git clone <<<<<<<<<<<<<<<<<<<<<<<<<<<https://github.com/RazorBackRoar/Nexus.git>>>>>>>>>>>>>>>>>>>>>>>>>>>
cd Nexus
pip install -r requirements.txt
pip install -e ../.razorcore  # Install build tools
```

### Build & Release

```bash
## Build app and create DMG
razorbuild Nexus

## Create release (auto-commits & tags)
razorcore save Nexus
```

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.
Copyright © 2026 RazorBackRoar
