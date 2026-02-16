Level 2 Document: Refer to /Users/home/Workspace/Apps/AGENTS.md (Level 1) for global SSOT standards.

# 🌀 Nexus - Safari Bookmark Manager Agent

**Package:** `nexus`
**Version:** 3.3.0
**Context Level:** LEVEL 3 (Application-Specific)

---

## 🏁 GLOBAL AUTHORITY

All standard patterns must follow:
👉 **`/Users/home/Workspace/Apps/MCP.md`**
👉 **`/Users/home/Workspace/Apps/.code-analysis/monorepo-analysis.md`**
👉 **`/Users/home/Workspace/Apps/.code-analysis/essential-queries.md`**
👉 **`/Users/home/Workspace/Apps/.code-analysis/AGENTS.md`**

This file contains **Nexus-specific** overrides and critical implementation details.

When opening this project/workspace, load context in this order:
1. `/Users/home/Workspace/Apps/MCP.md`
2. `/Users/home/Workspace/Apps/.code-analysis/monorepo-analysis.md`
3. `/Users/home/Workspace/Apps/.code-analysis/essential-queries.md`
4. `/Users/home/Workspace/Apps/.code-analysis/AGENTS.md`

---

## 🎯 Quick Context

- **Purpose:** Native macOS Safari bookmark manager with AppleScript automation
- **Primary Tech:** PySide6, plistlib, AppleScript
- **Key Modules:** `bookmarks.py`, `models.py`, `safari_bridge.py`
- **Build Commands:** `nexusbuild` or `razorbuild Nexus`

---

## ⚡ Critical Nexus-Specific Rules

### ⚡ Performance Optimization (Bolt)

- **Agent:** Bolt ⚡
- **Activation:** `bolt` (alias `snake`) or `razorcore bolt`
- **Goal:** < 2s startup, < 50MB bundle
- **Journal:** `.razorcore/bolt/journal.md`

### 1. macOS Permissions (MANDATORY - App Won't Work Without This)

**Full Disk Access is REQUIRED:**

1. Open `System Settings → Privacy & Security → Full Disk Access`
2. Add these applications:
   - ✅ `Terminal.app` (for development)
   - ✅ `Visual Studio Code.app` (if using VS Code)
   - ✅ `Nexus.app` (after building)

**Why:** Safari's `Bookmarks.plist` is protected by macOS security. Without FDA, you'll get:

```python
PermissionError: [Errno 1] Operation not permitted:
'/Users/home/Library/Safari/Bookmarks.plist'
```

**Verification:**

```bash
# Test if FDA is working
ls -la ~/Library/Safari/Bookmarks.plist

# If permission denied, FDA is not granted
# If you see file details, FDA is working
```

### 2. Safari Bookmark File Locations & Formats

```python
from pathlib import Path
import plistlib

class BookmarkManager:

```
"""Handles Safari bookmark file access."""

```text

```
# Modern macOS (Ventura 13.0+)
BOOKMARKS_PATH = Path.home() / "Library/Safari/Bookmarks.plist"

```text

```
def load_bookmarks(self) -> dict:
"""
Load Safari bookmarks from binary plist.

```text

```
⚠️ CRITICAL: Must open in binary mode ('rb')
Modern macOS uses binary plist format, not XML.
"""
try:
with open(self.BOOKMARKS_PATH, 'rb') as f:  # 'rb' not 'r'!
return plistlib.load(f)
except FileNotFoundError:
raise RuntimeError(
"Safari bookmarks not found. "
"Launch Safari at least once to create the file."
)
except PermissionError:
raise RuntimeError(
"Permission denied. Grant Full Disk Access:\n"
"System Settings → Privacy & Security → Full Disk Access"
)

```text

```
def save_bookmarks(self, data: dict):
"""Save modified bookmarks back to Safari."""
# ⚠️ Close Safari before saving to prevent conflicts
with open(self.BOOKMARKS_PATH, 'wb') as f:  # 'wb' not 'w'!
plistlib.dump(data, f)

```text

```

**Plist Structure:**

```python
{

```
'Children': [
{
'Title': 'BookmarksBar',
'Children': [
{'URLString': '<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<https://example.com',>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> 'URIDictionary': {...}},
{'Title': 'Folder', 'Children': [...]}  # Nested folders
]
},
{'Title': 'BookmarksMenu', 'Children': [...]},
{'Title': 'com.apple.ReadingList', 'Children': [...]}
]

