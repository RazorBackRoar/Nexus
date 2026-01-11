# Agent Instructions for Nexus

## Project Overview
- **Type**: Native macOS Desktop App (Safari Bookmark Manager)
- **Stack**: Python 3.13+, PySide6 (Qt6)
- **Architecture**: `.razorcore` shared library architecture
- **Build System**: PyInstaller (managed via `razorcore build`)
- **Target**: macOS ARM64 (Apple Silicon)

## Critical Rules
1. **Build System**: ALWAYS use `razorcore build Nexus`. NEVER use `py2app`, `briefcase`, or manual `pyinstaller` commands.
   - The build process uses the **universal build script** in `.razorcore/universal-build.sh`.
   - Settings for DMGs are **global** (hardcoded in universal-build.sh) for consistency.
2. **Shared Library**: Logic common to apps exists in `.razorcore`. Check there before reinventing the wheel.
3. **Assets**: Icons and resources live in `assets/`, NOT `src/resources/`.
4. **Versioning**: Single source of truth is `pyproject.toml`.

## ⚠️ LOCKED DMG SETTINGS - DO NOT MODIFY
These settings are standardized across ALL apps (4Charm, Nexus, Papyrus):

| Setting | Value |
|---------|-------|
| Window Size | 500×320 |
| Window Position | (200, 200) |
| Icon Size | 96px |
| Text Size | 14 |
| App Icon Position | (135, 130) |
| Applications Position | (375, 130) |

**Source**: `.razorcore/DMG_CONFIG.md` and `.razorcore/universal-build.sh` (lines 367-412)

## File Structure
- `pyproject.toml`       # Metadata & Version
- `Nexus.spec`           # PyInstaller Config (Required)
- `assets/`              # Icons (.icns)
- `src/`                 # Source Code
  - `nexus/`
    - `gui/`             # PySide6 Widgets (No .ui files, use code)
    - `core/`            # Business Logic
    - `utils/`           # Utilities

## Qt/PySide6 Guidelines
- **Framework**: PySide6 exclusively.
- **Styling**: Apps use a neon-dark theme. Use `razorcore.styling` widgets when possible.
- **Threading**: Use `razorcore.threading.BaseWorker` for background tasks to avoid freezing UI.
- **Layouts**: Always use standard layouts (QVBoxLayout, QHBoxLayout).

## Development Workflow
1. **Install**: `pip install -r requirements.txt && pip install -e ../.razorcore`
2. **Run**: `python src/nexus/main.py`
3. **Build**: `razorcore build Nexus` (Builds .app + DMG using universal system)
4. **Release**: `razorcore save Nexus` (Auto-commits, bumps version, pushes)

## Coding Standards
- **Imports**: Absolute imports (`from nexus.gui import ...`).
- **Type Hints**: Required for all function signatures.
- **Formatting**: Follows Black/Ruff via `.razorcore` configs.
