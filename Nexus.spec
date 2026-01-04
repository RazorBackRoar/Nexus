# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

APP_NAME = "Nexus"
SPEC_DIR = Path(globals().get("SPECPATH", Path.cwd())).resolve()
PROJECT_ROOT = SPEC_DIR
MAIN_SCRIPT = PROJECT_ROOT / "src" / "nexus" / "main.py"
ICON_FILE = PROJECT_ROOT / "assets" / "icons" / "Nexus.icns"
PYPROJECT = PROJECT_ROOT / "pyproject.toml"


def get_project_version(default: str = "0.0.0") -> str:
    if not PYPROJECT.exists():
        return default
    try:
        with PYPROJECT.open("rb") as fp:
            data = tomllib.load(fp)
        return data["project"]["version"]
    except Exception:
        return default


APP_VERSION = get_project_version()
BUNDLE_ID = "com.razorbackroar.nexus.app"


a = Analysis(
    [str(MAIN_SCRIPT)],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=[
        (str(PROJECT_ROOT / "assets"), "assets"),
        (str(PROJECT_ROOT / "LICENSE"), "."),
    ],
    hiddenimports=[
        "shiboken6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    icon=str(ICON_FILE),
    bundle_identifier=BUNDLE_ID,
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": APP_VERSION,
        "CFBundleShortVersionString": APP_VERSION,
        "LSMinimumSystemVersion": "11.0",
        "LSRequiresNativeExecution": True,
        "LSApplicationCategoryType": "public.app-category.utilities",
        "NSAppleEventsUsageDescription": "Nexus needs permission to control Safari to open your organized URL lists.",
        "NSHumanReadableCopyright": "Copyright © 2026 RazorBackRoar. All rights reserved.",
    },
)