```text

}
```

### 3. Data Models (Required Structure)

```python
from dataclasses import dataclass
from typing import List, Union
from uuid import uuid4

@dataclass
class Bookmark:

```
"""Individual bookmark item."""
title: str
url: str
uuid: str = None  # Auto-generate if not provided

```text

```
def **post_init**(self):
if self.uuid is None:
self.uuid = str(uuid4())

```text

```
def to_dict(self) -> dict:
"""Convert to Safari plist format."""
return {
'URLString': self.url,
'URIDictionary': {'title': self.title},
'WebBookmarkUUID': self.uuid,
'WebBookmarkType': 'WebBookmarkTypeLeaf'
}

```text

@dataclass
class BookmarkFolder:

```
"""Folder containing bookmarks/subfolders."""
title: str
children: List[Union['Bookmark', 'BookmarkFolder']]
uuid: str = None

```text

```
def **post_init**(self):
if self.uuid is None:
self.uuid = str(uuid4())

```text

```
def to_dict(self) -> dict:
"""Convert to Safari plist format."""
return {
'Title': self.title,
'Children': [child.to_dict() for child in self.children],
'WebBookmarkUUID': self.uuid,
'WebBookmarkType': 'WebBookmarkTypeList'
}

```text

```

### 4. AppleScript Safari Automation

```python
import subprocess
from typing import List

class SafariBridge:

```
"""Controls Safari via AppleScript."""

```text

```
def open_urls(self, urls: List[str], new_window: bool = False):
"""
Open URLs in Safari.

```text

```
Args:
urls: List of URLs to open
new_window: If True, opens in new Safari window
"""
# Build AppleScript
if new_window:
script = f'''
tell application "Safari"
activate
make new document
set URL of current tab of front window to "{urls[0]}"
end tell
'''
else:
script = f'''
tell application "Safari"
activate
open location "{urls[0]}"
end tell
'''

```text

```
# Execute AppleScript
result = subprocess.run(
['osascript', '-e', script],
capture_output=True,
text=True,
timeout=5
)

```text

```
if result.returncode != 0:
raise RuntimeError(f"AppleScript failed: {result.stderr}")

```text

```
def get_current_url(self) -> str:
"""Get URL of current Safari tab."""
script = '''
tell application "Safari"
return URL of current tab of front window
end tell
'''
result = subprocess.run(
['osascript', '-e', script],
capture_output=True,
text=True
)
return result.stdout.strip()

```text

```

---

## 🏗️ Nexus Project Structure

```text
Nexus/
├── src/nexus/
│   ├── __init__.py              # Contains __version__
│   ├── main.py                  # Entry point (calls print_startup_info)
│   ├── core/
│   │   ├── bookmarks.py         # Plist parsing & bookmark management
│   │   ├── models.py            # Bookmark/BookmarkFolder dataclasses
│   │   └── safari_bridge.py    # AppleScript automation layer
│   ├── gui/
│   │   ├── main_window.py       # Main UI (inherits SpaceBarAboutMixin)
│   │   └── tree_view.py         # Hierarchical bookmark display
│   └── utils/
│       └── url_parser.py        # Smart URL extraction from text
├── assets/
│   └── icons/Nexus.icns         # Application icon (REQUIRED)
├── tests/
│   ├── test_bookmarks.py        # Plist parsing tests
│   └── test_models.py           # Data model tests
├── Nexus.spec                   # PyInstaller config
├── pyproject.toml               # Version SSOT
└── AGENTS.md                    # This file
```

---

## 🔧 Build & Deploy Commands

```bash
# Full release build (app + DMG + Git tag, ~3min)
nexusbuild

# Canonical build entry
razorbuild Nexus

# Push changes (auto-commit, auto-version, auto-tag)
razorpush Nexus

# Run tests
pytest tests/

# Check compliance
razorcheck
```

---

## ✅ Required Workflows

- Run `razorcheck` before committing or opening a PR.
- Use `razorpush Nexus` (or `nexuspush`) for commit, version bump, tag, and push. Do not edit versions manually.
- Build via `nexusbuild` or `razorbuild Nexus`. **Never** run `universal-build.sh` directly.
- Use `razoragents` to sync `AGENTS.md` tables (usually run by `razorpush`).
- If you change `.razorcore` CLI commands or `pyproject.toml`, run `pip install -e ../.razorcore/`.
- **Always run the app after making changes** (`python -m nexus.main`) to visually verify updates before considering any task complete. This is mandatory—do not skip this step.

