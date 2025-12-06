# Nexus

```
███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝


## Nexus — Safari Bookmark & URL Manager for macOS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### ⚡ About

Nexus is a powerful native macOS application for managing Safari bookmarks and batch-opening URLs. Features a beautiful neon-themed dark interface with hierarchical bookmark organization.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### ✨ Highlights

- 🌐 **Safari Integration** – Batch open URLs in Safari with one click via AppleScript
- 📑 **Hierarchical Bookmarks** – Organize bookmarks in folders and subfolders
- 🎨 **Neon-Themed UI** – Customizable dark interface with vibrant accent colors
- 🔒 **Private Browsing** – Support for stealth/private browsing mode
- ✨ **Smart URL Processing** – Intelligent URL extraction and validation from raw text
- 📦 **Export/Import** – Save and load bookmark collections as JSON
- 🔍 **URL Extraction** – Paste messy text and extract all valid URLs automatically
- 📋 **Batch Operations** – Open, copy, or export multiple URLs at once
- 🖥️ **Apple Silicon Native** – Optimized for M1/M2/M3/M4 chips

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 📦 Installation

1. Download the latest `Nexus.dmg` from [Releases](https://github.com/RazorBackRoar/Nexus/releases)
2. Mount the DMG → drag `Nexus.app` into `/Applications` → eject
3. First launch (Gatekeeper):

   - **Method A:** Right-click `Nexus.app` → _Open_ → confirm
   - **Method B:**

     ```bash
     sudo xattr -cr /Applications/Nexus.app
     ```

4. **Grant Permissions:** Nexus needs permission to control Safari
   - Go to **System Settings → Privacy & Security → Automation**
   - Enable **Safari** for Nexus

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🚀 Usage

1. **Add Bookmarks:** Click "+" or paste URLs directly
2. **Organize:** Create folders, drag and drop to rearrange
3. **Batch Open:** Select multiple bookmarks → Click "Open in Safari"
4. **Extract URLs:** Paste any text containing URLs → Nexus finds them all
5. **Export:** Save your collection as JSON for backup or sharing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 💻 Requirements

- macOS 11.0 (Big Sur) or later
- Safari (for URL opening feature)
- ~2 GB free disk space
- No Python install needed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🔧 Troubleshooting

- **"App is damaged / Cannot be opened"** – Use the Gatekeeper override above
- **Safari not opening URLs** – Grant Automation permission in System Settings
- **URLs not extracting** – Ensure the text contains valid http:// or https:// links

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🛠️ Building from Source

```bash
# Clone repository
git clone https://github.com/RazorBackRoar/Nexus.git
cd Nexus

# Install dependencies
pip install -r requirements.txt

# Run from source
python src/nexus/main.py

# Build app
./build/scripts/build.sh
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 📜 License

MIT License – see `LICENSE.txt`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🐞 Support

- Issues: <https://github.com/RazorBackRoar/Nexus/issues>
- Source: <https://github.com/RazorBackRoar/Nexus>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🔐 Privacy

Nexus runs 100% locally. No telemetry, no analytics. Only uses AppleScript to communicate with Safari for URL opening.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### 👤 Author

**RazorBackRoar**

GitHub: [@RazorBackRoar](https://github.com/RazorBackRoar)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
