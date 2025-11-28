from pathlib import Path

from setuptools import setup

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def get_project_version(default: str = "0.0.0") -> str:
    pyproject = Path(__file__).resolve().parent / "pyproject.toml"
    if not pyproject.exists():
        return default
    try:
        with pyproject.open("rb") as fp:
            data = tomllib.load(fp)
        return data["project"]["version"]
    except Exception:
        return default


# --- Application Configuration (Single Source of Truth) ---
APP_NAME = "Nexus"
APP_SCRIPT = "src/main.py"
APP_VERSION = get_project_version()
BUNDLE_ID = "com.razorbackroar.nexus.app"
AUTHOR_NAME = "RazorBackRoar"

# --- Resource Files ---
# This list tells py2app which non-code files to include in the final app bundle.
# Format: list of tuples (destination_dir, [source_files])
# Empty string "" means root of Resources folder
DATA_FILES = [("", ["LICENSE.txt"])]

# --- Info.plist Configuration ---
# This dictionary is programmatically populated using the variables from above.
# When the script runs, py2app receives the final, filled-in values.
PLIST = {
    "CFBundleName": APP_NAME,
    "CFBundleDisplayName": APP_NAME,
    "CFBundleVersion": APP_VERSION,
    "CFBundleShortVersionString": APP_VERSION,
    "CFBundleIdentifier": BUNDLE_ID,
    "LSMinimumSystemVersion": "11.0",
    "NSHumanReadableCopyright": f"Copyright © 2025 {AUTHOR_NAME}. All rights reserved.",
    "NSAppleEventsUsageDescription": "Nexus needs permission to control Safari to open your organized URL lists.",
    "LSRequiresNativeExecution": True,  # Force macOS to recognize as Apple Silicon app, not iOS
    "LSApplicationCategoryType": "public.app-category.utilities",  # Categorize as Utilities app
}

# --- py2app Options ---
OPTIONS = {
    "iconfile": "src/assets/icons/Nexus.icns",
    "packages": ["PySide6"],
    "plist": PLIST,
    "bdist_base": "build/temp",
    "dist_dir": "dist",
    "strip": True,
    "argv_emulation": False,  # Disabled - Carbon framework not available on modern macOS
    "includes": [
        "shiboken6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ],
    "excludes": [
        # Exclude tkinter
        "tkinter",
        # Exclude unused PySide6 modules to reduce app size (~200-300MB savings)
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DAnimation",
        "PySide6.Qt3DExtras",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtQuickControls2",
        "PySide6.QtQuickWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtQml",
        "PySide6.QtSensors",
        "PySide6.QtSerialPort",
        "PySide6.QtSql",
        "PySide6.QtTest",
        "PySide6.QtBluetooth",
        "PySide6.QtLocation",
        "PySide6.QtPositioning",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.QtVirtualKeyboard",
        "PySide6.QtWebChannel",
        "PySide6.QtWebSockets",
    ],
}

# --- Setup Definition ---
# The setup() function also uses the variables for consistency.
setup(
    app=[APP_SCRIPT],
    name=APP_NAME,
    author=AUTHOR_NAME,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
