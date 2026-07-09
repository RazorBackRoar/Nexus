#!/usr/bin/env python3
"""Nexus.

A fully themeable, production-ready PySide6 app with a "neon outline" aesthetic,
hierarchical bookmarks, and powerful Safari automation.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from nexus.core.config import Config, setup_logging
from nexus.gui.main_window import MainWindow
from razorcore.appinfo import print_startup_info


_PACKAGE_DIR = Path(__file__).resolve().parent


def main():
    setup_logging()
    print_startup_info(Config.APP_NAME)
    app = QApplication(sys.argv)
    app.setOrganizationName(Config.ORGANIZATION)
    app.setOrganizationDomain(Config.DOMAIN)
    app.setApplicationName(Config.APP_NAME)

    # Set app icon
    icon_path = _PACKAGE_DIR.parent / "assets" / "icons" / "Nexus.icns"
    if icon_path.exists():
        from PySide6.QtGui import QIcon

        app.setWindowIcon(QIcon(str(icon_path)))

        # macOS: Set Dock icon when running from source
        if sys.platform == "darwin":
            try:
                from AppKit import (  # ty: ignore[unresolved-import]
                    NSApplication,
                    NSImage,
                )

                ns_app = NSApplication.sharedApplication()
                ns_image = NSImage.alloc().initWithContentsOfFile_(str(icon_path))
                if ns_image:
                    ns_app.setApplicationIconImage_(ns_image)
            except ImportError:
                pass  # PyObjC not available, skip dock icon

    window = MainWindow()

    # Ensure window is visible and on screen
    window.show()
    window.raise_()
    window.activateWindow()

    if not window.restored_window_geometry:
        screen = app.primaryScreen()
        if screen is not None:
            geometry = screen.geometry()
            window.move(
                (geometry.width() - window.width()) // 2,
                (geometry.height() - window.height()) // 2,
            )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