---

## 🚨 Common Pitfalls & Solutions

### ❌ Error: "PermissionError: Operation not permitted"

**Cause:** Missing Full Disk Access
**Fix:**
1. System Settings → Privacy & Security → Full Disk Access
2. Add Terminal.app, VS Code.app, Nexus.app
3. **Restart Terminal/IDE after granting permission**

### ❌ Error: "FileNotFoundError: Bookmarks.plist"

**Cause:** Safari has never been launched on this Mac
**Fix:** Open Safari once to initialize bookmark file

### ❌ Error: "Invalid plist format" or "UnicodeDecodeError"

**Cause:** Opening binary plist in text mode
**Fix:**

```python
# ❌ WRONG
with open(path, 'r') as f:

```
data = plistlib.load(f)

```text

# ✅ CORRECT
with open(path, 'rb') as f:  # Binary mode!

```
data = plistlib.load(f)

```text

```

### ❌ AppleScript Timeout or "Application isn't running"

**Cause:** Safari not running when automation attempted
**Fix:**

```python
# Check if Safari is running first
result = subprocess.run(

```
['osascript', '-e', 'tell application "System Events" to (name of processes) contains "Safari"'],
capture_output=True,
text=True

```text

)
if 'true' not in result.stdout:

```
# Launch Safari first
subprocess.run(['open', '-a', 'Safari'])
time.sleep(1)  # Wait for launch

```text

```

### ❌ Bookmarks Disappear After Save

**Cause:** Safari was running when plist was modified (file conflict)
**Fix:**

```python
def save_bookmarks(self, data: dict):

```
"""Always close Safari before saving."""
# Warn user to close Safari
subprocess.run(['osascript', '-e', 'tell application "Safari" to quit'])
time.sleep(0.5)

```text

```
# Now safe to save
with open(self.BOOKMARKS_PATH, 'wb') as f:
plistlib.dump(data, f)

```text

```

### ❌ ModuleNotFoundError in Built .app

**Cause:** Missing `hiddenimports` in `Nexus.spec`
**Fix:** Add to spec file:

```python
hiddenimports=[

```
'razorcore.styling',
'razorcore.threading',
'razorcore.appinfo',

```text

]
```

---

## 🧪 Testing Strategy

```bash
# Run all tests
pytest tests/

# Test with coverage
pytest --cov=src/nexus --cov-report=html tests/

# Test plist parsing specifically
pytest tests/test_bookmarks.py::test_parse_binary_plist -v

# Test AppleScript bridge (requires Safari running)
pytest tests/test_safari_bridge.py -v
```

---

## 📚 Related Documentation

- **CodeGraphContext Docs:** `/Users/home/Workspace/Apps/.code-analysis/monorepo-analysis.md`
- **CodeGraphContext Queries:** `/Users/home/Workspace/Apps/.code-analysis/essential-queries.md`
- **Code Analysis Agent Rules:** `/Users/home/Workspace/Apps/.code-analysis/AGENTS.md`
- **CLI Commands:** `/Users/home/Workspace/Apps/Guides/cli_commands.md`
- **CLI Inventory (Full):** `/Users/home/Workspace/Apps/Guides/cli_inventory.md`
- **Nexus Manual:** `/Users/home/Workspace/Apps/Guides/nexus_manual.md`
- **Engineering Hub:** `/Users/home/Workspace/Apps/AGENTS.md` (LEVEL 2)

---

## 🎯 When to Use What

| Scenario | Command/Pattern |
| --- | --- |
| Testing bookmark parsing | `python src/nexus/main.py` |
| Quick .app build for testing | `razorbuild Nexus` |
| Release to production | `nexusbuild` |
| Save work with version bump | `razorpush Nexus` |
| Read bookmarks | Use `plistlib.load()` with `'rb'` mode |
| Modify bookmarks | Close Safari first, then save |
| Control Safari | Use `SafariBridge` AppleScript wrapper |
| Display bookmark tree | Use `BookmarkFolder` recursive model |

## RazorCore Usage

See `/Users/home/Workspace/Apps/.razorcore/AGENTS.md` for the complete public API and safety rules.

<!-- verification check Tue Jan 27 23:52:04 MST 2026 -->
