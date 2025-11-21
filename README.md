# Nexus

**Safari Bookmark & URL Manager** - v5.0.0

A powerful macOS application for managing Safari bookmarks and batch-opening URLs with a beautiful neon-themed interface.

## Features

- 🌐 **Safari Integration** - Batch open URLs in Safari with one click
- 📑 **Hierarchical Bookmarks** - Organize bookmarks in folders and subfolders
- 🎨 **Themeable UI** - Customizable neon-themed dark interface
- 🔒 **Private Browsing** - Support for private/stealth mode
- ✨ **URL Processing** - Smart URL extraction and validation from text
- 📦 **Export/Import** - Save and load bookmark collections

## Installation

### Quick Install

1. Download `Nexus.dmg` from [Releases](https://github.com/RazorBackRoar/Nexus/releases)
2. Open the DMG file
3. Drag `Nexus.app` to Applications folder
4. **First launch:** Right-click on `Nexus.app` and select "Open"
5. Click "Open" when macOS shows the security warning

### Troubleshooting

If macOS blocks the app, go to:
**System Settings → Privacy & Security** → look for "Nexus.app was blocked" and click "Open Anyway"

You only need to do this once. After that, you can open Nexus normally.

## Requirements

- macOS 11.0 or later
- Python 3.11+ (for development)
- PySide6

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run from source
python src/Main.py

# Build app
./build.sh
```

## License

MIT License - See LICENSE.txt for details

## Author

**RazorBackRoar**

GitHub: [@RazorBackRoar](https://github.com/RazorBackRoar)

---

Built using PySide6
